from time import time
from django.db import transaction
from beanstalk_worker import task_decorator
from hat.audit import models as audit_models
from iaso.api.org_unit_change_requests.serializers import (
    OrgUnitChangeRequestAuditLogger,
)
from typing import List
from iaso.api.payments.serializers import PaymentAuditLogger, PaymentLotAuditLogger
from iaso.models import Task
from iaso.models.payments import Payment, PaymentLot, PaymentStatuses, PotentialPayment
from django.utils import timezone
from iaso.models.base import ERRORED
from django.db.models import Q


def create_payment_from_payment_lot(user, payment_lot, *, potential_payment):
    """Used within the context of a bulk operation"""
    payment = Payment.objects.create(
        status=PaymentStatuses.PENDING,
        user=potential_payment.user,
        created_by=user,
        updated_by=user,
        payment_lot=payment_lot,
    )
    # Save payment modification
    audit_logger = PaymentAuditLogger()
    change_request_audit_logger = OrgUnitChangeRequestAuditLogger()
    change_requests = potential_payment.change_requests.all()
    # Add change requests from potential payment to the newly created payment
    for change_request in change_requests:
        old_change_request_dump = change_request_audit_logger.serialize_instance(change_request)
        change_request.payment = payment
        change_request.potential_payment = None
        change_request.save()
        # Save change request modification
        change_request_audit_logger.log_modification(
            instance=change_request,
            old_data_dump=old_change_request_dump,
            request_user=user,
            source=audit_models.PAYMENT_LOT_API,
        )
    potential_payment.delete()
    # Log the payment change after the fk to change request has been set
    audit_logger.log_modification(
        instance=payment, old_data_dump=None, request_user=user, source=audit_models.PAYMENT_LOT_API
    )


def end_task_and_delete_payment_lot(payment_lot, potential_payments, task, message):
    task.status = ERRORED
    task.ended_at = timezone.now()
    task.result = {"result": ERRORED, "message": message}
    task.save()
    potential_payments.update(task=None)
    # update doesn't call save(), so we need to loop through the queryset and save each instance
    for potential_payment in potential_payments:
        potential_payment.save()
    payment_lot.delete()
    raise Exception("Error while creating Payment Lot")


@task_decorator(task_name="create_payment_lot")
def create_payment_lot(
    comment: str,
    name: str,
    potential_payment_ids: List[int],
    task: Task,
):
    """Background Task to create Payment Lot and convert Potential Payments into Payments
    Used exclusively within the context of the PaymentLot API. Users won't launch it directly from another endpoint.
    """
    start = time()
    the_task = task
    user = the_task.launcher
    the_task.report_progress_and_stop_if_killed(progress_message="Searching for Payments to modify")
    payment_lot = PaymentLot(name=name, comment=comment, created_by=user, updated_by=user)
    payment_lot.task = the_task
    payment_lot.save()

    # Addding a try/except so if there's an error while adding the potential payments, we can delete the payment lot and avoid empty payment lots in the DB
    # TODO Not sure we need to add the potential payments to the payment lot anymore
    try:
        # We want to filter out potential payments assigned to another task.
        # Since the task is assigned in the view after it's created, we filter out potential payments with no task or with the current task assigned (for safety)
        potential_payments = PotentialPayment.objects.filter(id__in=potential_payment_ids)
        potential_payments_for_lot = potential_payments.filter(task=the_task)
        # potential_payments_for_lot = potential_payments.filter((Q(task__isnull=True) | Q(task=the_task)))
        payment_lot.potential_payments.add(*potential_payments_for_lot, bulk=False)
        payment_lot.save()
    except:
        end_task_and_delete_payment_lot(
            payment_lot=payment_lot,
            potential_payments=potential_payments,
            task=the_task,
            message="Error while getting potential payments",
        )
    total = len(potential_payment_ids)
    if potential_payments_for_lot.count() != total:
        end_task_and_delete_payment_lot(
            payment_lot=payment_lot,
            potential_payments=potential_payments,
            task=the_task,
            message="One or several Potential payments not found",
        )

    else:
        with transaction.atomic():
            for index, potential_payment in enumerate(potential_payments_for_lot.iterator(chunk_size=2000)):
                potential_payment.payment_lot = payment_lot
                potential_payment.save()
                res_string = "%.2f sec, processed %i payments" % (time() - start, index)
                the_task.report_progress_and_stop_if_killed(
                    progress_message=res_string, end_value=total, progress_value=index
                )
                create_payment_from_payment_lot(user=user, payment_lot=payment_lot, potential_payment=potential_payment)
        # If potential payments haven't been deleted, it means there was a problem with the above transaction and it was reverted.
        # In this case we delete the payment lot and ERROR the task
        if payment_lot.potential_payments.count():
            end_task_and_delete_payment_lot(
                payment_lot=payment_lot,
                potential_payments=potential_payments,
                task=the_task,
                message="Error while creating one or several payments",
            )
        else:
            audit_logger = PaymentLotAuditLogger()
            # Compute status, although it should be NEW since we just created all the Payments
            payment_lot.compute_status()
            # Set task to null, so we can filter out active tasks in the payment lot API
            payment_lot.task = None
            payment_lot.save()
            audit_logger.log_modification(instance=payment_lot, old_data_dump=None, request_user=user)
            the_task.report_success(message="%d modified" % total)
