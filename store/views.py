from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, F, Count
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.template.loader import render_to_string
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from store.models import (
    Category, Product, ProductImage, ContactMessage,
    NewsletterSubscriber, ProductReview, HeroBanner
)
from store.forms import ContactForm, NewsletterForm, ProductReviewForm
from store.cart import Cart
from store.wishlist import Wishlist
from store.validators import get_safe_redirect_url


def _optimized_product_qs():
    """Base active product queryset optimized against N+1 category/image queries."""
    return (
        Product.objects.filter(is_active=True, category__is_active=True)
        .select_related('category')
        .prefetch_related('images')
    )


def home(request):
    """
    Homepage showcasing luxury PINACLE FASHIONS editorial experience:
    - Hero carousel (admin-managed banners + static fallbacks)
    - Moving brand tagline marquee
    - Shop by Categories (annotated product counts & category-specific covers)
    - Latest Products, Best Sellers, New Arrivals
    - Brand Story spotlight
    - Horizontal Customer Reviews carousel
    - Instagram Lookbook Gallery
    """
    categories = (
        Category.objects.filter(is_active=True, is_featured=True)
        .annotate(active_count=Count('products', filter=Q(products__is_active=True)))
        .order_by('order', 'name')
    )
    if not categories.exists():
        categories = (
            Category.objects.filter(is_active=True)
            .annotate(active_count=Count('products', filter=Q(products__is_active=True)))
            .order_by('order', 'name')
        )

    hero_banners = HeroBanner.objects.filter(is_active=True).order_by('order', '-created_at')[:5]

    latest_products = _optimized_product_qs().order_by('-created_at')[:8]
    new_arrivals = _optimized_product_qs().filter(is_new_arrival=True).order_by('-created_at')[:8]
    best_sellers = _optimized_product_qs().filter(is_best_seller=True).order_by('-created_at')[:8]
    featured_products = _optimized_product_qs().filter(is_featured=True).order_by('-created_at')[:8]

    sale_products = (
        _optimized_product_qs()
        .filter(sale_price__isnull=False)
        .exclude(sale_price__gte=F('regular_price'))
        .order_by('-created_at')[:8]
    )

    approved_reviews = (
        ProductReview.objects.filter(is_approved=True)
        .select_related('product')
        .order_by('-created_at')[:8]
    )

    context = {
        'hero_banners': hero_banners,
        'featured_categories': categories,
        'latest_products': latest_products,
        'new_arrivals': new_arrivals,
        'best_sellers': best_sellers,
        'featured_products': featured_products,
        'sale_products': sale_products,
        'approved_reviews': approved_reviews,
    }
    return render(request, 'store/home.html', context)


def shop(request):
    """
    Shop All catalog with optimized filtering (category, sale, price range, availability) & sorting.
    """
    products = _optimized_product_qs()

    q = request.GET.get('q', '').strip()[:120]
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(sku__icontains=q) |
            Q(description__icontains=q) |
            Q(category__name__icontains=q)
        )

    category_slug = request.GET.get('category', '').strip()
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=selected_category)

    sale_only = request.GET.get('sale') == '1'
    if sale_only:
        products = products.filter(sale_price__isnull=False).exclude(sale_price__gte=F('regular_price'))

    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    try:
        if min_price:
            min_dec = Decimal(min_price)
            if min_dec >= 0:
                products = products.filter(regular_price__gte=min_dec)
    except (InvalidOperation, ValueError, TypeError):
        min_price = ''
    try:
        if max_price:
            max_dec = Decimal(max_price)
            if max_dec >= 0:
                products = products.filter(regular_price__lte=max_dec)
    except (InvalidOperation, ValueError, TypeError):
        max_price = ''

    in_stock_only = request.GET.get('in_stock') == '1'
    if in_stock_only:
        products = products.filter(stock_quantity__gt=0)

    sort = request.GET.get('sort', 'newest')
    if sort == 'price_low':
        products = products.order_by('regular_price')
    elif sort == 'price_high':
        products = products.order_by('-regular_price')
    elif sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.get_page(1)

    categories = (
        Category.objects.filter(is_active=True)
        .annotate(active_count=Count('products', filter=Q(products__is_active=True)))
        .order_by('order', 'name')
    )

    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'total_count': paginator.count,
        'categories': categories,
        'selected_category': selected_category,
        'current_sort': sort,
        'search_query': q,
        'min_price': min_price,
        'max_price': max_price,
        'in_stock_only': in_stock_only,
        'sale_only': sale_only,
    }
    return render(request, 'store/shop.html', context)


def new_arrivals(request):
    """Curated New Arrivals page."""
    products = _optimized_product_qs().filter(is_new_arrival=True).order_by('-created_at')

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(active_count=Count('products', filter=Q(products__is_active=True)))
        .order_by('order', 'name')
    )

    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'total_count': paginator.count,
        'categories': categories,
        'title': 'New Arrivals',
        'subtitle': 'Explore our latest luxury weaves, festive drapes, and seasonal couture drops',
    }
    return render(request, 'store/shop.html', context)


def categories_list(request):
    """Overview of all active product categories."""
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(active_count=Count('products', filter=Q(products__is_active=True)))
        .order_by('order', 'name')
    )
    context = {
        'categories': categories,
    }
    return render(request, 'store/categories.html', context)


def category_detail(request, slug):
    """Category detail landing page listing all category products."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = _optimized_product_qs().filter(category=category).order_by('-created_at')

    sort = request.GET.get('sort', 'newest')
    if sort == 'price_low':
        products = products.order_by('regular_price')
    elif sort == 'price_high':
        products = products.order_by('-regular_price')
    elif sort == 'name_asc':
        products = products.order_by('name')

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(active_count=Count('products', filter=Q(products__is_active=True)))
        .order_by('order', 'name')
    )

    context = {
        'selected_category': category,
        'category': category,
        'categories': categories,
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'total_count': paginator.count,
        'current_sort': sort,
    }
    return render(request, 'store/shop.html', context)


def product_detail(request, slug):
    """
    Detailed product showcase:
    - High-definition gallery with interactive image zoom
    - Size & colour selection
    - Stock quantity & automatic Out-of-Stock restrictions
    - Add to Bag & Instant WhatsApp Buy Now
    - Verified customer reviews & submission
    - Related & recently viewed couture pieces
    """
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images', 'reviews'),
        slug=slug,
        is_active=True,
        category__is_active=True,
    )
    images = list(product.images.all())
    related_products = (
        _optimized_product_qs()
        .filter(category=product.category)
        .exclude(id=product.id)
        .order_by('-is_featured', '-created_at')[:4]
    )

    if request.method == 'POST' and 'submit_review' in request.POST:
        review_form = ProductReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.product = product
            review.save()
            messages.success(request, "Thank you! Your review has been published.")
            return redirect('store:product_detail', slug=product.slug)
        else:
            messages.error(request, "Please check your review details and try again.")
    else:
        review_form = ProductReviewForm()

    reviews = [r for r in product.reviews.all() if r.is_approved]

    recently_viewed = request.session.get('recently_viewed', [])
    if not isinstance(recently_viewed, list):
        recently_viewed = []
    if product.id in recently_viewed:
        recently_viewed.remove(product.id)
    recently_viewed.insert(0, product.id)
    request.session['recently_viewed'] = recently_viewed[:8]
    request.session.modified = True

    recent_ids = [pid for pid in recently_viewed if pid != product.id][:4]
    recently_viewed_products = _optimized_product_qs().filter(id__in=recent_ids) if recent_ids else []

    context = {
        'product': product,
        'images': images,
        'related_products': related_products,
        'recently_viewed_products': recently_viewed_products,
        'sizes': product.sizes_list,
        'colours': product.colours_list,
        'specs': product.specifications_dict,
        'reviews': reviews,
        'review_form': review_form,
    }
    return render(request, 'store/product_detail.html', context)


# ==========================================
# SHOPPING CART VIEWS
# ==========================================

def cart_detail(request):
    """View shopping cart with item controls and checkout CTA."""
    cart = Cart(request)
    context = {
        'cart': cart,
        'subtotal': cart.get_subtotal(),
        'total': cart.get_total(),
    }
    return render(request, 'store/cart.html', context)


@require_POST
def cart_add(request, product_id):
    """Add product to cart via standard form or AJAX with strict stock validation."""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True, category__is_active=True)

    if not product.is_in_stock:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'This product is currently out of stock.'}, status=400)
        messages.error(request, 'This product is currently out of stock.')
        return redirect(product.get_absolute_url())

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    size = request.POST.get('size') or (product.sizes_list[0] if product.sizes_list else 'Free Size')
    colour = request.POST.get('colour') or (product.colours_list[0] if product.colours_list else 'Standard')

    added = cart.add(product=product, quantity=quantity, size=size, colour=colour)
    if not added:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Could not add requested quantity to bag.'}, status=400)
        messages.error(request, 'Could not add requested quantity to bag.')
        return redirect(product.get_absolute_url())

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f"'{product.name}' was added to your bag.",
            'cart_count': len(cart),
            'cart_subtotal': str(cart.get_subtotal())
        })

    messages.success(request, f"Added {product.name} to your shopping bag.")
    return redirect('store:cart')


@require_POST
def cart_update(request):
    """Update item quantity in cart."""
    cart = Cart(request)
    item_key = (request.POST.get('item_key') or '').strip()
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if item_key:
        cart.update_quantity(item_key, quantity)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': len(cart),
            'cart_subtotal': str(cart.get_subtotal()),
            'cart_total': str(cart.get_total())
        })

    return redirect('store:cart')


@require_POST
def cart_remove(request, item_key):
    """Remove single item from cart."""
    cart = Cart(request)
    cart.remove(item_key)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': len(cart),
            'cart_subtotal': str(cart.get_subtotal()),
        })

    messages.info(request, "Item removed from your shopping bag.")
    return redirect('store:cart')


@require_POST
def cart_clear(request):
    """Clear all items from cart (POST-only with CSRF protection)."""
    cart = Cart(request)
    cart.clear()
    messages.info(request, "Your shopping bag is now empty.")
    return redirect('store:cart')


# ==========================================
# WISHLIST VIEWS
# ==========================================

def wishlist_view(request):
    """Display saved customer wishlist items."""
    wishlist = Wishlist(request)
    products = wishlist.get_products()
    context = {
        'products': products,
        'wishlist_count': len(wishlist),
    }
    return render(request, 'store/wishlist.html', context)


@require_POST
def wishlist_toggle(request, product_id):
    """Toggle active product in guest wishlist."""
    product = get_object_or_404(Product, id=product_id, is_active=True, category__is_active=True)
    wishlist = Wishlist(request)
    is_added = wishlist.toggle(product.id)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'added': is_added,
            'wishlist_count': len(wishlist),
            'message': 'Added to your wishlist' if is_added else 'Removed from your wishlist'
        })

    messages.success(request, 'Wishlist updated.')
    safe_next = get_safe_redirect_url(request, request.META.get('HTTP_REFERER'), fallback='store:wishlist')
    return redirect(safe_next)


# ==========================================
# BRAND, POLICIES & INFORMATIONAL PAGES
# ==========================================

def about_us(request):
    """Brand storytelling and philosophy page."""
    return render(request, 'store/about.html')


def policies_view(request):
    """Boutique policies: Shipping, Returns & Exchanges, Privacy & WhatsApp Ordering."""
    return render(request, 'store/policies.html')


@require_http_methods(["GET", "POST"])
def contact_us(request):
    """Contact page with direct WhatsApp link & server-validated inquiry form."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you for reaching out! Our stylists will respond shortly.")
            return redirect('store:contact')
        else:
            messages.error(request, "Please check the form inputs and try again.")
    else:
        form = ContactForm()

    context = {
        'form': form,
    }
    return render(request, 'store/contact.html', context)


@require_POST
def newsletter_signup(request):
    """Subscribe email to newsletter updates with strict server-side email validation."""
    email = (request.POST.get('email') or '').strip().lower()
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    try:
        validate_email(email)
    except ValidationError:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Please enter a valid email address.'}, status=400)
        messages.error(request, 'Please enter a valid email address.')
        safe_next = get_safe_redirect_url(request, request.META.get('HTTP_REFERER'), fallback='store:home')
        return redirect(safe_next)

    NewsletterSubscriber.objects.get_or_create(email=email)
    if is_ajax:
        return JsonResponse({'success': True, 'message': 'Thank you for subscribing to PINACLE FASHIONS VIP updates!'})
    messages.success(request, 'Thank you for subscribing to PINACLE FASHIONS VIP updates!')
    safe_next = get_safe_redirect_url(request, request.META.get('HTTP_REFERER'), fallback='store:home')
    return redirect(safe_next)


def quick_view(request, product_id):
    """AJAX quick view modal loader."""
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images'),
        id=product_id,
        is_active=True,
        category__is_active=True,
    )
    html = render_to_string('components/quick_view_content.html', {
        'product': product,
        'sizes': product.sizes_list,
        'colours': product.colours_list,
    }, request=request)
    return JsonResponse({'success': True, 'html': html})
