from django.contrib import admin
from store.models import Category, Product, ProductImage, ProductVariant, ContactMessage, NewsletterSubscriber, ProductReview, HeroBanner, AdminAuditLog

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_featured', 'order', 'active_products_count']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_featured', 'order']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'regular_price', 'sale_price', 'stock_quantity', 'is_active', 'is_featured', 'is_new_arrival', 'is_best_seller']
    list_filter = ['category', 'is_active', 'is_featured', 'is_new_arrival', 'is_best_seller']
    list_editable = ['regular_price', 'sale_price', 'stock_quantity', 'is_active']
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'phone', 'email', 'subject', 'message']

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'created_at']
    search_fields = ['email']

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'product', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating']
    list_editable = ['is_approved']

@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'eyebrow', 'order', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']

@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'username', 'action', 'target_type', 'target_repr', 'ip_address']
    list_filter = ['action', 'created_at']
    readonly_fields = ['username', 'action', 'target_type', 'target_repr', 'details', 'ip_address', 'created_at']

