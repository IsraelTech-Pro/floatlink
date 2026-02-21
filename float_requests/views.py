from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Max
from django.db import models

from agents.models import Agent

from .forms import FloatRequestCreateForm
from .models import FloatRequest, FloatRequestMessage, FloatRequestNotification
from .services import (
    accept_float_request,
    admin_complete_float_request,
    confirm_float_request,
    calculate_service_fee,
    haversine_km,
)


@login_required
def ecash_agents(request):
    amount = request.GET.get('amount')
    try:
        amount_val = float(amount) if amount else 0.0
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Invalid amount'}, status=400)

    agent = get_object_or_404(Agent, user=request.user)
    if not agent.is_verified:
        return JsonResponse({'ok': False, 'error': 'Agent not verified'}, status=403)

    qs = (
        Agent.objects
        .filter(
            is_verified=True,
            user__is_active=True,
            ecash_open=True,
            ecash_min__lte=amount_val,
            ecash_max__gte=amount_val,
        )
        .exclude(id=agent.id)
        .only('id', 'performance_score', 'user__username', 'ecash_min', 'ecash_max')
        .select_related('user')
        .order_by('-performance_score', 'id')
    )

    results = [
        {
            'id': a.id,
            'username': a.user.username,
            'score': float(a.performance_score),
            'min': float(a.ecash_min),
            'max': float(a.ecash_max),
        }
        for a in qs[:20]
    ]
    return JsonResponse({'ok': True, 'agents': results})


@login_required
def nearby_agents(request):
    try:
        lat = float(request.GET.get('lat', ''))
        lng = float(request.GET.get('lng', ''))
        amount = request.GET.get('amount')
        amount_val = float(amount) if amount else 0.0
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Invalid lat/lng/amount'}, status=400)

    agent = get_object_or_404(Agent, user=request.user)
    if not agent.is_verified:
        return JsonResponse({'ok': False, 'error': 'Agent not verified'}, status=403)

    # Basic ETA model: assume ~30km/h average in-city travel
    speed_kmh = 30.0
    radius_km = 10.0

    qs = (
        Agent.objects
        .filter(
            latitude__isnull=False,
            longitude__isnull=False,
            is_verified=True,
            user__is_active=True,
        )
        .exclude(id=agent.id)
        .only('id', 'latitude', 'longitude', 'performance_score', 'user__username')
        .select_related('user')
    )

    results = []
    for a in qs:
        dist_km = haversine_km(lat, lng, float(a.latitude), float(a.longitude))
        if dist_km > radius_km:
            continue
        eta_min = int(round((dist_km / speed_kmh) * 60))
        results.append({
            'id': a.id,
            'username': a.user.username,
            'distance_km': round(dist_km, 2),
            'eta_min': eta_min,
            'score': float(a.performance_score),
        })

    # Rank: nearest first, then performance score, then balance
    results.sort(key=lambda x: (x['distance_km'], -x['score']))
    return JsonResponse({'ok': True, 'agents': results[:10]})


@login_required
def create_request(request):
    if request.user.is_staff:
        raise Http404
    agent = get_object_or_404(Agent, user=request.user)
    if not agent.is_verified:
        messages.error(request, 'Your agent account must be verified before you can request float.')
        return redirect('agents:profile')

    if request.method == 'POST':
        form = FloatRequestCreateForm(request.POST)
        if form.is_valid():
            fr: FloatRequest = form.save(commit=False)
            fr.requesting_agent = agent
            fr.status = FloatRequest.Status.PENDING

            fr.save()

            User = get_user_model()
            for staff_user in User.objects.filter(is_staff=True, is_active=True):
                FloatRequestNotification.objects.create(
                    recipient=staff_user,
                    float_request=fr,
                    notification_type=FloatRequestNotification.NotificationType.NEW_REQUEST,
                )

            if fr.request_type == FloatRequest.RequestType.PHYSICAL_CASH:
                if fr.requester_latitude is None or fr.requester_longitude is None:
                    messages.error(request, 'Physical cash requests require GPS. Please allow location access and try again.')
                    return render(request, 'float_requests/create.html', {'form': form})

            messages.success(request, 'Float request created.')
            return redirect('float_requests:detail', pk=fr.pk)
    else:
        form = FloatRequestCreateForm()

    return render(request, 'float_requests/create.html', {'form': form})


@login_required
def my_requests(request):
    agent = get_object_or_404(Agent, user=request.user)
    requests = FloatRequest.objects.filter(requesting_agent=agent).order_by('-created_at')
    return render(request, 'float_requests/list.html', {'requests': requests, 'title': 'My Requests'})


@login_required
def incoming_requests(request):
    if not request.user.is_staff:
        raise Http404

    requests = (
        FloatRequest.objects
        .exclude(status=FloatRequest.Status.CANCELLED)
        .select_related('requesting_agent__user', 'accepted_by')
        .order_by('-created_at')
    )

    request_totals = {
        r.id: {
            'service_fee': calculate_service_fee(r.amount),
        }
        for r in requests
    }
    for rid, row in request_totals.items():
        amount = next((r.amount for r in requests if r.id == rid), None)
        if amount is not None:
            row['total_amount'] = amount + row['service_fee']

    return render(request, 'float_requests/incoming.html', {'requests': requests, 'request_totals': request_totals})


@login_required
def incoming_poll(request):
    if not request.user.is_staff:
        raise Http404
    return JsonResponse({'ok': True, 'requests': []})


@login_required
def notifications_poll(request):
    qs = (
        FloatRequestNotification.objects
        .filter(recipient=request.user, seen_at__isnull=True)
        .select_related('float_request', 'float_request__requesting_agent__user')
        .order_by('id')
    )

    payload = [
        {
            'id': n.id,
            'type': n.notification_type,
            'request_id': n.float_request_id,
            'amount': float(n.float_request.amount + calculate_service_fee(n.float_request.amount)) if request.user.is_staff else float(n.float_request.amount),
            'requester': n.float_request.requesting_agent.user.username,
        }
        for n in qs
    ]

    return JsonResponse({'ok': True, 'notifications': payload})


@login_required
@require_POST
def notification_ack(request, pk: int):
    n = get_object_or_404(FloatRequestNotification, pk=pk, recipient=request.user)
    if n.seen_at is None:
        n.seen_at = timezone.now()
        n.save(update_fields=['seen_at'])
    return JsonResponse({'ok': True})


@login_required
def incoming_feed(request):
    if not request.user.is_staff:
        raise Http404

    since_id = request.GET.get('since_id')
    try:
        since_id_int = int(since_id) if since_id else 0
    except Exception:
        since_id_int = 0

    qs = (
        FloatRequest.objects
        .filter(id__gt=since_id_int)
        .exclude(status=FloatRequest.Status.CANCELLED)
        .order_by('id')
        .select_related('requesting_agent__user')
    )

    payload = [
        {
            'id': r.id,
            'amount': float(r.amount + calculate_service_fee(r.amount)),
            'requester': r.requesting_agent.user.username,
            'status': r.status,
            'status_display': r.get_status_display(),
        }
        for r in qs
    ]

    return JsonResponse({'ok': True, 'requests': payload})


@login_required
def request_detail(request, pk: int):
    agent = Agent.objects.filter(user=request.user).first()
    fr = get_object_or_404(FloatRequest, pk=pk)

    is_staff = request.user.is_staff
    is_requester = bool(agent) and fr.requesting_agent_id == agent.id
    if not (is_staff or is_requester):
        raise Http404

    handled_agent = Agent.objects.filter(user=fr.accepted_by).first() if fr.accepted_by_id else None
    service_fee = calculate_service_fee(fr.amount)
    total_amount = fr.amount + service_fee

    return render(
        request,
        'float_requests/detail.html',
        {
            'fr': fr,
            'is_requester': is_requester,
            'is_staff': is_staff,
            'handled_agent': handled_agent,
            'service_fee': service_fee,
            'total_amount': total_amount,
        },
    )


@login_required
def request_messages(request, pk: int):
    agent = Agent.objects.filter(user=request.user).first()
    fr = get_object_or_404(FloatRequest, pk=pk)

    if request.user.is_staff:
        if not (request.user.is_superuser or fr.accepted_by_id == request.user.id):
            raise Http404
    else:
        if not agent or agent.id != fr.requesting_agent_id:
            raise Http404

    if fr.status not in (FloatRequest.Status.ACCEPTED, FloatRequest.Status.ADMIN_COMPLETED, FloatRequest.Status.COMPLETED):
        return JsonResponse({'ok': False, 'error': 'Chat not available yet.'}, status=400)

    since_id = request.GET.get('since_id')
    try:
        since_id_int = int(since_id) if since_id else 0
    except Exception:
        since_id_int = 0

    qs = (
        FloatRequestMessage.objects
        .filter(float_request=fr, id__gt=since_id_int)
        .select_related('sender__user', 'sender_user')
        .order_by('id')
    )

    messages_payload = [
        {
            'id': m.id,
            'sender': m.sender_user.get_username() if m.sender_user else (m.sender.user.username if m.sender_id else 'Unknown'),
            'sender_user_id': m.sender_user_id or (m.sender.user_id if m.sender_id else None),
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'created_at': m.created_at.isoformat(),
        }
        for m in qs
    ]

    return JsonResponse({'ok': True, 'messages': messages_payload})


@login_required
@require_POST
def send_message(request, pk: int):
    agent = Agent.objects.filter(user=request.user).first()
    fr = get_object_or_404(FloatRequest, pk=pk)

    if request.user.is_staff:
        if not (request.user.is_superuser or fr.accepted_by_id == request.user.id):
            raise Http404
    else:
        if not agent or agent.id != fr.requesting_agent_id:
            raise Http404

    if fr.status not in (FloatRequest.Status.ACCEPTED, FloatRequest.Status.ADMIN_COMPLETED, FloatRequest.Status.COMPLETED):
        return JsonResponse({'ok': False, 'error': 'Chat not available yet.'}, status=400)

    text = (request.POST.get('message') or '').strip()
    attachment = request.FILES.get('attachment')

    if not text and not attachment:
        return JsonResponse({'ok': False, 'error': 'Empty message.'}, status=400)

    m = FloatRequestMessage.objects.create(
        float_request=fr,
        sender=agent if not request.user.is_staff else None,
        sender_user=request.user,
        message=text,
        attachment=attachment,
    )
    return JsonResponse({'ok': True, 'id': m.id})


@login_required
def chat_history(request):
    if request.user.is_staff:
        qs = (
            FloatRequest.objects
            .filter(accepted_by=request.user)
            .filter(status__in=[FloatRequest.Status.ACCEPTED, FloatRequest.Status.ADMIN_COMPLETED, FloatRequest.Status.COMPLETED])
            .annotate(last_msg_id=Max('messages__id'))
            .order_by('-last_msg_id', '-id')
            .select_related('requesting_agent__user')
        )
    else:
        agent = get_object_or_404(Agent, user=request.user)
        qs = (
            FloatRequest.objects
            .filter(requesting_agent=agent)
            .filter(status__in=[FloatRequest.Status.ACCEPTED, FloatRequest.Status.ADMIN_COMPLETED, FloatRequest.Status.COMPLETED])
            .annotate(last_msg_id=Max('messages__id'))
            .order_by('-last_msg_id', '-id')
            .select_related('requesting_agent__user')
        )

    conversations = [{'fr': fr, 'other': None} for fr in qs]

    return render(request, 'float_requests/chat_history.html', {'conversations': conversations})


@login_required
@require_POST
def accept_request(request, pk: int):
    if not request.user.is_staff:
        raise Http404
    fr = get_object_or_404(FloatRequest, pk=pk)

    try:
        accept_float_request(fr, staff_user=request.user)
        messages.success(request, 'Request accepted. You can now process it and mark it done.')

        FloatRequestNotification.objects.create(
            recipient=fr.requesting_agent.user,
            float_request=fr,
            notification_type=FloatRequestNotification.NotificationType.ACCEPTED,
        )
    except Exception as e:
        messages.error(request, str(e))

    return redirect('float_requests:detail', pk=pk)


@login_required
@require_POST
def decline_request(request, pk: int):
    if not request.user.is_staff:
        raise Http404
    fr = get_object_or_404(FloatRequest, pk=pk)

    if fr.status != FloatRequest.Status.PENDING:
        messages.error(request, 'Only pending requests can be declined.')
        return redirect('float_requests:detail', pk=pk)

    fr.status = FloatRequest.Status.DECLINED
    fr.completed_at = timezone.now()
    fr.save(update_fields=['status', 'completed_at'])

    messages.success(request, 'Request declined.')
    return redirect('float_requests:detail', pk=pk)


@login_required
@require_POST
def cancel_request(request, pk: int):
    agent = get_object_or_404(Agent, user=request.user)
    fr = get_object_or_404(FloatRequest, pk=pk)

    if fr.requesting_agent_id != agent.id:
        raise Http404

    if fr.status != FloatRequest.Status.PENDING:
        messages.error(request, 'This request can no longer be cancelled.')
        return redirect('float_requests:detail', pk=pk)

    fr.status = FloatRequest.Status.CANCELLED
    fr.completed_at = timezone.now()
    fr.save(update_fields=['status', 'completed_at'])
    messages.success(request, 'Request cancelled.')
    return redirect('float_requests:my')


@login_required
@require_POST
def complete_request(request, pk: int):
    agent = Agent.objects.filter(user=request.user).first()
    fr = get_object_or_404(FloatRequest, pk=pk)

    try:
        if request.user.is_staff:
            admin_complete_float_request(fr, staff_user=request.user)
            messages.success(request, 'Marked done. Waiting for agent confirmation.')

            FloatRequestNotification.objects.create(
                recipient=fr.requesting_agent.user,
                float_request=fr,
                notification_type=FloatRequestNotification.NotificationType.ADMIN_COMPLETED,
            )
        else:
            if not agent:
                raise Http404
            confirm_float_request(fr, requesting_agent=agent)
            messages.success(request, 'Congratulations! Request confirmed. Transaction marked paid.')

            fr.refresh_from_db()
            if fr.accepted_by_id:
                FloatRequestNotification.objects.create(
                    recipient=fr.accepted_by,
                    float_request=fr,
                    notification_type=FloatRequestNotification.NotificationType.COMPLETED,
                )
    except Exception as e:
        messages.error(request, str(e))

    return redirect('float_requests:detail', pk=pk)
