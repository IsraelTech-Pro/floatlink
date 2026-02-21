from __future__ import annotations

from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

from django.db import transaction
from django.utils import timezone

from agents.models import Agent
from float_requests.models import FloatRequest
from transactions.models import Transaction


SERVICE_FEE_RATE = Decimal('0.005')


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return r * c


def calculate_service_fee(amount: Decimal) -> Decimal:
    return (amount * SERVICE_FEE_RATE).quantize(Decimal('0.01'))


@transaction.atomic
def accept_float_request(float_request: FloatRequest, staff_user) -> Transaction:
    float_request.refresh_from_db()

    if float_request.status != FloatRequest.Status.PENDING:
        raise ValueError('Request is not in PENDING state')

    if not getattr(staff_user, 'is_staff', False):
        raise PermissionError('Only staff can accept requests')

    float_request.status = FloatRequest.Status.ACCEPTED
    float_request.accepted_at = timezone.now()
    float_request.accepted_by = staff_user
    float_request.save(update_fields=['status', 'accepted_at', 'accepted_by'])

    service_fee = calculate_service_fee(float_request.amount)

    staff_agent, _created_staff_agent = Agent.objects.get_or_create(user=staff_user)

    tx, _created = Transaction.objects.get_or_create(
        float_request=float_request,
        defaults={
            'from_agent': float_request.requesting_agent,
            'to_agent': staff_agent,
            'amount': float_request.amount,
            'service_fee': service_fee,
            'status': Transaction.Status.CREATED,
        },
    )

    return tx


@transaction.atomic
def admin_complete_float_request(float_request: FloatRequest, staff_user) -> FloatRequest:
    float_request.refresh_from_db()

    if float_request.status != FloatRequest.Status.ACCEPTED:
        raise ValueError('Request must be ACCEPTED before staff can complete it')

    if not getattr(staff_user, 'is_staff', False):
        raise PermissionError('Only staff can complete requests')

    float_request.status = FloatRequest.Status.ADMIN_COMPLETED
    float_request.admin_completed_at = timezone.now()
    float_request.save(update_fields=['status', 'admin_completed_at'])
    return float_request


@transaction.atomic
def confirm_float_request(float_request: FloatRequest, requesting_agent: Agent) -> Transaction:
    float_request.refresh_from_db()

    if float_request.status != FloatRequest.Status.ADMIN_COMPLETED:
        raise ValueError('Request must be ADMIN_COMPLETED before the agent can confirm it')

    if float_request.requesting_agent_id != requesting_agent.id:
        raise PermissionError('Only the requesting agent can confirm completion')

    tx = Transaction.objects.select_for_update().get(float_request=float_request)

    float_request.status = FloatRequest.Status.COMPLETED
    float_request.agent_confirmed_at = timezone.now()
    float_request.completed_at = timezone.now()
    float_request.save(update_fields=['status', 'agent_confirmed_at', 'completed_at'])

    tx.status = Transaction.Status.PAID
    tx.save(update_fields=['status'])

    return tx
