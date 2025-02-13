from rest_framework import routers

from plugins.polio.api.dashboards.budget import BudgetDashboardViewSet
from plugins.polio.api.dashboards.campaign import CampaignDashboardViewSet

# TOFIX: Still haven't understood the exact problem but this should be
# the first import to avoid some 'BudgetProcess' errors in tests:
# `AttributeError: 'str' object has no attribute '_meta'`
from plugins.polio.api.dashboards.subactivities import SubActivityDashboardViewSet, SubActivityScopeDashboardViewSet
from plugins.polio.api.dashboards.vaccine_stock_history import VaccineStockHistoryDashboardViewSet
from plugins.polio.budget.api import BudgetProcessViewSet, BudgetStepViewSet, WorkflowViewSet

from plugins.polio.api.campaigns.campaign_groups import CampaignGroupViewSet
from plugins.polio.api.campaigns.campaigns import CampaignViewSet
from plugins.polio.api.campaigns.subactivities import SubActivityViewSet
from plugins.polio.api.campaigns.orgunits_per_campaigns import OrgUnitsPerCampaignViewset
from iaso.api.config import ConfigViewSet
from plugins.polio.api.chronogram.views import ChronogramViewSet, ChronogramTaskViewSet, ChronogramTemplateTaskViewSet
from plugins.polio.api.country_user_groups import CountryUsersGroupViewSet
from plugins.polio.api.dashboards.forma import FormAStocksViewSetV2
from plugins.polio.api.dashboards.launch_powerbi import LaunchPowerBIRefreshViewSet
from plugins.polio.api.dashboards.preparedness_dashboard import PreparednessDashboardViewSet
from plugins.polio.api.dashboards.rounds import RoundDashboardViewSet
from plugins.polio.api.dashboards.spreadsheetimport import SpreadSheetImportViewSet
from plugins.polio.api.dashboards.supply_chain import (
    PreAlertDashboardViewSet,
    VaccineArrivalReportDashboardViewSet,
    VaccineRequestFormDashboardViewSet,
)
from plugins.polio.api.dashboards.vaccine_stocks import VaccineStocksViewSet
from plugins.polio.api.lqas_im.countries_with_lqas_im import CountriesWithLqasIMConfigViewSet
from plugins.polio.api.lqas_im.lqas_im_country import LQASIMCountryViewset
from plugins.polio.api.lqas_im.lqasim_global_map import LQASIMGlobalMapViewSet
from plugins.polio.api.lqas_im.lqasim_zoom_in_map import LQASIMZoominMapBackgroundViewSet, LQASIMZoominMapViewSet
from plugins.polio.api.notifications.views import NotificationViewSet
from plugins.polio.api.polio_org_units import PolioOrgunitViewSet
from plugins.polio.api.rounds.reasons_for_delay import ReasonForDelayViewSet
from plugins.polio.api.rounds.round import RoundViewSet
from plugins.polio.api.rounds.round_date_history import RoundDateHistoryEntryViewset
from plugins.polio.api.vaccines.vaccine_authorization import VaccineAuthorizationViewSet
from plugins.polio.tasks.api.create_refresh_preparedness_data import RefreshPreparednessLaucherViewSet
from plugins.polio.api.vaccines.supply_chain import VaccineRequestFormViewSet
from plugins.polio.api.vaccines.repository_forms import VaccineRepositoryFormsViewSet
from plugins.polio.api.vaccines.repository_reports import VaccineRepositoryReportsViewSet
from plugins.polio.api.vaccines.stock_management import (
    VaccineStockManagementViewSet,
    OutgoingStockMovementViewSet,
    DestructionReportViewSet,
    IncidentReportViewSet,
    EarmarkedStockViewSet,
)

from plugins.polio.tasks.api.launch_vaccine_stock_archive import ArchiveVaccineStockViewSet
from plugins.polio.tasks.api.refresh_im_data import (
    RefreshIMAllDataViewset,
    RefreshIMHouseholdDataViewset,
    RefreshIMOutOfHouseholdDataViewset,
)
from plugins.polio.tasks.api.refresh_lqas_data import RefreshLQASDataViewset

router = routers.SimpleRouter()
router.register(r"polio/orgunits", PolioOrgunitViewSet, basename="PolioOrgunit")
router.register(r"polio/campaigns", CampaignViewSet, basename="Campaign")
router.register(r"polio/campaigns_subactivities", SubActivityViewSet, basename="campaigns_subactivities")
router.register(r"polio/chronograms/tasks", ChronogramTaskViewSet, basename="chronograms_tasks")
router.register(
    r"polio/chronograms/template_tasks", ChronogramTemplateTaskViewSet, basename="chronograms_template_tasks"
)
router.register(r"polio/chronograms", ChronogramViewSet, basename="chronograms")
router.register(r"polio/budget", BudgetProcessViewSet, basename="BudgetProcess")
router.register(r"polio/budgetsteps", BudgetStepViewSet, basename="BudgetStep")
router.register(r"polio/workflow", WorkflowViewSet, basename="BudgetWorkflow")
router.register(r"polio/campaignsgroup", CampaignGroupViewSet, basename="campaigngroup")
router.register(r"polio/preparedness_dashboard", PreparednessDashboardViewSet, basename="preparedness_dashboard")
router.register(r"polio/vaccines", VaccineStocksViewSet, basename="vaccines")
router.register(r"polio/v2/forma", FormAStocksViewSetV2, basename="forma")
router.register(r"polio/countryusersgroup", CountryUsersGroupViewSet, basename="countryusersgroup")
router.register(r"polio/orgunitspercampaign", OrgUnitsPerCampaignViewset, basename="orgunitspercampaign")
# duplicate of /api/configs. Can be removed once lqas OpenHexa pipeline switches to the main (iaso) endpoint
router.register(r"polio/configs", ConfigViewSet, basename="polioconfigs")
router.register(r"polio/datelogs", RoundDateHistoryEntryViewset, basename="datelogs")
router.register(r"polio/lqasim/countries", CountriesWithLqasIMConfigViewSet, basename="lqasimcountries")
router.register(r"polio/lqasimmap/country", LQASIMCountryViewset, basename="lqasimcountry")
router.register(r"polio/lqasmap/global", LQASIMGlobalMapViewSet, basename="lqasmapglobal")
router.register(r"polio/lqasmap/zoomin", LQASIMZoominMapViewSet, basename="lqasmapzoomin")
router.register(r"polio/lqasmap/zoominbackground", LQASIMZoominMapBackgroundViewSet, basename="lqasmapzoominbackground")
router.register(r"polio/vaccineauthorizations", VaccineAuthorizationViewSet, basename="vaccine_authorizations")
router.register(r"polio/powerbirefresh", LaunchPowerBIRefreshViewSet, basename="powerbirefresh")
router.register(r"polio/rounds", RoundViewSet, basename="rounds")
router.register(r"polio/reasonsfordelay", ReasonForDelayViewSet, basename="reasonsfordelay")
router.register(r"polio/tasks/refreshlqas", RefreshLQASDataViewset, basename="refreshlqas")
router.register(r"polio/tasks/refreshim/hh", RefreshIMHouseholdDataViewset, basename="refreshimhh")
router.register(r"polio/tasks/refreshim/ohh", RefreshIMOutOfHouseholdDataViewset, basename="refreshimohh")
router.register(r"polio/tasks/refreshim/hh_ohh", RefreshIMAllDataViewset, basename="refreshimhhohh")
router.register(r"polio/vaccine/request_forms", VaccineRequestFormViewSet, basename="vaccine_request_forms")
router.register(r"polio/vaccine/vaccine_stock", VaccineStockManagementViewSet, basename="vaccine_stocks")
router.register(r"polio/vaccine/repository", VaccineRepositoryFormsViewSet, basename="vaccine_repository")
router.register(
    r"polio/vaccine/repository_reports", VaccineRepositoryReportsViewSet, basename="vaccine_repository_reports"
)

router.register(
    r"polio/vaccine/stock/outgoing_stock_movement", OutgoingStockMovementViewSet, basename="outgoing_stock_movement"
)
router.register(r"polio/vaccine/stock/destruction_report", DestructionReportViewSet, basename="destruction_report")
router.register(r"polio/vaccine/stock/incident_report", IncidentReportViewSet, basename="incident_report")
router.register(r"polio/vaccine/stock/earmarked_stock", EarmarkedStockViewSet, basename="earmarked_stock")

router.register(r"polio/notifications", NotificationViewSet, basename="notifications")

router.register(r"tasks/create/refreshpreparedness", RefreshPreparednessLaucherViewSet, basename="refresh_preparedness")
router.register(r"tasks/create/archivevaccinestock", ArchiveVaccineStockViewSet, basename="archive_vaccine_stock")
router.register(
    r"polio/dashboards/vaccine_request_forms",
    VaccineRequestFormDashboardViewSet,
    basename="dashboard_vaccine_request_forms",
)
router.register(
    r"polio/dashboards/vaccine_stock_history",
    VaccineStockHistoryDashboardViewSet,
    basename="dashboard_vaccine_stock_history",
)
router.register(
    r"polio/dashboards/pre_alerts",
    PreAlertDashboardViewSet,
    basename="dashboard_pre-alerts",
)
router.register(
    r"polio/dashboards/arrival_reports",
    VaccineArrivalReportDashboardViewSet,
    basename="dashboard_arrival_reports",
)
router.register(
    r"polio/dashboards/budgets",
    BudgetDashboardViewSet,
    basename="dashboard_budgets",
)
router.register(
    r"polio/dashboards/campaigns",
    CampaignDashboardViewSet,
    basename="dashboard_campaigns",
)
router.register(
    r"polio/dashboards/rounds",
    RoundDashboardViewSet,
    basename="dashboard_rounds",
)
router.register(
    r"polio/dashboards/preparedness_sheets",
    SpreadSheetImportViewSet,
    basename="dashboard_preparedness_sheets",
)
router.register(
    r"polio/dashboards/subactivities",
    SubActivityDashboardViewSet,
    basename="dashboard_subactivities",
)
router.register(
    r"polio/dashboards/subactivityscopes",
    SubActivityScopeDashboardViewSet,
    basename="dashboard_subactivityscopes",
)
