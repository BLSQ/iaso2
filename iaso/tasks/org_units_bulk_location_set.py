from copy import deepcopy
from logging import getLogger
from time import time
from typing import Optional, List

from django.contrib.auth.models import User
from django.contrib.gis.db.models import GeometryCollectionField
from django.contrib.gis.db.models.aggregates import GeoAggregate
from django.contrib.gis.db.models.functions import Centroid
from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import Q, QuerySet

from beanstalk_worker import task_decorator
from hat.audit import models as audit_models
from iaso.api.org_unit_search import build_org_units_queryset
from iaso.models import Task, OrgUnit, DataSource
from iaso.utils.gis import convert_2d_point_to_3d


class OrgUnitWithFormStat(OrgUnit):
    instance_center: Optional[Point]

    class Meta:
        abstract = True


logger = getLogger(__name__)


def update_single_org_unit_location_from_bulk(user: Optional[User], org_unit: OrgUnitWithFormStat):
    original_copy = deepcopy(org_unit)
    if org_unit.location and not org_unit.geom:
        # skip orgunit if it already has location
        logger.info(f"skipping {org_unit.name} {org_unit.id} as it already has a location or geom")
        return
    # Assign and ensure it is 3d
    org_unit.location = convert_2d_point_to_3d(org_unit.instance_center) if org_unit.instance_center else None
    logger.info(f"updating {org_unit.name} {org_unit.id} with {org_unit.location}")
    org_unit.save()
    audit_models.log_modification(original_copy, org_unit, source=audit_models.ORG_UNIT_API_BULK, user=user)


@task_decorator(task_name="org_unit_bulk_location_set")
def org_units_bulk_location_set(
    app_id: Optional[str],
    select_all: bool,
    selected_ids: List[int],
    unselected_ids: List[int],
    searches: List,
    task: Task,
):
    """Background Task to bulk update org units."""
    start = time()
    task.report_progress_and_stop_if_killed(progress_message="Searching for Org Units to modify")

    # Restrict qs to org units accessible to the user
    user = task.launcher
    queryset = OrgUnit.objects.filter_for_user_and_app_id(user, app_id)

    if not select_all:
        queryset = queryset.filter(pk__in=selected_ids)
    else:
        queryset = queryset.exclude(pk__in=unselected_ids)
        if searches:
            profile = user.iaso_profile  # type: ignore
            base_queryset = queryset
            queryset = OrgUnit.objects.none()  # type: ignore
            for search in searches:
                search_queryset = build_org_units_queryset(base_queryset, search, profile)
                queryset = queryset.union(search_queryset)

    if not queryset:
        raise Exception("No matching org unit found")

    # Assure that none of the OrgUnit we are modifying is in a read only data source
    # ? Shouldn't this be done in the save() or in a constraint?
    read_only_data_sources = DataSource.objects.filter(
        id__in=queryset.values_list("version__data_source", flat=True), read_only=True
    )
    if read_only_data_sources.count() > 0:
        raise Exception("Modification on read only source are not allowed")

    total = queryset.count()

    # On the queryset, add a field which contain the center of all the instance attached to the orgunit
    filtre_deleted_instance = Q(instance__deleted=False)
    annotated_queryset: QuerySet[OrgUnitWithFormStat]
    annotated_queryset = queryset.annotate(
        instance_center=Centroid(IasoCollect("instance__location", filter=filtre_deleted_instance))
    )

    with transaction.atomic():
        for index, org_unit in enumerate(annotated_queryset.iterator(chunk_size=2000)):
            res_string = "%.2f sec, processed %i org units" % (time() - start, index)
            task.report_progress_and_stop_if_killed(progress_message=res_string, end_value=total, progress_value=index)
            update_single_org_unit_location_from_bulk(
                user,
                org_unit,
            )

        task.report_success(message="%d modified" % total)


class IasoCollect(GeoAggregate):
    """Fixed django.contrib.gis.db.models.aggregates.Collect that work with specifying a filter"""

    name = "Collect"
    output_field_class = GeometryCollectionField

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        c = super(GeoAggregate, self).resolve_expression(query, allow_joins, reuse, summarize, for_save)
        for field in c.get_source_fields():
            if not hasattr(field, "geom_type"):
                raise ValueError("Geospatial aggregates only allowed on geometry fields.")
        return c
