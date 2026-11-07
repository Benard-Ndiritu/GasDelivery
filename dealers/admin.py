from django.contrib import admin

from .models import DealerProfile


@admin.register(DealerProfile)
class DealerProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop_name', 'phone_number', 'status', 'is_active', 'delivery_radius', 'created_at')
    list_filter = ('status', 'is_active', 'delivery_radius')
    search_fields = ('name', 'shop_name', 'phone_number', 'user__phone_number')
    readonly_fields = ('created_at', 'updated_at')
