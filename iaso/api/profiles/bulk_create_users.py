import csv
import io

import pandas as pd
import phonenumbers

from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import serializers, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from django.contrib.auth.models import User, Permission, Group
from django.contrib.auth.password_validation import validate_password
from django.core import validators
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import FileResponse

from hat.audit.models import PROFILE_API_BULK
from hat.menupermissions import models as permission
from iaso.api.profiles.audit import ProfileAuditLogger
from iaso.models import BulkCreateUserCsvFile, Profile, OrgUnit, OrgUnitType, UserRole, Project
from iaso.utils.module_permissions import account_module_permissions

BULK_CREATE_USER_COLUMNS_LIST = [
    "username",
    "password",
    "email",
    "first_name",
    "last_name",
    "orgunit",
    "orgunit__source_ref",
    "profile_language",
    "dhis2_id",
    "organization",
    "permissions",
    "user_roles",
    "projects",
    "phone_number",
    "editable_org_unit_types",
]


class BulkCreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkCreateUserCsvFile
        fields = ["file"]
        read_only_fields = ["created_by", "created_at", "account"]


class HasUserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.has_perm(permission.USERS_ADMIN) or request.user.has_perm(permission.USERS_MANAGED):
            return True
        return False


class BulkCreateUserFromCsvViewSet(ModelViewSet):
    """Api endpoint to bulkcreate users and profiles from a CSV File.

    Mandatory columns are : ["username", "password", "email", "first_name", "last_name", "orgunit", "profile_language", "dhis2_id", "projects", "permissions", "user_roles", "projects"]

    Email, dhis2_id, permissions, profile_language and org_unit are not mandatory, but you must keep the columns.

    Sample csv input:

    username,password,email,first_name,last_name,orgunit,profile_language,permissions,dhis2_id,user_role,projects

    john,j0hnDoei5f@mous#,johndoe@bluesquarehub.com,John,D.,KINSHASA,fr,"iaso_submissions, iaso_forms",Enc73jC3, manager, "oms, RDC"

    You can add multiples permissions for the same user : "iaso_submissions, iaso_forms"
    You can add multiples org_units for the same user by ID or Name : "28334, Bas Uele, 9999"

    It's a better practice and less error-prone to use org_units IDs instead of names.


    The permissions are :

    "iaso_forms",

    "iaso_submissions",

    "iaso_mappings",

    "iaso_completeness",

    "iaso_org_units",

    "iaso_links",

    "iaso_users",

    "iaso_projects",

    "iaso_sources",

    "iaso_data_tasks",
    """

    result_key = "file"
    remove_results_key_if_paginated = True
    permission_classes = [HasUserPermission]

    def get_serializer_class(self):
        return BulkCreateUserSerializer

    def get_queryset(self):
        queryset = BulkCreateUserCsvFile.objects.none()

        return queryset

    @staticmethod
    def has_only_user_managed_permission(request):
        if not request.user.has_perm(permission.USERS_ADMIN) and request.user.has_perm(permission.USERS_MANAGED):
            return True
        return False

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user_created_count = 0

        has_geo_limit = False
        user_editable_org_unit_type_ids = set()
        if self.has_only_user_managed_permission(request):
            user_editable_org_unit_type_ids = request.user.iaso_profile.get_editable_org_unit_type_ids()
            has_geo_limit = True

        if request.FILES:
            # Retrieve and check the validity and format of the CSV File
            try:
                user_csv = request.FILES["file"]
                user_csv_decoded = user_csv.read().decode("utf-8")
                csv_str = io.StringIO(user_csv_decoded)
                delimiter = ";" if ";" in user_csv_decoded else ","
                reader = csv.reader(csv_str, delimiter=delimiter)
                """In case the delimiter is " ; " we must ensure that the multiple value can be read so we replace it
                    with a " * " instead of " , " """
                if delimiter == ";":
                    new_reader = []
                    for row in reader:
                        new_row = [cell.replace(",", "*") for cell in row]
                        new_reader.append(new_row)
                    reader = new_reader
                pd.read_csv(io.BytesIO(csv_str.getvalue().encode()), delimiter=delimiter)
            except UnicodeDecodeError as e:
                raise serializers.ValidationError({"error": f"Operation aborted. Error: {e}"})
            except pd.errors.ParserError as e:
                raise serializers.ValidationError({"error": f"Invalid CSV File. Error: {e}"})
            importer_user = request.user
            importer_account = request.user.iaso_profile.account
            importer_access_ou = OrgUnit.objects.filter_for_user_and_app_id(importer_user).only("id")
            csv_indexes = []
            file_instance = BulkCreateUserCsvFile.objects.create(
                file=user_csv, created_by=importer_user, account=importer_account
            )
            value_splitter = "," if delimiter == "," else "*"
            file_instance.save()
            audit_logger = ProfileAuditLogger()
            for i, row in enumerate(reader):
                if i > 0 and not set(BULK_CREATE_USER_COLUMNS_LIST).issubset(csv_indexes):
                    missing_elements = set(BULK_CREATE_USER_COLUMNS_LIST) - set(csv_indexes)
                    raise serializers.ValidationError(
                        {
                            "error": f"Something is wrong with your CSV File. Possibly missing {missing_elements} column(s)."
                        }
                    )
                org_units_list = set()
                user_roles_list = []
                user_groups_list = []
                projects_instance_list = []
                if i > 0:
                    email_address = True if row[csv_indexes.index("email")] else None
                    if email_address:
                        try:
                            validators.validate_email(row[csv_indexes.index("email")])
                        except ValidationError:
                            raise serializers.ValidationError(
                                {
                                    "error": "Operation aborted. Invalid Email at row : {}. Fix the error and try "
                                    "again.".format(i)
                                }
                            )
                    try:
                        try:
                            user = User.objects.create(
                                username=row[csv_indexes.index("username")],
                                first_name=row[csv_indexes.index("first_name")],
                                last_name=row[csv_indexes.index("last_name")],
                                email=row[csv_indexes.index("email")],
                            )
                            validate_password(row[csv_indexes.index("password")], user)
                            user.set_password(row[csv_indexes.index("password")])
                            user.save()
                        except ValidationError as e:
                            raise serializers.ValidationError(
                                {"error": "Operation aborted. Error at row %d. %s" % (i + 1, "; ".join(e.messages))}
                            )
                    except IntegrityError:
                        raise serializers.ValidationError(
                            {
                                "error": "Operation aborted. Error at row {} Account already exists : {}. Fix the "
                                "error and try "
                                "again.".format(i, row[csv_indexes.index("username")])
                            }
                        )

                    org_units = row[csv_indexes.index("orgunit")].split(value_splitter)
                    if has_geo_limit and len(list(filter(None, org_units))) == 0:
                        raise serializers.ValidationError(
                            {
                                "error": f"Operation aborted. A User with {permission.USERS_MANAGED} permission "
                                "has to create users with OrgUnits in the file"
                            }
                        )

                    org_units_source_refs = row[csv_indexes.index("orgunit__source_ref")].split(value_splitter)
                    org_units += org_units_source_refs
                    for ou in list(filter(None, org_units)):
                        ou = ou.strip()
                        if ou.isdigit():
                            try:
                                ou = OrgUnit.objects.select_related("org_unit_type").get(id=int(ou))
                                if has_geo_limit and ou not in importer_access_ou:
                                    raise serializers.ValidationError(
                                        {
                                            "error": f"Operation aborted. A User with {permission.USERS_MANAGED} permission "
                                            "has to create users with OrgUnits that are in the its controlled pyramid"
                                        }
                                    )
                                if ou not in importer_access_ou:
                                    raise serializers.ValidationError(
                                        {
                                            "error": "Operation aborted. Invalid OrgUnit {} at row : {}. "
                                            "You don't have access to this orgunit".format(ou, i + 1)
                                        }
                                    )
                                org_units_list.add(ou)
                            except ObjectDoesNotExist:
                                raise serializers.ValidationError(
                                    {
                                        "error": "Operation aborted. Invalid OrgUnit {} at row : {}. "
                                        "Fix the error "
                                        "and try "
                                        "again.".format(ou, i + 1)
                                    }
                                )
                        else:
                            # The same `OrgUnit` can appear more than once with the same `name` and `source_ref`
                            # due to multiple sequential imports from DHIS2 (this happens a lot). So we must
                            # select the one that matches the "default source version" of the account.
                            org_unit = (
                                OrgUnit.objects.select_related("org_unit_type")
                                .filter(
                                    Q(pk__in=importer_access_ou),
                                    Q(version_id=importer_account.default_version_id),
                                    Q(name=ou) | Q(source_ref=ou),
                                )
                                .order_by("-version_id")
                            )
                            if org_unit.count() > 1:
                                raise serializers.ValidationError(
                                    {
                                        "error": "Operation aborted. Multiple OrgUnits with `name` or `source_ref`: {} at row : {}."
                                        "Use Orgunit ID instead of name.".format(ou, i + 1)
                                    }
                                )
                            if not org_unit.count():
                                raise serializers.ValidationError(
                                    {
                                        "error": "Operation aborted. Invalid OrgUnit {} at row : {}. Fix "
                                        "the error "
                                        "and try "
                                        "again. Use Orgunit ID instead of name.".format(ou, i + 1)
                                    }
                                )
                            if org_unit[0] not in importer_access_ou:
                                raise serializers.ValidationError(
                                    {
                                        "error": "Operation aborted. Invalid OrgUnit {} at row : {}. "
                                        "You don't have access to this orgunit".format(ou, i + 1)
                                    }
                                )
                            org_units_list.add(org_unit[0])

                    profile = Profile.objects.create(account=importer_account, user=user)

                    if org_units_list and user_editable_org_unit_type_ids:
                        invalid_ids = [
                            org_unit.org_unit_type_id
                            for org_unit in org_units_list
                            if org_unit.org_unit_type_id
                            and not profile.has_org_unit_write_permission(
                                org_unit.org_unit_type_id, user_editable_org_unit_type_ids
                            )
                        ]
                        if invalid_ids:
                            invalid_names = ", ".join(
                                name
                                for name in OrgUnitType.objects.filter(pk__in=invalid_ids).values_list(
                                    "name", flat=True
                                )
                            )
                            raise serializers.ValidationError(
                                {
                                    "error": f"Operation aborted. You don't have rights on the following org unit types: {invalid_names}"
                                }
                            )

                    # Using try except for dhis2_id in case users are being created with an older version of the template
                    try:
                        dhis2_id = row[csv_indexes.index("dhis2_id")]
                    except ValueError:
                        dhis2_id = None
                    if dhis2_id:
                        # check if a profile with the same dhis_id already exists
                        if Profile.objects.filter(dhis2_id=dhis2_id).count() > 0:
                            raise serializers.ValidationError(
                                {
                                    "error": f"Operation aborted. User with same dhis_2 id already exists at row : { i + 1}. Fix "
                                    "the error "
                                    "and try "
                                    "again"
                                }
                            )

                        profile.dhis2_id = dhis2_id

                    # Using try except for organization in case users are being created with an older version of the template
                    try:
                        organization = row[csv_indexes.index("organization")]
                    except ValueError:
                        organization = None
                    if organization:
                        profile.organization = organization

                    try:
                        user_roles = row[csv_indexes.index("user_roles")]
                    except (IndexError, ValueError):
                        user_roles = None
                    if user_roles:
                        user_roles = user_roles.split(value_splitter)
                        # check if the roles exists in the account of the request user
                        # and add it to user_roles_list
                        for role in user_roles:
                            if role != "":
                                role = role[1::] if role[:1] == " " else role
                                try:
                                    role_instance = UserRole.objects.get(
                                        account=importer_account,
                                        group__name=f"{importer_account.id}_{role}",
                                    )
                                    user_roles_list.append(role_instance)
                                    # get the user group linked to the userrole
                                    user_group_item = Group.objects.get(pk=role_instance.group.id)
                                    user_groups_list.append(user_group_item)

                                except ObjectDoesNotExist:
                                    raise serializers.ValidationError(
                                        {
                                            "error": f"Error. User Role: {role}, at row {i + 1} does not exists: Fix "
                                            "the error and try again."
                                        }
                                    )
                    try:
                        projects = row[csv_indexes.index("projects")]
                    except (IndexError, ValueError):
                        projects = None
                    if projects:
                        projects = projects.split(value_splitter)
                        for project in projects:
                            if project != "":
                                project = project[1::] if project[:1] == " " else project
                                try:
                                    project_instance = Project.objects.get(account=importer_account, name=project)
                                    projects_instance_list.append(project_instance)
                                except ObjectDoesNotExist:
                                    raise serializers.ValidationError(
                                        {
                                            "error": f"Error. User Project: {project}, at row {i + 1} does not exists: Fix "
                                            "the error and try again."
                                        }
                                    )
                    try:
                        user_permissions = row[csv_indexes.index("permissions")].split(value_splitter)
                        current_account = request.user.iaso_profile.account
                        module_permissions = self.module_permissions(current_account)
                        for perm in user_permissions:
                            perm = perm[1::] if perm[:1] == " " else perm
                            if perm and perm in module_permissions:
                                try:
                                    perm = Permission.objects.get(codename=perm)
                                    user.user_permissions.add(perm)
                                    user.save()
                                except ObjectDoesNotExist:
                                    raise serializers.ValidationError(
                                        {
                                            "error": "Operation aborted. Invalid permission {} at row : {}. Fix "
                                            "the error "
                                            "and try "
                                            "again".format(perm, i + 1)
                                        }
                                    )
                    except ValueError:
                        pass
                    if row[csv_indexes.index("profile_language")]:
                        language = row[csv_indexes.index("profile_language")].lower()
                        profile.language = language
                    else:
                        profile.language = "fr"

                    if row[csv_indexes.index("phone_number")]:
                        phone_number = row[csv_indexes.index("phone_number")]
                        profile.phone_number = self.validate_phone_number(phone_number)

                    try:
                        editable_org_unit_types_ids = row[csv_indexes.index("editable_org_unit_types")]
                        editable_org_unit_types_ids = (
                            editable_org_unit_types_ids.split(",") if editable_org_unit_types_ids else None
                        )
                    except (IndexError, ValueError):
                        editable_org_unit_types_ids = None

                    if editable_org_unit_types_ids:
                        new_editable_org_unit_types = OrgUnitType.objects.filter(
                            projects__account=importer_account, id__in=editable_org_unit_types_ids
                        )
                        if new_editable_org_unit_types:
                            if user_editable_org_unit_type_ids:
                                invalid_ids = [
                                    out.pk
                                    for out in new_editable_org_unit_types
                                    if not profile.has_org_unit_write_permission(
                                        out.pk, user_editable_org_unit_type_ids
                                    )
                                ]
                                if invalid_ids:
                                    invalid_names = ", ".join(
                                        name
                                        for name in OrgUnitType.objects.filter(pk__in=invalid_ids).values_list(
                                            "name", flat=True
                                        )
                                    )
                                    raise serializers.ValidationError(
                                        {
                                            "error": f"Operation aborted. You don't have rights on the following org unit types: {invalid_names}"
                                        }
                                    )
                            profile.editable_org_unit_types.set(new_editable_org_unit_types)

                    profile.org_units.set(org_units_list)
                    # link the auth user to the user role corresponding auth group
                    profile.user.groups.set(user_groups_list)
                    # link the user profile to the user role.
                    profile.user_roles.set(user_roles_list)
                    profile.projects.set(projects_instance_list)

                    csv_file = pd.read_csv(io.BytesIO(csv_str.getvalue().encode()), delimiter=delimiter)
                    csv_file.at[i - 1, "password"] = None
                    csv_file = csv_file.to_csv(path_or_buf=None, index=False)
                    content_file = ContentFile(csv_file.encode("utf-8"))
                    file_instance.file.save(f"{file_instance.id}.csv", content_file)
                    profile.save()
                    audit_logger.log_modification(
                        instance=profile,
                        old_data_dump=None,
                        request_user=request.user,
                        source=f"{PROFILE_API_BULK}_create",
                    )
                    user_created_count += 1
                else:
                    csv_indexes = row
        response = {"Accounts created": user_created_count}
        return Response(response)

    @staticmethod
    def module_permissions(current_account):
        # Get all modules linked to the current account
        account_modules = current_account.modules if current_account.modules else []
        # Get and return all permissions linked to the modules
        return account_module_permissions(account_modules)

    @staticmethod
    def validate_phone_number(phone_number):
        try:
            # Parse phone number
            parsed_number = phonenumbers.parse(phone_number, None)
            # Check if the number is valid
            if not phonenumbers.is_valid_number(parsed_number):
                raise serializers.ValidationError(
                    {"error": f"Operation aborted. The phone number {phone_number} is invalid"}
                )

            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException as e:
            raise serializers.ValidationError(
                {"error": f"Operation aborted. This '{phone_number}' is not a phone number"}
            )

    @swagger_auto_schema(request_body=no_body)
    @action(detail=False, methods=["get"], url_path="getsample")
    def download_sample_csv(self, request):
        return FileResponse(open("iaso/api/fixtures/sample_bulk_user_creation.csv", "rb"))
