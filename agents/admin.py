from django.contrib import admin
from django.contrib import messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404, redirect

from .models import Agent


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'phone_number',
        'location',
        'latitude',
        'longitude',
        'performance_score',
        'performance_votes',
        'ecash_open',
        'ecash_min',
        'ecash_max',
        'is_verified',
        'user_is_active',
        'quick_actions',
        'created_at',
    )
    list_filter = ()
    search_fields = ('user__username', 'user__email', 'phone_number', 'location')

    actions = ('verify_agents', 'unverify_agents', 'terminate_agents')

    def user_is_active(self, obj: Agent):
        return obj.user.is_active

    user_is_active.boolean = True
    user_is_active.short_description = 'Active'

    def quick_actions(self, obj: Agent):
        verify_url = reverse('admin:agents_agent_verify', args=[obj.pk])
        unverify_url = reverse('admin:agents_agent_unverify', args=[obj.pk])
        terminate_url = reverse('admin:agents_agent_terminate', args=[obj.pk])

        parts = []
        if obj.is_verified:
            parts.append(format_html('<a class="button" href="{}">Unverify</a>', unverify_url))
        else:
            parts.append(format_html('<a class="button" href="{}">Verify</a>', verify_url))

        if obj.user.is_active:
            parts.append(format_html('<a class="button" href="{}">Terminate</a>', terminate_url))

        return format_html(' '.join(str(p) for p in parts))

    quick_actions.short_description = 'Actions'

    def verify_agents(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'Verified {updated} agent(s).', level=messages.SUCCESS)

    verify_agents.short_description = 'Verify selected agents'

    def unverify_agents(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'Unverified {updated} agent(s).', level=messages.SUCCESS)

    unverify_agents.short_description = 'Unverify selected agents'

    def terminate_agents(self, request, queryset):
        users = [a.user for a in queryset.select_related('user')]
        updated = 0
        for user in users:
            if user.is_active:
                user.is_active = False
                user.save(update_fields=['is_active'])
                updated += 1
        self.message_user(request, f'Terminated {updated} account(s).', level=messages.WARNING)

    terminate_agents.short_description = 'Terminate (deactivate) selected accounts'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:agent_id>/verify/', self.admin_site.admin_view(self.verify_view), name='agents_agent_verify'),
            path('<int:agent_id>/unverify/', self.admin_site.admin_view(self.unverify_view), name='agents_agent_unverify'),
            path('<int:agent_id>/terminate/', self.admin_site.admin_view(self.terminate_view), name='agents_agent_terminate'),
        ]
        return custom + urls

    def verify_view(self, request, agent_id: int):
        agent = get_object_or_404(Agent, pk=agent_id)
        agent.is_verified = True
        agent.save(update_fields=['is_verified'])
        self.message_user(request, f'Agent {agent} verified.', level=messages.SUCCESS)
        return redirect(request.META.get('HTTP_REFERER', reverse('admin:agents_agent_changelist')))

    def unverify_view(self, request, agent_id: int):
        agent = get_object_or_404(Agent, pk=agent_id)
        agent.is_verified = False
        agent.save(update_fields=['is_verified'])
        self.message_user(request, f'Agent {agent} unverified.', level=messages.WARNING)
        return redirect(request.META.get('HTTP_REFERER', reverse('admin:agents_agent_changelist')))

    def terminate_view(self, request, agent_id: int):
        agent = get_object_or_404(Agent, pk=agent_id)
        if agent.user.is_active:
            agent.user.is_active = False
            agent.user.save(update_fields=['is_active'])
            self.message_user(request, f'Account for {agent} deactivated.', level=messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER', reverse('admin:agents_agent_changelist')))

    def has_add_permission(self, request):
        return False
