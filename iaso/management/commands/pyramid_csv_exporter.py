import csv

from django.core.management.base import BaseCommand

from iaso.models import OrgUnit, OrgUnitType, DataSource, SourceVersion


class Command(BaseCommand):
    help = "Import a complete pyramid from a csv file"

    def add_arguments(self, parser):
        parser.add_argument("org_unit_csv_file", type=str)
        parser.add_argument("org_unit_type_csv_file", type=str)
        parser.add_argument("source_name", type=str)
        parser.add_argument("version", type=int)

    def handle(self, *args, **options):
        file_name = options.get("org_unit_csv_file")
        org_unit_file_name = options.get("org_unit_type_csv_file")
        source_name = options.get("source_name")
        version = options.get("version")

        source = DataSource.objects.get(name=source_name)
        version = SourceVersion.objects.get(number=version, data_source=source)

        type_ids = OrgUnit.objects.filter(version=version).values_list("org_unit_type_id", flat=True).distinct()
        types = OrgUnitType.objects.filter(id__in=type_ids)
        print(types)

        with open(org_unit_file_name, "w") as type_file:
            type_writer = csv.writer(type_file)
            for t in types:
                type_writer.writerow((t.id, t.name, ""))

        with open(file_name, "w") as units_file:
            writer = csv.writer(units_file)
            for t in OrgUnit.objects.filter(version=version).prefetch_related("org_unit_type").order_by("id"):
                writer.writerow(
                    (
                        t.source_ref if t.source_ref else "iaso_%d" % t.id,
                        t.name,
                        (
                            None
                            if t.parent is None
                            else (t.parent.source_ref if t.parent.source_ref else "iaso_%d" % t.parent.id)
                        ),
                        "",
                        t.org_unit_type.name,
                        t.geom if t.geom else t.simplified_geom,
                        t.location.x if t.location else None,
                        t.location.y if t.location else None,
                    )
                )
