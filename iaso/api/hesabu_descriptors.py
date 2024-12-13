import json
import os

from rest_framework import status, permissions
from rest_framework import viewsets
from rest_framework.response import Response

from iaso.models import DataSource


class HesabuDescriptorsViewSet(viewsets.ViewSet):
    """Hesabu descriptors API

    This API is restricted to authenticated users (no specific permission check)

    GET /api/datasources/<id>/hesabudescriptors
    """

    resource = "hesabudescriptors"
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, datasource_id, format="json"):
        sources = DataSource.objects.all()
        profile = request.user.iaso_profile
        sources = sources.filter(projects__account=profile.account, id=datasource_id)
        data_source = sources.all()[0]

        credentials = data_source.credentials

        if not credentials:
            return Response({"error": "no credentials configured"}, status=status.HTTP_501_NOT_IMPLEMENTED)

        return Response({"hesabudescriptors": [load_fixture_response("fixtures/hesabu.dhis2.fbrcameroun.org.json")]})


def load_fixture_response(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding="utf-8") as f:
        document = json.load(f)
        return document
