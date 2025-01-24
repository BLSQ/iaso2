from django.http import HttpResponse
from qr_code.qrcode.maker import make_qr_code_image
from qr_code.qrcode.utils import QRCodeOptions
from rest_framework import filters, permissions, status
from rest_framework.decorators import action


from iaso.models import Project
from .serializers import ProjectSerializer
from ..common import ModelViewSet


class ProjectsViewSet(ModelViewSet):
    """Projects API

    This API is restricted to authenticated users.

    GET /api/projects/
    GET /api/projects/<id>
    """

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["app_id", "name"]
    serializer_class = ProjectSerializer
    results_key = "projects"
    http_method_names = ["get", "head", "options", "trace"]

    def get_queryset(self):
        """Always filter the base queryset by account"""

        return Project.objects.filter(account=self.request.user.iaso_profile.account).filter_on_user_projects(
            self.request.user
        )

    @action(detail=True, methods=["get"])
    def qr_code(self, request, *args, **kwargs):
        """Returns the qrcode image to configure the mobile application."""
        project = self.get_object()
        return HttpResponse(
            status=status.HTTP_200_OK,
            content_type="image/png",
            content=make_qr_code_image(
                data='{"url": "' + request.build_absolute_uri("/") + '", "app_id": "' + project.app_id + '"}',
                qr_code_options=QRCodeOptions(size="S", image_format="png", error_correction="L"),
            ),
        )
