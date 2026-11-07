from django.contrib import admin

from .models import GasInventory, GasType


@admin.register(GasType)
class GasTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'cylinder_size', 'created_at')
    list_filter = ('cylinder_size',)
    search_fields = ('name',)


@admin.register(GasInventory)
class GasInventoryAdmin(admin.ModelAdmin):
    list_display = ('dealer', 'gas_type', 'price_refill', 'price_exchange', 'stock_available', 'updated_at')
    list_filter = ('stock_available', 'gas_type')
    search_fields = ('dealer__name', 'dealer__shop_name', 'gas_type__name')
