import itertools
import json
import logging
from timeit import default_timer as timer

from dhis2 import Api
from dhis2 import RequestException
from django.core.paginator import Paginator
from django.utils import timezone

import iaso.models as models
from iaso.models import OrgUnit, MappingVersion, ExportLog, RUNNING, ERRORED, EXPORTED
from .api_logger import ApiLogger  # type: ignore
from .value_formatter import format_value
from ..periods import Period

logger = logging.getLogger(__name__)


class InstanceExportError(BaseException):
    def __init__(self, *args):
        self.counts = args[1]
        self.descriptions = args[2]
        description = self.descriptions[0] if len(self.descriptions) > 0 else ""
        self.message = str(args[0]) + " : " + description

    def __str__(self):
        return "InstanceExportError, {} ".format(self.message)


def get_event_date(instance, form_mapping):
    event_date_source = MappingVersion.get_event_date_source(form_mapping)

    if event_date_source == MappingVersion.EVENT_DATE_SOURCE_FROM_SUBMISSION_CREATED_AT:
        return instance.source_created_at_with_fallback.strftime("%Y-%m-%d")
    if event_date_source == MappingVersion.EVENT_DATE_SOURCE_FROM_SUBMISSION_PERIOD:
        dhis2_period = Period.from_string(instance.period)
        start = dhis2_period.start_date().strftime("%Y-%m-%d")
        return start
    raise ValueError("unsupported event date source type '" + event_date_source + "'")


def uniquify(seq, idfun=None):
    if idfun is None:

        def idfun(x):
            return x

    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker not in seen:
            seen[marker] = 1
            result.append(item)

    return result


class BaseHandler:
    def __init__(self, *args):
        self.logger = logger

    def orgunit_resolver(self, orgunit_id):
        if orgunit_id.isnumeric():
            # should we enforce accounts ?
            # if it's a number then look up by id
            return OrgUnit.objects.filter(id=orgunit_id).first().source_ref

        # keep old behaviour eg : entity attribute generated based on instance.org_unit
        return orgunit_id


class AggregateHandler(BaseHandler):
    def handle_exception(self, resp, message):
        response = resp["response"]
        counts = {}
        descriptions = []

        if "importCount" in response:
            for count_type in ("imported", "updated", "deleted", "ignored"):
                counts[count_type] = response["importCount"][count_type]
        if response["status"] == "ERROR":
            if "description" in response:
                descriptions.append(response["description"])
            if "message" in response:
                descriptions.append(response["message"])

        # version < 2.38, a normal payload is sent with 200
        if "conflicts" in response:
            descriptions = [m["value"] for m in response["conflicts"]]

        # 2.38 nesting conflicts in response with 409
        if "response" in response and "conflicts" in response["response"]:
            descriptions = [m["value"] for m in response["response"]["conflicts"]]

        descriptions = uniquify(descriptions)
        if len(descriptions) > 0:
            self.logger.warn(
                "----------------------- aggregate EXPORT ERROR --------------------\n"
                + "Failed to create dataValueSets got {} {} {}".format(message, counts, descriptions)
            )
            return InstanceExportError(message, counts, descriptions)

        return None

    def map_to_values(self, instance, form_mapping, export_status=None, related_data=None):
        created_at = instance.source_created_at if instance.source_created_at else instance.created_at
        data_set_entry = {
            "dataSet": form_mapping["data_set_id"],
            "completeDate": created_at.strftime("%Y-%m-%d"),
            "period": instance.period,
            "orgUnit": instance.org_unit.source_ref,
            "dataValues": [],
        }

        answers = related_data if related_data else instance.json

        errored = False
        mapping_errors = []
        question_mappings = form_mapping["question_mappings"]
        for question_key in answers.keys():
            if question_key in question_mappings:
                try:
                    data_element = question_mappings[question_key]
                    if data_element.get("type") == MappingVersion.QUESTION_MAPPING_NEVER_MAPPED:
                        continue

                    data_element["question_key"] = question_key
                    raw_value = answers[question_key]
                    data_value = {
                        "dataElement": data_element["id"],
                        "value": format_value(data_element, raw_value, self.orgunit_resolver),
                        "comment": str(instance.id) + " " + str(raw_value) + " " + question_key,
                    }
                    if "categoryOptionCombo" in data_element:
                        data_value["categoryOptionCombo"] = data_element["categoryOptionCombo"]

                    if "attributeOptionCombo" in data_element:
                        data_value["attributeOptionCombo"] = data_element["attributeOptionCombo"]
                    data_set_entry["dataValues"].append(data_value)
                except Exception as error:
                    errored = True
                    mapping_errors.append([question_key, error])
                    self.logger.warn("ERROR Mapping {} {}".format(error, question_key))
        if errored:
            return (None, mapping_errors)
        else:
            return (data_set_entry, None)

    def export_page(self, prefix, data, export_statuses, stats, api):
        if len(data) == 0:
            stats["batched_time"] = 0
            return []

        export_log = self.export_page_values(prefix, data, export_statuses, stats, api)
        export_log_complete_ds = self.mark_dataset_as_complete(data, api)
        return [export_log, export_log_complete_ds]

    def mark_dataset_as_complete(self, data, api):
        def to_complete_data_set_registration(data_value_set):
            return {
                "period": data_value_set["period"],
                "dataSet": data_value_set["dataSet"],
                "organisationUnit": data_value_set["orgUnit"],
                "date": data_value_set["completeDate"],
            }

        complete_data_set_registrations = list(map(to_complete_data_set_registration, data))
        request = {"completeDataSetRegistrations": complete_data_set_registrations}
        resp_complete = api.post("completeDataSetRegistrations", request)
        self.logger.debug("completeDataSetRegistrations response %s" % resp_complete.text)
        export_log = ExportLog()
        export_log.sent = request
        try:
            export_log.received = resp_complete.json()
        except:
            print("problem in making datset complete")
        export_log.url = api.base_url + "/completeDataSetRegistrations"
        export_log.save()
        return export_log

    def flatten(self, data):
        flattened = []
        for agg in data:
            for dv in agg["dataValues"]:
                dv["orgUnit"] = agg["orgUnit"]
                dv["period"] = agg["period"]
                flattened.append(dv)
        return flattened

    def export_log_on(self, status, export_status, export_logs):
        export_status.status = status
        for export_log in export_logs:
            export_status.export_logs.add(export_log)
        export_status.save()

    def export_page_values(self, prefix, data, export_statuses, stats, api):
        try:
            # print(prefix, "POSTING to dataValueSets {} ".format(request))
            batched_start = timer()

            request = {"dataValues": self.flatten(data)}
            resp = api.post("dataValueSets", request).json()
            exception = self.handle_exception({"response": resp}, "transient")
            if exception:
                # fake it to behave like a bad request
                raise RequestException(409, api.base_url + "/dataValueSets", json.dumps(resp))

            batched_end = timer()
            batched_time = batched_end - batched_start
            stats["batched_time"] = batched_time
            self.logger.debug(prefix + str(resp))

            export_log = ExportLog()
            export_log.sent = request
            export_log.received = resp
            export_log.url = api.base_url + "/dataValueSets"
            export_log.http_status = 200
            export_log.save()

            return export_log

        except RequestException as dhis2_exception:
            message = "ERROR while processing " + prefix
            try:
                resp = json.loads(dhis2_exception.description)
            except:
                resp = {"status": "ERROR", "description": "non json response return by server"}

            exception = self.handle_exception({"response": resp}, message)

            export_log = ExportLog()
            export_log.sent = request
            export_log.received = resp
            export_log.http_code = dhis2_exception.code
            export_log.save()

            for export_status in export_statuses:
                self.export_log_on(ERRORED, export_status, [export_log])

            raise exception


class EventHandler(BaseHandler):
    def map_to_values(self, instance, form_mapping, export_status=None):
        event = {
            "program": form_mapping["program_id"],
            "event": instance.export_id,
            "orgUnit": instance.org_unit.source_ref,
            "eventDate": get_event_date(instance, form_mapping),
            "status": "COMPLETED",
            "dataValues": [],
        }
        if instance.location:
            event["coordinate"] = {"latitude": instance.location.y, "longitude": instance.location.x}
        errored = False
        event_errors = []
        question_mappings = form_mapping["question_mappings"]

        if instance.org_unit.source_ref == "" or instance.org_unit.source_ref is None:
            errored = True
            event_errors.append(
                [
                    "orgUnit",
                    Exception(
                        "unknown orgunit in dhis2 : "
                        + str(instance.org_unit.name)
                        + "("
                        + str(instance.org_unit.name)
                        + ")"
                    ),
                ]
            )
            self.logger.error(str(event_errors))

        questions_by_name = export_status.mapping_version.form_version.questions_by_name()

        for question_key in instance.json.keys():
            if question_key in questions_by_name and questions_by_name[question_key]["type"] == "select all that apply":
                question = questions_by_name[question_key]
                for choice in question["children"]:
                    choice_key = question_key + "__" + choice["name"]
                    if choice_key in question_mappings:
                        choice_mapping = question_mappings[choice_key]
                        if choice_mapping:
                            raw_value = instance.json[question_key]
                            raw_values = raw_value.split(" ")
                            boolval = "1" if (choice["name"] in raw_values) else "0"
                            data_value = {
                                "dataElement": choice_mapping["id"],
                                "value": format_value(choice_mapping, boolval, self.orgunit_resolver),
                            }
                            event["dataValues"].append(data_value)

            if question_key in question_mappings:
                try:
                    data_element = question_mappings[question_key]
                    if data_element.get("type") == MappingVersion.QUESTION_MAPPING_NEVER_MAPPED:
                        continue
                    data_element["question_key"] = question_key
                    raw_value = instance.json[question_key]

                    if data_element.get("type") == MappingVersion.QUESTION_MAPPING_MULTIPLE:
                        raw_values = raw_value.split(" ")

                        for value in data_element["values"]:
                            mapping_de = data_element["values"][value]
                            boolval = "1" if (value in raw_values) else "0"
                            data_value = {
                                "dataElement": mapping_de["id"],
                                "value": format_value(mapping_de, boolval, self.orgunit_resolver),
                                # "debug": str(raw_value) + " " + question_key,
                            }
                            event["dataValues"].append(data_value)
                    else:
                        data_value = {
                            "dataElement": data_element["id"],
                            "value": format_value(data_element, raw_value, self.orgunit_resolver),
                            # "debug": str(raw_value) + " " + question_key,
                        }
                        event["dataValues"].append(data_value)
                except Exception as error:
                    errored = True
                    event_errors.append([question_key, error])
                    self.logger.error("ERROR Mapping" + str(error) + "question_key" + question_key)

        if errored:
            return (None, event_errors)
        else:
            return (event, None)

    def export_page(self, prefix, data, export_statuses, stats, api):
        if len(data) == 0:
            stats["batched_time"] = 0
            return []

        try:
            payload = {"events": data}
            self.logger.debug(json.dumps(payload, indent=2))
            resp = api.post("events", payload).json()
            self.logger.debug(str(resp))

            exception = self.handle_exception({"response": resp}, "transient")
            if exception:
                # fake it to behave like a bad request
                raise RequestException(409, api.base_url + "/dataValueSets", json.dumps(resp))

            export_log = ExportLog()
            export_log.sent = payload
            export_log.received = resp
            export_log.url = api.base_url + "/events"
            export_log.http_status = 200
            export_log.save()

            return [export_log]
        except RequestException as dhis2_exception:
            message = "ERROR while processing " + prefix
            resp = json.loads(dhis2_exception.description)
            exception = self.handle_exception(resp, message)

            raise exception

    def handle_exception(self, resp, message):
        response = resp["response"]
        if response["status"] == "ERROR":
            counts = {}

            for count_type in ("imported", "updated", "deleted", "ignored"):
                counts[count_type] = response.get(count_type, 0)
            import_summaries = response.get("importSummaries") or response["response"]["importSummaries"]
            descriptions = [m["description"] for m in import_summaries if "description" in m]
            conflicts = [m["conflicts"] for m in import_summaries if "conflicts" in m]
            descriptions = uniquify(descriptions)
            self.logger.error("---------------------------------------------------------")
            self.logger.error("----------------------- EXPORT ERROR --------------------")
            self.logger.error("Failed to create events got" + str(descriptions) + str(conflicts) + str(resp))
            if len(descriptions) == 0:
                descriptions = [json.dumps(conflicts)]
            return InstanceExportError(message, counts, descriptions)


class EventTrackerHandler(BaseHandler):
    def get_instance_value(self, instance, question_key, mapping, answers):
        raw_value = answers[question_key]
        if "iaso_field" in mapping:
            if mapping["iaso_field"] == "instance.org_unit.source_ref":
                raw_value = instance.org_unit.source_ref

        return raw_value

    def get_status(self, instance, program_stage_id, form_mapping):
        status = "COMPLETED"
        key = f"status_{program_stage_id}"

        if key in instance.json:
            status = instance.json[key].upper()

        return status

    def map_to_values(self, instance, form_mapping, export_status=None, related_data=None):
        answers = related_data if related_data else instance.json

        question_mappings = form_mapping["question_mappings"]

        program_id = form_mapping["program_id"]
        orgunit_id = instance.org_unit.source_ref
        tracked_entity_type = form_mapping["tracked_entity_type"]

        program_stage_ids = []
        for question_name in form_mapping["question_mappings"]:
            for mapping in question_mappings[question_name]:
                if "programStage" in mapping:
                    program_stage_id = mapping["programStage"]
                    if program_stage_id not in program_stage_ids:
                        program_stage_ids.append(program_stage_id)

        event_date = get_event_date(instance, form_mapping)
        events = []
        errored = False

        for program_stage_id in program_stage_ids:
            event = {
                "program": form_mapping["program_id"],
                "programStage": program_stage_id,
                "orgUnit": instance.org_unit.source_ref,
                "eventDate": event_date,
                "status": self.get_status(instance, program_stage_id, form_mapping),
                "dataValues": [],
            }
            if instance.location:
                event["coordinate"] = {"latitude": instance.location.y, "longitude": instance.location.x}

            event_errors = []

            for question_key in form_mapping["question_mappings"]:
                if question_key in answers.keys():
                    for mapping in question_mappings[question_key]:
                        if "programStage" in mapping and mapping["programStage"] == program_stage_id:
                            if "dataElement" in mapping:
                                data_element = mapping["dataElement"]
                                raw_value = self.get_instance_value(instance, question_key, mapping, answers)

                                data_value = {
                                    "dataElement": data_element["id"],
                                    "value": format_value(data_element, raw_value, self.orgunit_resolver),
                                }

                                event["dataValues"].append(data_value)
            if len(event["dataValues"]) > 0:
                events.append(event)
            else:
                self.logger.debug(f"skipping event for stage {program_stage_id} in #{instance.id} no data")

        tracked_entity_with_events = {
            "orgUnit": orgunit_id,
            "trackedEntityType": tracked_entity_type,
            "attributes": [],
            "enrollments": [
                {
                    "trackedEntityType": tracked_entity_type,
                    "enrollmentDate": event_date,
                    "program": program_id,
                    "deleted": False,
                    "incidentDate": event_date,
                    "orgUnit": orgunit_id,
                    "events": events,
                }
            ],
        }

        for question_key in form_mapping["question_mappings"]:
            if question_key in answers.keys():
                for mapping in question_mappings[question_key]:
                    if "trackedEntityAttribute" in mapping:
                        tea = mapping["trackedEntityAttribute"]
                        raw_value = self.get_instance_value(instance, question_key, mapping, answers)
                        attribute = {
                            "attribute": tea["id"],
                            "value": format_value(tea, raw_value, self.orgunit_resolver),
                            "displayName": tea["name"],
                            "valueType": tea["valueType"],
                        }

                        tracked_entity_with_events["attributes"].append(attribute)

        if errored:
            return (None, event_errors)
        else:
            return ((instance, form_mapping, tracked_entity_with_events, export_status), None)

    def find_tracked_entity(
        self, api, country_dhis2_id, tracked_entity_type, unique_number_attribute_id, unique_number
    ):
        resp = api.get(
            "trackedEntityInstances",
            params={
                "fields": ":all,enrollments[:all,events[:all]]",
                "ou": country_dhis2_id,
                "ouMode": "DESCENDANTS",
                "trackedEntityType": tracked_entity_type,
                "filter": f"{unique_number_attribute_id}:EQ:{str(unique_number)}",
            },
        ).json()

        return self.get_first(resp["trackedEntityInstances"])

    def update_tracked_entity(self, api, tracked_entity):
        # print("update_tracked_entity", json.dumps(tracked_entity))
        resp = api.put("trackedEntityInstances/" + tracked_entity["trackedEntityInstance"], tracked_entity).json()
        self.logger.debug(str(resp))

        return resp

    def create_tracked_entity(self, api, tracked_entity):
        self.logger.debug("create_tracked_entity" + json.dumps(tracked_entity))
        resp = api.post("trackedEntityInstances", tracked_entity).json()

        self.logger.debug(str(resp))

        return resp

    def get_first(self, iterable, default=None):
        if iterable:
            for item in iterable:
                return item
        return default

    def generate_unique_number(self, api, unique_number_attribute_id, org_unit):
        org_unit_dhis2 = api.get(f"organisationUnits/{org_unit.source_ref}", params={"fields": "id,name,code"}).json()
        generated = api.get(
            f"trackedEntityAttributes/{unique_number_attribute_id}/generate",
            params={"ORG_UNIT_CODE": org_unit_dhis2["code"]},
        ).json()
        self.logger.debug("generate_unique_number" + str(generated))
        return generated["value"]

    def export_page(self, prefix, data, export_statuses, stats, raw_api):
        if len(data) == 0:
            stats["batched_time"] = 0
            return []
        api = ApiLogger(raw_api)

        for item in data:
            try:
                instance = item[0]
                form_mapping = item[1]
                tracked_entity_iaso = item[2]
                export_status = item[3]
                unique_number_attribute_id = form_mapping["tracked_entity_identifier"]
                country_dhis2_id = instance.org_unit.source_path().split("/")[1]

                parent_tei_uid = self.export_record(
                    api,
                    instance,
                    form_mapping,
                    tracked_entity_iaso,
                    export_status,
                    unique_number_attribute_id,
                    country_dhis2_id,
                )

                question_mappings = form_mapping["question_mappings"]
                for repeat_group in export_status.mapping_version.form_version.repeat_groups():
                    repeat_group_name = repeat_group["name"]
                    if repeat_group_name in question_mappings:
                        subform_mapping = question_mappings[repeat_group_name][0]
                        subform_mapping["question_mappings"] = {}
                        for question_name in question_mappings:
                            question_mapping = question_mappings[question_name]
                            if (
                                question_mapping != {"type": "neverMapped"}
                                and question_mapping[0].get("parent") == repeat_group_name
                            ):
                                subform_mapping["question_mappings"][question_name] = question_mapping

                        if repeat_group_name in instance.json:
                            for related_data in instance.json[repeat_group_name]:
                                mapped = self.map_to_values(
                                    instance, subform_mapping, export_status=export_status, related_data=related_data
                                )
                                unique_number_attribute_id = subform_mapping["tracked_entity_identifier"]
                                tracked_entity_iaso = mapped[0][2]
                                self.logger.debug("SUB form mapped to " + str(tracked_entity_iaso))
                                # export_record
                                related_tei_uid = self.export_record(
                                    api,
                                    instance,
                                    subform_mapping,
                                    tracked_entity_iaso,
                                    export_status,
                                    unique_number_attribute_id,
                                    country_dhis2_id,
                                )
                                # create relationship
                                if "relationship_type" in subform_mapping:
                                    relation_ship = {
                                        "relationshipType": subform_mapping["relationship_type"],
                                        "from": {"trackedEntityInstance": {"trackedEntityInstance": parent_tei_uid}},
                                        "to": {"trackedEntityInstance": {"trackedEntityInstance": related_tei_uid}},
                                    }
                                    api.post("relationships", relation_ship)

                export_logs = api.pop_export_logs()

                self.flag_as_exported(export_status, stats, export_logs)

            except RequestException as dhis2_exception:
                export_logs = api.pop_export_logs()
                for export_log in export_logs:
                    export_log.save()
                    export_status.export_logs.add(export_log)

                export_status.save()

                message = "ERROR while processing " + prefix

                resp = json.loads(dhis2_exception.description)

                exception = self.handle_exception(resp, message)
                self.flag_as_errored(export_status, exception.message, stats)

        return []

    def export_record(
        self,
        api,
        instance,
        form_mapping,
        tracked_entity_iaso,
        export_status,
        unique_number_attribute_id,
        country_dhis2_id,
    ):
        unique_number = self.get_first(
            [
                attribute["value"]
                for attribute in tracked_entity_iaso["attributes"]
                if attribute["attribute"] == unique_number_attribute_id
            ]
        )
        self.logger.debug("looking for" + unique_number_attribute_id, "in " + str(tracked_entity_iaso["attributes"]))
        self.logger.debug(str(instance.id) + "unique number ?" + str(unique_number))
        if unique_number:
            tracked_entity_dhis2 = self.find_tracked_entity(
                api, country_dhis2_id, form_mapping["tracked_entity_type"], unique_number_attribute_id, unique_number
            )
            if tracked_entity_dhis2:
                # copy the new events in the first enrollment
                for event in tracked_entity_iaso["enrollments"][0]["events"]:
                    tracked_entity_dhis2["enrollments"][0]["events"].append(event)
                self.update_tracked_entity(api, tracked_entity_dhis2)
                return tracked_entity_dhis2["trackedEntityInstance"]
            else:
                raise Exception(f"error : no tracked entity with unique number : {unique_number}")
        else:
            unique_number = self.generate_unique_number(api, unique_number_attribute_id, instance.org_unit)

            self.logger.debug(str(instance.id) + "unique number ?" + str(unique_number))

            unique_number_attribute = self.get_first(
                [
                    attribute
                    for attribute in tracked_entity_iaso["attributes"]
                    if attribute["attribute"] == unique_number_attribute_id
                ]
            )
            if unique_number_attribute:
                unique_number_attribute["value"] = unique_number
            else:
                tracked_entity_iaso["attributes"].append(
                    {"attribute": unique_number_attribute_id, "value": unique_number}
                )

            tracked_entity_resp = self.create_tracked_entity(api, tracked_entity_iaso)
            return tracked_entity_resp["response"]["importSummaries"][0]["reference"]

    def flag_as_exported(self, export_status, stats, export_logs):
        export_request = export_status.export_request

        stats["exported_count"] += 1
        export_status.status = EXPORTED
        for export_log in export_logs:
            export_log.save()
            export_status.export_logs.add(export_log)
        export_status.save()

        instance = export_status.instance
        instance.last_export_success_at = timezone.now()
        instance.save()

        export_request.errored_count = stats["errored_count"]
        export_request.exported_count = stats["exported_count"]
        export_request.save()

    def handle_exception(self, resp, message):
        if not "response" in resp and resp["status"] == "ERROR":
            final_message = message + resp["message"]
            return InstanceExportError(final_message, {}, [final_message])

        response = resp["response"]

        if response["status"] == "ERROR":
            counts = {}

            for count_type in ("imported", "updated", "deleted", "ignored"):
                counts[count_type] = response.get(count_type, 0)
            import_summaries = response.get("importSummaries") or response["response"]["importSummaries"]
            descriptions = [m["description"] for m in import_summaries if "description" in m]
            conflicts = [m["conflicts"] for m in import_summaries if "conflicts" in m]
            descriptions = uniquify(descriptions)
            if len(descriptions) == 0:
                descriptions = [conflicts[0][0]["value"]]
            self.logger.error("---------------------------------------------------------")
            self.logger.error("----------------------- EXPORT ERROR --------------------")
            self.logger.error(
                "Failed to create events got" + str(descriptions) + "conflicts " + str(conflicts) + "resp " + str(resp)
            )
            return InstanceExportError(message, counts, descriptions)

    def flag_as_errored(self, export_status, message, stats):
        stats["errored_count"] += 1
        export_status.status = ERRORED
        export_status.last_error_message = message
        export_status.save()


class DataValueExporter:
    def __init__(self):
        self.form_mappings_cache = {}
        self.api_cache = {}
        self.handlers = {
            models.AGGREGATE: AggregateHandler(),
            models.EVENT: EventHandler(),
            models.EVENT_TRACKER: EventTrackerHandler(),
        }

    def get_api(self, mapping_version):
        if not mapping_version.id in self.api_cache:
            credentials = mapping_version.mapping.data_source.credentials
            self.api_cache[mapping_version.id] = Api(credentials.url, credentials.login, credentials.password)
        return self.api_cache[mapping_version.id]

    def export_log_on(self, status, export_status, export_logs):
        export_status.status = status
        for export_log in export_logs:
            export_status.export_logs.add(export_log)
        export_status.save()

    def map_page_to_data_values(self, prefix, export_statuses, skipped):
        data = {models.AGGREGATE: [], models.EVENT: [], models.EVENT_TRACKER: []}

        for export_status in export_statuses:
            instance = export_status.instance

            form_mapping = export_status.mapping_version

            if not instance.json:
                skipped.append((instance.id, "no data json"))
                continue

            if not form_mapping:
                skipped.append((instance.id, "no mapping"))
                continue

            (values, map_errors) = self.handlers[form_mapping.mapping.mapping_type].map_to_values(
                instance, form_mapping.json, export_status
            )

            if map_errors:
                message = "ERROR while processing " + prefix + ", instance_id %d" % (instance.id,)
                exception = InstanceExportError(message, {}, list(map(lambda x: x[0] + " " + str(x[1]), map_errors)))

                raise exception
            else:
                data[form_mapping.mapping.mapping_type].append(values)
        return data

    def flag_as_errored(self, export_request, export_statuses, message, stats):
        for export_status in export_statuses:
            stats["errored_count"] += len(export_statuses)
            export_status.status = ERRORED
            export_status.save()

        export_request.exportstatus_set.filter(status="QUEUED").update(status="SKIPPED")

        export_request.status = ERRORED
        export_request.ended_at = timezone.now()
        export_request.finished = True
        export_request.errored_count = stats["errored_count"]
        export_request.exported_count = stats["exported_count"]
        export_request.last_error_message = message
        export_request.save()

    def flag_as_exported(self, export_request, export_statuses, stats, export_logs):
        stats["exported_count"] += len(export_statuses)
        for export_status in export_statuses:
            self.export_log_on(EXPORTED, export_status, export_logs)

        for export_status in export_statuses:
            instance = export_status.instance
            instance.last_export_success_at = timezone.now()
            instance.to_export = False
            instance.save()

        export_request.errored_count = stats["errored_count"]
        export_request.exported_count = stats["exported_count"]
        export_request.save()

    def export_instances(self, export_request, page_size=25, continue_on_error=False):
        export_request.status = RUNNING
        export_request.started_at = timezone.now()
        export_request.continue_on_error = continue_on_error
        export_request.save()

        paginator = Paginator(
            export_request.exportstatus_set.prefetch_related("mapping_version")
            .prefetch_related("instance")
            .prefetch_related("instance__org_unit")
            .prefetch_related("instance__org_unit__version")
            .order_by("id")
            .all(),
            page_size,
        )
        if paginator.count == 0:
            logger.warning(f"Not linked error status for {export_request}")

        skipped = []
        stats = {"exported_count": 0, "errored_count": 0}
        export_statuses = []
        for page in range(1, paginator.num_pages + 1):
            page_start = timer()
            prefix = "page %d/%d" % (page, paginator.num_pages)

            try:
                export_statuses = paginator.page(page).object_list
                if len(export_statuses) == 0:
                    logger.warning(f"Empty page {page} for {export_request}")
                    continue
                data = self.map_page_to_data_values(prefix, export_statuses, skipped)
                api = self.get_api(export_statuses[0].mapping_version)

                export_logs_aggregate = self.handlers[models.AGGREGATE].export_page(
                    prefix, data[models.AGGREGATE], export_statuses, stats, api
                )

                export_logs_event = self.handlers[models.EVENT].export_page(
                    prefix, data[models.EVENT], export_statuses, stats, api
                )

                self.handlers[models.EVENT_TRACKER].export_page(
                    prefix, data[models.EVENT_TRACKER], export_statuses, stats, api
                )

                if len(data[models.EVENT_TRACKER]) == 0:
                    export_logs = list(itertools.chain(export_logs_aggregate, export_logs_event))
                    self.flag_as_exported(export_request, export_statuses, stats, export_logs)

                page_end = timer()
                page_time = page_end - page_start
                logger.debug(
                    prefix
                    + " in %1.2f sec (dhis2 time %1.2f batched): %d skipped"
                    % (page_time, stats["batched_time"], len(skipped))
                )

            except InstanceExportError as exception:
                self.flag_as_errored(export_request, export_statuses, exception.message, stats)
                if not export_request.continue_on_error:
                    raise exception

            # it's ok to catch BaseException, we want to be able to mark it as errored if cancelled or worst
            except BaseException as exception:
                self.flag_as_errored(
                    export_request, export_statuses, repr(exception) + " : " + type(exception).__name__, stats
                )
                raise exception

        export_request.status = EXPORTED if stats["errored_count"] == 0 else ERRORED
        export_request.finished = True
        export_request.errored_count = stats["errored_count"]
        export_request.exported_count = stats["exported_count"]
        export_request.ended_at = timezone.now()
        export_request.save()
