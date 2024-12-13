from copy import deepcopy
from time import time
from typing import Optional, List

from django.db import transaction

from beanstalk_worker import task_decorator
from hat.audit import models as audit_models
from iaso.api.org_unit_search import build_org_units_queryset
from iaso.models import Task, OrgUnit, DataSource, OrgUnitType, Group


def update_single_unit_from_bulk(
    user, org_unit, *, validation_status, org_unit_type_id, groups_ids_added, groups_ids_removed
):
    """Used within the context of a bulk operation"""

    original_copy = deepcopy(org_unit)
    if validation_status is not None:
        org_unit.validation_status = validation_status
    if org_unit_type_id is not None:
        org_unit_type = OrgUnitType.objects.get(pk=org_unit_type_id)
        org_unit.org_unit_type = org_unit_type
    if groups_ids_added is not None:
        for group_id in groups_ids_added:
            group = Group.objects.get(pk=group_id)
            group.org_units.add(org_unit)
    if groups_ids_removed is not None:
        for group_id in groups_ids_removed:
            group = Group.objects.get(pk=group_id)
            group.org_units.remove(org_unit)

    org_unit.save()

    audit_models.log_modification(original_copy, org_unit, source=audit_models.ORG_UNIT_API_BULK, user=user)


@task_decorator(task_name="org_unit_bulk_update")
def org_units_bulk_update(
    app_id: Optional[str],
    select_all: bool,
    selected_ids: List[int],
    unselected_ids: List[int],
    searches: List,
    org_unit_type_id: Optional[List[int]],
    groups_ids_added: Optional[List[int]],
    groups_ids_removed: Optional[List[int]],
    validation_status: Optional[str],
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
            # TODO: investigate: can the user be anonymous on next line?
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
    editable_org_unit_type_ids = user.iaso_profile.get_editable_org_unit_type_ids()
    skipped_messages = []

    # FIXME Task don't handle rollback properly if task is killed by user or other error
    with transaction.atomic():
        for index, org_unit in enumerate(queryset.iterator(chunk_size=2000)):
            if org_unit.org_unit_type and not user.iaso_profile.has_org_unit_write_permission(
                org_unit_type_id=org_unit.org_unit_type.pk,
                prefetched_editable_org_unit_type_ids=editable_org_unit_type_ids,
            ):
                skipped_messages.append(
                    f"Org unit `{org_unit.name}` (#{org_unit.pk}) silently skipped "
                    f"because user `{user.username}` (#{user.pk}) cannot edit "
                    f"an org unit of type `{org_unit.org_unit_type.name}` (#{org_unit.org_unit_type.pk})."
                )
                continue

            res_string = "%.2f sec, processed %i org units" % (time() - start, index)
            task.report_progress_and_stop_if_killed(progress_message=res_string, end_value=total, progress_value=index)
            update_single_unit_from_bulk(
                user,
                org_unit,
                validation_status=validation_status,
                org_unit_type_id=org_unit_type_id,
                groups_ids_added=groups_ids_added,
                groups_ids_removed=groups_ids_removed,
            )

        message = f"{total} modified"
        if skipped_messages:
            message = f"{total - len(skipped_messages)} modified\n"
            message += f"{len(skipped_messages)} skipped\n"
            message += "\n".join(skipped_messages)

        task.report_success(message=message)
