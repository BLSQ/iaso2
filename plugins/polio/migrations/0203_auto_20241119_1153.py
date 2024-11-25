# Generated by Django 4.2.11 on 2024-11-19 11:53

from django.db import migrations


def remove_softdeleted_prealerts(apps, schema_editor):
    VaccinePreAlert = apps.get_model("polio", "VaccinePreAlert")
    the_items = VaccinePreAlert.objects.filter(deleted_at__isnull=False)

    print(f"Removing {the_items.count()} softdeleted prealerts")
    the_items.delete()


def remove_softdeleted_arrival_reports(apps, schema_editor):
    VaccineArrivalReport = apps.get_model("polio", "VaccineArrivalReport")
    the_items = VaccineArrivalReport.objects.filter(deleted_at__isnull=False)

    print(f"Removing {the_items.count()} softdeleted arrival reports")
    the_items.delete()


def rename_po_number_if_not_unique(apps, schema_editor):
    VaccinePreAlert = apps.get_model("polio", "VaccinePreAlert")
    VaccineArrivalReport = apps.get_model("polio", "VaccineArrivalReport")

    # Handle VaccinePreAlert duplicates
    prealerts = VaccinePreAlert.objects.filter(po_number__isnull=False).exclude(po_number="").order_by("created_at")
    seen_po_numbers = {}

    for prealert in prealerts:
        if prealert.po_number in seen_po_numbers:
            # Check if the prealert is identical to the first one seen with this PO number
            first_prealert = seen_po_numbers[prealert.po_number][0]

            if (
                prealert.date_pre_alert_reception == first_prealert.date_pre_alert_reception
                and prealert.estimated_arrival_time == first_prealert.estimated_arrival_time
                and prealert.expiration_date == first_prealert.expiration_date
                and prealert.doses_shipped == first_prealert.doses_shipped
                and prealert.doses_per_vial == first_prealert.doses_per_vial
                and prealert.vials_shipped == first_prealert.vials_shipped
                and prealert.request_form_id == first_prealert.request_form_id
            ):
                print(f"Deleting duplicate prealert with PO number {prealert.po_number} as its a duplicate")
                prealert.delete()

            else:
                suffix_index = len(seen_po_numbers[prealert.po_number]) - 1
                suffix = chr(ord("a") + suffix_index)
                original_po_number = prealert.po_number
                prealert.po_number = f"{prealert.po_number}_{suffix}"
                seen_po_numbers[original_po_number].append(prealert)
                print(f"Renaming prealert {original_po_number} to {prealert.po_number} as its different")
                prealert.save()
        else:
            seen_po_numbers[prealert.po_number] = [prealert]

    # Handle VaccineArrivalReport duplicates
    arrival_reports = (
        VaccineArrivalReport.objects.filter(po_number__isnull=False).exclude(po_number="").order_by("created_at")
    )
    seen_po_numbers = {}

    for report in arrival_reports:
        if report.po_number in seen_po_numbers:
            first_report = seen_po_numbers[report.po_number][0]

            if (
                report.arrival_report_date == first_report.arrival_report_date
                and report.doses_received == first_report.doses_received
                and report.expiration_date == first_report.expiration_date
                and report.doses_shipped == first_report.doses_shipped
                and report.doses_per_vial == first_report.doses_per_vial
                and report.vials_shipped == first_report.vials_shipped
                and report.vials_received == first_report.vials_received
                and report.request_form_id == first_report.request_form_id
            ):
                print(f"Deleting duplicate arrival report with PO number {report.po_number} as its a duplicate")
                report.delete()
            else:
                suffix_index = len(seen_po_numbers[report.po_number]) - 1
                suffix = chr(ord("a") + suffix_index)
                original_po_number = report.po_number
                report.po_number = f"{report.po_number}_{suffix}"
                print(f"Renaming arrival report {original_po_number} to {report.po_number} as its different")
                seen_po_numbers[original_po_number].append(report)
                report.save()
        else:
            seen_po_numbers[report.po_number] = [report]


def undo_migration(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("polio", "0202_populate_forma_round"),
    ]

    operations = [
        migrations.RunPython(remove_softdeleted_prealerts, undo_migration),
        migrations.RunPython(remove_softdeleted_arrival_reports, undo_migration),
        migrations.RunPython(rename_po_number_if_not_unique, undo_migration),
    ]
