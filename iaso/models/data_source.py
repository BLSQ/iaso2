from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.contrib.auth.models import AnonymousUser, User
import typing


class DataSource(models.Model):
    """DataSources allow linking multiple things imported from the same source (DHIS2, CSV, ...)"""

    name = models.CharField(max_length=255, unique=True)
    read_only = models.BooleanField(default=False)
    projects = models.ManyToManyField("Project", related_name="data_sources", blank=True)
    credentials = models.ForeignKey(
        "ExternalCredentials",
        on_delete=models.SET_NULL,
        related_name="data_sources",
        null=True,
        blank=True,
    )

    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    default_version = models.ForeignKey("SourceVersion", null=True, blank=True, on_delete=models.SET_NULL)
    tree_config_status_fields = ArrayField(
        models.CharField(max_length=30, blank=True, choices=[]),
        default=list,
        blank=True,
        help_text="List of statuses used for display configuration of the OrgUnit tree.",
    )
    public = models.BooleanField(default=False)

    def __str__(self):
        return "{} ".format(self.name)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Override `__init__` to avoid a circular import.
        # This could be replaced by a callable in Django ≥ 5.
        # https://docs.djangoproject.com/en/5.0/releases/5.0/#more-options-for-declaring-field-choices
        from iaso.models import OrgUnit

        self._meta.get_field("tree_config_status_fields").base_field.choices = OrgUnit.VALIDATION_STATUS_CHOICES

    def clean(self, *args, **kwargs):
        super().clean()
        self.tree_config_status_fields = list(set(self.tree_config_status_fields))

    def as_dict(self):
        versions = SourceVersion.objects.filter(data_source_id=self.id)
        return {
            "name": self.name,
            "description": self.description,
            "id": self.id,
            "url": self.credentials.url if self.credentials else None,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
            "versions": [v.as_dict_without_data_source() for v in versions],
            "tree_config_status_fields": self.tree_config_status_fields,
        }

    def as_small_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
            "tree_config_status_fields": self.tree_config_status_fields,
        }

    def as_list(self):
        return {"name": self.name, "id": self.id}


class SourceVersionQuerySet(models.QuerySet):
    def filter_for_user(self, user: typing.Union[User, AnonymousUser, None]):
        queryset = self
        if user and user.is_anonymous:
            return self.none()

        if user and user.is_authenticated:
            queryset = queryset.filter(data_source__projects__account=user.iaso_profile.account).distinct()

        return queryset


SourceVersionManager = models.Manager.from_queryset(SourceVersionQuerySet)


class SourceVersion(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="versions")
    number = models.IntegerField()
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SourceVersionManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["data_source", "number"], name="unique_number_data_source_version")
        ]

    def __str__(self):
        return "%s %d" % (self.data_source, self.number)

    def as_dict(self):
        return {
            "data_source": self.data_source.as_dict(),
            "number": self.number,
            "description": self.description,
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
        }

    def as_small_dict(self):
        return {
            "data_source": self.data_source.as_small_dict(),
            "number": self.number,
            "description": self.description,
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
        }

    def as_list(self):
        return {
            "data_source": self.data_source.as_list(),
            "number": self.number,
            "id": self.id,
        }

    def as_dict_without_data_source(self):
        return {
            "number": self.number,
            "description": self.description,
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
            "org_units_count": self.orgunit_set.count(),
        }

    def as_report_dict(self):
        report = {}
        report["org_units"] = self.orgunit_set.count()
        report["org_units_with_location"] = self.orgunit_set.exclude(location=None).count()
        report["org_units_with_shapes"] = self.orgunit_set.filter(simplified_geom__isnull=False).count()
        org_unit_types = self.orgunit_set.values_list("org_unit_type__name", "org_unit_type__id").distinct()
        org_unit_types_report = {}
        for t in org_unit_types:
            name, ident = t
            org_unit_types_report[name] = self.orgunit_set.filter(org_unit_type_id=ident).count()
        report["types"] = org_unit_types_report
        group_report = {}
        groups = self.orgunit_set.values_list("groups__name", "groups__id").distinct()
        for group in groups:
            name, ident = group
            group_report[name] = self.orgunit_set.filter(groups__id=ident).count()
        report["groups"] = group_report
        return report
