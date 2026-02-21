from django.db import models

from agents.models import Agent
from float_requests.models import FloatRequest


class Transaction(models.Model):
    class Status(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'

    float_request = models.OneToOneField(FloatRequest, on_delete=models.CASCADE, related_name='transaction')
    from_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='outgoing_transactions')
    to_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='incoming_transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Transaction #{self.pk}"
