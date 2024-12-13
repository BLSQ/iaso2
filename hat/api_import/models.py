from django.contrib.auth.models import User

from django.db import models

from django.db.models import CASCADE

IMPORT_TYPE = (
    ("orgUnit", "Org Unit"),
    ("instance", "Form instance"),
    ("bulk", "Bulk Org Units and Instances"),
    ("storageLog", "Storage logs"),
)


class APIImport(models.Model):
    """This model is used to log API call from the mobile app

    The idea is that the mobile app user may not have great internet connection where they are
    so in case of import problem we can fix it server side and not ask them to upload again.
    """

    class Meta:
        db_table = "vector_control_apiimport"

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User, on_delete=CASCADE, null=True, related_name="apiimports"
    )  # Null only when importing from CLI
    import_type = models.TextField(max_length=25, choices=IMPORT_TYPE, null=True, blank=True)
    json_body = models.JSONField()
    headers = models.JSONField(null=True, blank=True)
    has_problem = models.BooleanField(default=False)
    exception = models.TextField(blank=True, default="")

    def __str__(self):
        return "{} - {} - {} - {}".format(
            self.id,
            self.user,
            self.import_type,
            self.created_at,
        )

    def as_dict(self):
        res = {
            "id": self.id,
            "user": self.user.username,
            "created_at": self.created_at,
            "type": self.import_type,
        }

        if self.import_type == "trap":
            res["trap_count"] = self.trap_set.count()
        elif self.import_type == "catch":
            res["catch_count"] = self.catch_set.count()
        elif self.import_type == "target":
            res["target_count"] = self.target_set.count()
        return res
