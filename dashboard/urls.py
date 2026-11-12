from django.urls import path
from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    # Auth
    path('login/', views.admin_login_view, name='login'),
    path('logout/', views.admin_logout_view, name='logout'),

    # Overview
    path('', views.dashboard_overview, name='overview'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/edit/<int:pk>/', views.product_edit, name='product_edit'),
    path('products/toggle-active/<int:pk>/', views.product_toggle_active, name='product_toggle_active'),
    path('products/delete/<int:pk>/', views.product_delete, name='product_delete'),
    path('products/image-delete/<int:image_id>/', views.product_image_delete, name='product_image_delete'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/edit/<int:pk>/', views.category_edit, name='category_edit'),
    path('categories/toggle-active/<int:pk>/', views.category_toggle_active, name='category_toggle_active'),
    path('categories/delete/<int:pk>/', views.category_delete, name='category_delete'),

    # Homepage Hero Banners
    path('banners/', views.banner_list, name='banner_list'),
    path('banners/create/', views.banner_create, name='banner_create'),
    path('banners/edit/<int:pk>/', views.banner_edit, name='banner_edit'),
    path('banners/delete/<int:pk>/', views.banner_delete, name='banner_delete'),

    # Inventory
    path('inventory/', views.inventory_view, name='inventory'),
    path('inventory/update/<int:product_id>/', views.inventory_quick_update, name='inventory_quick_update'),

    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/export-csv/', views.order_export_csv, name='order_export_csv'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/print/', views.order_invoice, name='order_invoice'),
    path('orders/<str:order_number>/status/<str:status_code>/', views.order_quick_status, name='order_quick_status'),

    # Security Audit Trail
    path('audit-logs/', views.audit_log_list, name='audit_logs'),
]
