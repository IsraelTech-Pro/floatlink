from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group

from agents.models import Agent


User = get_user_model()


class AgentInline(admin.StackedInline):
    model = Agent
    can_delete = False
    extra = 0
    max_num = 1


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
        'agent_verified',
    )

    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    actions = ('verify_selected', 'unverify_selected', 'terminate_selected')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Profile', {'fields': ('first_name', 'last_name', 'email'), 'classes': ('collapse',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions'), 'classes': ('collapse',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
    )

    inlines = (AgentInline,)

    def agent_verified(self, obj):
        agent = getattr(obj, 'agent', None)
        return bool(agent and agent.is_verified)

    agent_verified.boolean = True
    agent_verified.short_description = 'Verified'

    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def verify_selected(self, request, queryset):
        updated = 0
        for user in queryset:
            agent, _created = Agent.objects.get_or_create(user=user)
            if not agent.is_verified:
                agent.is_verified = True
                agent.save(update_fields=['is_verified'])
                updated += 1
        self.message_user(request, f'Verified {updated} user(s).', level=messages.SUCCESS)

    verify_selected.short_description = 'Verify selected users'

    def unverify_selected(self, request, queryset):
        updated = 0
        for user in queryset:
            agent, _created = Agent.objects.get_or_create(user=user)
            if agent.is_verified:
                agent.is_verified = False
                agent.save(update_fields=['is_verified'])
                updated += 1
        self.message_user(request, f'Unverified {updated} user(s).', level=messages.WARNING)

    unverify_selected.short_description = 'Unverify selected users'

    def terminate_selected(self, request, queryset):
        updated = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f'Terminated {updated} account(s).', level=messages.ERROR)

    terminate_selected.short_description = 'Terminate (deactivate) selected accounts'
