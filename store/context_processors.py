from django.conf import settings
from store.models import Category
from store.cart import Cart
from store.wishlist import Wishlist

def categories_processor(request):
    """Provides all active categories ordered for navigation."""
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    return {
        'nav_categories': categories
    }

def cart_processor(request):
    """Provides cart and cart stats to all templates."""
    cart = Cart(request)
    return {
        'cart': cart,
        'cart_count': len(cart),
        'cart_subtotal': cart.get_subtotal(),
    }

def wishlist_processor(request):
    """Provides wishlist count and saved product IDs to all templates."""
    wishlist = Wishlist(request)
    return {
        'wishlist_count': len(wishlist),
        'wishlist_ids': wishlist.wishlist,
    }

def brand_info_processor(request):
    """Global brand identity constants."""
    return {
        'BRAND_NAME': settings.BRAND_NAME,
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
        'WHATSAPP_DISPLAY_NUMBER': getattr(settings, 'WHATSAPP_DISPLAY_NUMBER', '+91 9292247815'),
        'INSTAGRAM_HANDLE': getattr(settings, 'INSTAGRAM_HANDLE', 'pinaclefashions'),
        'INSTAGRAM_URL': getattr(settings, 'INSTAGRAM_URL', 'https://www.instagram.com/pinaclefashions/'),
        'SUPPORT_EMAIL': getattr(settings, 'SUPPORT_EMAIL', 'pinaclefashions@gmail.com'),
        'STORE_LOCATION': getattr(settings, 'STORE_LOCATION', 'Kerala, India'),
    }

