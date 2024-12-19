from argparse import ArgumentParser
from django.core.management.base import BaseCommand
import pandas as pd
import math
import uuid
from django.utils.timezone import now

from iaso.management.commands.command_logger import CommandLogger

from plugins.active_list.models import Import, ActivePatientsList
from iaso.models import OrgUnit

from logging import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    help = """Testing the import of a list of active patients from an Excel file"""

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--name", type=str, required=False, help="Campaign obr name")

    def handle(self, name=None, *args, **options):
        pd.set_option("display.max_rows", None)
        pd.set_option("display.max_columns", None)

        # Read the CSV file into a DataFrame
        df = pd.read_excel("plugins/active_list/sample_data/sample-file-active.xlsx", sheet_name=0)

        # Rename columns
        df = df.rename(
            columns={
                "N°": "number",
                "CODE ETS": "code_ets",
                "NOM ETABLISSEMENT": "facility_name",
                "Periode": "period",
                "CODE IDENTIFIANT": "identifier_code",
                "SEXE": "sex",
                "POIDS": "weight",
                "Nouvelle inclusion": "new_inclusion",
                "Transfert-In": "transfer_in",
                "Retour dans les soins": "return_to_care",
                "TB / VIH": "tb_hiv",
                "Type de VIH": "hiv_type",
                "Ligne therapeuthique": "treatment_line",
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
        df["stable"] = df["stable"].map({"Oui": True, "Non": False})
        df["sex"] = df["sex"].map({"F": "FEMALE", "M": "MALE"})
        df["treatment_line"] = df["treatment_line"].map(
            {"1er Ligne": "1STLINE", "2e Ligne": "2NDLINE", "3e Ligne": "3RDLINE"}
        )
        df["hiv_type"] = df["hiv_type"].map({"1": "HIV1", "2": "HIV2", "1&2": "HIV 1&2"})

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
                    "facility_name": row["facility_name"],
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

        # Create Import object
        import_obj = Import.objects.create(
            org_unit_id=1,
            month="2024-06-01",
            source="excel",
            hash_key="abc12345",
            file_name="sample-file-active.xlsx-3-4" + uuid.uuid4().hex,
            file_check="def67890",
        )

        # Create ActivePatientsList objects
        active_patients_list = []
        index = 0
        for row in data:
            active_patients_list.append(
                ActivePatientsList(
                    number=index,
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
                    regimen=row["regimen"],
                    stable=row["stable"],
                    transfer_out=row["transfer_out"],
                    death=row["death"],
                    art_stoppage=row["art_stoppage"],
                    served_elsewhere=row["served_elsewhere"],
                    active=True,
                    import_source=import_obj,
                    validation_status="waiting_for_validation",
                    org_unit=OrgUnit.objects.get(id=47140),
                )
            )
            index = index + 1

        # Save the objects into the database
        ActivePatientsList.objects.bulk_create(active_patients_list)
