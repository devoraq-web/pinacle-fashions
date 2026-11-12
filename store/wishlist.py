from store.models import Product

WISHLIST_SESSION_ID = 'pinacle_wishlist'


class Wishlist:
    def __init__(self, request):
        self.session = request.session
        wishlist = self.session.get(WISHLIST_SESSION_ID)
        if not isinstance(wishlist, list):
            wishlist = self.session[WISHLIST_SESSION_ID] = []
        self.wishlist = wishlist

    def add(self, product_id):
        product_id = int(product_id)
        if product_id not in self.wishlist:
            self.wishlist.append(product_id)
            self.save()

    def remove(self, product_id):
        product_id = int(product_id)
        if product_id in self.wishlist:
            self.wishlist.remove(product_id)
            self.save()

    def toggle(self, product_id):
        """Toggle product in wishlist. Returns True if added, False if removed."""
        product_id = int(product_id)
        if product_id in self.wishlist:
            self.wishlist.remove(product_id)
            self.save()
            return False
        else:
            self.wishlist.append(product_id)
            self.save()
            return True

    def has_product(self, product_id):
        return int(product_id) in self.wishlist

    def get_products(self):
        return (
            Product.objects.filter(id__in=self.wishlist, is_active=True, category__is_active=True)
            .select_related('category')
            .prefetch_related('images')
        )

    def save(self):
        self.session[WISHLIST_SESSION_ID] = self.wishlist
        self.session.modified = True

    def __len__(self):
        if not self.wishlist:
            return 0
        return Product.objects.filter(
            id__in=self.wishlist,
            is_active=True,
            category__is_active=True,
        ).count()
