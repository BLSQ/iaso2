from copy import deepcopy
from time import time
from typing import List
from django.db import transaction
from beanstalk_worker import task_decorator
from hat.audit import models as audit_models
from iaso.api.payments.serializers import PaymentLotAuditLogger
from iaso.models import Task
from iaso.models.base import ERRORED, KILLED, KilledException
from iaso.models.payments import Payment, PaymentLot, PaymentStatuses
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist


def end_task_and_update_payment_lot(payment_lot, task, message):
    task.status = ERRORED
    task.ended_at = timezone.now()
    task.result = {"result": ERRORED, "message": message}
    task.save()
    payment_lot.task = None
    payment_lot.save()


def report_progress_and_stop_if_killed_and_update_payment_lot(
    payment_lot, task, progress_message, progress_value=None, end_value=None
):
    try:
        task.report_progress_and_stop_if_killed(
            progress_message=progress_message, progress_value=progress_value, end_value=end_value
        )
    except KilledException:
        payment_lot.task = None
        payment_lot.save()
        raise KilledException("Killed by user")


def update_payment_from_bulk(user, payment, *, status, api):
    """Used within the context of a bulk operation"""

    original_copy = deepcopy(payment)
    source = api if api else audit_models.PAYMENT_API_BULK
    if status is not None and status in PaymentStatuses:
        payment.status = status
    payment.save()

    audit_models.log_modification(original_copy, payment, source=source, user=user)


@task_decorator(task_name="payments_bulk_update")
def payments_bulk_update(
    select_all: bool,
    selected_ids: List[int],
    unselected_ids: List[int],
    status: str,
    payment_lot_id: int,
    api: str,
    task: Task,
):
    """Background Task to bulk update payments.
    All updated payments should be related to the provided payment_lot_id
    """
    start = time()
    the_task = task
    if not payment_lot_id:
        the_task.status = ERRORED
        the_task.ended_at = timezone.now()
        the_task.result = {"result": ERRORED, "message": "Missing PaymentLot id"}
        the_task.save()
    else:
        try:
            payment_lot = PaymentLot.objects.get(id=payment_lot_id)
        except ObjectDoesNotExist:
            the_task.status = ERRORED
            the_task.ended_at = timezone.now()
            the_task.result = {"result": ERRORED, "message": "Payment Lot not found"}
            the_task.save()
        # Handle killing task after retrieving payment lot, so payment lot's task field can be updated
        report_progress_and_stop_if_killed_and_update_payment_lot(
            payment_lot=payment_lot, task=the_task, progress_message="Searching for Payments to modify"
        )
        # audit stuff
        payment_log_audit = PaymentLotAuditLogger()
        old_payment_lot = payment_log_audit.serialize_instance(payment_lot)
        user = the_task.launcher

        # Restrict qs to payments accessible to the user
        queryset = Payment.objects.filter(created_by__iaso_profile__account=user.iaso_profile.account).filter(
            payment_lot_id=payment_lot_id
        )

        if not select_all:
            queryset = queryset.filter(pk__in=selected_ids)
        else:
            queryset = queryset.exclude(pk__in=unselected_ids)

        total = queryset.count()

        if not total:
            end_task_and_update_payment_lot(payment_lot=payment_lot, task=the_task, message="No matching payment found")
            return

        # FIXME Task don't handle rollback properly if task is killed by user or other error
        with transaction.atomic():
            for index, payment in enumerate(queryset.iterator(chunk_size=2000)):
                res_string = "%.2f sec, processed %i payments" % (time() - start, index)
                report_progress_and_stop_if_killed_and_update_payment_lot(
                    payment_lot=payment_lot,
                    task=the_task,
                    progress_message=res_string,
                    end_value=total,
                    progress_value=index,
                )
                update_payment_from_bulk(user, payment, status=status, api=api)
            # Update PaymentLot status if needed. Since the bulk update doesn't necessarily include
            # all Payments, we need to check if the status changed
            old_payment_lot_status = payment_lot.status
            new_payment_lot_status = payment_lot.compute_status()
            if old_payment_lot_status != new_payment_lot_status:
                payment_lot.status = new_payment_lot_status
                payment_lot.task = None
                payment_lot.save()
                payment_log_audit.log_modification(
                    old_data_dump=old_payment_lot,
                    instance=payment_lot,
                    request_user=user,
                    source=audit_models.PAYMENT_API_BULK,
                )
            else:
                payment_lot.task = None
                payment_lot.save()
            the_task.report_success(message="%d modified" % total)


@task_decorator(task_name="mark_payments_as_read")
def mark_payments_as_read(
    payment_lot_id: int,
    api: str,
    task: Task,
):
    """
    Task to change the `status` of  all `Payments` in a `PaymentLot` to `SENT`
    It's launched via the `PaymentLot` API only, so the check on access rights is performed there
    """
    start = time()
    the_task = task

    try:
        payment_lot = PaymentLot.objects.get(id=payment_lot_id)
    except ObjectDoesNotExist:
        the_task.status = ERRORED
        the_task.ended_at = timezone.now()
        the_task.result = {"result": ERRORED, "message": "Payment Lot not found"}
        the_task.save()
    # Handling task being killed after we get the payment_lot, so we can set its task field back to None if the task is killed
    report_progress_and_stop_if_killed_and_update_payment_lot(
        payment_lot=payment_lot, task=the_task, progress_message="Searching for Payments to modify"
    )

    payments = Payment.objects.filter(payment_lot=payment_lot)
    total = payments.count()

    # audit stuff
    user = the_task.launcher
    audit_logger = PaymentLotAuditLogger()
    old_payment_lot = audit_logger.serialize_instance(payment_lot)

    # FIXME Task don't handle rollback properly if task is killed by user or other error
    with transaction.atomic():
        for index, payment in enumerate(payments.iterator(chunk_size=2000)):
            res_string = "%.2f sec, processed %i payments" % (time() - start, index)
            report_progress_and_stop_if_killed_and_update_payment_lot(
                payment_lot=payment_lot,
                task=the_task,
                progress_message=res_string,
                end_value=total,
                progress_value=index,
            )
            update_payment_from_bulk(user, payment, status=PaymentStatuses.SENT, api=api)

        # All Payments have been updated so we always need to update the PaymentLot status
        payment_lot.status = payment_lot.compute_status()
        payment_lot.task = None
        payment_lot.save()
        audit_logger.log_modification(old_data_dump=old_payment_lot, instance=payment_lot, request_user=user)

        the_task.report_success(message="%d modified" % total)
