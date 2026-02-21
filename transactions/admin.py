from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'float_request', 'from_agent', 'to_agent', 'amount', 'service_fee', 'status', 'created_at')
    list_filter = ()
    search_fields = ('from_agent__user__username', 'to_agent__user__username')

    def has_add_permission(self, request):
        return False
