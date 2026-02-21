from django import template
from django.contrib.auth import get_user_model
from django.db.models import Count

from agents.models import Agent
from float_requests.models import FloatRequest
from transactions.models import Transaction

register = template.Library()


@register.simple_tag
def admin_dashboard_stats():
    User = get_user_model()

    users_total = User.objects.count()
    agents_total = Agent.objects.count()
    agents_verified = Agent.objects.filter(is_verified=True).count()
    agents_active = Agent.objects.filter(user__is_active=True).count()

    fr_rows = FloatRequest.objects.values('status').annotate(c=Count('id'))
    fr_counts = {k: 0 for k in ['PENDING', 'ACCEPTED', 'ADMIN_COMPLETED', 'COMPLETED', 'CANCELLED', 'DECLINED']}
    fr_total = 0
    for row in fr_rows:
        status = row['status']
        if status in fr_counts:
            fr_counts[status] = row['c']
        fr_total += row['c']

    tx_rows = Transaction.objects.values('status').annotate(c=Count('id'))
    tx_counts = {k: 0 for k in ['CREATED', 'PAID', 'FAILED']}
    tx_total = 0
    for row in tx_rows:
        status = row['status']
        if status in tx_counts:
            tx_counts[status] = row['c']
        tx_total += row['c']

    return {
        'users_total': users_total,
        'agents_total': agents_total,
        'agents_verified': agents_verified,
        'agents_active': agents_active,
        'float_requests': {
            'total': fr_total,
            **fr_counts,
        },
        'transactions': {
            'total': tx_total,
            **tx_counts,
        },
    }
