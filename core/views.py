from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import Http404
from django.db.models import Count
from django.db.models import Q

from agents.models import Agent
from float_requests.models import FloatRequest
from float_requests.services import calculate_service_fee
from transactions.models import Transaction

from .forms import CreateAdminUserForm


def home(request):
    return render(request, 'core/home.html')


@login_required
def dashboard(request):
    agent = Agent.objects.get(user=request.user)

    my_requests_count = FloatRequest.objects.filter(requesting_agent=agent).count()
    tx_count = Transaction.objects.filter(Q(from_agent=agent) | Q(to_agent=agent)).count()
    incoming_count = 0
    if request.user.is_staff:
        incoming_count = FloatRequest.objects.filter(status=FloatRequest.Status.PENDING).count()

    return render(
        request,
        'core/dashboard.html',
        {
            'agent': agent,
            'my_requests_count': my_requests_count,
            'incoming_count': incoming_count,
            'tx_count': tx_count,
        },
    )


@login_required
def create_admin(request):
    if not request.user.is_superuser:
        raise Http404

    if request.method == 'POST':
        form = CreateAdminUserForm(request.POST, allow_make_superuser=True)
        if form.is_valid():
            form.save()
            messages.success(request, 'Admin user created.')
            return redirect('core:create_admin')
    else:
        form = CreateAdminUserForm(allow_make_superuser=True)

    return render(request, 'core/create_admin.html', {'form': form})


@login_required
def staff_operations(request):
    if not request.user.is_staff:
        raise Http404

    pending = (
        FloatRequest.objects
        .filter(status=FloatRequest.Status.PENDING)
        .select_related('requesting_agent__user', 'accepted_by')
        .order_by('-created_at')
    )
    accepted = (
        FloatRequest.objects
        .filter(status=FloatRequest.Status.ACCEPTED)
        .select_related('requesting_agent__user', 'accepted_by')
        .order_by('-accepted_at', '-created_at')
    )
    admin_completed = (
        FloatRequest.objects
        .filter(status=FloatRequest.Status.ADMIN_COMPLETED)
        .select_related('requesting_agent__user', 'accepted_by')
        .order_by('-admin_completed_at', '-created_at')
    )

    rows = FloatRequest.objects.values('status').annotate(c=Count('id'))
    counts = {'PENDING': 0, 'ACCEPTED': 0, 'ADMIN_COMPLETED': 0}
    for row in rows:
        s = row['status']
        if s in counts:
            counts[s] = row['c']

    all_requests = list(pending) + list(accepted) + list(admin_completed)
    request_totals = {
        r.id: {
            'service_fee': calculate_service_fee(r.amount),
        }
        for r in all_requests
    }
    for rid, row in request_totals.items():
        amount = next((r.amount for r in all_requests if r.id == rid), None)
        if amount is not None:
            row['total_amount'] = amount + row['service_fee']

    handler_user_ids = [r.accepted_by_id for r in all_requests if r.accepted_by_id]
    handled_agents = {
        a.user_id: a
        for a in Agent.objects.filter(user_id__in=handler_user_ids).select_related('user')
    }

    return render(
        request,
        'core/staff_operations.html',
        {
            'pending': pending,
            'accepted': accepted,
            'admin_completed': admin_completed,
            'counts': counts,
            'request_totals': request_totals,
            'handled_agents': handled_agents,
        },
    )


@login_required
def staff_analytics(request):
    if not request.user.is_staff:
        raise Http404

    fr_rows = FloatRequest.objects.values('status').annotate(c=Count('id'))
    fr = {k: 0 for k in ['PENDING', 'ACCEPTED', 'ADMIN_COMPLETED', 'COMPLETED', 'CANCELLED', 'DECLINED']}
    total = 0
    for row in fr_rows:
        s = row['status']
        if s in fr:
            fr[s] = row['c']
        total += row['c']
    fr['total'] = total

    tx_rows = Transaction.objects.values('status').annotate(c=Count('id'))
    tx = {k: 0 for k in ['CREATED', 'PAID', 'FAILED']}
    tx_total = 0
    for row in tx_rows:
        s = row['status']
        if s in tx:
            tx[s] = row['c']
        tx_total += row['c']
    tx['total'] = tx_total

    return render(request, 'core/staff_analytics.html', {'fr': fr, 'tx': tx})


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        raise Http404

    pending = (
        FloatRequest.objects
        .filter(status=FloatRequest.Status.PENDING)
        .select_related('requesting_agent__user', 'accepted_by')
        .order_by('-created_at')
    )
    ongoing = (
        FloatRequest.objects
        .filter(status__in=[FloatRequest.Status.ACCEPTED, FloatRequest.Status.ADMIN_COMPLETED])
        .select_related('requesting_agent__user', 'accepted_by')
        .order_by('-accepted_at', '-created_at')
    )
    completed = (
        FloatRequest.objects
        .filter(status=FloatRequest.Status.COMPLETED)
        .select_related('requesting_agent__user', 'accepted_by')
        .order_by('-completed_at', '-created_at')
    )
    uncompleted = (
        FloatRequest.objects
        .filter(status=FloatRequest.Status.ACCEPTED)
        .select_related('requesting_agent__user', 'accepted_by')
        .order_by('-accepted_at', '-created_at')
    )

    counts = {
        'pending': pending.count(),
        'admin_completed': FloatRequest.objects.filter(status=FloatRequest.Status.ADMIN_COMPLETED).count(),
        'accepted': FloatRequest.objects.filter(status=FloatRequest.Status.ACCEPTED).count(),
        'completed': completed.count(),
        'cancelled': FloatRequest.objects.filter(status=FloatRequest.Status.CANCELLED).count(),
        'declined': FloatRequest.objects.filter(status=FloatRequest.Status.DECLINED).count(),
    }

    all_requests = list(pending) + list(ongoing) + list(completed) + list(uncompleted)
    request_totals = {
        r.id: {
            'service_fee': calculate_service_fee(r.amount),
        }
        for r in all_requests
    }
    for rid, row in request_totals.items():
        amount = next((r.amount for r in all_requests if r.id == rid), None)
        if amount is not None:
            row['total_amount'] = amount + row['service_fee']

    handler_user_ids = [r.accepted_by_id for r in all_requests if r.accepted_by_id]
    handled_agents = {
        a.user_id: a
        for a in Agent.objects.filter(user_id__in=handler_user_ids).select_related('user')
    }

    return render(
        request,
        'core/admin_dashboard.html',
        {
            'counts': counts,
            'pending': pending,
            'ongoing': ongoing,
            'completed': completed,
            'uncompleted': uncompleted,
            'request_totals': request_totals,
            'handled_agents': handled_agents,
        },
    )
