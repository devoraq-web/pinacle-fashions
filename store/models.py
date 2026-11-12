import os
from decimal import Decimal
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True, help_text="Show this category in the customer store")
    is_featured = models.BooleanField(default=True, db_index=True, help_text="Show in featured categories on homepage")
    order = models.PositiveIntegerField(default=0, db_index=True, help_text="Sort order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('store:category_detail', kwargs={'slug': self.slug})

    @property
    def active_products_count(self):
        return self.products.filter(is_active=True).count()


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    sku = models.CharField(max_length=64, unique=True, help_text="Unique Product Code e.g. PF-SR-001")
    description = models.TextField(help_text="Detailed product description")
    specifications = models.TextField(
        blank=True,
        help_text="Specifications formatted line-by-line (e.g. Fabric: Pure Silk | Work: Zari Embroidery | Wash: Dry Clean)"
    )
    regular_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Original / MRP price in INR")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Discounted offer price in INR")
    stock_quantity = models.PositiveIntegerField(default=10, help_text="Available inventory units")
    
    # Attributes & options
    available_sizes = models.CharField(
        max_length=255, 
        default="S, M, L, XL, XXL", 
        help_text="Comma-separated sizes (e.g., S, M, L, XL, XXL or Free Size)"
    )
    available_colours = models.CharField(
        max_length=255, 
        default="Champagne Gold, Maroon, Royal Blue", 
        help_text="Comma-separated colors (e.g., Champagne Gold, Wine Red, Peacock Blue)"
    )
    
    # Flags
    is_active = models.BooleanField(default=True, db_index=True, help_text="Visible in store")
    is_featured = models.BooleanField(default=False, db_index=True, help_text="Show in Featured Collections")
    is_new_arrival = models.BooleanField(default=False, db_index=True, help_text="Show in New Arrivals section")
    is_best_seller = models.BooleanField(default=False, db_index=True, help_text="Show in Best Sellers section")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def get_absolute_url(self):
        return reverse('store:product_detail', kwargs={'slug': self.slug})

    @property
    def price(self):
        """Current applicable price (sale_price if set and lower, else regular_price)."""
        if self.sale_price and self.sale_price < self.regular_price:
            return self.sale_price
        return self.regular_price

    @property
    def is_on_sale(self):
        return bool(self.sale_price and self.sale_price < self.regular_price)

    @property
    def discount_percentage(self):
        if self.is_on_sale and self.regular_price > 0:
            diff = self.regular_price - self.sale_price
            return int(round((diff / self.regular_price) * 100))
        return 0

    @property
    def is_in_stock(self):
        return self.is_active and self.stock_quantity > 0

    @property
    def sizes_list(self):
        if not self.available_sizes:
            return []
        return [s.strip() for s in self.available_sizes.split(',') if s.strip()]

    @property
    def colours_list(self):
        if not self.available_colours:
            return []
        return [c.strip() for c in self.available_colours.split(',') if c.strip()]

    @property
    def primary_image(self):
        # Iterate prefetched cache if available to avoid N+1 SQL queries
        imgs = list(self.images.all())
        for img in imgs:
            if img.is_primary:
                return img
        return imgs[0] if imgs else None

    @property
    def average_rating(self):
        approved = [r for r in self.reviews.all() if r.is_approved]
        if approved:
            avg = sum(r.rating for r in approved) / len(approved)
            return round(avg, 1)
        return 5.0

    @property
    def reviews_count(self):
        return sum(1 for r in self.reviews.all() if r.is_approved)

    @property
    def specifications_dict(self):
        """Parses specifications lines into label: value pairs."""
        specs = {}
        if not self.specifications:
            return specs
        for line in self.specifications.split('\n'):
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                key, val = line.split(':', 1)
                specs[key.strip()] = val.strip()
            elif '|' in line:
                parts = line.split('|')
                for part in parts:
                    if ':' in part:
                        k, v = part.split(':', 1)
                        specs[k.strip()] = v.strip()
            else:
                specs[line] = ''
        return specs


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/%Y/%m/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['order', '-is_primary', 'id']

    def __str__(self):
        return f"Image for {self.product.name} ({'Primary' if self.is_primary else 'Gallery'})"

    def save(self, *args, **kwargs):
        # If this is marked as primary, unmark existing primary images for this product
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductVariant(models.Model):
    """Optional explicit variant matrix for size + color combinations."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=32)
    colour = models.CharField(max_length=64)
    stock_quantity = models.PositiveIntegerField(default=5)
    sku_code = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'
        unique_together = ('product', 'size', 'colour')

    def __str__(self):
        return f"{self.product.name} - {self.size} / {self.colour}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    subject = models.CharField(max_length=200, default="Customer Inquiry")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name} ({self.created_at.strftime('%d-%b-%Y')})"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer_name = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField(default=5, help_text="Rating from 1 to 5 stars")
    review_text = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Product Review'
        verbose_name_plural = 'Product Reviews'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name} on {self.product.name} ({self.rating}★)"

    @property
    def stars_range(self):
        return range(self.rating)

    @property
    def empty_stars_range(self):
        return range(5 - self.rating)


class HeroBanner(models.Model):
    """Admin-managed homepage editorial carousel banners."""
    eyebrow = models.CharField(max_length=120, default="Haute Couture 2026")
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    image = models.ImageField(upload_to='banners/')
    cta_primary_text = models.CharField(max_length=60, default="Explore Collections")
    cta_primary_url = models.CharField(max_length=255, default="/shop/")
    cta_secondary_text = models.CharField(max_length=60, blank=True, default="New Arrivals")
    cta_secondary_url = models.CharField(max_length=255, blank=True, default="/new-arrivals/")
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Hero Banner'
        verbose_name_plural = 'Hero Banners'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title


class AdminAuditLog(models.Model):
    """Security audit trail for sensitive administrative operations."""
    username = models.CharField(max_length=150)
    action = models.CharField(max_length=100, db_index=True)
    target_type = models.CharField(max_length=64, blank=True)
    target_repr = models.CharField(max_length=255, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.CharField(max_length=45, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Admin Audit Log'
        verbose_name_plural = 'Admin Audit Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.username}: {self.action} ({self.target_repr})"



