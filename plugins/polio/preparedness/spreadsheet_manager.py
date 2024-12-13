"""Generation of the Preparedness Google Sheet for a Campaign

Use a template configured in polio.Config preparedness_template_id.

The general logic is that we copy a template Spreadsheet file stored in Google Spreadsheet,
and we adapt the value for the particular campaign we are generating to.
We copy the Regional worksheet for each region in the Campaign scope, then add a column for each district.
"""

import copy
from logging import getLogger
from typing import Optional

import gspread  # type: ignore
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import gettext_lazy as _
from gspread.utils import rowcol_to_a1, Dimension, a1_range_to_grid_range  # type: ignore
from rest_framework import exceptions

from hat.__version__ import VERSION
from iaso.models import OrgUnit
from plugins.polio.models import CountryUsersGroup, Campaign
from plugins.polio.preparedness.client import get_client, get_google_config

logger = getLogger(__name__)

# you need to create a polio.Config object with this key in the DB
PREPAREDNESS_TEMPLATE_CONFIG_KEY = "preparedness_template_id"
TEMPLATE_VERSION = "v3.3"


def create_spreadsheet(title: str, lang: str):
    client = get_client()
    config = get_google_config(PREPAREDNESS_TEMPLATE_CONFIG_KEY)
    if lang not in ("EN", "FR", "PT"):
        # We allow it for future dev but display an error to avoid carelessly adding new language
        logger.error("Unsupported lang for preparedness template")
    if TEMPLATE_VERSION not in config:
        raise Exception(f"Template config for {TEMPLATE_VERSION} not found")

    template = config[TEMPLATE_VERSION].get(lang.lower())

    if not template:
        raise Exception(f"Template for {lang} and version {TEMPLATE_VERSION} not found")
    logger.info(f"Creating spreadsheet {title} from {template}")

    spreadsheet = client.copy(template, title)
    logger.info(f"Created spreadsheet {spreadsheet.url}")
    spreadsheet.share(None, perm_type="anyone", role="writer", with_link=True)
    return spreadsheet


def update_national_worksheet(sheet: gspread.Worksheet, vaccines: str, country=None, payment_mode=""):
    country_name = country.name if country else ""
    updates = [
        {"range": "C4", "values": [[payment_mode]]},
        {"range": "C11", "values": [[vaccines]]},
        {"range": "C6", "values": [[country_name]]},
    ]

    sheet.batch_update(updates)


def duplicate_cells(sheet, template_range, num_time):
    """Duplicate cells vertically to the right"""
    copy_range = a1_range_to_grid_range(template_range)

    if not copy_range["startColumnIndex"] == copy_range["endColumnIndex"] - 1:
        raise Exception("Not only we support a vertical range on the same col")

    copy_range["sheetId"] = sheet.id
    paste_range = {
        "sheetId": sheet.id,
        "startRowIndex": copy_range["startRowIndex"],
        "endRowIndex": copy_range["endRowIndex"],
        "startColumnIndex": copy_range["startColumnIndex"] + 1,
        "endColumnIndex": copy_range["endColumnIndex"] + num_time,
    }
    body = {
        "requests": [
            {
                "insertRange": {
                    "range": paste_range,
                    "shiftDimension": Dimension.cols,
                },
            },
            {
                "copyPaste": {
                    "source": copy_range,
                    "destination": paste_range,
                    "pasteType": "PASTE_NORMAL",
                    "pasteOrientation": "NORMAL",
                },
            },
        ]
    }

    sheet.spreadsheet.batch_update(body)


def update_regional_worksheet(sheet: gspread.Worksheet, region_name: str, region_districts):
    district_names = [d.name for d in region_districts]
    num_district = len(district_names)
    district_name_range = f"{rowcol_to_a1(7, 6)}:{rowcol_to_a1(7, 6 + num_district)}"
    updates = [{"range": "c4", "values": [[region_name]]}, {"range": district_name_range, "values": [district_names]}]
    # Make a columns for each district
    # General
    duplicate_cells(sheet, "E6:E70", num_district)
    # Summary
    duplicate_cells(sheet, "C73:C79", num_district)

    sheet.batch_update(updates, value_input_option="USER_ENTERED")


# Google Sheet don't automatically copy the protected ranges when duplicating a sheet, so we do it by hand
def copy_protected_range_to_sheet(template_protected_ranges, new_sheet):
    new_sheet_id = new_sheet.id
    new_protected_ranges = []
    for template_protected_range in template_protected_ranges:
        new_protected_range = copy.deepcopy(template_protected_range)
        del new_protected_range["protectedRangeId"]
        # Parameter "requestingUserCanEdit" is read only
        if "requestingUserCanEdit" in new_protected_range:
            del new_protected_range["requestingUserCanEdit"]
        # Editor property not allowed in warningOnly protection
        #  The original editors list from the template is keep otherwise the protection is listed but don't actually
        #  prevent edition. Seems a bug in Google Sheet, probably related to the fact that the new owner is a Service
        #  Account.
        if new_protected_range.get("warningOnly"):
            if "editors" in new_protected_range:
                del new_protected_range["editors"]
        new_protected_range["range"]["sheetId"] = new_sheet_id
        if "unprotectedRanges" in new_protected_range:
            for unprotected_range in new_protected_range["unprotectedRanges"]:
                unprotected_range["sheetId"] = new_sheet_id
        new_protected_ranges.append(new_protected_range)
    # Return requests, don't execute them in order to batch execute all of them at the end
    requests = []
    for pr in new_protected_ranges:
        requests.append({"addProtectedRange": {"protectedRange": pr}})
    return requests


def get_region_from_district(districts):
    # May not be the most efficient
    return OrgUnit.objects.filter(id__in=districts.values_list("parent_id", flat=True).distinct())


def generate_spreadsheet_for_campaign(campaign: Campaign, round_number: Optional[int]):
    lang = "EN"

    try:
        country = campaign.country
        if not country:
            exceptions.ValidationError({"message": _("No country found for campaign")})
        cug = CountryUsersGroup.objects.get(country=country)
        lang = cug.language
    except Exception as e:
        logger.exception(e)
        logger.error(f"Could not find template language for {campaign}")
    spreadsheet = create_spreadsheet(campaign.obr_name, lang)

    # set some meta data for debugging
    domain = get_current_site(None).domain
    spreadsheet.sheet1.batch_update(
        [
            {"range": "A28", "values": [[domain]]},
            {"range": "B28", "values": [[VERSION]]},
            {"range": "B29", "values": [[TEMPLATE_VERSION]]},
        ]
    )
    update_national_worksheet(
        spreadsheet.worksheet("National"),
        vaccines=campaign.vaccines,
        payment_mode=campaign.payment_mode,
        country=campaign.country,
    )
    regional_template_worksheet = spreadsheet.worksheet("Regional")
    meta = spreadsheet.fetch_sheet_metadata()
    template_range = meta["sheets"][regional_template_worksheet.index]["protectedRanges"]  # regional_template_worksheet
    batched_requests = []
    districts = campaign.get_districts_for_round_number(round_number)
    regions = get_region_from_district(districts)

    current_index = 2
    for index, region in enumerate(regions):
        regional_worksheet = regional_template_worksheet.duplicate(current_index, None, region.name)
        batched_requests += copy_protected_range_to_sheet(template_range, regional_worksheet)
        region_districts = districts.filter(parent=region)
        update_regional_worksheet(regional_worksheet, region.name, region_districts)
        current_index += 1
    spreadsheet.batch_update({"requests": batched_requests})
    spreadsheet.del_worksheet(regional_template_worksheet)
    return spreadsheet
