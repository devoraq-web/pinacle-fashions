from django.contrib import admin
from orders.models import Order, OrderItem, CustomerAddress

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_code', 'selected_size', 'selected_colour', 'unit_price', 'quantity', 'total_price']

@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'mobile_number', 'city', 'district', 'state', 'pin_code', 'created_at']
    search_fields = ['full_name', 'mobile_number', 'city', 'pin_code']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'customer_phone', 'total_price', 'status', 'order_source', 'created_at']
    list_filter = ['status', 'order_source', 'created_at']
    search_fields = ['order_number', 'customer_name', 'customer_phone', 'address__pin_code']
    inlines = [OrderItemInline]
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'whatsapp_url']

