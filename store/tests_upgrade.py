import io
import shutil
import tempfile
import uuid
from decimal import Decimal
from PIL import Image

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from orders.models import Order
from store.models import AdminAuditLog, Category, HeroBanner, Product
from store.validators import sanitize_and_optimize_image, sanitize_csv_cell, validate_image_file


def _make_test_jpeg_bytes(color=(198, 164, 106), size=(120, 160)):
    buf = io.BytesIO()
    img = Image.new('RGB', size, color=color)
    img.save(buf, format='JPEG', quality=85)
    return buf.getvalue()


class UpgradeStorefrontAndSecurityTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_tmp_dir = tempfile.mkdtemp(prefix='pinacle_test_media_')
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_tmp_dir)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._media_tmp_dir, ignore_errors=True)
        super().tearDownClass()
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.category = Category.objects.create(
            name='Kanjeevaram Sarees',
            slug='sarees',
            is_featured=True,
            order=1,
        )
        self.product = Product.objects.create(
            name='Royal Zari Kanjeevaram Silk Saree',
            slug='royal-zari-kanjeevaram',
            sku='PF-TEST-101',
            category=self.category,
            description='Handloom mulberry pure silk weave with champagne zari.',
            regular_price=Decimal('12000.00'),
            sale_price=Decimal('9500.00'),
            stock_quantity=5,
            available_sizes='Free Size, Custom Blouse',
            available_colours='Maroon, Ivory',
            is_featured=True,
            is_new_arrival=True,
            is_active=True,
        )
        self.staff_user = User.objects.create_user(
            username='boutique_admin',
            password='StrongPassword!2026',
            is_staff=True,
            is_superuser=True,
        )
        self.regular_user = User.objects.create_user(
            username='regular_customer',
            password='UserPassword!2026',
            is_staff=False,
        )

    def tearDown(self):
        cache.clear()

    def test_storefront_pages_render_and_include_security_headers(self):
        routes = [
            reverse('store:home'),
            reverse('store:shop'),
            reverse('store:shop') + '?sale=1',
            reverse('store:new_arrivals'),
            reverse('store:categories'),
            reverse('store:category_detail', kwargs={'slug': self.category.slug}),
            reverse('store:product_detail', kwargs={'slug': self.product.slug}),
            reverse('store:policies'),
            reverse('store:about'),
            reverse('store:contact'),
            reverse('store:wishlist'),
            reverse('store:cart'),
        ]
        for url in routes:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Expected 200 for {url}")
            self.assertIn('Content-Security-Policy', resp.headers)
            self.assertEqual(resp.headers.get('X-Content-Type-Options'), 'nosniff')
            self.assertIn('Referrer-Policy', resp.headers)
            self.assertIn('Permissions-Policy', resp.headers)

        home_html = self.client.get(reverse('store:home')).content.decode('utf-8')
        self.assertIn('Every Thread Tells a Story', home_html)
        self.assertIn('pf-product-grid', home_html)
        self.assertIn('pf-category-grid', home_html)
        self.assertIn('pfReviewTrack', home_html)

    def test_herobanner_renders_on_homepage(self):
        img_file = SimpleUploadedFile('banner.jpg', _make_test_jpeg_bytes(), content_type='image/jpeg')
        banner = HeroBanner.objects.create(
            eyebrow='Bridal Atelier 2026',
            title='Custom Zari Bridal Edit',
            subtitle='Curated exclusively for wedding celebrations.',
            image=img_file,
            is_active=True,
            order=1,
        )
        try:
            resp = self.client.get(reverse('store:home'))
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, 'Custom Zari Bridal Edit')
        finally:
            if banner.image:
                banner.image.delete(save=False)

    def test_cart_clear_requires_post_and_wishlist_open_redirect_blocked(self):
        get_clear = self.client.get(reverse('store:cart_clear'))
        self.assertEqual(get_clear.status_code, 405)

        post_clear = self.client.post(reverse('store:cart_clear'))
        self.assertEqual(post_clear.status_code, 302)

        evil_ref_resp = self.client.post(
            reverse('store:wishlist_toggle', kwargs={'product_id': self.product.id}),
            HTTP_REFERER='https://evil.example.com/phish',
        )
        self.assertEqual(evil_ref_resp.status_code, 302)
        self.assertEqual(evil_ref_resp['Location'], reverse('store:wishlist'))

    def test_buy_now_server_price_authority_variant_validation_and_idempotency(self):
        checkout_url = reverse('orders:checkout')
        get_resp = self.client.get(checkout_url, {
            'source': 'BUY_NOW',
            'product_id': self.product.id,
            'quantity': 2,
            'size': 'TAMPERED_SIZE',
            'colour': 'TAMPERED_COLOUR',
        })
        self.assertEqual(get_resp.status_code, 200)
        token = get_resp.context['form'].initial['checkout_token']
        self.assertTrue(token)

        payload = {
            'product_id': self.product.id,
            'quantity': 2,
            'size': 'TAMPERED_SIZE',
            'colour': 'TAMPERED_COLOUR',
            'order_source': 'BUY_NOW',
            'checkout_token': token,
            'full_name': 'Lakshmi Nair',
            'mobile_number': '+91 98765 43210',
            'house_name_number': 'Rose Villa 14',
            'street_location': 'MG Road, Ravipuram',
            'city': 'Kochi',
            'district': 'Ernakulam',
            'state': 'Kerala',
            'pin_code': '682016',
            'delivery_instructions': 'Call on arrival',
        }
        post_resp = self.client.post(checkout_url, payload)
        self.assertEqual(post_resp.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.first()
        # Server recomputed price: 9500 * 2 = 19000
        self.assertEqual(order.total_price, Decimal('19000.00'))
        self.assertIn('wa.me/919292247815', order.whatsapp_url)
        item = order.items.first()
        # Tampered variants clamped back to product catalog defaults
        self.assertEqual(item.selected_size, 'Free Size')
        self.assertEqual(item.selected_colour, 'Maroon')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)

        # Replay exact same token: must not create duplicate order or double-decrement stock
        replay_resp = self.client.post(checkout_url, payload)
        self.assertEqual(replay_resp.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)

    def test_checkout_rejects_invalid_phone_and_pin(self):
        checkout_url = reverse('orders:checkout')
        get_resp = self.client.get(checkout_url, {
            'source': 'BUY_NOW',
            'product_id': self.product.id,
            'quantity': 1,
        })
        token = get_resp.context['form'].initial['checkout_token']

        bad_payload = {
            'product_id': self.product.id,
            'quantity': 1,
            'order_source': 'BUY_NOW',
            'checkout_token': token,
            'full_name': 'Test Buyer',
            'mobile_number': '12345',
            'house_name_number': 'House 1',
            'street_location': 'Main Street',
            'city': 'Kochi',
            'district': 'Ernakulam',
            'state': 'Kerala',
            'pin_code': '000012',
        }
        resp = self.client.post(checkout_url, bad_payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
        self.assertTrue(resp.context['form'].errors)

    def test_admin_auth_throttle_open_redirect_logout_and_audit_log(self):
        # Unauthenticated dashboard redirect + no-store header
        overview_resp = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(overview_resp.status_code, 302)
        self.assertIn('no-store', overview_resp.headers.get('Cache-Control', ''))

        # Non-staff user denied dashboard access
        self.client.force_login(self.regular_user)
        non_staff_resp = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(non_staff_resp.status_code, 302)
        self.client.logout()

        # Login brute force throttle (5 failed attempts -> 6th returns 429)
        login_url = reverse('dashboard:login')
        for _ in range(5):
            r = self.client.post(login_url, {'username': 'boutique_admin', 'password': 'wrong-password'})
            self.assertEqual(r.status_code, 200)

        locked_resp = self.client.post(login_url, {'username': 'boutique_admin', 'password': 'StrongPassword!2026'})
        self.assertEqual(locked_resp.status_code, 429)
        self.assertTrue(AdminAuditLog.objects.filter(action='LOGIN_BLOCKED').exists())

        # Clear cache and test safe ?next= open redirect protection
        cache.clear()
        ok_login = self.client.post(
            login_url + '?next=https://evil.example.com/steal',
            {'username': 'boutique_admin', 'password': 'StrongPassword!2026'},
        )
        self.assertEqual(ok_login.status_code, 302)
        self.assertEqual(ok_login['Location'], reverse('dashboard:overview'))

        # Audit log view accessible for authenticated staff
        audit_resp = self.client.get(reverse('dashboard:audit_logs'))
        self.assertEqual(audit_resp.status_code, 200)

        # Logout enforces POST
        get_logout = self.client.get(reverse('dashboard:logout'))
        self.assertEqual(get_logout.status_code, 405)
        post_logout = self.client.post(reverse('dashboard:logout'))
        self.assertEqual(post_logout.status_code, 302)

    def test_image_validator_and_csv_formula_neutralization(self):
        fake_img = SimpleUploadedFile('evil.jpg', b'<html><script>alert(1)</script></html>', content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            validate_image_file(fake_img)

        svg_file = SimpleUploadedFile('vector.svg', b'<svg></svg>', content_type='image/svg+xml')
        with self.assertRaises(ValidationError):
            validate_image_file(svg_file)

        valid_img = SimpleUploadedFile('photo.jpg', _make_test_jpeg_bytes(), content_type='image/jpeg')
        sanitized = sanitize_and_optimize_image(valid_img)
        self.assertTrue(sanitized.name.endswith('.jpg'))
        self.assertNotEqual(sanitized.name, 'photo.jpg')
        # Verify sanitized name is random 32-char UUID hex + .jpg
        uuid.UUID(sanitized.name.rsplit('.', 1)[0])

        self.assertEqual(sanitize_csv_cell('=CMD|"/c calc"!A0'), "'=CMD|\"/c calc\"!A0")
        self.assertEqual(sanitize_csv_cell('+1234'), "'+1234")
        self.assertEqual(sanitize_csv_cell('-SUM(A1:A2)'), "'-SUM(A1:A2)")
        self.assertEqual(sanitize_csv_cell('@evil'), "'@evil")
        self.assertEqual(sanitize_csv_cell('Lakshmi Nair'), 'Lakshmi Nair')

    def test_dynamic_category_visibility_empty_state_and_shop_now_cta(self):
        empty_cat = Category.objects.create(
            name='Bridal Lehengas',
            slug='lehengas',
            is_active=True,
            is_featured=True,
            order=2,
        )
        hidden_cat = Category.objects.create(
            name='Secret Archive',
            slug='secret-archive',
            is_active=False,
            is_featured=True,
            order=3,
        )
        hidden_prod = Product.objects.create(
            name='Hidden Archive Silk',
            slug='hidden-archive-silk',
            sku='PF-HID-901',
            category=hidden_cat,
            description='Must not be public while category is inactive.',
            regular_price=Decimal('5000.00'),
            stock_quantity=4,
            is_active=True,
        )

        home_resp = self.client.get(reverse('store:home'))
        self.assertEqual(home_resp.status_code, 200)
        home_html = home_resp.content.decode('utf-8')
        # Category cards stay visible even at 0 products with Shop Now CTA
        self.assertIn('Bridal Lehengas', home_html)
        self.assertIn('Shop Now', home_html)
        # Deactivated category and its product never appear publicly
        self.assertNotIn('Secret Archive', home_html)
        self.assertNotIn('Hidden Archive Silk', home_html)

        empty_cat_resp = self.client.get(reverse('store:category_detail', kwargs={'slug': empty_cat.slug}))
        self.assertEqual(empty_cat_resp.status_code, 200)
        self.assertContains(empty_cat_resp, 'No products available in this collection yet.')

        self.assertEqual(self.client.get(reverse('store:category_detail', kwargs={'slug': hidden_cat.slug})).status_code, 404)
        self.assertEqual(self.client.get(reverse('store:product_detail', kwargs={'slug': hidden_prod.slug})).status_code, 404)

    def test_no_fake_fallback_product_sections_when_empty(self):
        # Update only existing product to neither new-arrival nor best-seller
        self.product.is_new_arrival = False
        self.product.is_best_seller = False
        self.product.save(update_fields=['is_new_arrival', 'is_best_seller'])

        # New Arrivals page shows empty collection state (no fallback to unrelated items)
        new_resp = self.client.get(reverse('store:new_arrivals'))
        self.assertEqual(new_resp.status_code, 200)
        self.assertContains(new_resp, 'No products available in this collection yet.')
        self.assertNotContains(new_resp, self.product.name)

        # Homepage hides empty Best Sellers and New Arrivals sections rather than faking fallback cards
        home_html = self.client.get(reverse('store:home')).content.decode('utf-8')
        self.assertIn('Latest Products', home_html)
        self.assertNotIn('Signature Best Sellers', home_html)
        self.assertNotIn('New Arrivals</h2>', home_html)

        # Deactivating all products renders zero product cards on homepage while preserving category cards
        self.product.is_active = False
        self.product.save(update_fields=['is_active'])
        empty_home_html = self.client.get(reverse('store:home')).content.decode('utf-8')
        self.assertNotIn('Latest Products', empty_home_html)
        self.assertNotIn('pf-product-card', empty_home_html)
        self.assertIn('pf-category-card', empty_home_html)

    def test_admin_product_and_category_management_updates_store_immediately(self):
        self.client.force_login(self.staff_user)

        img_file = SimpleUploadedFile('kurti.jpg', _make_test_jpeg_bytes(), content_type='image/jpeg')
        create_resp = self.client.post(
            reverse('dashboard:product_create'),
            {
                'name': 'Ivory Chikankari Silk Kurti',
                'sku': 'PF-KT-999',
                'category': self.category.id,
                'description': 'Hand-embroidered Lucknowi chikankari.',
                'specifications': 'Fabric: Pure Chanderi',
                'regular_price': '4200.00',
                'sale_price': '3600.00',
                'stock_quantity': 6,
                'available_sizes': 'S, M, L',
                'available_colours': 'Ivory',
                'is_active': 'on',
                'is_new_arrival': 'on',
                'images': [img_file],
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        created_prod = Product.objects.get(sku='PF-KT-999')
        try:
            self.assertEqual(created_prod.images.count(), 1)
            shop_html = self.client.get(reverse('store:shop')).content.decode('utf-8')
            self.assertIn('Ivory Chikankari Silk Kurti', shop_html)

            # Toggle inactive via dashboard endpoint
            toggle_resp = self.client.post(reverse('dashboard:product_toggle_active', kwargs={'pk': created_prod.id}))
            self.assertEqual(toggle_resp.status_code, 302)
            created_prod.refresh_from_db()
            self.assertFalse(created_prod.is_active)
            self.assertEqual(
                self.client.get(reverse('store:product_detail', kwargs={'slug': created_prod.slug})).status_code,
                404,
            )

            # Delete product via dashboard endpoint
            del_resp = self.client.post(reverse('dashboard:product_delete', kwargs={'pk': created_prod.id}))
            self.assertEqual(del_resp.status_code, 302)
            self.assertFalse(Product.objects.filter(id=created_prod.id).exists())
        finally:
            for img in list(created_prod.images.all()):
                if img.image:
                    img.image.delete(save=False)

        # Toggle category inactive + verify audit log and separate guest store view
        cat_toggle = self.client.post(reverse('dashboard:category_toggle_active', kwargs={'pk': self.category.id}))
        self.assertEqual(cat_toggle.status_code, 302)
        self.category.refresh_from_db()
        self.assertFalse(self.category.is_active)
        self.assertTrue(AdminAuditLog.objects.filter(action='CATEGORY_DEACTIVATED').exists())
        guest_client = Client()
        cats_resp = guest_client.get(reverse('store:categories'))
        self.assertEqual(cats_resp.status_code, 200)
        self.assertEqual(list(cats_resp.context['categories']), [])
        self.assertNotIn('Kanjeevaram Sarees', cats_resp.content.decode('utf-8'))

    def test_guest_session_cart_red_badge_and_out_of_stock_protection(self):
        home_html = self.client.get(reverse('store:home')).content.decode('utf-8')
        self.assertIn('pf-badge-count--cart', home_html)
        self.assertIn('id="header-cart-count"', home_html)

        # Guest add via AJAX updates session cart count
        add_resp = self.client.post(
            reverse('store:cart_add', kwargs={'product_id': self.product.id}),
            {'quantity': 2, 'size': 'Free Size', 'colour': 'Maroon'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(add_resp.status_code, 200)
        self.assertEqual(add_resp.json()['cart_count'], 2)

        cart_html = self.client.get(reverse('store:cart')).content.decode('utf-8')
        self.assertIn(self.product.name, cart_html)

        # Find composite key in session & update quantity dynamically
        item_key = next(iter(self.client.session['pinacle_cart'].keys()))
        upd_resp = self.client.post(
            reverse('store:cart_update'),
            {'item_key': item_key, 'quantity': 3},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(upd_resp.status_code, 200)
        self.assertEqual(upd_resp.json()['cart_count'], 3)

        # Out-of-stock product displays label and cannot be added to bag
        self.product.stock_quantity = 0
        self.product.save(update_fields=['stock_quantity'])
        self.assertContains(self.client.get(reverse('store:shop')), 'Out of Stock')
        oos_add = self.client.post(
            reverse('store:cart_add', kwargs={'product_id': self.product.id}),
            {'quantity': 1},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(oos_add.status_code, 400)
        # Visiting cart prunes out-of-stock / inactive items
        self.assertNotIn(self.product.name, self.client.get(reverse('store:cart')).content.decode('utf-8'))

    def test_discreet_admin_login_links_and_full_dashboard_protection(self):
        login_url = reverse('dashboard:login')
        overview_url = reverse('dashboard:overview')

        # 1. Footer shows subtle Admin Login link cleanly; main header navbar does NOT show Admin Login
        home_html = self.client.get(reverse('store:home')).content.decode('utf-8')
        header_html = home_html.split('</header>', 1)[0]
        footer_html = home_html.split('<footer', 1)[1]
        self.assertNotIn('Admin Login', header_html)
        self.assertNotIn(login_url, header_html)
        self.assertIn(f'href="{login_url}"', footer_html)
        self.assertIn('Admin Login', footer_html)

        # 2. About Us page contains subtle Admin Login link to named dashboard:login route
        about_html = self.client.get(reverse('store:about')).content.decode('utf-8')
        self.assertIn(f'href="{login_url}"', about_html)
        self.assertIn('pf-about-admin-link', about_html)

        # 3. Protected dashboard URLs redirect anonymous guests & non-staff users to login
        protected_urls = [
            overview_url,
            reverse('dashboard:product_list'),
            reverse('dashboard:category_list'),
            reverse('dashboard:banner_list'),
            reverse('dashboard:inventory'),
            reverse('dashboard:order_list'),
            reverse('dashboard:audit_logs'),
        ]
        for url in protected_urls:
            anon_resp = self.client.get(url)
            self.assertEqual(anon_resp.status_code, 302)
            self.assertTrue(anon_resp['Location'].startswith(login_url))

        # Logged-in non-staff user is redirected back to login and denied access
        self.client.force_login(self.regular_user)
        for url in protected_urls:
            cust_resp = self.client.get(url)
            self.assertEqual(cust_resp.status_code, 302)
            self.assertTrue(cust_resp['Location'].startswith(login_url))
        # Non-staff user visiting login page does NOT enter dashboard
        self.assertEqual(self.client.get(login_url).status_code, 200)
        self.client.logout()

        # 4. Valid staff login redirects to dashboard overview; already-logged-in staff visiting login redirects straight to dashboard
        post_login = self.client.post(login_url, {
            'username': 'boutique_admin',
            'password': 'StrongPassword!2026',
        })
        self.assertEqual(post_login.status_code, 302)
        self.assertEqual(post_login['Location'], overview_url)

        already_logged_in = self.client.get(login_url)
        self.assertEqual(already_logged_in.status_code, 302)
        self.assertEqual(already_logged_in['Location'], overview_url)

        # 5. No public admin registration endpoint exists
        self.assertEqual(self.client.get('/dashboard/register/').status_code, 404)
        self.assertEqual(self.client.get('/register/').status_code, 404)

    def test_seed_data_disabled_by_default_and_empty_store_stays_clean(self):
        # Clear catalog and orders completely
        Order.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        AdminAuditLog.objects.all().delete()

        # Invoking seed_data without --allow-demo-seed must NOT recreate any business records
        out = io.StringIO()
        call_command('seed_data', stdout=out)
        self.assertIn('disabled by default', out.getvalue())
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)

        # Public homepage and categories page stay clean without fallback categories or 404 links
        home_html = self.client.get(reverse('store:home')).content.decode('utf-8')
        self.assertNotIn('pf-category-card', home_html)
        self.assertNotIn('pf-product-card', home_html)
        self.assertNotIn('/category/sarees/', home_html)
        self.assertNotIn('/category/kurtis/', home_html)

        cats_html = self.client.get(reverse('store:categories')).content.decode('utf-8')
        self.assertIn('No collections available yet.', cats_html)

        # Logged-in admin dashboard shows exact zero stats across login/refresh/logout/login
        self.client.force_login(self.staff_user)
        dash_resp = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertEqual(dash_resp.context['total_categories'], 0)
        self.assertEqual(dash_resp.context['total_products'], 0)
        self.assertEqual(dash_resp.context['total_orders'], 0)
        self.assertEqual(dash_resp.context['pending_orders'], 0)
        self.assertEqual(dash_resp.context['total_revenue'], 0)
        self.assertContains(dash_resp, '₹0')
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(Product.objects.count(), 0)

    def test_category_form_validation_error_display_and_value_preservation(self):
        self.client.force_login(self.staff_user)
        create_url = reverse('dashboard:category_create')

        # 1. Invalid category image upload preserves entered text/order and shows field & alert errors
        bad_img = SimpleUploadedFile('not_image.txt', b'plain text content', content_type='text/plain')
        bad_img_resp = self.client.post(create_url, {
            'name': 'Heritage Organza',
            'description': 'Fine sheer silk drapes preserved on error.',
            'image': bad_img,
            'order': '4',
            'is_active': 'on',
        })
        self.assertEqual(bad_img_resp.status_code, 200)
        self.assertFalse(Category.objects.filter(name='Heritage Organza').exists())
        bad_img_html = bad_img_resp.content.decode('utf-8')
        self.assertIn('alert-danger', bad_img_html)
        self.assertIn('invalid-feedback', bad_img_html)
        self.assertIn('Upload a valid image', bad_img_html)
        self.assertIn('value="Heritage Organza"', bad_img_html)
        self.assertIn('Fine sheer silk drapes preserved on error.', bad_img_html)
        self.assertIn('value="4"', bad_img_html)

        # 2. Missing required category name displays field error and preserves description/order
        missing_name_resp = self.client.post(create_url, {
            'name': '',
            'description': 'Kept description on missing name.',
            'order': '7',
        })
        self.assertEqual(missing_name_resp.status_code, 200)
        missing_html = missing_name_resp.content.decode('utf-8')
        self.assertIn('This field is required.', missing_html)
        self.assertIn('Kept description on missing name.', missing_html)
        self.assertIn('value="7"', missing_html)

        # 3. Valid category creation succeeds and cleans up uploaded file cleanly
        good_img = SimpleUploadedFile('organza.jpg', _make_test_jpeg_bytes(), content_type='image/jpeg')
        ok_resp = self.client.post(create_url, {
            'name': 'Heritage Organza',
            'description': 'Hand-embroidered organza collection.',
            'image': good_img,
            'order': '4',
            'is_active': 'on',
            'is_featured': 'on',
        })
        self.assertEqual(ok_resp.status_code, 302)
        created_cat = Category.objects.get(name='Heritage Organza')
        try:
            self.assertTrue(bool(created_cat.image))

            # 4. Invalid edit submission preserves entered edit values and renders error visibly
            bad_edit_resp = self.client.post(reverse('dashboard:category_edit', kwargs={'pk': created_cat.pk}), {
                'name': '',
                'description': 'Edited description kept on error.',
                'order': '9',
            })
            self.assertEqual(bad_edit_resp.status_code, 200)
            edit_html = bad_edit_resp.content.decode('utf-8')
            self.assertIn('This field is required.', edit_html)
            self.assertIn('Edited description kept on error.', edit_html)
            self.assertIn('value="9"', edit_html)
        finally:
            if created_cat.image:
                created_cat.image.delete(save=False)

    def test_product_form_validation_error_display_and_value_preservation(self):
        self.client.force_login(self.staff_user)
        create_url = reverse('dashboard:product_create')
        expected_sale_msg = 'Sale price must be strictly lower than regular MRP price.'

        base_payload = {
            'name': 'Emerald Banarasi Brocade Saree',
            'sku': 'PF-BN-701',
            'category': self.category.id,
            'description': 'Pure silk brocade weave with zari pallu.',
            'specifications': 'Fabric: Pure Silk\nWash: Dry Clean',
            'regular_price': '5000.00',
            'stock_quantity': '6',
            'available_sizes': 'Free Size',
            'available_colours': 'Emerald, Gold',
            'is_active': 'on',
        }

        # 1. Sale price equal to regular price displays exact message beside field & preserves values
        eq_resp = self.client.post(create_url, {**base_payload, 'sale_price': '5000.00'})
        self.assertEqual(eq_resp.status_code, 200)
        self.assertFalse(Product.objects.filter(sku='PF-BN-701').exists())
        eq_html = eq_resp.content.decode('utf-8')
        self.assertIn(expected_sale_msg, eq_html)
        self.assertIn('invalid-feedback', eq_html)
        self.assertIn('value="Emerald Banarasi Brocade Saree"', eq_html)
        self.assertIn('value="PF-BN-701"', eq_html)
        self.assertIn('value="5000.00"', eq_html)

        # 2. Sale price greater than regular price + invalid image displays BOTH errors & preserves values
        bad_img = SimpleUploadedFile('evil_script.jpg', b'<html>alert</html>', content_type='image/jpeg')
        gt_resp = self.client.post(create_url, {
            **base_payload,
            'sale_price': '6200.00',
            'images': [bad_img],
        })
        self.assertEqual(gt_resp.status_code, 200)
        self.assertFalse(Product.objects.filter(sku='PF-BN-701').exists())
        gt_html = gt_resp.content.decode('utf-8')
        self.assertIn(expected_sale_msg, gt_html)
        self.assertIn('evil_script.jpg', gt_html)
        self.assertIn('value="6200.00"', gt_html)
        self.assertIn('Pure silk brocade weave with zari pallu.', gt_html)

        # 3. Valid product creation succeeds cleanly
        good_img = SimpleUploadedFile('emerald.jpg', _make_test_jpeg_bytes(), content_type='image/jpeg')
        ok_resp = self.client.post(create_url, {
            **base_payload,
            'sale_price': '4200.00',
            'images': [good_img],
        })
        self.assertEqual(ok_resp.status_code, 302)
        created_prod = Product.objects.get(sku='PF-BN-701')
        try:
            self.assertEqual(created_prod.images.count(), 1)

            # 4. Product edit validation error displays field error cleanly while preserving inputs
            bad_edit = self.client.post(reverse('dashboard:product_edit', kwargs={'pk': created_prod.pk}), {
                **base_payload,
                'name': 'Updated Emerald Saree Draft',
                'regular_price': '4500.00',
                'sale_price': '4500.00',
            })
            self.assertEqual(bad_edit.status_code, 200)
            edit_html = bad_edit.content.decode('utf-8')
            self.assertIn(expected_sale_msg, edit_html)
            self.assertIn('value="Updated Emerald Saree Draft"', edit_html)
        finally:
            for img in list(created_prod.images.all()):
                if img.image:
                    img.image.delete(save=False)


