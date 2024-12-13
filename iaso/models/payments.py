from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class PaymentStatuses(models.TextChoices):
    PENDING = "pending", _("Pending")
    SENT = "sent", _("Sent")
    REJECTED = "rejected", _("Rejected")
    PAID = "paid", _("Paid")


class Payment(models.Model):
    """
    Model to store the status of payments linked to multiple OrgUnitChangeRequest by the same user.
    User is the user that will receive the payment for the change request he did
    """

    status = models.CharField(choices=PaymentStatuses.choices, default=PaymentStatuses.PENDING, max_length=40)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment")
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="payment_created_set"
    )
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="payment_updated_set"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_lot = models.ForeignKey(
        "PaymentLot", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )

    def __str__(self):
        return "{} - {} - {} - {}".format(
            self.id,
            self.status,
            self.user,
            self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )


class PotentialPayment(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="potential_payment")
    payment_lot = models.ForeignKey(
        "PaymentLot", on_delete=models.SET_NULL, null=True, blank=True, related_name="potential_payments"
    )
    task = models.ForeignKey(
        "Task", on_delete=models.SET_NULL, null=True, blank=True, related_name="potential_payments"
    )


class PaymentLot(models.Model):
    """
    Model to store lots / batches of payments. Each payment can belong to only one lot.
    This model includes a mechanism to dynamically compute the status of a payment lot based on the statuses of the payments it contains.
    """

    class Statuses(models.TextChoices):
        NEW = "new", _("New")  # Default status, indicating a newly created lot or a lot with no payments sent.
        SENT = "sent", _("Sent")  # Indicates that all payments in the lot have been sent.
        PAID = "paid", _("Paid")  # Indicates that all payments in the lot have been paid.
        PARTIALLY_PAID = "partially_paid", _(
            "Partially Paid"
        )  # Indicates that some, but not all, payments in the lot have been paid.

    name = models.CharField(max_length=255)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_lot_created_set")
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="payment_lot_updated_set"
    )
    status = models.CharField(choices=Statuses.choices, default=Statuses.NEW, max_length=40)
    task = models.ForeignKey("Task", on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_lots")

    def compute_status(self):
        payments = self.payments.all()
        if not payments.exists():
            return self.Statuses.NEW
        total_payments = payments.count()
        paid_payments = payments.filter(status=PaymentStatuses.PAID).count()
        sent_payments = payments.filter(status=PaymentStatuses.SENT).count()

        if paid_payments == total_payments:
            return self.Statuses.PAID
        elif paid_payments > 0:
            return self.Statuses.PARTIALLY_PAID
        elif sent_payments == total_payments:
            return self.Statuses.SENT
        else:
            return self.Statuses.NEW

    def __str__(self):
        return "{} - {}".format(self.name, self.created_at.strftime("%Y-%m-%d %H:%M:%S"))
