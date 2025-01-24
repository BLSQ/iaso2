import hashlib
import typing

from django.core import exceptions
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import serializers, parsers, status
from rest_framework.exceptions import NotFound
from rest_framework.fields import Field
from rest_framework.response import Response

from iaso.models import FormAttachment, Form, Project
from .common import ModelViewSet, TimestampField
from .forms import HasFormPermission
from .query_params import APP_ID
from hat.menupermissions import models as permission
from ..utils.clamav import scan_uploaded_file_for_virus


class FormAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormAttachment
        fields = ["id", "name", "file", "md5", "form_id", "created_at", "updated_at"]

    form_id: Field = serializers.PrimaryKeyRelatedField(source="form", queryset=Form.objects.all())
    file = serializers.FileField(required=True, allow_empty_file=False)  # field is not required in model
    name = serializers.CharField(read_only=True)
    md5 = serializers.CharField(read_only=True)
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)

    def validate(self, data: typing.MutableMapping):
        form: Form = data["form"]
        if form is None:
            raise serializers.ValidationError("Form cannot be null")

        # validate form (access check)
        permission_checker = HasFormPermission()
        if not permission_checker.has_object_permission(self.context["request"], self.context["view"], form):
            raise serializers.ValidationError({"form_id": "Invalid form id"})

        return data

    def create(self, validated_data):
        form: Form = validated_data["form"]
        file: InMemoryUploadedFile = validated_data["file"]

        is_safe, details = scan_uploaded_file_for_virus(file)
        if not is_safe:
            raise exceptions.ValidationError({"file": [details]})
        try:
            previous_attachment = FormAttachment.objects.get(name=file.name, form=form)
            previous_attachment.file = file
            previous_attachment.md5 = self.md5sum(file)
            previous_attachment.save()
            return previous_attachment
        except FormAttachment.DoesNotExist:
            return FormAttachment.objects.create(form=form, name=file.name, file=file, md5=self.md5sum(file))
        except Exception as e:
            # putting the error in an array to prevent front-end crash
            raise exceptions.ValidationError({"file": [e]})

    @staticmethod
    def md5sum(file: File):
        md5 = hashlib.md5()
        for chunk in file.chunks():
            md5.update(chunk)
        return md5.hexdigest()


class HasFormAttachmentPermission(HasFormPermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if not self.has_permission(request, view):
            return False

        ok_forms = Form.objects_include_deleted.filter_for_user_and_app_id(
            request.user, request.query_params.get("app_id")
        )

        return ok_forms.filter(id=obj.form_id).exists()


class FormAttachmentsViewSet(ModelViewSet):
    f"""Form Attachments API

    Read-only methods are accessible to anonymous users. All other actions are restricted to authenticated users
    having the "{permission.FORMS}"  permission.

    GET /api/formattachments/?form_id=<form_id>
    GET /api/formattachments/<id>/
    POST /api/formattachments/
    DELETE /api/formattachments/<id>/
    """

    permission_classes = [HasFormAttachmentPermission]
    serializer_class = FormAttachmentSerializer
    queryset = FormAttachment.objects.all()
    ordering_fields = ["order"]
    parser_classes = (parsers.MultiPartParser, parsers.JSONParser)
    http_method_names = ["get", "post", "head", "delete", "options", "trace"]

    def get_queryset(self):
        if self.request.user.is_anonymous:
            app_id = self.request.query_params.get(APP_ID)
            if app_id is not None:
                try:
                    Project.objects.get_for_user_and_app_id(self.request.user, app_id)
                    queryset = FormAttachment.objects.filter(form__projects__app_id=app_id)
                except Project.DoesNotExist:
                    raise NotFound(f"Project not found for {app_id}")
            else:
                queryset = FormAttachment.objects.none()

        else:
            profile = self.request.user.iaso_profile
            queryset = FormAttachment.objects.filter(form__projects__account=profile.account)

        orders = self.request.query_params.get("order", "updated_at").split(",")
        # We don't send attachments for deleted forms
        queryset = queryset.filter(form__deleted_at=None)
        form_id = self.request.query_params.get("form_id", None)
        if form_id:
            try:
                Form.objects.get(id=form_id)
                queryset = queryset.filter(form__id=form_id)
            except Form.DoesNotExist:
                raise NotFound(f"Form not found for {form_id}")

        queryset = queryset.order_by(*orders)
        return queryset.distinct()

    def delete(self, request, pk=None):
        attachment: FormAttachment = FormAttachment.objects.get(id=pk)
        if attachment is None:
            raise NotFound("Form attachment not found")
        attachment.file.delete()
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
