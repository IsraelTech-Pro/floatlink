from django.conf import settings
from django.db import models

from agents.models import Agent


class FloatRequest(models.Model):
    class RequestType(models.TextChoices):
        E_CASH = 'E_CASH', 'E-cash'
        PHYSICAL_CASH = 'PHYSICAL_CASH', 'Physical cash'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        ADMIN_COMPLETED = 'ADMIN_COMPLETED', 'Admin completed'
        COMPLETED = 'COMPLETED', 'Completed'
        DECLINED = 'DECLINED', 'Declined'
        CANCELLED = 'CANCELLED', 'Cancelled'

    requesting_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='requests_created')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    request_type = models.CharField(max_length=20, choices=RequestType.choices, default=RequestType.E_CASH)

    requester_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    requester_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='float_requests_accepted',
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    admin_completed_at = models.DateTimeField(null=True, blank=True)
    agent_confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Request #{self.pk} - {self.amount}"


class FloatRequestMessage(models.Model):
    float_request = models.ForeignKey(FloatRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='sent_float_messages', null=True, blank=True)
    sender_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_float_messages_user', null=True, blank=True)
    message = models.TextField()
    attachment = models.FileField(upload_to='chat_uploads/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Message #{self.pk}"


class FloatRequestNotification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_REQUEST = 'NEW_REQUEST', 'New request'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        ADMIN_COMPLETED = 'ADMIN_COMPLETED', 'Admin completed'
        COMPLETED = 'COMPLETED', 'Completed'

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='float_notifications')
    float_request = models.ForeignKey(FloatRequest, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    seen_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Notification #{self.pk}"
