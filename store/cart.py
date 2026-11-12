import re
from decimal import Decimal
from store.models import Product

CART_SESSION_ID = 'pinacle_cart'


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not isinstance(cart, dict):
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def _sanitize_token(self, val, fallback='Standard'):
        cleaned = re.sub(r'[^A-Za-z0-9_-]+', '-', (val or fallback).strip()).strip('-')
        return cleaned[:32] or fallback

    def _get_item_key(self, product_id, size, colour):
        """Creates a URL-safe unique key per product + size + colour combination."""
        clean_size = self._sanitize_token(size, 'Standard').upper()
        clean_colour = self._sanitize_token(colour, 'Standard').title()
        return f"{product_id}_{clean_size}_{clean_colour}"

    def add(self, product, quantity=1, size='Free Size', colour='Standard', override_quantity=False):
        """Add a product to the cart or update its quantity strictly enforcing DB stock & options."""
        product_id = str(product.id)
        if not product.is_active or not product.category.is_active or not product.is_in_stock:
            return False

        sizes = product.sizes_list
        colours = product.colours_list
        size = size if (not sizes or size in sizes) else sizes[0]
        colour = colour if (not colours or colour in colours) else colours[0]
        item_key = self._get_item_key(product_id, size, colour)

        current_stock = product.stock_quantity
        try:
            quantity = max(1, int(quantity))
        except (ValueError, TypeError):
            quantity = 1

        if item_key not in self.cart:
            self.cart[item_key] = {
                'product_id': product.id,
                'quantity': 0,
                'size': size[:64],
                'colour': colour[:64],
            }

        if override_quantity:
            new_qty = quantity
        else:
            new_qty = int(self.cart[item_key].get('quantity', 0)) + quantity

        if new_qty > current_stock:
            new_qty = current_stock

        if new_qty <= 0:
            self.remove(item_key)
            return False
        else:
            self.cart[item_key]['quantity'] = new_qty
            self.save()
            return True

    def update_quantity(self, item_key, quantity):
        if item_key in self.cart:
            try:
                qty = int(quantity)
            except (ValueError, TypeError):
                qty = 1

            if qty <= 0:
                self.remove(item_key)
                return

            product_id = self.cart[item_key]['product_id']
            try:
                product = Product.objects.get(id=product_id, is_active=True, category__is_active=True)
                if product.stock_quantity <= 0:
                    self.remove(item_key)
                    return
                if qty > product.stock_quantity:
                    qty = product.stock_quantity
            except Product.DoesNotExist:
                self.remove(item_key)
                return

            self.cart[item_key]['quantity'] = qty
            self.save()

    def remove(self, item_key):
        """Remove an item from cart by its composite key."""
        if item_key in self.cart:
            del self.cart[item_key]
            self.save()

    def clear(self):
        """Remove all items from session cart."""
        self.cart = {}
        self.session[CART_SESSION_ID] = {}
        self.session.modified = True

    def save(self):
        self.session[CART_SESSION_ID] = self.cart
        self.session.modified = True

    def __iter__(self):
        """Iterate over the items in the cart using prefetched DB products & live prices."""
        product_ids = [item['product_id'] for item in self.cart.values()]
        if not product_ids:
            return

        products = (
            Product.objects.filter(id__in=product_ids)
            .select_related('category')
            .prefetch_related('images')
        )
        product_map = {p.id: p for p in products}

        cart_copy = self.cart.copy()
        for item_key, item in cart_copy.items():
            product = product_map.get(item['product_id'])
            if not product or not product.is_active or not product.category.is_active or product.stock_quantity <= 0:
                self.remove(item_key)
                continue

            qty = min(int(item['quantity']), product.stock_quantity)
            if qty != item['quantity']:
                self.cart[item_key]['quantity'] = qty
                self.save()

            item_data = item.copy()
            item_data['item_key'] = item_key
            item_data['product'] = product
            item_data['quantity'] = qty
            # Always use authoritative live price from DB
            unit_price = product.price
            item_data['unit_price'] = unit_price
            item_data['total_price'] = unit_price * qty
            yield item_data

    def __len__(self):
        """Count all items in the cart."""
        return sum(int(item.get('quantity', 0)) for item in self.cart.values())

    def get_subtotal(self):
        """Calculate total amount of all items in cart."""
        total = Decimal('0.00')
        for item in self:
            total += item['total_price']
        return total

    def get_total(self):
        """Subtotal + shipping (Complimentary Pan-India Courier)."""
        return self.get_subtotal()
