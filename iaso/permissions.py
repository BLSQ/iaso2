from rest_framework import permissions
from rest_framework.exceptions import NotAuthenticated

from iaso.api.serializers import AppIdSerializer
from iaso.models import Project


class ReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return False


class IsAuthenticatedOrReadOnlyWhenNoAuthenticationRequired(permissions.IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        app_id = AppIdSerializer(data=request.query_params).get_app_id(raise_exception=False)
        if app_id is None:
            return super().has_permission(request, view)

        try:
            project = Project.objects.get(app_id=app_id)
        except Project.DoesNotExist:
            return super().has_permission(request, view)

        if not bool(request.user and request.user.is_authenticated):
            if project.needs_authentication:
                raise NotAuthenticated()
        elif request.user.iaso_profile.account.id != project.account.id:
            raise NotAuthenticated()

        return super().has_permission(request, view)
