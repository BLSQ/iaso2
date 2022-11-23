# TODO: need better type annotations in this file
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from iaso.models import Entity, Instance, OrgUnit, Account


class StorageDevice(models.Model):
    """
    A storage device used by the mobile application

    For the first use-case (current situation), storage devices are NFC cards that are linked to an entity (a person).

    We'd like to keep that flexible (potentially, other storage devices type could be used for other purposes), so it's
    important to keep this model pretty generic (business logic and specific data and logic pushed to as much as possible
    to StorageLogEntry and to the API).

    StorageDevices are linked to an account, only users from the correct account can see/use/edit them.
    """

    NFC = "NFC"
    USB = "USB"
    SD = "SD"

    STORAGE_TYPE_CHOICES = [
        (NFC, "NFC"),
        (USB, "USB"),
        (SD, "SD"),
    ]

    OK = "OK"
    BLACKLISTED = "BLACKLISTED"

    STATUS_CHOICES = [
        (OK, "OK"),
        (BLACKLISTED, "BLACKLISTED"),
    ]

    # Reasons a Device can be blacklisted
    STOLEN = "STOLEN"
    LOST = "LOST"
    DAMAGED = "DAMAGED"
    ABUSE = "ABUSE"
    OTHER = "OTHER"

    STATUS_REASON_CHOICES = [
        (STOLEN, "STOLEN"),
        (LOST, "LOST"),
        (DAMAGED, "DAMAGED"),
        (ABUSE, "ABUSE"),
        (OTHER, "OTHER"),
    ]

    # A unique identifier for the storage device in a given account. It is provided to the backend by the mobile app,
    # the first time a StorageLogEntry is created for the customer_chosen_id, type, account triplet.
    # (the ID is scoped by type, this is visible in API URLs such as .../{storage_type}/{storage_id}/...)
    # At the database level, the real PK is the Django autogenerated one, but it is not visible to the users.
    customer_chosen_id = models.CharField(max_length=255)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    type = models.CharField(max_length=8, choices=STORAGE_TYPE_CHOICES)

    # Status-related fields
    # Devices can be blacklisted, and in that case it's interesting to keep details in status_* fields
    # CAUTION: do not change those fields directly, use the change_status() method instead
    status = models.CharField(max_length=64, choices=STATUS_CHOICES, default=OK)
    status_reason = models.CharField(max_length=64, choices=STATUS_REASON_CHOICES, blank=True)
    status_comment = models.TextField(blank=True)
    status_updated_at = models.DateTimeField(blank=True, null=True)

    org_unit = models.ForeignKey(OrgUnit, on_delete=models.SET_NULL, null=True, blank=True)
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def change_status(self, new_status: str, reason: str, comment: str, performed_by: User) -> None:
        # TODO: this method is tested indirectly via the API but would deserve a proper, more detailed unit test
        """
        Change the status of the device, and add a log entry for this
        """
        self.status = new_status
        self.status_reason = reason
        self.status_comment = comment
        self.status_updated_at = timezone.now()
        self.save()

        StorageLogEntry.objects.create(
            device=self,
            operation_type=StorageLogEntry.CHANGE_STATUS,
            performed_by=performed_by,
            performed_at=timezone.now(),
            status=new_status,
            status_reason=reason,
            status_comment=comment,
        )

    def __str__(self):
        return f"{self.customer_chosen_id} ({self.type})"

    class Meta:
        unique_together = ("customer_chosen_id", "account", "type")


class StorageLogEntryManager(models.Manager):
    # TODO: this manager method deserves its own unit tests and proper type annotations
    def create_and_update_device(
        self,
        log_id,
        device,
        operation_type,
        performed_at,
        user,
        concerned_orgunit,
        concerned_entity,
        concerned_instances,
    ) -> None:
        """
        Create a new StorageLogEntry, and perform StorageDevice-related operations:

        - update the device, so it is linked to the org unit and entity referenced in the log entry
        - if the log entry is of type WRITE_PROFILE to a new Storage device, blacklist old devices for the same entity

        This is the preferred method to create new log entries. It is assumed the StorageDevice already exists when this
        method is called.
        """

        log_entry = self.create(
            id=log_id,
            device=device,
            operation_type=operation_type,
            performed_at=performed_at,
            performed_by=user,
            org_unit=concerned_orgunit,
            entity=concerned_entity,
        )

        log_entry.instances.set(concerned_instances)

        # We update the orgunit and entity of the device to reflect what was pushed as the last log
        device.entity = concerned_entity
        device.org_unit = concerned_orgunit
        device.save()

        # Blacklist old devices for the same entity
        if operation_type == StorageLogEntry.WRITE_PROFILE:
            old_devices = StorageDevice.objects.filter(entity=concerned_entity).exclude(id=device.id)
            for old_device in old_devices:
                old_device.change_status(
                    new_status=StorageDevice.BLACKLISTED,
                    reason=StorageDevice.OTHER,
                    comment=f"Profile was written on {device.customer_chosen_id} on {performed_at}",
                    performed_by=user,
                )


class StorageLogEntry(models.Model):
    """
    This model keeps track of all the operations that were performed on a storage device, this is important for
    auditability reasons.

    Realistically, many fields on this model are probably specific to our first use-case (NFC cards linked to people in
    entities): operations, link to entity and org_unit, etc.

    In the current implementation/use-case, a card is linked to an entity (= a person), and store:
    - a profile (metadata about the person)
    - a list of RECORDS (that represent visits to this person), as records in a circular buffer
    Possible operations are:

    - WRITE_PROFILE: when a profile is written on the storage device, this automatically links the device to the entity
    (that represents a person).
    - RESET: used to reset the storage device. This operation will also wipe the profile, and therefore nullify the
    link to the entity.
    - READ: all data is read from the card (profile + all records)
    - WRITE_RECORD: a new record is written on the storage device
    - CHANGE_STATUS: the status of the storage device is changed (e.g. from "OK" to "BLACKLISTED"). This is cannot be
    done from the mobile app on the field, but via a manager using the web interface.
    """

    WRITE_PROFILE = "WRITE_PROFILE"
    RESET = "RESET"
    READ = "READ"
    WRITE_RECORD = "WRITE_RECORD"
    CHANGE_STATUS = "CHANGE_STATUS"

    OPERATION_TYPE_CHOICES = [
        (WRITE_PROFILE, "WRITE_PROFILE"),
        (RESET, "RESET"),
        (READ, "READ"),
        (WRITE_RECORD, "WRITE_RECORD"),
        (CHANGE_STATUS, "CHANGE_STATUS"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(StorageDevice, on_delete=models.CASCADE, related_name="log_entries")
    operation_type = models.CharField(max_length=32, choices=OPERATION_TYPE_CHOICES)
    # when as te data read/written on the storage device. This is chosen by the mobile app, that can happen earlier than
    # when the backend knows about it (not true for CHANGE_STATUS since this is performed in Django, not on the mobile).
    performed_at = models.DateTimeField()
    performed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    # Multiple instances/submissions can be saved on a StorageDevice
    instances = models.ManyToManyField(Instance, blank=True, related_name="storage_log_entries")
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.SET_NULL, null=True, blank=True)
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True)

    # For traceability reasons, we keep track of the status and reason at each log entry
    status = models.CharField(max_length=64, choices=StorageDevice.STATUS_CHOICES, blank=True)
    status_reason = models.CharField(max_length=64, choices=StorageDevice.STATUS_REASON_CHOICES, blank=True)
    status_comment = models.TextField(blank=True)

    objects = StorageLogEntryManager()

    class Meta:
        ordering = ["-performed_at"]
        verbose_name_plural = "storage log entries"
