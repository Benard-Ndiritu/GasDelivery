from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'method', 'amount', 'status', 'mpesa_receipt', 'paid_at', 'created_at')
    list_filter = ('method', 'status')
    search_fields = ('order__id', 'mpesa_receipt', 'checkout_request_id', 'phone_number')
    readonly_fields = ('created_at', 'updated_at', 'paid_at', 'checkout_request_id', 'merchant_request_id')
