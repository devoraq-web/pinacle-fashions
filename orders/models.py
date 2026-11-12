import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from store.models import Product


class CustomerAddress(models.Model):
    full_name = models.CharField(max_length=150)
    mobile_number = models.CharField(max_length=20)
    house_name_number = models.CharField(max_length=255, verbose_name="House Name / House Number")
    street_location = models.CharField(max_length=255, verbose_name="Street / Location")
    city = models.CharField(max_length=120)
    district = models.CharField(max_length=120)
    state = models.CharField(max_length=120, default="Kerala")
    pin_code = models.CharField(max_length=12, verbose_name="PIN Code")
    delivery_instructions = models.TextField(blank=True, verbose_name="Optional Delivery Instructions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Customer Address'
        verbose_name_plural = 'Customer Addresses'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.city}, {self.pin_code})"

    @property
    def formatted_address(self):
        parts = [
            self.house_name_number,
            self.street_location,
            self.city,
            self.district,
            f"{self.state} - {self.pin_code}"
        ]
        return ", ".join([p for p in parts if p])


class Order(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_SHIPPED = 'SHIPPED'
    STATUS_DELIVERED = 'DELIVERED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending WhatsApp Confirmation'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    SOURCE_BUY_NOW = 'BUY_NOW'
    SOURCE_CART = 'CART'
    SOURCE_CHOICES = [
        (SOURCE_BUY_NOW, 'Direct Buy Now'),
        (SOURCE_CART, 'Cart Checkout'),
    ]

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    address = models.ForeignKey(CustomerAddress, on_delete=models.PROTECT, related_name='orders')
    
    # Snapshot of customer contact for fast queries
    customer_name = models.CharField(max_length=150)
    customer_phone = models.CharField(max_length=20)
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    order_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_BUY_NOW)
    notes = models.TextField(blank=True, help_text="Customer notes / instructions")
    
    # WhatsApp tracking
    whatsapp_url = models.TextField(blank=True, help_text="Generated WhatsApp chat link")
    is_whatsapp_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} - {self.customer_name} (₹{self.total_price})"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate e.g. PF-2026-A1B2C3
            year = timezone.now().strftime('%y%m')
            random_part = uuid.uuid4().hex[:6].upper()
            self.order_number = f"PF-{year}-{random_part}"
        super().save(*args, **kwargs)

    @property
    def total_items_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def status_badge_class(self):
        classes = {
            self.STATUS_PENDING: 'bg-warning text-dark',
            self.STATUS_CONFIRMED: 'bg-info text-dark',
            self.STATUS_PROCESSING: 'bg-primary text-white',
            self.STATUS_SHIPPED: 'bg-secondary text-white',
            self.STATUS_DELIVERED: 'bg-success text-white',
            self.STATUS_CANCELLED: 'bg-danger text-white',
        }
        return classes.get(self.status, 'bg-secondary text-white')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    
    # Permanent snapshots of ordered product details at the exact moment of order
    product_name = models.CharField(max_length=255)
    product_code = models.CharField(max_length=64, help_text="Product SKU / Code snapshot")
    product_image_url = models.CharField(max_length=500, blank=True)
    selected_size = models.CharField(max_length=64, default="Free Size")
    selected_colour = models.CharField(max_length=64, default="Standard")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.product_name} x {self.quantity} ({self.selected_size}/{self.selected_colour})"

