import pkgutil
from typing import List, Union

from django.conf import settings
from django.contrib import auth
from django.urls import URLPattern, URLResolver, include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView  # type: ignore

from hat.api.token_authentication import token_auth
from iaso import matching
from iaso.api.config import ConfigViewSet
from iaso.api.data_store import DataStoreViewSet
from iaso.api.mobile.metadata.last_updates import LastUpdatesViewSet
from iaso.api.profiles.profile_logs import ProfileLogsViewset
from iaso.api.tasks.create.copy_version import CopyVersionViewSet
from iaso.api.tasks.create.dhis2_ou_importer import Dhis2OuImporterViewSet
from iaso.api.tasks.create.org_units_bulk_update import OrgUnitsBulkUpdate
from iaso.api.tasks.create.payments_bulk_update import PaymentsBulkUpdate
from iaso.api.tasks.create.profiles_bulk_update import ProfilesBulkUpdate
from iaso.models import MatchingAlgorithm
from plugins.router import router as plugins_router

from .api.accounts import AccountViewSet
from .api.algorithms import AlgorithmsViewSet
from .api.algorithms_runs import AlgorithmsRunsViewSet
from .api.api_tokens import APITokenViewSet
from .api.apps import AppsViewSet
from .api.data_source_versions_synchronization.views import DataSourceVersionsSynchronizationViewSet
from .api.profiles.bulk_create_users import BulkCreateUserFromCsvViewSet
from .api.check_version import CheckVersionViewSet
from .api.comment import CommentViewSet
from .api.completeness import CompletenessViewSet
from .api.completeness_stats import CompletenessStatsV2ViewSet
from .api.data_sources import DataSourceViewSet
from .api.deduplication.entity_duplicate import EntityDuplicateViewSet  # type: ignore
from .api.deduplication.entity_duplicate_analyzis import EntityDuplicateAnalyzisViewSet  # type: ignore
from .api.derived_instances import DerivedInstancesViewSet
from .api.devices import DevicesViewSet
from .api.devices_ownership import DevicesOwnershipViewSet
from .api.devices_position import DevicesPositionViewSet
from .api.dhis2_resources import DHIS2_VIEWSETS
from .api.enketo import (
    EnketoSubmissionAPIView,
    enketo_create_url,
    enketo_edit_url,
    enketo_form_download,
    enketo_form_list,
    enketo_public_create_url,
    enketo_public_launch,
)
from .api.entity import EntityViewSet
from .api.entity_types import EntityTypeViewSet
from .api.export_requests import ExportRequestsViewSet
from .api.feature_flags import FeatureFlagViewSet
from .api.form_attachments import FormAttachmentsViewSet
from .api.form_versions import FormVersionsViewSet
from .api.forms import FormsViewSet, MobileFormViewSet
from .api.groups import GroupsViewSet
from .api.hesabu_descriptors import HesabuDescriptorsViewSet
from .api.instances import InstancesViewSet
from .api.links import LinkViewSet
from .api.logs import LogsViewSet
from .api.mapping_versions import MappingVersionsViewSet
from .api.metrics.views import MetricTypeViewSet, MetricValueViewSet
from .api.microplanning import AssignmentViewSet, MobilePlanningViewSet, PlanningViewSet, TeamViewSet
from .api.mobile.bulk_uploads import MobileBulkUploadsViewSet
from .api.mobile.entity import MobileEntityViewSet, MobileEntityDeletedViewSet
from .api.mobile.entity_type import MobileEntityTypesViewSet
from .api.mobile.groups import MobileGroupsViewSet
from .api.mobile.group_sets import MobileGroupSetsViewSet
from .api.mobile.org_units import MobileOrgUnitViewSet
from .api.mobile.reports import MobileReportsViewSet
from .api.mobile.storage import MobileStoragePasswordViewSet
from .api.modules import ModulesViewSet
from .api.org_unit_change_request_configurations.views import OrgUnitChangeRequestConfigurationViewSet
from .api.org_unit_change_request_configurations.views_mobile import MobileOrgUnitChangeRequestConfigurationViewSet
from .api.org_unit_change_requests.views import OrgUnitChangeRequestViewSet
from .api.org_unit_change_requests.views_mobile import MobileOrgUnitChangeRequestViewSet
from .api.org_unit_tree.views import OrgUnitTreeViewSet
from .api.org_unit_types import OrgUnitTypeViewSet
from .api.org_unit_types.viewsets import OrgUnitTypeViewSetV2
from .api.org_unit_validation_status import ValidationStatusViewSet
from .api.org_units import OrgUnitViewSet
from .api.pages import PagesViewSet
from .api.payments.views import PaymentLotsViewSet, PaymentOptionsViewSet, PaymentsViewSet, PotentialPaymentsViewSet
from .api.periods import PeriodsViewSet
from .api.permissions import PermissionsViewSet
from .api.profiles.profiles import ProfilesViewSet
from .api.projects import ProjectsViewSet
from .api.reports import ReportsViewSet
from .api.setup_account import SetupAccountViewSet
from .api.source_versions import SourceVersionViewSet
from .api.storage import StorageBlacklistedViewSet, StorageLogViewSet, StorageViewSet, logs_per_device
from .api.superset import SupersetTokenViewSet
from .api.tasks.views import TaskSourceViewSet
from .api.tasks.create.export_mobile_setup import ExportMobileSetupViewSet
from .api.tasks.create.import_gpkg import ImportGPKGViewSet
from .api.tasks.create.instance_bulk_gps_push import InstanceBulkGpsPushViewSet
from .api.tasks.create.org_unit_bulk_location_set import OrgUnitsBulkLocationSet
from .api.user_roles import UserRolesViewSet
from .api.workflows.changes import WorkflowChangeViewSet
from .api.workflows.followups import WorkflowFollowupViewSet
from .api.workflows.import_export import export_workflow, import_workflow
from .api.workflows.mobile import MobileWorkflowViewSet
from .api.workflows.versions import WorkflowVersionViewSet
from .api.group_sets.views import GroupSetsViewSet
from .dhis2.authentication import dhis2_callback  # type: ignore

URL = Union[URLPattern, URLResolver]
URLList = List[URL]

router = routers.DefaultRouter()
router.register(
    r"mobile/orgunits/changes/configs",
    MobileOrgUnitChangeRequestConfigurationViewSet,
    basename="mobileorgunitschangesconfigs",
)
router.register(
    r"orgunits/changes/configs", OrgUnitChangeRequestConfigurationViewSet, basename="orgunitschangesconfigs"
)
router.register(r"orgunits/changes", OrgUnitChangeRequestViewSet, basename="orgunitschanges")
router.register(r"mobile/orgunits/changes", MobileOrgUnitChangeRequestViewSet, basename="mobileorgunitschanges")
router.register(r"orgunits/tree", OrgUnitTreeViewSet, basename="orgunitstree")
router.register(r"orgunits", OrgUnitViewSet, basename="orgunits")
router.register(r"orgunittypes", OrgUnitTypeViewSet, basename="orgunittypes")
router.register(r"v2/orgunittypes", OrgUnitTypeViewSetV2, basename="orgunittypes")
router.register(r"apps", AppsViewSet, basename="apps")
router.register(r"projects", ProjectsViewSet, basename="projects")
router.register(r"potential_payments", PotentialPaymentsViewSet, basename="potential_payments")
router.register(r"payments/lots", PaymentLotsViewSet, basename="paymentslots")
router.register(r"payments/options", PaymentOptionsViewSet, basename="paymentsoptions")
router.register(r"payments", PaymentsViewSet, basename="payments")
router.register(r"instances", InstancesViewSet, basename="instances")
router.register(r"forms", FormsViewSet, basename="forms")
router.register(r"mobile/forms", MobileFormViewSet, basename="formsmobile")
router.register(r"pages", PagesViewSet, basename="pages")
router.register(r"formversions", FormVersionsViewSet, basename="formversions")
router.register(r"formattachments", FormAttachmentsViewSet, basename="formattachments")
router.register(r"periods", PeriodsViewSet, basename="periods")
router.register(r"devices", DevicesViewSet, basename="devices")
router.register(r"devicesownerships", DevicesOwnershipViewSet, basename="devicesownership")
router.register(r"devicespositions?", DevicesPositionViewSet, basename="devicesposition")
router.register(r"datasources/sync", DataSourceVersionsSynchronizationViewSet, basename="datasources_synchronization")
router.register(r"datasources", DataSourceViewSet, basename="datasources")
router.register(r"accounts", AccountViewSet, basename="accounts")
router.register(r"apitoken", APITokenViewSet, basename="apitoken")
router.register(r"sourceversions", SourceVersionViewSet, basename="sourceversion")
router.register(r"links", LinkViewSet, basename="links")
router.register(r"logs", LogsViewSet, basename="logs")
router.register(r"profiles", ProfilesViewSet, basename="profiles")
router.register(r"algorithms", AlgorithmsViewSet, basename="algorithms")
router.register(r"algorithmsruns", AlgorithmsRunsViewSet, basename="algorithmsruns")
router.register(r"groups", GroupsViewSet, basename="groups")
router.register(r"group_sets", GroupSetsViewSet, basename="group_sets")
router.register(r"mobile/groups", MobileGroupsViewSet, basename="groupsmobile")
router.register(r"mobile/group_sets", MobileGroupSetsViewSet, basename="groupsetsmobile")
router.register(r"completeness", CompletenessViewSet, basename="completeness")
router.register(r"v2/completeness_stats", CompletenessStatsV2ViewSet, basename="completeness_stats")
router.register(r"exportrequests", ExportRequestsViewSet, basename="exportrequests")
router.register(r"mappingversions", MappingVersionsViewSet, basename="mappingversions")
router.register(r"permissions", PermissionsViewSet, basename="permissions")
router.register(r"derivedinstances", DerivedInstancesViewSet, basename="derivedinstances")
router.register(r"mobile/orgunits", MobileOrgUnitViewSet, basename="orgunitsmobile")
router.register(r"featureflags", FeatureFlagViewSet, basename="featureflags")
router.register(r"mobile/checkversion", CheckVersionViewSet, basename="checkversion")
router.register(r"copyversion", CopyVersionViewSet, basename="copyversion")
router.register(r"dhis2ouimporter", Dhis2OuImporterViewSet, basename="dhis2ouimporter")
router.register(r"setupaccount", SetupAccountViewSet, basename="setupaccount")
router.register(r"tasks/create/orgunitsbulkupdate", OrgUnitsBulkUpdate, basename="orgunitsbulkupdate")
router.register(r"tasks/create/paymentsbulkupdate", PaymentsBulkUpdate, basename="paymentsbulkupdate")
router.register(r"tasks/create/profilesbulkupdate", ProfilesBulkUpdate, basename="profilesbulkupdate")
router.register(r"tasks/create/orgunitsbulklocationset", OrgUnitsBulkLocationSet, basename="orgunitsbulklocationset")
router.register(r"tasks/create/importgpkg", ImportGPKGViewSet, basename="importgpkg")
router.register(r"tasks/create/exportmobilesetup", ExportMobileSetupViewSet, basename="exportmobilesetup")
router.register(r"tasks/create/instancebulkgpspush", InstanceBulkGpsPushViewSet, basename="instancebulkgpspush")
router.register(r"tasks", TaskSourceViewSet, basename="tasks")
router.register(r"comments", CommentViewSet, basename="comments")
router.register(r"entities", EntityViewSet, basename="entity")
router.register(r"mobile/entities/deleted", MobileEntityDeletedViewSet, basename="entitiesdeleted")
router.register(r"mobile/entities", MobileEntityViewSet, basename="entities")
router.register(r"entitytypes", EntityTypeViewSet, basename="entitytype")
router.register(r"mobile/entitytypes?", MobileEntityTypesViewSet, basename="entitytype")
router.register(r"entityduplicates", EntityDuplicateViewSet, basename="entityduplicates")
router.register(r"entityduplicates_analyzes", EntityDuplicateAnalyzisViewSet, basename="entityduplicates_analyzes")
router.register(r"bulkcreateuser", BulkCreateUserFromCsvViewSet, basename="bulkcreateuser")
router.register(r"microplanning/teams", TeamViewSet, basename="teams")
router.register(r"microplanning/plannings", PlanningViewSet, basename="planning")
router.register(r"microplanning/assignments", AssignmentViewSet, basename="assignments")
router.register(r"mobile/plannings", MobilePlanningViewSet, basename="mobileplanning")
router.register(r"storages", StorageViewSet, basename="storage")
router.register(r"mobile/storages?/logs", StorageLogViewSet, basename="storagelogs")
router.register(r"mobile/storages?/blacklisted", StorageBlacklistedViewSet, basename="storageblacklisted")
router.register(r"mobile/storages?/passwords", MobileStoragePasswordViewSet, basename="storagepasswords")

router.register(r"workflowversions", WorkflowVersionViewSet, basename="workflowversions")

router.register(r"workflowfollowups", WorkflowFollowupViewSet, basename="workflowfollowups")
router.register(r"workflowchanges", WorkflowChangeViewSet, basename="workflowchanges")
router.register(r"mobile/workflows", MobileWorkflowViewSet, basename="mobileworkflows")
router.register(r"reports", ReportsViewSet, basename="report")
router.register(r"mobile/reports", MobileReportsViewSet, basename="report")
router.register(r"userroles", UserRolesViewSet, basename="userroles")
router.register(r"userlogs", ProfileLogsViewset, basename="userlogs")

router.register(r"datastore", DataStoreViewSet, basename="datastore")
router.register(r"validationstatus", ValidationStatusViewSet, basename="validationstatus")

router.register(r"mobile/metadata/lastupdates", LastUpdatesViewSet, basename="lastupdates")
router.register(r"modules", ModulesViewSet, basename="modules")
router.register(r"configs", ConfigViewSet, basename="jsonconfigs")
router.register(r"mobile/bulkupload", MobileBulkUploadsViewSet, basename="mobilebulkupload")
router.register(r"superset/token", SupersetTokenViewSet, basename="supersettoken")
router.register(r"metrictypes", MetricTypeViewSet, basename="metrictypes")
router.register(r"metricvalues", MetricValueViewSet, basename="metricvalues")
router.registry.extend(plugins_router.registry)

urlpatterns: URLList = [
    path(
        "fill/<form_uuid>/<org_unit_id>/<period>",
        view=enketo_public_launch,
        name="enketo_public_launch",
    ),
    path("enketo/create/", view=enketo_create_url, name="enketo-create-url"),
    path("enketo/public_create_url/", view=enketo_public_create_url, name="enketo_public_create_url"),
    path("enketo/edit/<instance_uuid>/", view=enketo_edit_url, name="enketo-edit-url"),
    path("enketo/formList", view=enketo_form_list, name="enketo-form-list"),
    path("enketo/formDownload/", view=enketo_form_download, name="enketo_form_download"),
    path("enketo/submission", view=EnketoSubmissionAPIView.as_view(), name="enketo-submission"),
    path("logout-iaso", auth.views.LogoutView.as_view(next_page="login"), name="logout-iaso"),
]


def append_datasources_subresource(viewset, resource_name, urlpatterns):
    urlpatterns.append(
        path(
            "datasources/<datasource_id>/" + resource_name + "/",
            view=viewset.as_view({"get": "list"}),
            name=resource_name,
        )
    )
    urlpatterns.append(
        path(
            "datasources/<datasource_id>/" + resource_name + ".<format>",
            view=viewset.as_view({"get": "list"}),
            name=resource_name,
        )
    )


if not settings.DISABLE_PASSWORD_LOGINS:
    urlpatterns = urlpatterns + [
        path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    ]

urlpatterns = urlpatterns + [
    path("storages/<str:storage_type>/<str:storage_customer_chosen_id>/logs", logs_per_device),
    path("workflows/export/<workflow_id>/", export_workflow, name="export_workflow"),
    path("workflows/import/", import_workflow, name="import_workflow"),
    path("", include(router.urls)),
]
# External Auth
urlpatterns = urlpatterns + [
    path("dhis2/<dhis2_slug>/login/", dhis2_callback, name="dhis2_callback"),
    path("token_auth/", token_auth),
]

for dhis2_resource in DHIS2_VIEWSETS:
    append_datasources_subresource(dhis2_resource, dhis2_resource.resource, urlpatterns)

append_datasources_subresource(HesabuDescriptorsViewSet, HesabuDescriptorsViewSet.resource, urlpatterns)

##########   creating algorithms in the database so that they will appear in the API  ##########
try:
    import importlib

    for pkg in pkgutil.iter_modules(matching.__path__):
        full_name = "iaso.matching." + pkg.name
        algo_module = importlib.import_module(full_name)
        algo = algo_module.Algorithm()
        MatchingAlgorithm.objects.get_or_create(name=full_name, defaults={"description": algo.description})

except Exception as e:
    print("!! failed to create MatchingAlgorithm based on code, probably in manage.py migrate", e)
