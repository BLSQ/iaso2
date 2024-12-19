import calendar
import hashlib
import os
import uuid
from datetime import timedelta
from datetime import date
import pandas as pd
import math
import openpyxl
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Max
from django.http import HttpResponse
from django.db import models
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from iaso.models import OrgUnit
from .forms import ValidationForm
from .settings import OPENHEXA_USER, OPENHEXA_PASSWORD
from django.utils.encoding import smart_str
from .openhexa import *

from .models import (
    Import,
    SOURCE_EXCEL,
    ActivePatientsList,
    VALIDATION_STATUS_CHOICES,
    Validation,
    PATIENT_LIST_DISPLAY_FIELDS,
    HIV_UNKNOWN,
    HIV_HIV1,
    HIV_HIV2,
    HIV_HIV1_AND_2,
)
from ..polio.settings import DISTRICT

UPLOAD_FOLDER = "upload"  # Create this folder in your project directory

ALLOWED_EXTENSIONS = {"xlsx", "xls", "ods", "csv", "xlsb", "xltm", "xltx", "xlsm"}
OK = "OK"
ERROR_FILE_ALREADY_UPLOADED = "ERROR_FILE_ALREADY_UPLOADED"
ERROR_PERIOD_ALREADY_UPLOADED = "ERROR_PERIOD_ALREADY_UPLOADED"
ERROR_NO_FILE = "ERROR_NO_FILE"
ERROR_WRONG_FILE_FORMAT = "ERROR_WRONG_FILE_FORMAT"
ERROR_UNKNOWN = "ERROR_UNKNOWN"

RESPONSES = {
    OK: {"message": "Merci! Votre fichier est bien enregistré!", "status": 201},
    ERROR_FILE_ALREADY_UPLOADED: {
        "message": "Ce fichier a déjà été uploadé, êtes vous sûr?",
        "status": 400,
        "bypassable": True,
    },
    ERROR_PERIOD_ALREADY_UPLOADED: {
        "message": "Cette période a déjà été encodée pour cet établissement, êtes vous sûr de vouloir continuer?",
        "status": 400,
        "bypassable": True,
    },
    ERROR_NO_FILE: {"message": "Vous n'avez pas ajouté de fichier", "status": 400, "bypassable": False},
    ERROR_WRONG_FILE_FORMAT: {"message": "Ce fichier n'est pas un fichier excel", "status": 400, "bypassable": True},
    ERROR_UNKNOWN: {"message": "Erreur", "status": 400, "bypassable": False},
}


@login_required
def homepage(request):
    return render(request, "homepage.html", {})


@login_required
def patient_list(request):
    return render(request, "patient_list.html", {})


@login_required
def upload(request):
    if request.method == "POST":
        org_unit_id = request.POST.get("org_unit_id")
        period = request.POST.get("period")
        bypass = request.POST.get("bypass")

        if "file" not in request.FILES:
            result = ERROR_NO_FILE
        else:
            file = request.FILES["file"]
            if file.name == "":
                result = ERROR_NO_FILE
            elif not allowed_file(file.name):
                result = ERROR_WRONG_FILE_FORMAT
            elif file and allowed_file(file.name):
                filename = smart_str(file.name)
                result = upload_to_openhexa(filename, file, org_unit_id, period, bypass)
            else:
                result = ERROR_UNKNOWN

        return JsonResponse(RESPONSES[result], status=RESPONSES[result]["status"])

    return render(request, "upload.html", {})


@login_required
def validation(request):
    org_unit = None
    if request.method == "POST":
        form = ValidationForm(request.POST)
        if form.is_valid():
            form.instance.user_id = request.user.id
            form.instance.user_name = request.user.username
            form.instance.level = DISTRICT
            form.instance.save()
            # return redirect('validation_list') # Replace 'validation_list' with the actual URL name
    else:
        form = ValidationForm()
    return render(
        request,
        "validation.html",
        {
            "org_unit": org_unit,
            "statuses": VALIDATION_STATUS_CHOICES,
            "request": request,
            "form": form,
        },
    )


def validation_api(request, org_unit_id, period):
    org_units = OrgUnit.objects.filter(parent_id=org_unit_id).order_by("name")

    table_content = []
    report_count = 0
    for org_unit in org_units:
        obj = {}
        obj["Site"] = org_unit.name
        latest_import = Import.objects.filter(org_unit=org_unit).filter(month=period).order_by("-creation_date").first()
        if latest_import:
            report_count = report_count + 1
            obj["A rapporté"] = "Oui"
            latest_validation = Validation.objects.filter(source_import=latest_import).order_by("-created_at").first()
            if latest_validation:
                obj["Statut"] = latest_validation.validation_status
                obj["Observation"] = latest_validation.comment
                obj["Niveau Validation"] = latest_validation.level
            else:
                obj["Statut"] = ""
                obj["Observation"] = ""
                obj["Niveau Validation"] = ""
            obj["Dernière modification"] = latest_import.creation_date.strftime(("%d/%m/%y %H:%M:%S"))
            obj["import_id"] = latest_import.id
        else:
            obj["A rapporté"] = "Non"
            obj["Statut"] = ""
            obj["Observation"] = ""
            obj["Niveau Validation"] = ""
            obj["Dernière modification"] = ""
            obj["import_id"] = None

        table_content.append(obj)

    res = {"table_content": table_content, "completeness": "%s/%s" % (report_count, len(org_units))}
    return JsonResponse(res, status=200, safe=False)


def get_human_readable_value(model_instance, field_name):
    """
    Returns the human-readable value of a choice field in a Django model.

    Args:
      model_instance: An instance of a Django model.
      field_name: The name of the choice field.

    Returns:
      The human-readable value of the field, or None if the field is not a choice field
      or does not exist.
    """
    try:
        field = model_instance._meta.get_field(field_name)
        if field.choices:
            method_name = f"get_{field_name}_display"
            return getattr(model_instance, method_name)()
        elif isinstance(field, models.BooleanField):
            return "Oui" if getattr(model_instance, field_name) else "Non"
    except FieldDoesNotExist:
        return None

    return getattr(model_instance, field_name)


def get_first_and_last_day(date_str):
    """
    Calculates the first and last day of the month given a date string in the format "YYYY-MM".

    Args:
      date_str: A string representing the year and month in the format "YYYY-MM".

    Returns:
      A tuple containing two strings:
        - The first day of the month in the format "YYYY-MM-DD".
        - The last day of the month in the format "YYYY-MM-DD".
    """
    year, month = map(int, date_str.split("-"))

    # Get the number of days in the month
    _, last_day = calendar.monthrange(year, month)

    # Format the first and last days
    first_day_str = f"{year}-{month:02d}-01"
    last_day_str = f"{year}-{month:02d}-{last_day}"

    return first_day_str, last_day_str


def patient_list_api(request, org_unit_id, period):
    xls = request.GET.get("xls", None)
    mode = request.GET.get("mode", "default")
    latest_ids = (
        ActivePatientsList.objects.filter(org_unit_id=org_unit_id)
        .values("identifier_code")
        .annotate(latest_id=Max("id"))
    )

    patients = ActivePatientsList.objects.filter(id__in=[item["latest_id"] for item in latest_ids])
    if mode == "default":
        last_import = Import.objects.filter(org_unit=org_unit_id)
        last_import = last_import.filter(month=period).order_by("-creation_date").first()
        patients = ActivePatientsList.objects.filter(import_source=last_import).order_by("number")
    elif mode == "expected":
        first_day_str, last_day_str = get_first_and_last_day(period)
        patients = (
            patients.filter(active=True)
            .filter(next_dispensation_date__gte=first_day_str)
            .filter(next_dispensation_date__lte=last_day_str)
            .filter(org_unit_id=org_unit_id)
            .order_by("next_dispensation_date")
        )
    elif mode == "active":
        patients = patients.filter(active=True).filter(org_unit_id=org_unit_id)
    elif mode == "lost":
        today = date.today()
        patients = (
            patients.filter(active=True).filter(next_dispensation_date__lte=today).filter(org_unit_id=org_unit_id)
        )

    if xls is None:
        table_content = []
        for patient in patients:
            patient_object = {}
            for field in PATIENT_LIST_DISPLAY_FIELDS:
                patient_object[PATIENT_LIST_DISPLAY_FIELDS[field]] = get_human_readable_value(patient, field)
                if mode in ("expected", "lost", "active"):
                    if field == "days_dispensed":
                        patient_object["Date de rupture"] = get_human_readable_value(patient, "next_dispensation_date")
            table_content.append(patient_object)
        res = {
            "table_content": table_content,
        }
        return JsonResponse(res, status=200, safe=False)
    else:
        org_unit = OrgUnit.objects.get(pk=org_unit_id)
        return export_active_patients_excel(patients, org_unit.name, period)


def export_active_patients_excel(active_patients, name, period):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active

    # Add headers using French names from PATIENT_LIST_DISPLAY_FIELDS
    headers = list(PATIENT_LIST_DISPLAY_FIELDS.values())
    for col_num, header in enumerate(headers, 1):
        worksheet.cell(row=1, column=col_num).value = header

    for row_num, patient in enumerate(active_patients, 2):
        for col_num, field in enumerate(PATIENT_LIST_DISPLAY_FIELDS.keys(), 1):
            worksheet.cell(row=row_num, column=col_num).value = get_human_readable_value(patient, field)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="active_patients-%s-%s.xlsx"' % (name, period)
    workbook.save(response)
    return response


def check_presence(file_hash, org_unit_id, month):
    hash_exists = Import.objects.filter(hash_key=file_hash).exists()
    period_exists = Import.objects.filter(org_unit_id=org_unit_id, month=month).exists()

    if hash_exists:
        return "ERROR_FILE_ALREADY_UPLOADED"

    if period_exists:
        return "ERROR_PERIOD_ALREADY_UPLOADED"
    return "OK"


def hash_blob(binary_blob):
    """
    Calculates the SHA-256 hash of a binary blob.

    Args:
      binary_blob: The binary data as bytes.

    Returns:
      The hexadecimal representation of the SHA-256 hash.
    """

    hasher = hashlib.sha256()
    hasher.update(binary_blob)
    return hasher.hexdigest()


def upload_to_openhexa(file_name, file, org_unit_id, month, bypass=False):
    client = OpenHEXAClient("https://app.openhexa.org/")
    client.authenticate(with_credentials=(OPENHEXA_USER, OPENHEXA_PASSWORD), with_token=None)
    content = file.read()
    h = hash_blob(content)
    result = check_presence(h, org_unit_id, month)
    # TODO store all the errors of the file and not only one of the error results
    file_check = result
    name_exists = Import.objects.filter(file_name=file_name).exists()
    if name_exists:
        base, ext = os.path.splitext(file_name)  # Split into base name and extension
        file_name = f"{base}_{uuid.uuid4()}{ext}"
    if bypass:
        result = OK
    if result == OK:
        client.upload_object(
            "civ-lhspla-file-active-db7fae",
            "uploads-lhspla/%s" % file_name,
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        i = Import(
            hash_key=h,
            file_name=file_name,
            org_unit_id=org_unit_id,
            month=month,
            file_check=file_check,
            source=SOURCE_EXCEL,
        )
        i.save()
        import_data(content, i)
    return result


def check_file(file):
    # To implement
    # warning on multiple sheets
    # needed columns are not there -> refuse file
    # unrecognized value in column
    # wrong value in column (wrong type, wrong choice in a selection
    # name of facility does not match with the one that was picked
    pass


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def import_data(file, the_import):
    # the code of this function is relatively bad, it has been generated by AI
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)

    # Read the CSV file into a DataFrame
    df = pd.read_excel(file, sheet_name=0)
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)  # trimming all white spaces
    # Rename columns
    df = df.rename(
        columns={
            "N°": "number",
            "CODE ETS": "code_ets",
            "CODE": "code_ets",
            "NOM ETABLISSEMENT": "facility_name",
            "Periode": "period",
            "MOIS DE RAPPORTAGE": "period",
            "CODE IDENTIFIANT": "identifier_code",
            "SEXE": "sex",
            "POIDS": "weight",
            "Nouvelle inclusion": "new_inclusion",
            "Transfert-In": "transfer_in",
            "Retour dans les soins": "return_to_care",
            "TB / VIH": "tb_hiv",
            "Type de VIH": "hiv_type",
            "Régime": "REGIME",
            "régime": "REGIME",
            "regime": "REGIME",
            "Ligne therapeuthique": "treatment_line",
            "Ligne thérapeutique": "treatment_line",
            "Date de la dernière dispensation": "last_dispensation_date",
            "Nombre de jours dispensés": "days_dispensed",
            "STABLE": "stable",
            "Transfert Out": "transfer_out",
            "Décès": "death",
            "Arrêt TARV": "art_stoppage",
            "Servi ailleurs": "served_elsewhere",
        }
    )

    # Convert columns to boolean
    for col in [
        "new_inclusion",
        "transfer_in",
        "return_to_care",
        "tb_hiv",
        "transfer_out",
        "death",
        "art_stoppage",
        "served_elsewhere",
    ]:
        df[col] = df[col].apply(lambda x: True if x == 1 else False)

    # Map values in column `stable`
    df["stable"] = df["stable"].replace({"Oui": True, "Non": False})
    df["sex"] = df["sex"].replace({"F": "FEMALE", "M": "MALE"})
    df["treatment_line"] = df["treatment_line"].replace(
        {
            "1er Ligne": "1STLINE",
            "2e Ligne": "2NDLINE",
            "3e Ligne": "3RDLINE",
            "1": "1STLINE",
            "2": "2NDLINE",
            "3": "3RDLINE",
            1: "1STLINE",
            2: "2NDLINE",
            3: "3RDLINE",
        }
    )

    df["REGIME"] = df["REGIME"].replace(
        {
            "TDF 3TC DTG": "TDF/3TC/DTG",
            "ABC 3TC DTG": "ABC/3TC/DTG",
            "ABC 3TC ATV-r": "ABC/3TC/ATV-r",
            "ABC 3TC EFV": "ABC/3TC/EFV",
            "ABC 3TC LPV-r": "ABC/3TC/LPV-r",
            "ABC 3TC NVP": "ABC/3TC/NVP",
            "AZT 3TC ABC": "AZT/3TC/ABC",
            "AZT 3TC ATV-r": "AZT/3TC/ATV-r",
            "AZT 3TC DTG": "AZT/3TC/DTG",
            "AZT 3TC EFV": "AZT/3TC/EFV",
            "AZT 3TC LPV-r": "AZT/3TC/LPV-r",
            "AZT 3TC TDF": "AZT/3TC/TDF",
            "TDF 3TC ATV-r": "TDF/3TC/ATV-r",
            "TDF 3TC EFV": "TDF/3TC/EFV",
            "TDF 3TC LPV-r": "TDF/3TC/LPV-r",
        }
    )

    df["hiv_type"] = df["hiv_type"].replace(
        {
            1: HIV_HIV1,
            2: HIV_HIV2,
            "1&2": HIV_HIV1_AND_2,
            math.nan: HIV_UNKNOWN,
            "nan": HIV_UNKNOWN,
            "VIH 1 + 2": HIV_HIV1_AND_2,
            "VIH 1": HIV_HIV1,
            "VIH 2": HIV_HIV2,
        }
    )

    # Convert `last_dispensation_date` to datetime
    df["last_dispensation_date"] = pd.to_datetime(df["last_dispensation_date"])

    # Create a list of dictionaries
    data = []
    for _, row in df.iterrows():
        data.append(
            {
                "number": row["number"],
                "region": row["REGION"],
                "district": row["DISTRICT"],
                "code_ets": row["code_ets"],
                "facility_name": row.get("facility_name") if row.get("facility_name") else "",
                "period": row["period"],
                "identifier_code": row["identifier_code"],
                "sex": row["sex"],
                "age": row["AGE"],
                "weight": row["weight"] if not math.isnan(row["weight"]) else None,
                "new_inclusion": row["new_inclusion"],
                "transfer_in": row["transfer_in"],
                "return_to_care": row["return_to_care"],
                "tb_hiv": row["tb_hiv"],
                "hiv_type": row["hiv_type"],
                "treatment_line": row["treatment_line"],
                "last_dispensation_date": row["last_dispensation_date"],
                "days_dispensed": row["days_dispensed"],
                "regimen": row["REGIME"],
                "stable": row["stable"],
                "transfer_out": row["transfer_out"],
                "death": row["death"],
                "art_stoppage": row["art_stoppage"],
                "served_elsewhere": row["served_elsewhere"],
            }
        )

    # Create ActivePatientsList objects
    active_patients_list = []

    for row in data:
        active = not (row["transfer_out"] or row["art_stoppage"] or row["death"] or row["served_elsewhere"])
        next_dispensation_date = row["last_dispensation_date"] + timedelta(days=row["days_dispensed"])
        active_patients_list.append(
            ActivePatientsList(
                number=row["number"],
                region=row["region"],
                district=row["district"],
                code_ets=row["code_ets"],
                facility_name=row["facility_name"],
                period=row["period"],
                identifier_code=row["identifier_code"],
                sex=row["sex"],
                age=row["age"],
                weight=row["weight"],
                new_inclusion=row["new_inclusion"],
                transfer_in=row["transfer_in"],
                return_to_care=row["return_to_care"],
                tb_hiv=row["tb_hiv"],
                hiv_type=row["hiv_type"],
                treatment_line=row["treatment_line"],
                last_dispensation_date=row["last_dispensation_date"],
                days_dispensed=row["days_dispensed"],
                next_dispensation_date=next_dispensation_date,
                regimen=row["regimen"],
                stable=row["stable"],
                transfer_out=row["transfer_out"],
                death=row["death"],
                art_stoppage=row["art_stoppage"],
                served_elsewhere=row["served_elsewhere"],
                active=active,
                import_source=the_import,
                validation_status="waiting_for_validation",
                org_unit=the_import.org_unit,
            )
        )

    # Save the objects into the database
    ActivePatientsList.objects.bulk_create(active_patients_list)
