import logging
import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods

from store.models import Product
from store.cart import Cart
from orders.models import Order, OrderItem
from orders.forms import CheckoutForm
from orders.whatsapp import get_whatsapp_order_url

logger = logging.getLogger(__name__)


def _resolve_valid_variant(product, raw_size, raw_colour):
    """Validates selected size & colour against product catalog options to prevent option tampering."""
    sizes = product.sizes_list
    colours = product.colours_list

    clean_size = (raw_size or '').strip()[:64]
    if sizes:
        size = clean_size if clean_size in sizes else sizes[0]
    else:
        size = clean_size or 'Free Size'

    clean_colour = (raw_colour or '').strip()[:64]
    if colours:
        colour = clean_colour if clean_colour in colours else colours[0]
    else:
        colour = clean_colour or 'Standard'

    return size, colour


@require_http_methods(["GET", "POST"])
def checkout_view(request):
    """
    Handles both Single Product Buy Now and Multi-Product Cart Checkout.
    Validates all prices and stock strictly on the server inside an atomic database transaction,
    enforces duplicate-submission idempotency, saves order records, and builds the WhatsApp link.
    """
    cart = Cart(request)

    is_buy_now = request.GET.get('source') == 'BUY_NOW' or request.POST.get('order_source') == 'BUY_NOW'
    buy_now_product = None
    buy_now_qty = 1
    buy_now_size = 'Free Size'
    buy_now_colour = 'Standard'

    if is_buy_now:
        prod_id = request.GET.get('product_id') or request.POST.get('product_id')
        if not prod_id:
            messages.error(request, "No product selected for Buy Now.")
            return redirect('store:shop')

        buy_now_product = get_object_or_404(
            Product.objects.prefetch_related('images'),
            id=prod_id,
            is_active=True,
            category__is_active=True,
        )
        try:
            buy_now_qty = int(request.GET.get('quantity') or request.POST.get('quantity') or 1)
        except (ValueError, TypeError):
            buy_now_qty = 1

        if buy_now_qty < 1:
            buy_now_qty = 1

        raw_size = request.GET.get('size') or request.POST.get('size')
        raw_colour = request.GET.get('colour') or request.POST.get('colour')
        buy_now_size, buy_now_colour = _resolve_valid_variant(buy_now_product, raw_size, raw_colour)

        if not buy_now_product.is_in_stock or buy_now_product.stock_quantity < buy_now_qty:
            messages.error(request, f"Sorry, only {buy_now_product.stock_quantity} unit(s) available for {buy_now_product.name}.")
            return redirect(buy_now_product.get_absolute_url())

        items_preview = [{
            'product': buy_now_product,
            'name': buy_now_product.name,
            'sku': buy_now_product.sku,
            'image_url': buy_now_product.primary_image.image.url if buy_now_product.primary_image else '',
            'size': buy_now_size,
            'colour': buy_now_colour,
            'quantity': buy_now_qty,
            'unit_price': buy_now_product.price,
            'total_price': buy_now_product.price * buy_now_qty,
        }]
        subtotal = buy_now_product.price * buy_now_qty
        shipping = Decimal('0.00')
        grand_total = subtotal + shipping

    else:
        if len(cart) == 0:
            messages.warning(request, "Your shopping bag is empty.")
            return redirect('store:cart')

        items_preview = []
        for item in cart:
            p = item['product']
            items_preview.append({
                'product': p,
                'name': p.name,
                'sku': p.sku,
                'image_url': p.primary_image.image.url if p.primary_image else '',
                'size': item['size'],
                'colour': item['colour'],
                'quantity': item['quantity'],
                'unit_price': item['unit_price'],
                'total_price': item['total_price'],
            })
        subtotal = cart.get_subtotal()
        shipping = Decimal('0.00')
        grand_total = cart.get_total()

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        submitted_token = (request.POST.get('checkout_token') or '').strip()

        # Check duplicate form submission via idempotency token
        completed_tokens = request.session.get('completed_checkout_orders', {})
        if submitted_token and submitted_token in completed_tokens:
            existing_order_num = completed_tokens[submitted_token]
            existing_order = Order.objects.filter(order_number=existing_order_num).first()
            if existing_order:
                wa_url = existing_order.whatsapp_url or get_whatsapp_order_url(existing_order)
                success_url = reverse('orders:order_success', kwargs={'order_number': existing_order.order_number})
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
                    return JsonResponse({
                        'success': True,
                        'order_number': existing_order.order_number,
                        'whatsapp_url': wa_url,
                        'success_url': success_url
                    })
                return redirect(success_url + "?wa=1")

        if form.is_valid():
            # Verify token matches session active token if token mechanism was active on page load
            active_token = request.session.get('active_checkout_token')
            if submitted_token and active_token and submitted_token != active_token:
                messages.warning(request, "Your checkout session expired or was already submitted. Please review your bag.")
                return redirect('store:cart')

            try:
                with transaction.atomic():
                    address = form.save()
                    computed_subtotal = Decimal('0.00')
                    shipping_fee = Decimal('0.00')

                    order = Order.objects.create(
                        address=address,
                        customer_name=address.full_name,
                        customer_phone=address.mobile_number,
                        subtotal=Decimal('0.00'),
                        shipping_cost=shipping_fee,
                        total_price=Decimal('0.00'),
                        order_source=Order.SOURCE_BUY_NOW if is_buy_now else Order.SOURCE_CART,
                        notes=address.delivery_instructions,
                    )

                    if is_buy_now:
                        locked_product = Product.objects.select_for_update().prefetch_related('images').get(
                            id=buy_now_product.id, is_active=True, category__is_active=True
                        )
                        if locked_product.stock_quantity < buy_now_qty:
                            raise ValueError(
                                f"Insufficient stock for {locked_product.name}. Available: {locked_product.stock_quantity}"
                            )

                        # Always compute price strictly from authoritative DB record
                        unit_price = locked_product.price
                        line_total = unit_price * buy_now_qty
                        computed_subtotal += line_total

                        img_url = locked_product.primary_image.image.url if locked_product.primary_image else ''
                        OrderItem.objects.create(
                            order=order,
                            product=locked_product,
                            product_name=locked_product.name,
                            product_code=locked_product.sku,
                            product_image_url=img_url,
                            selected_size=buy_now_size,
                            selected_colour=buy_now_colour,
                            unit_price=unit_price,
                            quantity=buy_now_qty,
                            total_price=line_total,
                        )

                        locked_product.stock_quantity = max(0, locked_product.stock_quantity - buy_now_qty)
                        locked_product.save(update_fields=['stock_quantity'])

                    else:
                        cart_items = list(cart)
                        if not cart_items:
                            raise ValueError("Your shopping bag is empty.")

                        for item in cart_items:
                            p_id = item['product'].id
                            locked_prod = Product.objects.select_for_update().prefetch_related('images').get(
                                id=p_id, is_active=True, category__is_active=True
                            )
                            item_qty = int(item['quantity'])
                            if item_qty < 1:
                                raise ValueError(f"Invalid quantity for '{locked_prod.name}'.")
                            if locked_prod.stock_quantity < item_qty:
                                raise ValueError(
                                    f"Insufficient stock for '{locked_prod.name}'. Available: {locked_prod.stock_quantity}"
                                )

                            valid_size, valid_colour = _resolve_valid_variant(locked_prod, item['size'], item['colour'])
                            unit_price = locked_prod.price
                            line_total = unit_price * item_qty
                            computed_subtotal += line_total

                            p_img = locked_prod.primary_image.image.url if locked_prod.primary_image else ''
                            OrderItem.objects.create(
                                order=order,
                                product=locked_prod,
                                product_name=locked_prod.name,
                                product_code=locked_prod.sku,
                                product_image_url=p_img,
                                selected_size=valid_size,
                                selected_colour=valid_colour,
                                unit_price=unit_price,
                                quantity=item_qty,
                                total_price=line_total,
                            )

                            locked_prod.stock_quantity = max(0, locked_prod.stock_quantity - item_qty)
                            locked_prod.save(update_fields=['stock_quantity'])

                        cart.clear()

                    # Save authoritative server-calculated totals & WhatsApp link
                    order.subtotal = computed_subtotal
                    order.total_price = computed_subtotal + shipping_fee
                    wa_url = get_whatsapp_order_url(order)
                    order.whatsapp_url = wa_url
                    order.save(update_fields=['subtotal', 'total_price', 'whatsapp_url'])

                # Consume token and store idempotency record in session
                if submitted_token:
                    completed_tokens[submitted_token] = order.order_number
                    # Keep at most recent 10 tokens in session
                    if len(completed_tokens) > 10:
                        oldest_key = next(iter(completed_tokens))
                        del completed_tokens[oldest_key]
                    request.session['completed_checkout_orders'] = completed_tokens
                request.session.pop('active_checkout_token', None)
                request.session.modified = True

                success_url = reverse('orders:order_success', kwargs={'order_number': order.order_number})
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
                    return JsonResponse({
                        'success': True,
                        'order_number': order.order_number,
                        'whatsapp_url': wa_url,
                        'success_url': success_url,
                    })

                return redirect(success_url + "?wa=1")

            except ValueError as e:
                messages.error(request, str(e))
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
                    return JsonResponse({'success': False, 'message': str(e)}, status=400)
            except Exception:
                logger.exception("Unexpected checkout failure")
                err_msg = "Could not process your order right now. Please try again or contact us on WhatsApp."
                messages.error(request, err_msg)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
                    return JsonResponse({'success': False, 'message': err_msg}, status=500)
        else:
            messages.error(request, "Please check the highlighted delivery address details.")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
                first_err = next(iter(form.errors.values()))[0] if form.errors else "Invalid address details."
                return JsonResponse({'success': False, 'message': str(first_err)}, status=400)

    else:
        checkout_token = uuid.uuid4().hex
        request.session['active_checkout_token'] = checkout_token
        request.session.modified = True

        initial_data = {
            'state': 'Kerala',
            'checkout_token': checkout_token,
        }
        if is_buy_now:
            initial_data.update({
                'product_id': buy_now_product.id,
                'quantity': buy_now_qty,
                'size': buy_now_size,
                'colour': buy_now_colour,
                'order_source': 'BUY_NOW',
            })
        else:
            initial_data['order_source'] = 'CART'

        form = CheckoutForm(initial=initial_data)

    context = {
        'form': form,
        'is_buy_now': is_buy_now,
        'buy_now_product': buy_now_product,
        'buy_now_qty': buy_now_qty,
        'buy_now_size': buy_now_size,
        'buy_now_colour': buy_now_colour,
        'items_preview': items_preview,
        'subtotal': subtotal,
        'shipping': shipping,
        'grand_total': grand_total,
    }
    return render(request, 'orders/checkout.html', context)


def order_success_view(request, order_number):
    """
    Shows thank you screen with order summary and direct WhatsApp confirmation button.
    """
    order = get_object_or_404(
        Order.objects.select_related('address').prefetch_related('items'),
        order_number=order_number
    )
    auto_redirect = request.GET.get('wa') == '1'

    context = {
        'order': order,
        'whatsapp_url': order.whatsapp_url or get_whatsapp_order_url(order),
        'auto_redirect': auto_redirect,
    }
    return render(request, 'orders/order_success.html', context)
