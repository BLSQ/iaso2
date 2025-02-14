"""Permissions list

These permissions are used and not the django built in one on each model.
They are used for API access but also to see which page a user has access
in the frontend.

To add a new permission:
1. Add a constant to hold its label
2. Add it to the CustomPermissionSupport.Meta.permissions tuple bellow
3. Generate a migration via makemigrations (and run the migration locally)
4. Add it in hat/assets/js/apps/Iaso/domains/users/permissionsMessages.ts
5. Add it to en.json and fr.json

If you don't follow these steps you will break the frontend!

The frontend is getting the list of existing permission from the
`/api/permissions/` endpoint
"""

from django.conf import settings, LazySettings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from importlib import import_module


_ASSIGNMENTS = "iaso_assignments"
_COMPLETENESS = "iaso_completeness"
_COMPLETENESS_STATS = "iaso_completeness_stats"
_DATASTORE_READ = "iaso_datastore_read"
_DATASTORE_WRITE = "iaso_datastore_write"
_DATA_TASKS = "iaso_data_tasks"
_ENTITIES = "iaso_entities"
_ENTITY_TYPE_WRITE = "iaso_entity_type_write"
_ENTITIES_DUPLICATE_READ = "iaso_entity_duplicates_read"
_ENTITIES_DUPLICATE_WRITE = "iaso_entity_duplicates_write"
_FORMS = "iaso_forms"
_FORMS_STATS = "iaso_forms_stats"
_LINKS = "iaso_links"
_MAPPINGS = "iaso_mappings"
_MOBILE_APP_OFFLINE_SETUP = "iaso_mobile_app_offline_setup"
_MODULES = "iaso_modules"
_ORG_UNITS = "iaso_org_units"
_ORG_UNITS_READ = "iaso_org_units_read"
_ORG_UNITS_TYPES = "iaso_org_unit_types"
_ORG_UNITS_GROUPS = "iaso_org_unit_groups"
_ORG_UNITS_CHANGE_REQUEST_REVIEW = "iaso_org_unit_change_request_review"
_ORG_UNITS_CHANGE_REQUEST_CONFIGURATIONS = "iaso_org_unit_change_request_configurations"
_PAGES = "iaso_pages"
_PAGE_WRITE = "iaso_page_write"
_PAYMENTS = "iaso_payments"
_PLANNING_WRITE = "iaso_planning_write"
_PLANNING_READ = "iaso_planning_read"
_PROJECTS = "iaso_projects"
_REGISTRY_WRITE = "iaso_registry_write"
_REGISTRY_READ = "iaso_registry_read"
_REPORTS = "iaso_reports"
_SOURCE_WRITE = "iaso_write_sources"
_SOURCES = "iaso_sources"
_STORAGE = "iaso_storages"
_SUBMISSIONS = "iaso_submissions"
_SUBMISSIONS_UPDATE = "iaso_update_submission"
_TEAMS = "iaso_teams"
_USERS_ADMIN = "iaso_users"
_USERS_MANAGED = "iaso_users_managed"
_USERS_ROLES = "iaso_user_roles"
_WORKFLOW = "iaso_workflows"


# Trypelim
_ANONYMOUS_VIEW = "iaso_trypelim_anonymous"
_AREAS = "iaso_trypelim_management_areas"
_AREAS_EDIT = "iaso_trypelim_management_edit_areas"
_AREAS_SHAPES_EDIT = "iaso_trypelim_management_edit_shape_areas"
_CASES = "iaso_trypelim_case_cases"
_CASE_ANALYSIS = "iaso_trypelim_case_analysis"
_COORDINATIONS = "iaso_trypelim_management_coordinations"
_DEVICES = "iaso_trypelim_management_devices"
_DOWNLOAD_DATAS = "iaso_trypelim_datas_download"
_DUPLICATES = "iaso_trypelim_duplicates"
_EDIT_PATIENT = "iaso_trypelim_datas_patient_edition"
_STATS_GRAPHS = "iaso_trypelim_stats_graphs"
_STATS_REPORTS = "iaso_trypelim_stats_reports"
_HEALTH_STRUCTURES = "iaso_trypelim_management_health_structures"
_LAB = "iaso_trypelim_lab"
_LAB_UPLOAD = "iaso_trypelim_labupload"
_LOCATOR = "iaso_trypelim_locator"
_MACROPLANNING = "iaso_trypelim_plannings_macroplanning"
_MICROPLANNING = "iaso_trypelim_plannings_microplanning"
_MODIFICATIONS = "iaso_trypelim_modifications"
_PLANNINGS = "iaso_trypelim_management_plannings"
_PLANNINGS_TEMPLATE = "iaso_trypelim_management_plannings_template"
_QUALITY_CONTROL = "iaso_trypelim_qualitycontrol"
_RECONCILIATION = "iaso_trypelim_case_reconciliation"
_ROUTES = "iaso_trypelim_plannings_routes"
_UPLOAD_OF_CASE_FILES = "iaso_trypelim_datasets_datauploads"
_UPLOAD_OF_VILLAGES = "iaso_trypelim_datasets_villageuploads"
_TRYPELIM_TEAMS = "iaso_trypelim_management_teams"
_USERS = "iaso_trypelim_management_users"
_VECTOR_CONTROL = "iaso_trypelim_vectorcontrol"
_VECTOR_CONTROL_UPLOAD = "iaso_trypelim_vectorcontrolupload"
_VILLAGES = "iaso_trypelim_management_villages"
_WORKZONES = "iaso_trypelim_management_workzones"
_ZONES = "iaso_trypelim_management_zones"
_ZONES_EDIT = "iaso_trypelim_management_edit_zones"
_ZONES_SHAPES_EDIT = "iaso_trypelim_management_edit_shape_zones"

_PREFIX = "menupermissions."
ASSIGNMENTS = _PREFIX + _ASSIGNMENTS
COMPLETENESS = _PREFIX + _COMPLETENESS
COMPLETENESS_STATS = _PREFIX + _COMPLETENESS_STATS
DATASTORE_READ = _PREFIX + _DATASTORE_READ
DATASTORE_WRITE = _PREFIX + _DATASTORE_WRITE
DATA_TASKS = _PREFIX + _DATA_TASKS
ENTITIES = _PREFIX + _ENTITIES
ENTITY_TYPE_WRITE = _PREFIX + _ENTITY_TYPE_WRITE
ENTITIES_DUPLICATE_READ = _PREFIX + _ENTITIES_DUPLICATE_READ
ENTITIES_DUPLICATE_WRITE = _PREFIX + _ENTITIES_DUPLICATE_WRITE
FORMS = _PREFIX + _FORMS
FORMS_STATS = _PREFIX + _FORMS_STATS
LINKS = _PREFIX + _LINKS
MAPPINGS = _PREFIX + _MAPPINGS
MOBILE_APP_OFFLINE_SETUP = _PREFIX + _MOBILE_APP_OFFLINE_SETUP
MODULES = _PREFIX + _MODULES
ORG_UNITS = _PREFIX + _ORG_UNITS
ORG_UNITS_READ = _PREFIX + _ORG_UNITS_READ
ORG_UNITS_TYPES = _PREFIX + _ORG_UNITS_TYPES
ORG_UNITS_GROUPS = _PREFIX + _ORG_UNITS_GROUPS
ORG_UNITS_CHANGE_REQUEST_REVIEW = _PREFIX + _ORG_UNITS_CHANGE_REQUEST_REVIEW
ORG_UNITS_CHANGE_REQUEST_CONFIGURATIONS = _PREFIX + _ORG_UNITS_CHANGE_REQUEST_CONFIGURATIONS
PAYMENTS = _PREFIX + _PAYMENTS
PAGES = _PREFIX + _PAGES
PAGE_WRITE = _PREFIX + _PAGE_WRITE
PLANNING_WRITE = _PREFIX + _PLANNING_WRITE
PLANNING_READ = _PREFIX + _PLANNING_READ


# Import from plugins
for plugin in settings.PLUGINS:
    try:
        exported_permissions = import_module(f"plugins.{plugin}.permissions").exported_permissions
        for permission_name, permission_value in exported_permissions.items():
            globals()[permission_name] = permission_value
    except ImportError:
        print(f"{plugin} plugin has no permission support")


PROJECTS = _PREFIX + _PROJECTS
REGISTRY_WRITE = _PREFIX + _REGISTRY_WRITE
REGISTRY_READ = _PREFIX + _REGISTRY_READ
REPORTS = _PREFIX + _REPORTS
SOURCE_WRITE = _PREFIX + _SOURCE_WRITE
SOURCES = _PREFIX + _SOURCES
STORAGE = _PREFIX + _STORAGE
SUBMISSIONS = _PREFIX + _SUBMISSIONS
SUBMISSIONS_UPDATE = _PREFIX + _SUBMISSIONS_UPDATE
TEAMS = _PREFIX + _TEAMS
USERS_ADMIN = _PREFIX + _USERS_ADMIN
USERS_MANAGED = _PREFIX + _USERS_MANAGED
USERS_ROLES = _PREFIX + _USERS_ROLES
WORKFLOW = _PREFIX + _WORKFLOW

# Trypelim
ANONYMOUS_VIEW = _PREFIX + _ANONYMOUS_VIEW
AREAS = _PREFIX + _AREAS
AREAS_EDIT = _PREFIX + _AREAS_EDIT
AREAS_SHAPES_EDIT = _PREFIX + _AREAS_SHAPES_EDIT
CASES = _PREFIX + _CASES
CASE_ANALYSIS = _PREFIX + _CASE_ANALYSIS
COORDINATIONS = _PREFIX + _COORDINATIONS
DEVICES = _PREFIX + _DEVICES
DOWNLOAD_DATAS = _PREFIX + _DOWNLOAD_DATAS
DUPLICATES = _PREFIX + _DUPLICATES
EDIT_PATIENT = _PREFIX + _EDIT_PATIENT
HEALTH_STRUCTURES = _PREFIX + _HEALTH_STRUCTURES
LAB = _PREFIX + _LAB
LAB_UPLOAD = _PREFIX + _LAB_UPLOAD
LOCATOR = _PREFIX + _LOCATOR
MACROPLANNING = _PREFIX + _MACROPLANNING
MICROPLANNING = _PREFIX + _MICROPLANNING
MODIFICATIONS = _PREFIX + _MODIFICATIONS
PLANNINGS = _PREFIX + _PLANNINGS
PLANNINGS_TEMPLATE = _PREFIX + _PLANNINGS_TEMPLATE
QUALITY_CONTROL = _PREFIX + _QUALITY_CONTROL
RECONCILIATION = _PREFIX + _RECONCILIATION
ROUTES = _PREFIX + _ROUTES
STATS_GRAPHS = _PREFIX + _STATS_GRAPHS
STATS_REPORTS = _PREFIX + _STATS_REPORTS
UPLOAD_OF_CASE_FILES = _PREFIX + _UPLOAD_OF_CASE_FILES
UPLOAD_OF_VILLAGES = _PREFIX + _UPLOAD_OF_VILLAGES
TRYPELIM_TEAMS = _PREFIX + _TRYPELIM_TEAMS
USERS = _PREFIX + _USERS
VECTOR_CONTROL = _PREFIX + _VECTOR_CONTROL
VECTOR_CONTROL_UPLOAD = _PREFIX + _VECTOR_CONTROL_UPLOAD
VILLAGES = _PREFIX + _VILLAGES
WORKZONES = _PREFIX + _WORKZONES
ZONES = _PREFIX + _ZONES
ZONES_EDIT = _PREFIX + _ZONES_EDIT
ZONES_SHAPES_EDIT = _PREFIX + _ZONES_SHAPES_EDIT


class CustomPermissionSupport(models.Model):
    """Model used to hold our custom permission."""

    @staticmethod
    def get_full_permission_list():
        return [couple[0] for couple in CustomPermissionSupport._meta.permissions]

    # Used in setup_account api
    DEFAULT_PERMISSIONS_FOR_NEW_ACCOUNT_USER = [
        _FORMS,
        _SUBMISSIONS,
        _MAPPINGS,
        _COMPLETENESS,
        _ORG_UNITS,
        _LINKS,
        _USERS_ADMIN,
        _PROJECTS,
        _SOURCES,
        _DATA_TASKS,
        _REPORTS,
    ]

    class Meta:
        managed = False  # No database table creation or deletion operations \
        # will be performed for this model.

        permissions = (
            (_FORMS, _("Formulaires")),
            (_FORMS_STATS, _("Statistiques pour les formulaires")),
            (_MAPPINGS, _("Correspondances avec DHIS2")),
            (_MODULES, _("modules")),
            (_COMPLETENESS, _("Complétude des données")),
            (_ORG_UNITS, _("Unités d'organisations")),
            (_ORG_UNITS_READ, _("Lire les unités d'organisations")),
            (_REGISTRY_WRITE, _("Editer le Registre")),
            (_REGISTRY_READ, _("Lire le Registre")),
            (_LINKS, _("Correspondances sources")),
            (_USERS_ADMIN, _("Users")),
            (_USERS_MANAGED, _("Users managed")),
            (_PAGES, _("Pages")),
            (_PROJECTS, _("Projets")),
            (_SOURCES, _("Sources")),
            (_DATA_TASKS, _("Tâches")),
            (_SUBMISSIONS, _("Soumissions")),
            (_SUBMISSIONS_UPDATE, _("Editer soumissions")),
            (_PLANNING_WRITE, _("Editer le planning")),
            (_PLANNING_READ, _("Lire le planning")),
            (_REPORTS, _("Reports")),
            (_TEAMS, _("Equipes")),
            (_ASSIGNMENTS, _("Attributions")),
            (_ENTITIES, _("Entities")),
            (_ENTITY_TYPE_WRITE, _("Write entity type")),
            (_STORAGE, _("Storages")),
            (_COMPLETENESS_STATS, _("Completeness stats")),
            (_WORKFLOW, _("Workflows")),
            (_ENTITIES_DUPLICATE_READ, _("Read Entity duplicates")),
            (_ENTITIES_DUPLICATE_WRITE, _("Write Entity duplicates")),
            (_USERS_ROLES, _("Manage user roles")),
            (_DATASTORE_READ, _("Read data store")),
            (_DATASTORE_WRITE, _("Write data store")),
            (_ORG_UNITS_TYPES, _("Org unit types")),
            (_ORG_UNITS_GROUPS, _("Org unit groups")),
            (_ORG_UNITS_CHANGE_REQUEST_REVIEW, _("Org unit change request review")),
            (_ORG_UNITS_CHANGE_REQUEST_CONFIGURATIONS, _("Org unit change request configurations")),
            (_SOURCE_WRITE, _("Write data source")),
            (_PAGE_WRITE, _("Write page")),
            (_PAYMENTS, _("Payments page")),
            (_MOBILE_APP_OFFLINE_SETUP, ("Mobile app offline setup")),
            # Trypelim
            (_ANONYMOUS_VIEW, "Anonymisation des patients"),
            (_AREAS, _("Areas")),
            (_AREAS_EDIT, _("Edit areas")),
            (_AREAS_SHAPES_EDIT, _("Edit areas shapes")),
            (_CASES, _("Cases")),
            (_CASE_ANALYSIS, _("Cases analysis")),
            (_COORDINATIONS, _("Coordinations")),
            (_DEVICES, _("Devices")),
            (_DOWNLOAD_DATAS, _("Téléchargement de données")),
            (_DUPLICATES, _("Doublons")),
            (_EDIT_PATIENT, _("Edition d'un patient")),
            (_HEALTH_STRUCTURES, _("Health facilities")),
            (_LAB, _("Labo")),
            (_LAB_UPLOAD, _("Labo import")),
            (_LOCATOR, _("Locator")),
            (_MACROPLANNING, _("Macroplanning")),
            (_MICROPLANNING, _("Microplanning")),
            (_MODIFICATIONS, _("Modifications")),
            (_PLANNINGS, _("Plannings")),
            (_PLANNINGS_TEMPLATE, _("Plannings template")),
            (_QUALITY_CONTROL, _("Quality control")),
            (_RECONCILIATION, _("Reconciliation")),
            (_ROUTES, _("Routes")),
            (_STATS_GRAPHS, _("Graphs")),
            (_STATS_REPORTS, _("Reports")),
            (_UPLOAD_OF_CASE_FILES, _("Upload of cases files")),
            (_UPLOAD_OF_VILLAGES, _("Upload of villages files")),
            (_TRYPELIM_TEAMS, _("Teams")),
            (_USERS, _("Users")),
            (_VECTOR_CONTROL, _("Vector control")),
            (_VECTOR_CONTROL_UPLOAD, _("Vector control import Gpx")),
            (_VILLAGES, _("Villages")),
            (_WORKZONES, _("Work zones")),
            (_ZONES, _("Zones")),
            (_ZONES_EDIT, _("Edit zones")),
            (_ZONES_SHAPES_EDIT, _("Edit zones shapes")),
        )

    @staticmethod
    def filter_permissions(permissions, modules_permissions, settings: LazySettings):
        content_types = [ContentType.objects.get_for_model(CustomPermissionSupport)]

        for plugin in settings.PLUGINS:
            try:
                permission_model = import_module(f"plugins.{plugin}.permissions").permission_model
                content_types.append(ContentType.objects.get_for_model(permission_model))
            except ImportError:
                print(f"{plugin} plugin has no permission support")

        permissions = (
            permissions.filter(content_type__in=content_types)
            .filter(codename__startswith="iaso_")
            .filter(codename__in=modules_permissions)
            .exclude(codename__contains="datastore")
            .exclude(codename__contains="iaso_beneficiaries")
            .order_by("id")
        )

        return permissions

    @staticmethod
    def assert_right_to_assign(user, permission_codename: str):
        if not user.has_perm(USERS_ADMIN) and permission_codename == _USERS_ADMIN:
            raise PermissionDenied(f"Only users with {USERS_ADMIN} permission can grant {USERS_ADMIN} permission")
