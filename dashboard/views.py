import csv
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.views.decorators.http import require_POST, require_http_methods

from store.models import Product, Category, ProductImage, ContactMessage, HeroBanner, AdminAuditLog
from store.validators import (
    sanitize_and_optimize_image,
    sanitize_csv_cell,
    get_safe_redirect_url,
    get_client_ip,
)
from orders.models import Order
from dashboard.forms import ProductForm, CategoryForm, HeroBannerForm, OrderStatusForm

logger = logging.getLogger(__name__)

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900  # 15 minutes


def is_staff_check(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _log_admin_action(request, action, target_type='', target_repr='', details='', username_override=None):
    """Records sensitive admin actions into persistent AdminAuditLog."""
    try:
        uname = username_override or (request.user.username if request.user.is_authenticated else 'anonymous')
        AdminAuditLog.objects.create(
            username=uname[:150],
            action=action[:100],
            target_type=target_type[:64],
            target_repr=target_repr[:255],
            details=details[:1000],
            ip_address=get_client_ip(request),
        )
    except Exception:
        logger.warning("Failed writing admin audit log entry cleanly.")


@require_http_methods(["GET", "POST"])
def admin_login_view(request):
    """Secure branded login page for PINACLE FASHIONS Admin with brute-force rate limiting."""
    if request.user.is_authenticated and is_staff_check(request.user):
        return redirect('dashboard:overview')

    client_ip = get_client_ip(request)
    ip_cache_key = f"pf_login_fail_{client_ip}"
    attempts = cache.get(ip_cache_key, 0)

    if request.method == 'POST':
        if attempts >= LOGIN_MAX_ATTEMPTS:
            messages.error(
                request,
                "Too many failed login attempts detected. Access temporarily locked for 15 minutes."
            )
            _log_admin_action(
                request,
                action='LOGIN_BLOCKED',
                target_type='Auth',
                target_repr=request.POST.get('username', '')[:64],
                details=f"Rate limit exceeded ({attempts} failures).",
                username_override=request.POST.get('username', '')[:64] or 'anonymous'
            )
            return render(request, 'dashboard/login.html', {'form': AuthenticationForm()}, status=429)

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if is_staff_check(user):
                cache.delete(ip_cache_key)
                login(request, user)
                _log_admin_action(request, action='LOGIN_SUCCESS', target_type='Auth', target_repr=user.username)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                next_url = get_safe_redirect_url(
                    request,
                    request.GET.get('next') or request.POST.get('next'),
                    fallback='dashboard:overview'
                )
                return redirect(next_url)
            else:
                attempts += 1
                cache.set(ip_cache_key, attempts, LOGIN_LOCKOUT_SECONDS)
                _log_admin_action(
                    request,
                    action='LOGIN_UNAUTHORIZED',
                    target_type='Auth',
                    target_repr=user.username,
                    details='Non-staff account attempted admin login.',
                    username_override=user.username
                )
                messages.error(request, "Access restricted. Only authorized administrators may enter.")
        else:
            attempts += 1
            cache.set(ip_cache_key, attempts, LOGIN_LOCKOUT_SECONDS)
            _log_admin_action(
                request,
                action='LOGIN_FAILED',
                target_type='Auth',
                target_repr=request.POST.get('username', '')[:64],
                details=f"Invalid credentials attempt #{attempts}.",
                username_override=request.POST.get('username', '')[:64] or 'anonymous'
            )
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, 'dashboard/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


@require_POST
def admin_logout_view(request):
    """Logout securely via CSRF-protected POST request."""
    if request.user.is_authenticated:
        _log_admin_action(request, action='LOGOUT', target_type='Auth', target_repr=request.user.username)
    logout(request)
    messages.info(request, "You have been logged out securely.")
    return redirect('dashboard:login')


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
def dashboard_overview(request):
    """Executive overview with KPI cards, revenue metrics, stock alerts, and recent orders."""
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    total_categories = Category.objects.count()

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status=Order.STATUS_PENDING).count()
    confirmed_orders = Order.objects.filter(status=Order.STATUS_CONFIRMED).count()

    out_of_stock_count = Product.objects.filter(stock_quantity=0).count()
    low_stock_products = Product.objects.filter(stock_quantity__gt=0, stock_quantity__lte=3).select_related('category')[:5]

    revenue_agg = Order.objects.exclude(status=Order.STATUS_CANCELLED).aggregate(total=Sum('total_price'))
    total_revenue = revenue_agg['total'] or 0

    recent_orders = Order.objects.select_related('address').prefetch_related('items').order_by('-created_at')[:8]
    unread_messages = ContactMessage.objects.filter(is_read=False).count()

    context = {
        'total_products': total_products,
        'active_products': active_products,
        'total_categories': total_categories,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'out_of_stock_count': out_of_stock_count,
        'low_stock_products': low_stock_products,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'unread_messages': unread_messages,
    }
    return render(request, 'dashboard/overview.html', context)


# ==========================================
# PRODUCT MANAGEMENT
# ==========================================

@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
def product_list(request):
    """List, filter, and search catalog products."""
    products = Product.objects.select_related('category').prefetch_related('images').all()

    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(sku__icontains=q) |
            Q(category__name__icontains=q)
        )

    category_id = request.GET.get('category')
    if category_id and category_id.isdigit():
        products = products.filter(category_id=int(category_id))

    stock_status = request.GET.get('stock')
    if stock_status == 'out':
        products = products.filter(stock_quantity=0)
    elif stock_status == 'low':
        products = products.filter(stock_quantity__gt=0, stock_quantity__lte=3)
    elif stock_status == 'in':
        products = products.filter(stock_quantity__gt=3)

    paginator = Paginator(products, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    categories = Category.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'categories': categories,
        'search_query': q,
        'selected_category': category_id,
        'stock_status': stock_status,
    }
    return render(request, 'dashboard/product_list.html', context)


def _validate_product_images(files):
    """Validates and sanitizes uploaded product gallery images before persistence."""
    sanitized_files = []
    image_errors = []
    for f in files:
        try:
            sanitized_files.append(sanitize_and_optimize_image(f))
        except ValidationError as err:
            image_errors.append(f"{f.name}: {'; '.join(err.messages)}")
    return sanitized_files, image_errors


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_http_methods(["GET", "POST"])
def product_create(request):
    """Add new product with strict multi-image binary validation & EXIF sanitization."""
    image_errors = []
    if request.method == 'POST':
        form = ProductForm(request.POST)
        is_form_valid = form.is_valid()
        sanitized_files, image_errors = _validate_product_images(request.FILES.getlist('images'))

        if is_form_valid and not image_errors:
            product = form.save()
            for idx, clean_file in enumerate(sanitized_files):
                p_img = ProductImage(
                    product=product,
                    is_primary=(idx == 0),
                    order=idx
                )
                p_img.image.save(clean_file.name, clean_file, save=True)

            _log_admin_action(
                request,
                action='PRODUCT_CREATED',
                target_type='Product',
                target_repr=f"{product.name} ({product.sku})",
                details=f"Price: ₹{product.price}, Stock: {product.stock_quantity}, Images: {len(sanitized_files)}"
            )
            messages.success(request, f"Product '{product.name}' created successfully with {len(sanitized_files)} image(s)!")
            return redirect('dashboard:product_list')
        else:
            for e in image_errors:
                messages.error(request, e)
            if not is_form_valid:
                messages.error(request, "Please resolve the errors highlighted below.")
    else:
        form = ProductForm()

    context = {
        'form': form,
        'image_errors': image_errors,
        'title': 'Add New Fashion Product',
        'is_edit': False,
    }
    return render(request, 'dashboard/product_form.html', context)


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_http_methods(["GET", "POST"])
def product_edit(request, pk):
    """Edit existing product and manage sanitized gallery images."""
    product = get_object_or_404(Product, pk=pk)
    image_errors = []

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        is_form_valid = form.is_valid()
        sanitized_files, image_errors = _validate_product_images(request.FILES.getlist('images'))

        if is_form_valid and not image_errors:
            primary_img_id = request.POST.get('primary_image_id')
            if primary_img_id and primary_img_id.isdigit():
                ProductImage.objects.filter(product=product).update(is_primary=False)
                ProductImage.objects.filter(product=product, id=int(primary_img_id)).update(is_primary=True)

            product = form.save()
            existing_count = product.images.count()
            for idx, clean_file in enumerate(sanitized_files):
                p_img = ProductImage(
                    product=product,
                    is_primary=(existing_count == 0 and idx == 0),
                    order=existing_count + idx
                )
                p_img.image.save(clean_file.name, clean_file, save=True)

            _log_admin_action(
                request,
                action='PRODUCT_UPDATED',
                target_type='Product',
                target_repr=f"{product.name} ({product.sku})",
                details=f"Price: ₹{product.price}, Stock: {product.stock_quantity}, New Images: {len(sanitized_files)}"
            )
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect('dashboard:product_list')
        else:
            for e in image_errors:
                messages.error(request, e)
            if not is_form_valid:
                messages.error(request, "Please correct the errors in the form.")
    else:
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'image_errors': image_errors,
        'product': product,
        'images': product.images.all(),
        'title': f"Edit: {product.name}",
        'is_edit': True,
    }
    return render(request, 'dashboard/product_form.html', context)


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_POST
def product_delete(request, pk):
    """Delete product."""
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    sku = product.sku
    product.delete()
    _log_admin_action(request, action='PRODUCT_DELETED', target_type='Product', target_repr=f"{name} ({sku})")
    messages.success(request, f"Product '{name}' was deleted.")
    return redirect('dashboard:product_list')


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_POST
def product_toggle_active(request, pk):
    """Toggle product active/inactive visibility in the storefront."""
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=['is_active'])
    state_label = 'Activated' if product.is_active else 'Deactivated'
    _log_admin_action(
        request,
        action=f"PRODUCT_{state_label.upper()}",
        target_type='Product',
        target_repr=f"{product.name} ({product.sku})",
    )
    messages.success(request, f"Product '{product.name}' is now {'Active' if product.is_active else 'Inactive'}.")
    return redirect('dashboard:product_list')


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_POST
def product_image_delete(request, image_id):
    """Delete a single product gallery image."""
    image = get_object_or_404(ProductImage, id=image_id)
    product_id = image.product.id
    prod_sku = image.product.sku
    image.delete()
    _log_admin_action(request, action='PRODUCT_IMAGE_DELETED', target_type='ProductImage', target_repr=prod_sku)
    messages.info(request, "Image deleted.")
    return redirect('dashboard:product_edit', pk=product_id)


# ==========================================
# CATEGORY MANAGEMENT
# ==========================================

@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
def category_list(request):
    """List all categories with product counts."""
    categories = Category.objects.annotate(prod_count=Count('products')).order_by('order', 'name')
    return render(request, 'dashboard/category_list.html', {'categories': categories})


def _validate_and_save_category(request, form):
    """Validates and sanitizes category image upload before saving the category."""
    uploaded_img = request.FILES.get('image')
    clean_file = None
    if uploaded_img:
        try:
            clean_file = sanitize_and_optimize_image(uploaded_img, max_dim=1200)
        except ValidationError as err:
            form.add_error('image', err)
            messages.error(request, "Please resolve the category form errors highlighted below.")
            return None

    category = form.save(commit=False)
    if clean_file is not None:
        category.image.save(clean_file.name, clean_file, save=False)
    category.save()
    return category


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_http_methods(["GET", "POST"])
def category_create(request):
    """Create a new product category with sanitized cover image."""
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = _validate_and_save_category(request, form)
            if category is not None:
                _log_admin_action(request, action='CATEGORY_CREATED', target_type='Category', target_repr=category.name)
                messages.success(request, f"Category '{category.name}' created.")
                return redirect('dashboard:category_list')
        else:
            messages.error(request, "Please resolve the category form errors highlighted below.")
    else:
        form = CategoryForm()

    return render(request, 'dashboard/category_form.html', {'form': form, 'title': 'Add New Category'})


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_http_methods(["GET", "POST"])
def category_edit(request, pk):
    """Edit existing category."""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            updated = _validate_and_save_category(request, form)
            if updated is not None:
                _log_admin_action(request, action='CATEGORY_UPDATED', target_type='Category', target_repr=updated.name)
                messages.success(request, f"Category '{updated.name}' updated.")
                return redirect('dashboard:category_list')
        else:
            messages.error(request, "Please resolve the category form errors highlighted below.")
    else:
        form = CategoryForm(instance=category)

    return render(request, 'dashboard/category_form.html', {
        'form': form,
        'category': category,
        'title': f"Edit: {category.name}",
    })


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_POST
def category_delete(request, pk):
    """Delete a category."""
    category = get_object_or_404(Category, pk=pk)
    name = category.name
    category.delete()
    _log_admin_action(request, action='CATEGORY_DELETED', target_type='Category', target_repr=name)
    messages.success(request, f"Category '{name}' deleted.")
    return redirect('dashboard:category_list')


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_POST
def category_toggle_active(request, pk):
    """Toggle category active/inactive visibility in the customer store."""
    category = get_object_or_404(Category, pk=pk)
    category.is_active = not category.is_active
    category.save(update_fields=['is_active'])
    state_label = 'Activated' if category.is_active else 'Deactivated'
    _log_admin_action(
        request,
        action=f"CATEGORY_{state_label.upper()}",
        target_type='Category',
        target_repr=category.name,
    )
    messages.success(request, f"Category '{category.name}' is now {'Active' if category.is_active else 'Inactive'}.")
    return redirect('dashboard:category_list')


# ==========================================
# HERO BANNERS MANAGEMENT
# ==========================================

@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
def banner_list(request):
    """Manage homepage editorial hero banners."""
    banners = HeroBanner.objects.all().order_by('order', '-created_at')
    return render(request, 'dashboard/banner_list.html', {'banners': banners})


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_http_methods(["GET", "POST"])
def banner_create(request):
    """Create a homepage hero banner."""
    if request.method == 'POST':
        form = HeroBannerForm(request.POST, request.FILES)
        if form.is_valid():
            banner = form.save(commit=False)
            uploaded_img = request.FILES.get('image')
            if uploaded_img:
                clean_file = sanitize_and_optimize_image(uploaded_img, max_dim=1920)
                banner.image.save(clean_file.name, clean_file, save=False)
            banner.save()
            _log_admin_action(request, action='BANNER_CREATED', target_type='HeroBanner', target_repr=banner.title)
            messages.success(request, f"Hero banner '{banner.title}' created.")
            return redirect('dashboard:banner_list')
    else:
        form = HeroBannerForm()

    return render(request, 'dashboard/banner_form.html', {'form': form, 'title': 'Add Homepage Hero Banner'})


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_http_methods(["GET", "POST"])
def banner_edit(request, pk):
    """Edit homepage hero banner."""
    banner = get_object_or_404(HeroBanner, pk=pk)
    if request.method == 'POST':
        form = HeroBannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            banner = form.save(commit=False)
            uploaded_img = request.FILES.get('image')
            if uploaded_img:
                clean_file = sanitize_and_optimize_image(uploaded_img, max_dim=1920)
                banner.image.save(clean_file.name, clean_file, save=False)
            banner.save()
            _log_admin_action(request, action='BANNER_UPDATED', target_type='HeroBanner', target_repr=banner.title)
            messages.success(request, f"Hero banner '{banner.title}' updated.")
            return redirect('dashboard:banner_list')
    else:
        form = HeroBannerForm(instance=banner)

    return render(request, 'dashboard/banner_form.html', {
        'form': form,
        'banner': banner,
        'title': f"Edit Banner: {banner.title}",
    })


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_POST
def banner_delete(request, pk):
    """Delete homepage hero banner."""
    banner = get_object_or_404(HeroBanner, pk=pk)
    title = banner.title
    banner.delete()
    _log_admin_action(request, action='BANNER_DELETED', target_type='HeroBanner', target_repr=title)
    messages.success(request, f"Hero banner '{title}' deleted.")
    return redirect('dashboard:banner_list')


# ==========================================
# INVENTORY MANAGEMENT
# ==========================================

@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
def inventory_view(request):
    """Dedicated inventory control dashboard."""
    products = Product.objects.select_related('category').prefetch_related('images').order_by('stock_quantity', 'name')

    stock_filter = request.GET.get('filter')
    if stock_filter == 'out':
        products = products.filter(stock_quantity=0)
    elif stock_filter == 'low':
        products = products.filter(stock_quantity__gt=0, stock_quantity__lte=3)
    elif stock_filter == 'in':
        products = products.filter(stock_quantity__gt=3)

    paginator = Paginator(products, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/inventory.html', {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'stock_filter': stock_filter,
    })


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_POST
def inventory_quick_update(request, product_id):
    """Update stock quantity in-place from inventory table safely."""
    product = get_object_or_404(Product, id=product_id)
    try:
        old_stock = product.stock_quantity
        new_stock = int(request.POST.get('stock_quantity', product.stock_quantity))
        if new_stock < 0:
            raise ValueError("Stock cannot be negative")
        product.stock_quantity = new_stock
        product.save(update_fields=['stock_quantity'])
        _log_admin_action(
            request,
            action='STOCK_UPDATED',
            target_type='Product',
            target_repr=f"{product.name} ({product.sku})",
            details=f"Stock changed {old_stock} -> {new_stock}"
        )
        messages.success(request, f"Updated stock for '{product.name}' to {product.stock_quantity}.")
    except (ValueError, TypeError):
        messages.error(request, "Invalid stock value.")

    safe_back = get_safe_redirect_url(request, request.META.get('HTTP_REFERER'), fallback='dashboard:inventory')
    return redirect(safe_back)


# ==========================================
# ORDER MANAGEMENT
# ==========================================

@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
def order_list(request):
    """List customer orders with status filters, date filters, and search."""
    orders = Order.objects.select_related('address').prefetch_related('items').all()

    q = request.GET.get('q', '').strip()
    if q:
        orders = orders.filter(
            Q(order_number__icontains=q) |
            Q(customer_name__icontains=q) |
            Q(customer_phone__icontains=q) |
            Q(address__city__icontains=q) |
            Q(address__pin_code__icontains=q)
        )

    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    date_filter = request.GET.get('date')
    if date_filter:
        orders = orders.filter(created_at__date=date_filter)

    paginator = Paginator(orders, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/order_list.html', {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'status_choices': Order.STATUS_CHOICES,
        'selected_status': status,
        'search_query': q,
        'date_filter': date_filter or '',
    })


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_http_methods(["GET", "POST"])
def order_detail(request, order_number):
    """View full customer order, items, delivery address, and update status."""
    order = get_object_or_404(
        Order.objects.select_related('address').prefetch_related('items'),
        order_number=order_number
    )

    if request.method == 'POST':
        old_status = order.status
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            _log_admin_action(
                request,
                action='ORDER_STATUS_UPDATED',
                target_type='Order',
                target_repr=f"#{order.order_number}",
                details=f"Status: {old_status} -> {order.status}"
            )
            messages.success(request, f"Order #{order.order_number} status updated to {order.get_status_display()}.")
            return redirect('dashboard:order_detail', order_number=order.order_number)
    else:
        form = OrderStatusForm(instance=order)

    clean_phone = ''.join(c for c in order.customer_phone if c.isdigit())
    if len(clean_phone) == 10:
        clean_phone = '91' + clean_phone
    customer_wa_link = f"https://wa.me/{clean_phone}?text=Hello%20{order.customer_name},%20regarding%20your%20PINACLE%20FASHIONS%20order%20#{order.order_number}..."

    return render(request, 'dashboard/order_detail.html', {
        'order': order,
        'items': order.items.all(),
        'address': order.address,
        'form': form,
        'customer_wa_link': customer_wa_link,
    })


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
def order_invoice(request, order_number):
    """Printable invoice and courier packing slip."""
    order = get_object_or_404(
        Order.objects.select_related('address').prefetch_related('items'),
        order_number=order_number
    )
    return render(request, 'dashboard/order_invoice.html', {
        'order': order,
        'items': order.items.all(),
        'address': order.address,
    })


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
def order_export_csv(request):
    """Export orders to CSV safely with CSV formula-injection neutralization."""
    _log_admin_action(request, action='ORDER_CSV_EXPORTED', target_type='Order', target_repr='All Orders CSV')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pinacle_fashions_orders.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Order Number', 'Date', 'Customer Name', 'Phone',
        'House / Building', 'Street / Location', 'City', 'District', 'State', 'PIN Code',
        'Items Ordered', 'Subtotal', 'Shipping', 'Total Price', 'Status', 'Notes'
    ])

    orders = Order.objects.select_related('address').prefetch_related('items').order_by('-created_at')
    for order in orders:
        items_summary = "; ".join([
            f"{item.product_name} ({item.selected_size}/{item.selected_colour}) x{item.quantity}"
            for item in order.items.all()
        ])
        addr = order.address
        writer.writerow([
            sanitize_csv_cell(order.order_number),
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            sanitize_csv_cell(order.customer_name),
            sanitize_csv_cell(order.customer_phone),
            sanitize_csv_cell(addr.house_name_number),
            sanitize_csv_cell(addr.street_location),
            sanitize_csv_cell(addr.city),
            sanitize_csv_cell(addr.district),
            sanitize_csv_cell(addr.state),
            sanitize_csv_cell(addr.pin_code),
            sanitize_csv_cell(items_summary),
            str(order.subtotal),
            str(order.shipping_cost),
            str(order.total_price),
            sanitize_csv_cell(order.get_status_display()),
            sanitize_csv_cell(order.notes),
        ])

    return response


@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
@require_POST
def order_quick_status(request, order_number, status_code):
    """Quick single-click status transition."""
    order = get_object_or_404(Order, order_number=order_number)
    if status_code in dict(Order.STATUS_CHOICES):
        old_status = order.status
        order.status = status_code
        order.save(update_fields=['status'])
        _log_admin_action(
            request,
            action='ORDER_STATUS_UPDATED',
            target_type='Order',
            target_repr=f"#{order.order_number}",
            details=f"Quick update: {old_status} -> {status_code}"
        )
        messages.success(request, f"Order #{order.order_number} marked as {order.get_status_display()}.")

    safe_back = get_safe_redirect_url(request, request.META.get('HTTP_REFERER'), fallback='dashboard:order_list')
    return redirect(safe_back)


# ==========================================
# SECURITY AUDIT LOGS
# ==========================================

@login_required(login_url='dashboard:login')
@user_passes_test(is_staff_check, login_url='dashboard:login')
def audit_log_list(request):
    """View security & administrative audit trail."""
    logs = AdminAuditLog.objects.all()
    action_filter = request.GET.get('action', '').strip()
    if action_filter:
        logs = logs.filter(action=action_filter)

    paginator = Paginator(logs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/audit_logs.html', {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'action_filter': action_filter,
    })
