import pathlib
import typing
from io import BytesIO

from django.utils import timezone, dateparse
from pyxform import create_survey_from_xls, errors, Survey as BaseSurvey  # type: ignore


class ParsingError(Exception):
    pass


class Survey:
    """Container class for pyxform survey.
    Used for xml/json conversion.
    """

    def __init__(self, survey: BaseSurvey, *, xls_file_name: str):
        self._survey = survey
        self._xls_file_name = xls_file_name

    def to_xml(self):
        xml_file_content = self._survey.to_xml(validate=False)

        return xml_file_content.encode("utf-8")

    def to_json(self):
        return self._survey.to_json_dict()

    def generate_file_name(self, extension: str):
        xls_path = pathlib.Path(self._xls_file_name)

        return f"{xls_path.stem}.{extension}"

    @property
    def form_id(self):
        return self._survey.id_string

    @property
    def version(self):
        return self._survey.version


def to_json_dict(form_version):  # TODO: remove
    if not form_version.xls_file:
        return None
    try:
        # Since version 2.1.0, pyxform expects a path or a bytes | BytesIO | IOBase object
        # see pyxform get_definition_data() function
        file = form_version.xls_file
        file_content = BytesIO(file.read())
        file_content.name = file.name
        survey = create_survey_from_xls(file_content)
        return survey.to_json_dict()
    except FileNotFoundError as e:
        print("Failed to form in xls", e)

    return None


def visit(node, questions_by_name):
    parent = node.get("type", None) is not None and (node["type"] == "survey" or node["type"] == "group")
    if parent:
        if "children" in node:
            for child in node["children"]:
                visit(child, questions_by_name)
    else:
        try:
            questions_by_name[node["name"]] = node
        except:
            print("error", node)


def to_questions_by_name(form_descriptor):
    questions_by_name = {}
    if not form_descriptor or len(form_descriptor) == 0:
        return questions_by_name
    visit(form_descriptor, questions_by_name)
    return questions_by_name


def visit_by_path(node, questions_by_name, current_path):
    parent = node.get("type", None) is not None and (node["type"] == "survey" or node["type"] == "group")

    if node.get("name", "") == "data":
        node_current_path = ""
    elif current_path == "":
        node_current_path = node.get("name", "")
    else:
        node_current_path = current_path + "/" + node.get("name", "")

    if parent:
        if "children" in node:
            for child in node["children"]:
                visit_by_path(child, questions_by_name, node_current_path)
    else:
        try:
            questions_by_name[node_current_path] = node
        except:
            visit_by_path("error", node, node_current_path)


def to_questions_by_path(form_descriptor):
    questions_by_path = {}
    if not form_descriptor or len(form_descriptor) == 0:
        return questions_by_path
    visit_by_path(form_descriptor, questions_by_path, "")
    return questions_by_path


def parse_xls_form(xls_file: typing.BinaryIO, *, previous_version: str = None) -> Survey:
    """Parse an ODK xls form file.

    :param xls_file: a named file-like object (a persistent file or a django uploaded file will do)
    :param previous_version: used to validate the version present in the Excel file or to auto-generate it
    """

    try:
        # Since version 2.1.0, pyxform expects a path or a bytes | BytesIO | IOBase object
        # see pyxform get_definition_data() function
        file_content = BytesIO(xls_file.read())
        file_content.name = xls_file.name
        survey = create_survey_from_xls(file_content, default_name="data")
    except errors.PyXFormError as e:
        raise ParsingError(f"Invalid XLS file: {e}")

    if survey.version == "":
        survey.version = _generate_form_version(previous_version)

    if not survey.version.isnumeric() or len(survey.version) > 10:
        raise ParsingError("Invalid XLS file: Invalid version (must be a string of 1-10 numbers).")

    if previous_version is not None and previous_version.isnumeric() and int(previous_version) >= int(survey.version):
        raise ParsingError("Invalid XLS file: Parsed version should be greater than previous version.")

    return Survey(survey, xls_file_name=xls_file.name)


def _generate_form_version(previous_version: typing.Optional[str]) -> str:
    """Generate a form version in the yyyymmddrr format.
    If a previous version is provided, and is also in the yyyymmddrr, it will be used to check if we should increment
    the revision part(rr) or create a new revision for the day

    :param previous_version: last saved version number in our system
    """

    today = timezone.now().date()
    if previous_version is not None and len(previous_version) == 10:  # previous version in yyyymmddrr format
        previous_version_date_string = f"{previous_version[:4]}-{previous_version[4:6]}-{previous_version[6:8]}"
        if dateparse.parse_date(previous_version_date_string) == today:  # previous version was created today
            if previous_version[8:] == "99":
                raise ParsingError("Invalid XLS file: Too many versions.")

            return str(int(previous_version) + 1)

    return f"{today.strftime('%Y%m%d')}01"
