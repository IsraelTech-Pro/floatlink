import json

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AgentProfileForm, AgentRegistrationForm, UserDisplayNameForm
from .models import Agent


def register(request):
    if request.method == 'POST':
        form = AgentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()

            agent, _created = Agent.objects.get_or_create(user=user)
            agent.phone_number = form.cleaned_data['phone_number']
            agent.location = form.cleaned_data['location']
            agent.save(update_fields=['phone_number', 'location'])

            login(request, user)
            return redirect('core:dashboard')
    else:
        form = AgentRegistrationForm()

    return render(request, 'agents/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            Agent.objects.get_or_create(user=user)
            return redirect('core:dashboard')
    return render(request, 'agents/login.html')


def logout_view(request):
    logout(request)
    return redirect('core:home')


@login_required
def profile(request):
    agent = Agent.objects.get(user=request.user)

    if request.method == 'POST':
        form = AgentProfileForm(request.POST, instance=agent)
        user_form = UserDisplayNameForm(request.POST, instance=request.user)
        if form.is_valid() and user_form.is_valid():
            form.save()
            user_form.save()
            messages.success(request, 'Profile updated.')
            return redirect('agents:profile')
    else:
        form = AgentProfileForm(instance=agent)
        user_form = UserDisplayNameForm(instance=request.user)

    return render(request, 'agents/profile.html', {'agent': agent, 'form': form, 'user_form': user_form})


@login_required
@require_POST
def update_gps(request):
    agent = get_object_or_404(Agent, user=request.user)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        payload = {}

    lat = payload.get('latitude')
    lng = payload.get('longitude')

    if lat is None or lng is None:
        return JsonResponse({'ok': False, 'error': 'Missing latitude/longitude'}, status=400)

    agent.latitude = lat
    agent.longitude = lng
    agent.save(update_fields=['latitude', 'longitude'])
    return JsonResponse({'ok': True})
