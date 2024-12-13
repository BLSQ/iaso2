import typing
from uuid import uuid4

from django.contrib.auth.models import User, AnonymousUser
from django.db import models


class ProjectQuerySet(models.QuerySet):
    def get_for_user_and_app_id(
        self, user: typing.Optional[typing.Union[User, AnonymousUser]], app_id: typing.Optional[str]
    ):
        """Attempt to find a valid project to which the user has access, and that corresponds to the
        provided app_id. If the user is not authenticated, he can still access the project if it does not
        require authentication.

        Raises a Project.DoesNotExist exception if no valid project can be found.

        :param user: User
        :param app_id: str
        """

        if app_id is not None:
            try:
                project = self.get(app_id=app_id)
                if (
                    user is None
                    or not project.needs_authentication
                    or (
                        user.is_authenticated
                        and user.iaso_profile is not None
                        and project.account.id == user.iaso_profile.account.id
                    )
                ):
                    return project
            except self.model.DoesNotExist:  # we want to launch a custom exception message
                pass

        raise self.model.DoesNotExist(f"Could not find project for user {user} and app_id {app_id}")


ProjectManager = models.Manager.from_queryset(ProjectQuerySet)


class Project(models.Model):
    """A data collection project, associated with a single mobile application"""

    name = models.TextField(null=False, blank=False)
    forms = models.ManyToManyField("Form", blank=True, related_name="projects")
    account = models.ForeignKey("Account", on_delete=models.DO_NOTHING, null=True, blank=True)
    app_id = models.TextField(null=True, blank=True)
    needs_authentication = models.BooleanField(default=False)
    feature_flags = models.ManyToManyField("FeatureFlag", related_name="+", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    external_token = models.UUIDField(default=uuid4, null=True)
    min_version = models.IntegerField(null=True, blank=False)
    redirection_url = models.URLField(null=True, blank=True)

    objects = ProjectManager()

    def __str__(self):
        return "{} ".format(self.name)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "app_id": self.app_id}

    def has_feature(self, feature_code):
        return self.feature_flags.filter(code=feature_code).exists()
