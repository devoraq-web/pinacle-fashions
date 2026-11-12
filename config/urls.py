from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


def healthz_view(request):
    """Lightweight healthcheck endpoint for Render."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


# Customize standard Django Admin headers
admin.site.site_header = "PINACLE FASHIONS Admin Portal"
admin.site.site_title = "PINACLE FASHIONS"
admin.site.index_title = "Brand Management & Catalog"

urlpatterns = [
    path('healthz/', healthz_view, name='healthz'),

    # Built-in Django Admin
    path('admin/', admin.site.urls),

    # Custom Admin Dashboard
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),

    # Orders & WhatsApp Checkout
    path('orders/', include('orders.urls', namespace='orders')),

    # Customer Store (Catalog, Cart, Wishlist, Pages)
    path('', include('store.urls', namespace='store')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

