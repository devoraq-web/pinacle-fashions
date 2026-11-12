from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from store.models import Category, Product, ProductImage, ContactMessage, NewsletterSubscriber
from orders.models import Order, OrderItem, CustomerAddress
from orders.whatsapp import get_whatsapp_order_url, format_whatsapp_message


class PinacleFashionsSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser(
            username='testadmin',
            email='admin@pinaclefashions.com',
            password='testpassword123'
        )

        # Category
        self.category = Category.objects.create(
            name="Sarees",
            slug="sarees",
            description="Pure silk sarees"
        )

        # In-stock product
        self.product = Product.objects.create(
            category=self.category,
            name="Royal Maroon Kanjeevaram Saree",
            slug="royal-maroon-kanjeevaram-saree",
            sku="PF-SR-TEST",
            description="Exquisite silk saree",
            specifications="Fabric: Pure Silk",
            regular_price=Decimal("4999.00"),
            sale_price=Decimal("3999.00"),
            stock_quantity=10,
            available_sizes="Free Size",
            available_colours="Maroon, Gold",
            is_active=True,
            is_featured=True,
            is_new_arrival=True,
        )

        # Out-of-stock product
        self.oos_product = Product.objects.create(
            category=self.category,
            name="Sold Out Silk Saree",
            slug="sold-out-silk-saree",
            sku="PF-SR-OOS",
            description="Sold out item",
            regular_price=Decimal("2999.00"),
            stock_quantity=0,
            is_active=True
        )

    def test_customer_pages_render(self):
        """Test customer-facing pages load with HTTP 200."""
        routes = [
            reverse('store:home'),
            reverse('store:shop'),
            reverse('store:new_arrivals'),
            reverse('store:categories'),
            reverse('store:category_detail', kwargs={'slug': self.category.slug}),
            reverse('store:product_detail', kwargs={'slug': self.product.slug}),
            reverse('store:cart'),
            reverse('store:wishlist'),
            reverse('store:about'),
            reverse('store:contact'),
        ]
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed with {response.status_code}")

    def test_cart_session_flow(self):
        """Test guest add to cart, update quantity, and remove."""
        response = self.client.post(
            reverse('store:cart_add', kwargs={'product_id': self.product.id}),
            {'quantity': 2, 'size': 'Free Size', 'colour': 'Maroon'}
        )
        self.assertEqual(response.status_code, 302)
        cart_page = self.client.get(reverse('store:cart'))
        self.assertContains(cart_page, self.product.name)

        # Try adding out-of-stock product
        oos_response = self.client.post(
            reverse('store:cart_add', kwargs={'product_id': self.oos_product.id}),
            {'quantity': 1}
        )
        cart_page = self.client.get(reverse('store:cart'))
        self.assertNotContains(cart_page, self.oos_product.name)

    def test_wishlist_toggle(self):
        """Test guest wishlist toggle."""
        response = self.client.post(
            reverse('store:wishlist_toggle', kwargs={'product_id': self.product.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['added'])
        self.assertEqual(data['wishlist_count'], 1)

    def test_whatsapp_checkout_buy_now(self):
        """Test Buy Now checkout creates order and encodes WhatsApp message."""
        checkout_data = {
            'order_source': 'BUY_NOW',
            'product_id': self.product.id,
            'quantity': 1,
            'size': 'Free Size',
            'colour': 'Maroon',
            'full_name': 'Lakshmi Priya',
            'mobile_number': '9847123456',
            'house_name_number': 'Aura Heritage Villa #12',
            'street_location': 'MG Road',
            'city': 'Kochi',
            'district': 'Ernakulam',
            'state': 'Kerala',
            'pin_code': '682001',
            'delivery_instructions': 'Call before delivery',
        }
        initial_stock = self.product.stock_quantity
        response = self.client.post(reverse('orders:checkout'), checkout_data)
        
        self.assertEqual(response.status_code, 302)
        order = Order.objects.filter(customer_name='Lakshmi Priya').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_price, self.product.price)
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock - 1)

        self.assertIn('https://wa.me/919292247815?text=', order.whatsapp_url)
        self.assertIn('PINACLE', order.whatsapp_url)

    def test_cart_checkout_multiple_items(self):
        """Test multi-item cart checkout."""
        # Add 2 items to cart
        self.client.post(
            reverse('store:cart_add', kwargs={'product_id': self.product.id}),
            {'quantity': 2, 'size': 'Free Size', 'colour': 'Maroon'}
        )
        checkout_data = {
            'order_source': 'CART',
            'full_name': 'Ananya Menon',
            'mobile_number': '9123456789',
            'house_name_number': 'House No. 44',
            'street_location': 'Panampilly Nagar',
            'city': 'Kochi',
            'district': 'Ernakulam',
            'state': 'Kerala',
            'pin_code': '682036',
        }
        response = self.client.post(reverse('orders:checkout'), checkout_data)
        self.assertEqual(response.status_code, 302)
        order = Order.objects.filter(customer_name='Ananya Menon').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 2)
        self.assertEqual(order.total_price, self.product.price * 2)

    def test_contact_and_newsletter(self):
        """Test contact form and newsletter subscription."""
        contact_res = self.client.post(reverse('store:contact'), {
            'name': 'Gauri',
            'phone': '9895123456',
            'email': 'gauri@gmail.com',
            'subject': 'Saree Inquiries',
            'message': 'Do you ship to Dubai?'
        })
        self.assertEqual(contact_res.status_code, 302)
        self.assertTrue(ContactMessage.objects.filter(name='Gauri').exists())

        news_res = self.client.post(reverse('store:newsletter_signup'), {'email': 'vip@pinacle.com'})
        self.assertTrue(NewsletterSubscriber.objects.filter(email='vip@pinacle.com').exists())

    def test_admin_dashboard_protection_and_access(self):
        """Test that unauthenticated users are redirected and admin has full access."""
        overview_url = reverse('dashboard:overview')
        
        anon_response = self.client.get(overview_url)
        self.assertEqual(anon_response.status_code, 302)

        self.client.login(username='testadmin', password='testpassword123')
        admin_response = self.client.get(overview_url)
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, "Executive Dashboard Overview")

        routes = [
            reverse('dashboard:product_list'),
            reverse('dashboard:product_create'),
            reverse('dashboard:product_edit', kwargs={'pk': self.product.pk}),
            reverse('dashboard:category_list'),
            reverse('dashboard:inventory'),
            reverse('dashboard:order_list'),
        ]
        for r in routes:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 200, f"Dashboard route {r} failed with {res.status_code}")

    def test_healthz_endpoint(self):
        """Health check endpoint returns 200 OK JSON for Render probes."""
        res = self.client.get(reverse('healthz'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {'status': 'ok'})

    def test_checkout_and_success_communicate_whatsapp_payment_arrangement(self):
        """Checkout and success screens clearly state WhatsApp confirmation and payment arrangement."""
        res = self.client.get(
            f"{reverse('orders:checkout')}?source=BUY_NOW&product_id={self.product.id}&quantity=1"
        )
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '+91 9292247815')
        self.assertContains(res, 'payment arrangement')

    def test_ensure_admin_command_idempotent(self):
        """ensure_admin creates a superuser only once from env vars and never duplicates."""
        import os
        from io import StringIO
        from unittest.mock import patch
        from django.core.management import call_command

        out = StringIO()
        with patch.dict(os.environ, {
            'DJANGO_ADMIN_USERNAME': 'deployadmin',
            'DJANGO_ADMIN_EMAIL': 'deploy@pinaclefashions.com',
            'DJANGO_ADMIN_PASSWORD': 'StrongTestPassword!99',
        }):
            call_command('ensure_admin', stdout=out)
            self.assertTrue(User.objects.filter(username='deployadmin', is_superuser=True).exists())
            call_command('ensure_admin', stdout=out)
            self.assertEqual(User.objects.filter(username='deployadmin').count(), 1)

    def test_cloudinary_storage_accepts_sanitized_image_contentfile(self):
        """Sanitized ContentFile uploads cleanly through MediaCloudinaryStorage."""
        import io
        import os
        from unittest.mock import patch
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from store.validators import sanitize_and_optimize_image

        buf = io.BytesIO()
        Image.new('RGB', (40, 40), color='maroon').save(buf, format='JPEG')
        uploaded = SimpleUploadedFile('sample.jpg', buf.getvalue(), content_type='image/jpeg')
        clean_file = sanitize_and_optimize_image(uploaded)

        with patch.dict(os.environ, {
            'CLOUDINARY_CLOUD_NAME': 'demo',
            'CLOUDINARY_API_KEY': '123456',
            'CLOUDINARY_API_SECRET': 'secret',
        }):
            from cloudinary_storage.storage import MediaCloudinaryStorage
            storage = MediaCloudinaryStorage()
            with patch('cloudinary.uploader.upload', return_value={'public_id': 'media/products/test_img'}) as mock_upload:
                saved_id = storage._save('products/2026/11/test.jpg', clean_file)
                self.assertEqual(saved_id, 'media/products/test_img')
                self.assertTrue(mock_upload.called)

    def test_footer_instagram_and_new_whatsapp_links(self):
        """Footer Instagram icon/link and all WhatsApp links reflect centralized branding."""
        home_res = self.client.get(reverse('store:home'))
        self.assertEqual(home_res.status_code, 200)
        self.assertContains(
            home_res,
            'href="https://www.instagram.com/pinaclefashions/" target="_blank" rel="noopener noreferrer"',
        )
        self.assertContains(home_res, 'href="https://wa.me/919292247815"')
        self.assertContains(home_res, '+91 9292247815')
        self.assertNotContains(home_res, '6238006820')
        self.assertNotContains(home_res, '62380 06820')

        contact_res = self.client.get(reverse('store:contact'))
        self.assertEqual(contact_res.status_code, 200)
        self.assertContains(contact_res, 'https://wa.me/919292247815')
        self.assertContains(contact_res, '+91 9292247815')
        self.assertContains(contact_res, 'https://www.instagram.com/pinaclefashions/')

        detail_res = self.client.get(
            reverse('store:product_detail', kwargs={'slug': self.product.slug})
        )
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'https://wa.me/919292247815?text=')
