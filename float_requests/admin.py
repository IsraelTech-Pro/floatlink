from django.contrib import admin

from .models import FloatRequest


@admin.register(FloatRequest)
class FloatRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'requesting_agent',
        'request_type',
        'amount',
        'status',
        'accepted_by',
        'accepted_at',
        'admin_completed_at',
        'agent_confirmed_at',
        'requester_latitude',
        'requester_longitude',
        'created_at',
    )
    list_filter = ()
    search_fields = ('requesting_agent__user__username', 'accepted_by__username')

    def has_add_permission(self, request):
        return False
