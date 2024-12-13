from uuid import uuid4

from django.conf import settings
from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils.translation import gettext_lazy as _


class Device(models.Model):
    imei = models.CharField(max_length=250, null=True, blank=True)
    test_device = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    projects = models.ManyToManyField("Project", related_name="devices", blank=True)

    def __str__(self):
        return "{} ".format(self.imei)

    def as_dict(self):
        return {
            "imei": self.imei,
            "test_device": self.test_device,
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
        }


class DeviceOwnership(models.Model):
    device = models.ForeignKey("Device", on_delete=models.CASCADE)
    project = models.ForeignKey("Project", blank=True, null=True, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start = models.DateTimeField(auto_now_add=True)
    end = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} - {}".format(self.device, self.user)

    def as_dict(self):
        return {
            "device": self.device.as_dict(),
            "user": self.user.iaso_profile.as_short_dict(),
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
        }


class DevicePosition(models.Model):
    CAR = "car"
    FOOT = "foot"
    TRUCK = "truck"

    TRANSPORT_TYPE_CHOICES = ((CAR, _("Car")), (FOOT, _("Foot")), (TRUCK, _("Truc")))

    uuid = models.UUIDField(default=uuid4, unique=True)
    device = models.ForeignKey("Device", on_delete=models.CASCADE)
    location = PointField(dim=3, srid=4326)
    transport = models.CharField(max_length=32, choices=TRANSPORT_TYPE_CHOICES)
    accuracy = models.DecimalField(decimal_places=2, max_digits=7)
    captured_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def latitude(self):
        return self.location.y if self.location is not None else None

    @property
    def longitude(self):
        return self.location.x if self.location is not None else None

    @property
    def altitude(self):
        return self.location.z if self.location is not None else None

    def __str__(self):
        return str(self.uuid) + " - " + str(self.device)
