import csv
import requests

"""
Disclaimer: This script is a work in progress. There are many ways to improve and
make this script more generic. For the time being, you can set it up as follows:

1. Put all data in a CSV with column names:
    - "partner" this will become the OU groups
    - For each OrgUnitType: short_name
2. Make sure SERVER_BASE_URL and AUTH_TOKEN are correctly configured to your
   desired server.
"""

SERVER_BASE_URL = "https://server.org"

orgunits_url = SERVER_BASE_URL + "/api/orgunits/"
groups_url = SERVER_BASE_URL + "/api/groups/"
create_org_unit_url = SERVER_BASE_URL + "/api/orgunits/create_org_unit/"
org_unit_types_url = SERVER_BASE_URL + "/api/v2/orgunittypes/"

AUTH_TOKEN = "XXX"
headers = {"Authorization": "Bearer %s" % AUTH_TOKEN}

SOURCE_ID = 1  # ID of the default source
COUNTRY_ID = 1  # ID of the main node of the org unit tree
CSV_NAME = "example.csv"


def csv_to_dict(filename):
    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        return [{k: v.strip() for k, v in row.items()} for row in reader]


def get_group_id_by_name(groups, name):
    for group in groups:
        if group["name"] == name:
            return group["id"]
    return None


def find_or_create_org_unit(name, org_unit_type_id, parent_id, group_id=None):
    search_url = (
        orgunits_url
        + f'?limit=20&order=id&page=1&searches=[{{"validation_status":"VALID","search":"{name}","source":{SOURCE_ID},"orgUnitTypeId":"{org_unit_type_id}","orgUnitParentId":"{parent_id}"}}]'
    )
    response = requests.get(search_url, headers=headers)

    result_count = response.json()["count"]
    if result_count == 0:
        print("CREATING")
        payload = {
            "id": None,
            "name": name,
            "org_unit_type_id": org_unit_type_id,
            "groups": [group_id] if group_id else [],
            "sub_source": None,
            "aliases": [],
            "validation_status": "VALID",
            "parent_id": parent_id,
        }
        resp = requests.post(create_org_unit_url, headers=headers, json=payload)
        return resp.json()["id"]
    else:
        if result_count > 1:
            print(f"WARNING: Found multiple results for {name}")
        print("FOUND")
        return response.json()["orgunits"][0]["id"]


# Call the function with your csv file path
rows = csv_to_dict(CSV_NAME)


# Groups
groups = {}
print("Fetching group ids, create groups if needed")

groups_in_csv = {row["partner"] for row in rows}
existing_groups = requests.get(groups_url, headers=headers).json()["groups"]
existing_group_names = {g["name"] for g in existing_groups}

for group_name in groups_in_csv:
    if group_name in existing_group_names:
        groups[group_name] = get_group_id_by_name(existing_groups, group_name)
    else:
        print(f"\tcreating group: {group_name}")
        payload = {"name": group_name, "source_ref": ""}
        response = requests.post(groups_url, headers=headers, json=payload)
        groups[group_name] = response.json()["id"]

print("Groups", groups)

# OU Types
print("Fetching OU types")
ou_types = {}
response = requests.get(org_unit_types_url, headers=headers).json()["orgUnitTypes"]
for out in response:
    ou_types[out["short_name"]] = out["id"]
print("OU types", ou_types)


pyramid_dict = {}
# Turn the file into a pyramid. E.g. for South Sudan:
# state
#   |- county
#       |- payam
#           |- CHC-CHP
for row in rows:
    state = row["State"]
    lga = row["LGA"]
    ward = row["Ward"]
    phc_site = row["PHC/Site"]
    group_name = row["partner"]

    if state in pyramid_dict:
        if lga in pyramid_dict[state]:
            if ward in pyramid_dict[state][lga]:
                pyramid_dict[state][lga][ward][phc_site] = group_name
            else:
                pyramid_dict[state][lga][ward] = {phc_site: group_name}
        else:
            pyramid_dict[state][lga] = {ward: {phc_site: group_name}}
    else:
        pyramid_dict[state] = {lga: {ward: {phc_site: group_name}}}


# TODO: Generalize this based on the retrieved OU types
for state in pyramid_dict.keys():
    print(state, end=" ")
    state_id = find_or_create_org_unit(name=state, org_unit_type_id=ou_types["State"], parent_id=COUNTRY_ID)

    for lga in pyramid_dict[state].keys():
        print("\t" + lga, end=" ")
        county_id = find_or_create_org_unit(
            name=lga,
            org_unit_type_id=ou_types["LGA"],
            parent_id=state_id,
        )

        for ward in pyramid_dict[state][lga].keys():
            print("\t\t" + ward, end=" ")
            payam_id = find_or_create_org_unit(
                name=ward,
                org_unit_type_id=ou_types["Ward"],
                parent_id=county_id,
            )

            for phc_site in pyramid_dict[state][lga][ward].keys():
                print("\t\t\t" + phc_site, end=": ")
                group_name = pyramid_dict[state][lga][ward][phc_site]
                print(group_name)
                find_or_create_org_unit(
                    name=phc_site,
                    org_unit_type_id=ou_types["PHC/Site"],
                    parent_id=payam_id,
                    group_id=groups[group_name],
                )
