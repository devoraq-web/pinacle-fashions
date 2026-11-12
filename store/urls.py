from django.urls import path
from store import views

app_name = 'store'

urlpatterns = [
    # Customer Store Pages
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('new-arrivals/', views.new_arrivals, name='new_arrivals'),
    path('categories/', views.categories_list, name='categories'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # Shopping Cart
    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/', views.cart_update, name='cart_update'),
    path('cart/remove/<str:item_key>/', views.cart_remove, name='cart_remove'),
    path('cart/clear/', views.cart_clear, name='cart_clear'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),

    # Informational Pages
    path('about/', views.about_us, name='about'),
    path('contact/', views.contact_us, name='contact'),
    path('policies/', views.policies_view, name='policies'),

    # AJAX & Utilities
    path('api/quick-view/<int:product_id>/', views.quick_view, name='quick_view'),
    path('newsletter/subscribe/', views.newsletter_signup, name='newsletter_signup'),
]

