from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver


class AgentsConfig(AppConfig):
    name = 'agents'


@receiver(post_migrate)
def ensure_agents_for_existing_users(sender, **kwargs):
    if getattr(sender, 'name', None) != 'agents':
        return

    from .models import Agent

    User = get_user_model()
    for user in User.objects.all().only('id'):
        Agent.objects.get_or_create(user=user)

