from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from store.models import Product, Category, HeroBanner
from orders.models import Order
from store.validators import validate_image_file


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'sku',
            'category',
            'description',
            'specifications',
            'regular_price',
            'sale_price',
            'stock_quantity',
            'available_sizes',
            'available_colours',
            'is_active',
            'is_featured',
            'is_new_arrival',
            'is_best_seller',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Royal Maroon Kanjeevaram Silk Saree'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PF-SR-101'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed luxury description of fabric, design, and style...'}),
            'specifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Fabric: Pure Silk\nWork: Zari Weaving\nLength: 6.3m with Blouse\nWash Care: Dry Clean Only'}),
            'regular_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Original Price (₹)', 'step': '0.01', 'min': '1'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Offer Price (₹) - Leave blank if not on sale', 'step': '0.01', 'min': '0'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Units in stock', 'min': '0'}),
            'available_sizes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. S, M, L, XL, XXL or Free Size'}),
            'available_colours': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Royal Maroon, Champagne Gold, Navy Blue'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_new_arrival': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_best_seller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_regular_price(self):
        price = self.cleaned_data.get('regular_price')
        if price is None or price <= Decimal('0.00'):
            raise ValidationError("Regular price must be greater than zero.")
        return price

    def clean(self):
        cleaned = super().clean()
        reg = cleaned.get('regular_price')
        sale = cleaned.get('sale_price')
        if sale is not None:
            if sale <= Decimal('0.00'):
                self.add_error('sale_price', "Sale price must be greater than zero.")
            elif reg is not None and sale >= reg:
                self.add_error('sale_price', "Sale price must be strictly lower than regular MRP price.")
        return cleaned


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'image', 'is_active', 'is_featured', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Short description'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,image/webp'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def clean_image(self):
        img = self.cleaned_data.get('image')
        # Only run file content validation on newly uploaded InMemory/Temporary files
        if img and hasattr(img, 'content_type'):
            validate_image_file(img)
        return img


class HeroBannerForm(forms.ModelForm):
    class Meta:
        model = HeroBanner
        fields = [
            'eyebrow',
            'title',
            'subtitle',
            'image',
            'cta_primary_text',
            'cta_primary_url',
            'cta_secondary_text',
            'cta_secondary_url',
            'order',
            'is_active',
        ]
        widgets = {
            'eyebrow': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bridal Couture 2026'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Timeless Grace, Handwoven'}),
            'subtitle': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Editorial tagline...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,image/webp'}),
            'cta_primary_text': forms.TextInput(attrs={'class': 'form-control'}),
            'cta_primary_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/shop/'}),
            'cta_secondary_text': forms.TextInput(attrs={'class': 'form-control'}),
            'cta_secondary_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/new-arrivals/'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_image(self):
        img = self.cleaned_data.get('image')
        if img and hasattr(img, 'content_type'):
            validate_image_file(img)
        return img


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
