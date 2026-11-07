from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'dealer', 'gas_type', 'order_type', 'status', 'price', 'created_at')
    list_filter = ('status', 'order_type', 'gas_type')
    search_fields = ('id', 'customer__phone_number', 'dealer__name', 'dealer__shop_name')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('customer', 'dealer', 'gas_type')
