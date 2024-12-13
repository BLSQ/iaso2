import csv
import json

from django.contrib.gis.geos import GEOSGeometry

from iaso.management.commands.command_logger import CommandLogger


def color(status):
    if status == "modified":
        return CommandLogger.YELLOW
    if status == "same":
        return CommandLogger.END
    if status == "new":
        return CommandLogger.GREEN
    if status == "deleted":
        return CommandLogger.RED
    return CommandLogger.END


class ShapelyJsonEncoder(json.JSONEncoder):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def default(self, obj):
        if hasattr(obj, "as_dict"):
            return obj.as_dict()
        return obj.wkt


class Dumper:
    def __init__(self, logger):
        self.iaso_logger = logger

    def dump_stats(self, diffs):
        stats_ou = {}

        for diff in diffs:
            if not diff.status in stats_ou:
                stats_ou[diff.status] = 1
            else:
                stats_ou[diff.status] += 1

        stats_comparison_by_field = {}

        for diff in diffs:
            for comp in diff.comparisons:
                if not comp.field in stats_comparison_by_field:
                    stats_comparison_by_field[comp.field] = {}
                comp_stats = stats_comparison_by_field[comp.field]
                if not comp.status in comp_stats:
                    comp_stats[comp.status] = {}
                if not "count" in comp_stats[comp.status]:
                    comp_stats[comp.status]["count"] = 1
                else:
                    comp_stats[comp.status]["count"] += 1
                comp_stats[comp.status]["sample"] = diff.org_unit.source_ref

        stats = {"orgUnits": stats_ou, "orgUnitsByField": stats_comparison_by_field}
        self.iaso_logger.info(json.dumps(stats, indent=4))
        return stats

    def dump_as_json(self, diffs):
        self.iaso_logger.info(json.dumps(diffs, indent=4, cls=ShapelyJsonEncoder))

    def dump_as_csv(self, diffs, fields, csv_file, number_of_parents=5):
        res = []

        header = ["externalId", "diff status", "type"]

        diffable_fields = []
        for field in fields:
            if field.startswith("groupset:") or field.startswith("group:"):
                diffable_fields.append(field.split(":")[2])
            else:
                diffable_fields.append(field)
        for field in diffable_fields:
            header.extend((field, field + " before", field + " after"))
            if field == "geometry":
                header.append("distance diff (KM)")
        for i in range(1, number_of_parents + 1):
            header.extend(["parent %d name before" % i, "parent %d name after" % i])
        res.append(header)

        for diff in diffs:
            results = [
                diff.org_unit.source_ref,
                diff.status,
                diff.org_unit.org_unit_type.name if diff.org_unit and diff.org_unit.org_unit_type else "",
            ]
            for field in fields:
                comparison = list(filter(lambda x: x.field == field, diff.comparisons))[0]
                results.append(comparison.status)
                if field != "geometry":
                    results.append(str(comparison.before))
                    results.append(str(comparison.after))
                else:
                    if "MULTIPOLYGON" in str(comparison.before) or "MULTIPOLYGON" in str(comparison.after):
                        results.append(str(comparison.before)[:40])
                        results.append(str(comparison.after)[:40])
                    else:
                        results.append(str(comparison.before))
                        results.append(str(comparison.after))
                    # Add distance between two points
                    if "POINT Z" in str(comparison.before) and comparison.after:
                        if str(comparison.before)[:40] != str(comparison.after)[:40]:
                            results.append(
                                "{:.3f}".format(
                                    GEOSGeometry(comparison.before).distance(GEOSGeometry(str(comparison.after))) * 100
                                )
                            )
                        else:
                            results.append(0)
                    else:
                        if not comparison.before and not comparison.after:
                            results.append("")
                        else:
                            results.append("NA")

            current_dhis2 = diff.orgunit_dhis2
            current_ref = diff.orgunit_ref
            for i in range(number_of_parents):
                if current_dhis2:
                    current_dhis2 = current_dhis2.parent
                results.append(current_dhis2.name if current_dhis2 else None)
                if current_ref:
                    current_ref = current_ref.parent
                results.append(current_ref.name if current_ref else None)

            res.append(results)
        writer = csv.writer(csv_file)
        for row in res:
            writer.writerow(row)

    def dump_as_table(self, diffs, fields, stats):
        display = []
        header = ["externalId", "name", "ou status"]
        fields = list(
            set(
                list(filter(lambda f: "modified" in stats["orgUnitsByField"][f], fields))
                + list(filter(lambda f: "new" in stats["orgUnitsByField"][f], fields))
            )
        )
        for field in fields:
            if field.startswith("groupset:"):
                header.append(field.split(":")[2])
            else:
                header.append(field)

        display.append(header)
        for diff in diffs:
            if diff.status != "same":
                results = [diff.org_unit.source_ref, diff.org_unit.name, diff.status]

                for field in fields:
                    comparison = list(filter(lambda x: x.field == field, diff.comparisons))[0]
                    if comparison.status == "same":
                        results.append("same")
                    else:
                        results.append(
                            self.iaso_logger.colorize(
                                " vs ".join([str(comparison.before), str(comparison.after)])
                                + ((" Dist : %.2f " % comparison.distance) if comparison.distance else ""),
                                color(comparison.status),
                            )
                        )

                display.append(results)

        for d in display:
            message = "\t".join(map(lambda s: self.iaso_logger.colorize(str(s).ljust(20, " "), color(s)), d))
            if d[2] == "new":
                self.iaso_logger.info(self.iaso_logger.colorize(message, CommandLogger.GREEN))
            elif d[2] == "modified":
                self.iaso_logger.info(self.iaso_logger.colorize(message, CommandLogger.RED))
            else:
                self.iaso_logger.info(message)
