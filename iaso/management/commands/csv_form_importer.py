import csv
import json
from collections import defaultdict
from uuid import uuid4

from django.core.management.base import BaseCommand
from django.db import transaction

from iaso.models import OrgUnit, Instance, Form


class Command(BaseCommand):
    help = "Import a complete tree from a csv file"

    def add_arguments(self, parser):
        parser.add_argument("--csv_file", type=str)
        parser.add_argument("--mapping_csv_file", type=str)
        parser.add_argument("--template_json", type=str)
        parser.add_argument("--options_csv_file", type=str)
        parser.add_argument("--form_id", type=str)
        parser.add_argument("--limit", type=int, required=False)

    def handle(self, *args, **options):
        with transaction.atomic():
            file_name = options.get("csv_file")
            template_json = options.get("template_json")
            mapping_file_name = options.get("mapping_csv_file")
            options_file_name = options.get("options_csv_file")
            limit = options.get("limit", None)
            form_id = options.get("form_id")
            form = Form.objects.get(form_id=form_id)
            project = form.projects.first()
            mapping = {}

            f = open(template_json)
            template = json.loads(f.read())
            # print("template!", json.dumps(template, indent=2))
            with open(mapping_file_name, encoding="utf-8-sig") as mappingfile:
                mapping_csv_reader = csv.reader(mappingfile, delimiter=";")

                for row in list(mapping_csv_reader)[1:]:
                    print(row)
                    row_name = row[0].strip()
                    xls_form_id = row[1].strip()
                    question_type = row[2].strip()
                    formula = row[3].strip()
                    if xls_form_id.strip() or question_type == "multiselect":
                        mapping[row_name] = {"xls_form_id": xls_form_id}
                        mapping[row_name]["type"] = question_type
                        if formula:
                            mapping[row_name]["formula"] = formula

            option_mapping = defaultdict(dict)
            with open(options_file_name, encoding="utf-8-sig") as optionfile:
                option_csv_reader = csv.reader(optionfile, delimiter=",")
                for row in list(option_csv_reader)[1:]:
                    print(row)
                    option = row[1]
                    form_value = row[2]
                    xls_values = [v for v in row[3:] if v]
                    option_mapping[option][form_value] = {
                        # "type": t,
                        "question_id": form_value,
                        "values": xls_values,
                    }

            print("option_mapping", json.dumps(option_mapping, indent=2))
            # print("mapping", json.dumps(mapping, indent=2))

            keys = mapping.keys()
            # print(file_name)
            if True:
                with open(file_name, encoding="utf-8-sig") as csv_file:
                    csv_reader = csv.reader(csv_file, delimiter=";")
                    index = 1
                    for row in csv_reader:
                        if limit and index > limit:
                            break
                        if index % 1000 == 0:
                            print("index", index)

                        if index == 1:
                            headers = row
                            col_indices = {headers[i].strip(): i for i in range(len(headers))}
                            for key in col_indices:
                                if key not in keys:
                                    print("unmapped", key)
                            # print("col_indices", col_indices)
                        else:
                            source_ref = row[0].strip()
                            if not source_ref:
                                continue
                            data = template.copy()

                            for key in keys:
                                m = mapping[key]

                                formula = m.get("formula", None)
                                t = m.get("type", None)
                                # print("-%s-" % t, key)
                                # print(t, t == "select", t== "multiselect")
                                # print(key, formula, t)
                                if formula:
                                    formula = formula.strip()
                                    variables = formula.split("-")
                                    # print(formula)
                                    v1 = variables[0].strip()
                                    v2 = variables[1].strip()
                                    try:
                                        value = max(float(data[v1]) - float(data[v2]), 0)

                                        data[m["xls_form_id"]] = int(value)
                                        # print(formula, value)
                                    except Exception:
                                        pass
                                        # print("problems with values", v1, data[v1], v2, data[v2], e)

                                    # print(formula)
                                elif t == "select":
                                    value = row[col_indices[key]]
                                    if value:
                                        value = value.strip()
                                    # print("SELECT key, value", value)
                                    select_id = m["xls_form_id"]
                                    option_map = option_mapping[select_id]
                                    # print("option_map", option_map)

                                    for select, d in option_map.items():
                                        # print(select, d)
                                        if value in d["values"]:
                                            # print("FOUND FOUND", value, d["values"] )
                                            data[select_id] = select
                                            data[select] = 1
                                        else:
                                            # print("NOT FOUND", value, d["values"], select)
                                            data[select] = 0
                                elif t.strip() == "multiselect":
                                    # print("key", key)
                                    # print("MULTISELECT SAMA")
                                    local_mapping = option_mapping[key]
                                    # print("local_mapping", local_mapping)

                                    # print("option_map", option_map)
                                    # print("option_map", option_map)
                                    value = row[col_indices[key]]
                                    # print("key, value", key, value)
                                    for select, d in local_mapping.items():
                                        # print(select, d)
                                        for v in d["values"]:
                                            v = v.strip()
                                            if v in value:
                                                data[select] = 1
                                                # print("multiselect found ", select)

                                            else:
                                                data[select] = 0
                                                # print("multiselect NOT FOUND ", select)

                                    # print("type", t)
                                else:
                                    # print('key', key, m)
                                    try:
                                        value = row[col_indices[key]]
                                        value = value.strip()
                                        # print(m['xls_form_id'], value)

                                        if callable(getattr(value, "upper", None)):
                                            if value.upper() == "OUI":
                                                value = 1
                                                # print("oui")
                                            elif value.upper() == "NON":
                                                value = 0
                                                # print("non")

                                        data[m["xls_form_id"]] = value
                                        # print("value for %s %s %s" % (key, m['xls_form_id'], value, ))
                                    except Exception:  # FIXME: too broad exception
                                        pass
                                uuid = str(uuid4())
                                data["instanceID"] = "uuid:%s" % uuid

                            try:
                                # print(json.dumps(data, indent=2))
                                ou = OrgUnit.objects.get(source_ref=row[0].strip(), version_id=101)
                                # print("OU", ou)
                                instance = Instance()
                                instance.period = "2019"
                                instance.json = data
                                instance.uuid = uuid
                                instance.org_unit = ou
                                instance.form = form
                                instance.project = project
                                f_name = ("{}-{}".format(ou.name, uuid))[:96] + ".xml"
                                # print(f_name)
                                instance.file = f_name
                                instance.file_name = f_name
                                instance.save()
                                # print(instance.id)
                            except:
                                print("EXCEPTION!!!")
                                pass
                        index += 1
