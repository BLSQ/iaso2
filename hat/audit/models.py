import json
import uuid

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import models

PROFILE_API = "profile_api"
PROFILE_API_BULK = "profile_api_bulk"
PASSWORD_API = "password_api"
PATIENT_API = "patient_api"
ORG_UNIT_API = "org_unit_api"
ORG_UNIT_CHANGE_REQUEST = "org_unit_change_request"
ORG_UNIT_API_BULK = "org_unit_api_bulk"
GROUP_SET_API = "group_set_api"
INSTANCE_API = "instance_api"
FORM_API = "form_api"
GPKG_IMPORT = "gpkg_import"
CAMPAIGN_API = "campaign_api"
PAYMENT_API_BULK = "payment_api_bulk"
PAYMENT_API = "payment_api"
PAYMENT_LOT_API = "payment_lot_api"
ORG_UNIT_CHANGE_REQUEST_API = "org_unit_change_request_api"
ORG_UNIT_CHANGE_REQUEST_CONFIGURATION_API = "org_unit_change_request_configuration_api"
DJANGO_ADMIN = "django_admin"
BULK_UPLOAD = "bulk_upload"
BULK_UPLOAD_MERGED_ENTITY = "bulk_upload_merged_entity"
ENTITY_DUPLICATE_MERGE = "entity_duplicate_merge"
ENTITY_API = "entity_api"


def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    shared_keys = d1_keys.intersection(d2_keys)
    added = d2_keys - d1_keys
    removed = d1_keys - d2_keys
    modified_values = {k: {"before": d1.get(k), "after": d2.get(k)} for k in shared_keys if d1[k] != d2[k]}
    added_values = {k: {"before": None, "after": d2[k]} for k in added}
    removed_values = {k: {"before": d1[k], "after": None} for k in removed}
    return {"added": added_values, "removed": removed_values, "modified": modified_values}


class IasoJsonEncoder(json.JSONEncoder):
    """This Encoder is needed for object that use UUID as their primary id
    e.g. Campaign"""

    def default(self, o):
        if isinstance(o, uuid.UUID):
            return str(o)
        return json.JSONEncoder.default(self, o)


class Modification(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    # This is a charField and not a number field so it can also fit uuid
    object_id = models.CharField(max_length=40, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")
    past_value = models.JSONField(encoder=IasoJsonEncoder)
    new_value = models.JSONField(encoder=IasoJsonEncoder)
    source = models.TextField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{} - {} - {} - {}".format(
            self.content_type,
            self.object_id,
            self.user,
            self.created_at,
        )

    def as_dict(self):
        return {
            "id": self.id,
            "content_type": self.content_type.app_label,
            "object_id": self.object_id,
            "past_value": self.past_value,
            "new_value": self.new_value,
            "source": self.source,
            "user": self.user.iaso_profile.as_dict() if self.user else None,
            "created_at": self.created_at,
        }

    def as_list(self, fields):
        dict_list = {
            "id": self.id,
            "content_type": self.content_type.app_label,
            "object_id": self.object_id,
            "source": self.source,
            "user": self.user.iaso_profile.as_short_dict() if self.user else None,
            "created_at": self.created_at,
        }
        if "past_value" in fields:
            dict_list["past_value"] = self.past_value
        if "new_value" in fields:
            dict_list["new_value"] = self.new_value
        if "field_diffs" in fields:
            dict_list["field_diffs"] = self.field_diffs()

        return dict_list

    def field_diffs(self):
        past_values = self.past_value or []
        new_values = self.new_value or []
        past_value = past_values[0] if len(past_values) > 0 else {}
        new_value = new_values[0] if len(new_values) > 0 else {}
        past_fields = past_value.get("fields") or {}
        new_fields = new_value.get("fields") or {}
        return dict_compare(past_fields, new_fields)


def log_modification(v1, v2, source, user=None):
    modification = Modification()
    modification.past_value = []
    modification.new_value = []
    if v1:
        modification.object_id = v1.id
        modification.past_value = json.loads(serializers.serialize("json", [v1]))
    elif v2:
        modification.object_id = v2.id
    if v2:
        modification.content_object = v2
        modification.new_value = json.loads(serializers.serialize("json", [v2]))
    elif v1:
        modification.content_object = v1
    modification.source = source
    modification.user = user
    modification.save()
    return modification
