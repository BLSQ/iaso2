import json
import os
import psycopg2
from psycopg2.extras import Json

# from geojson import MultiPolygon, Point
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point, Polygon

from iaso.utils.gis import simplify_geom
from iaso.models import *

# Replace these with your actual database connection details
# conn_params = {"dbname": "your_database", "user": "your_username", "password": "your_password", "host": "localhost"}


def load_json_to_postgis(json_path):
    with open(json_path, "r") as file:
        data = json.load(file)

    # # Connect to your database
    # conn = psycopg2.connect(**conn_params)
    # cursor = conn.cursor()

    # Add geometries to org units
    for unit in data["features"]:
        geom_type = unit.get("geometry", {}).get("type", None)
        if geom_type == "MultiPolygon":
            geom = MultiPolygon(unit["geometry"]["coordinates"])
        elif geom_type == "Point":
            geom = Point(unit["geometry"]["coordinates"])
        else:
            geom = None

        source_ref = unit["properties"]["adm2_id"]

        try:
            org_unit = OrgUnit.objects.get(source_ref=source_ref)
            org_unit.geom = MultiPolygon(GEOSGeometry(json.dumps(unit["geometry"])))
            org_unit.simplified_geom = simplify_geom(org_unit.geom)
            org_unit.save()
            print(f"SUCCESS: parsed geom for source_ref {source_ref}")
        except Exception:
            print(f"ERROR: Can't parse geom for source_ref {source_ref}")

    # conn.commit()
    # cursor.close()
    # conn.close()


def run():
    # Replace 'path/to/your/file.json' with the path to your JSON file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "BFA_districts.geojson")
    load_json_to_postgis(json_path)
