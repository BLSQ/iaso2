from django.db import transaction

from beanstalk_worker import task_decorator

from iaso.models import Task, OrgUnitChangeRequest


@task_decorator(task_name="org_unit_change_requests_bulk_approve")
def org_unit_change_requests_bulk_approve(
    change_requests_ids: list[int],
    approved_fields: list[str],
    task: Task,
):
    task.report_progress_and_stop_if_killed(progress_message="Synchronizing source versions…")

    user = task.launcher

    change_requests = OrgUnitChangeRequest.objects.filter(id__in=change_requests_ids)

    with transaction.atomic():
        for change_request in change_requests:
            change_request.approve(user, approved_fields)

    task.report_success(message=f"Bulk approved {len(change_requests_ids)} change requests.")


@task_decorator(task_name="org_unit_change_requests_bulk_reject")
def org_unit_change_requests_bulk_reject(
    change_requests_ids: list[int],
    rejection_comment: str,
    task: Task,
):
    task.report_progress_and_stop_if_killed(progress_message="Synchronizing source versions…")

    user = task.launcher

    change_requests = OrgUnitChangeRequest.objects.filter(id__in=change_requests_ids)

    with transaction.atomic():
        for change_request in change_requests:
            change_request.reject(user, rejection_comment)

    task.report_success(message=f"Bulk rejected {len(change_requests_ids)} change requests.")
