# Generated by Django 4.2.13 on 2024-06-26 12:25

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("menupermissions", "0060_alter_custompermissionsupport_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="custompermissionsupport",
            options={
                "managed": False,
                "permissions": (
                    ("iaso_forms", "Formulaires"),
                    ("iaso_mappings", "Correspondances avec DHIS2"),
                    ("iaso_modules", "modules"),
                    ("iaso_completeness", "Complétude des données"),
                    ("iaso_org_units", "Unités d'organisations"),
                    ("iaso_registry", "Registre"),
                    ("iaso_links", "Correspondances sources"),
                    ("iaso_users", "Users"),
                    ("iaso_users_managed", "Users managed"),
                    ("iaso_pages", "Pages"),
                    ("iaso_projects", "Projets"),
                    ("iaso_sources", "Sources"),
                    ("iaso_data_tasks", "Tâches"),
                    ("iaso_polio", "Polio"),
                    ("iaso_polio_config", "Polio config"),
                    ("iaso_polio_notifications", "Polio notifications"),
                    ("iaso_submissions", "Soumissions"),
                    ("iaso_update_submission", "Editer soumissions"),
                    ("iaso_planning", "Planning"),
                    ("iaso_reports", "Reports"),
                    ("iaso_teams", "Equipes"),
                    ("iaso_assignments", "Attributions"),
                    ("iaso_polio_budget", "Budget Polio"),
                    ("iaso_entities", "Entities"),
                    ("iaso_entity_type_write", "Write entity type"),
                    ("iaso_storages", "Storages"),
                    ("iaso_completeness_stats", "Completeness stats"),
                    ("iaso_workflows", "Workflows"),
                    ("iaso_polio_budget_admin", "Budget Polio Admin"),
                    ("iaso_entity_duplicates_read", "Read Entity duplicates"),
                    ("iaso_entity_duplicates_write", "Write Entity duplicates"),
                    ("iaso_user_roles", "Manage user roles"),
                    ("iaso_datastore_read", "Read data store"),
                    ("iaso_datastore_write", "Write data store"),
                    ("iaso_org_unit_types", "Org unit types"),
                    ("iaso_org_unit_groups", "Org unit groups"),
                    (
                        "iaso_org_unit_change_request_review",
                        "Org unit change request review",
                    ),
                    ("iaso_write_sources", "Write data source"),
                    ("iaso_page_write", "Write page"),
                    ("iaso_payments", "Payments page"),
                    ("iaso_mobile_app_offline_setup", "Mobile app offline setup"),
                    (
                        "iaso_polio_vaccine_authorizations_read_only",
                        "Polio Vaccine Authorizations Read Only",
                    ),
                    (
                        "iaso_polio_vaccine_authorizations_admin",
                        "Polio Vaccine Authorizations Admin",
                    ),
                    (
                        "iaso_polio_vaccine_supply_chain_read",
                        "Polio Vaccine Supply Chain Read",
                    ),
                    (
                        "iaso_polio_vaccine_supply_chain_write",
                        "Polio Vaccine Supply Chain Write",
                    ),
                    (
                        "iaso_polio_vaccine_stock_management_read",
                        "Polio Vaccine Stock Management Read",
                    ),
                    (
                        "iaso_polio_vaccine_stock_management_write",
                        "Polio Vaccine Stock Management Write",
                    ),
                    ("iaso_trypelim_anonymous", "Anonymisation des patients"),
                    ("iaso_trypelim_management_areas", "Areas"),
                    ("iaso_trypelim_management_edit_areas", "Edit areas"),
                    ("iaso_trypelim_management_edit_shape_areas", "Edit areas shapes"),
                    ("iaso_trypelim_case_cases", "Cases"),
                    ("iaso_trypelim_case_analysis", "Cases analysis"),
                    ("iaso_trypelim_management_coordinations", "Coordinations"),
                    ("iaso_trypelim_management_devices", "Devices"),
                    ("iaso_trypelim_datas_download", "Téléchargement de données"),
                    ("iaso_trypelim_duplicates", "Doublons"),
                    ("iaso_trypelim_datas_patient_edition", "Edition d'un patient"),
                    ("iaso_trypelim_management_health_structures", "Health facilities"),
                    ("iaso_trypelim_lab", "Labo"),
                    ("iaso_trypelim_labupload", "Labo import"),
                    ("iaso_trypelim_locator", "Locator"),
                    ("iaso_trypelim_plannings_macroplanning", "Macroplanning"),
                    ("iaso_trypelim_plannings_microplanning", "Microplanning"),
                    ("iaso_trypelim_modifications", "Modifications"),
                    ("iaso_trypelim_management_plannings", "Plannings"),
                    (
                        "iaso_trypelim_management_plannings_template",
                        "Plannings template",
                    ),
                    ("iaso_trypelim_qualitycontrol", "Quality control"),
                    ("iaso_trypelim_case_reconciliation", "Reconciliation"),
                    ("iaso_trypelim_plannings_routes", "Routes"),
                    ("iaso_trypelim_stats_graphs", "Graphs"),
                    ("iaso_trypelim_stats_reports", "Reports (Trypelim)"),
                    ("iaso_trypelim_datasets_datauploads", "Upload of cases files"),
                    (
                        "iaso_trypelim_datasets_villageuploads",
                        "Upload of villages files",
                    ),
                    ("iaso_trypelim_management_teams", "Teams (Trypelim)"),
                    ("iaso_trypelim_management_users", "Users"),
                    ("iaso_trypelim_vectorcontrol", "Vector control"),
                    ("iaso_trypelim_vectorcontrolupload", "Vector control import Gpx"),
                    ("iaso_trypelim_management_villages", "Villages"),
                    ("iaso_trypelim_management_workzones", "Work zones"),
                    ("iaso_trypelim_management_zones", "Zones"),
                    ("iaso_trypelim_management_edit_zones", "Edit zones"),
                    ("iaso_trypelim_management_edit_shape_zones", "Edit zones shapes"),
                ),
            },
        ),
    ]
