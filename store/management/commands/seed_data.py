import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import io

from store.models import Category, Product, ProductImage
from orders.models import Order, OrderItem, CustomerAddress


def create_fashion_image(title, category_name, color_hex="#C5A059", bg_hex="#F5EFE6", width=800, height=1000):
    """Generates an aesthetic editorial fashion card graphic using PIL."""
    img = Image.new('RGB', (width, height), color=bg_hex)
    draw = ImageDraw.Draw(img)

    # Outer ornate gold border
    border_margin = 30
    draw.rectangle(
        [border_margin, border_margin, width - border_margin, height - border_margin],
        outline="#D4AF37",
        width=3
    )
    draw.rectangle(
        [border_margin + 8, border_margin + 8, width - border_margin - 8, height - border_margin - 8],
        outline="#C5A059",
        width=1
    )

    # Decorative inner color panel
    draw.rectangle(
        [60, 60, width - 60, height - 220],
        fill=color_hex
    )

    # Subtle fabric texture stripes
    for y in range(80, height - 240, 24):
        draw.line([(80, y), (width - 80, y)], fill="#FFFFFF", width=1)

    # Center Brand Emblem & Category text
    draw.text((width // 2, 280), "PINACLE FASHIONS", fill="#FFFFFF", anchor="mm")
    draw.text((width // 2, 330), f"★ {category_name.upper()} COUTURE ★", fill="#F4E6C3", anchor="mm")

    # Product Title in lower label
    draw.rectangle([60, height - 200, width - 60, height - 70], fill="#FFFFFF")
    draw.rectangle([60, height - 200, width - 60, height - 70], outline="#E6E0D5", width=1)
    draw.text((width // 2, height - 155), title[:36], fill="#1C1A17", anchor="mm")
    draw.text((width // 2, height - 115), "100% Handcrafted Indian Heritage", fill="#8A8275", anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=92)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Populate demo PINACLE FASHIONS categories, products, admin user, and sample orders (requires --allow-demo-seed)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--allow-demo-seed',
            action='store_true',
            help='Explicitly opt in to seeding sample categories, products, and test orders.',
        )

    def handle(self, *args, **options):
        if not options.get('allow_demo_seed'):
            self.stdout.write(
                self.style.WARNING(
                    "Demo seeding is disabled by default so deleted categories, products, and orders are never "
                    "recreated automatically. Pass --allow-demo-seed only if you intentionally want sample demo data."
                )
            )
            return

        self.stdout.write("Seeding PINACLE FASHIONS store catalog...")

        # 1. Create Superuser / Admin
        admin_user, created = User.objects.get_or_create(username="admin")
        if created:
            admin_user.set_password("pinaclefashions123")
            admin_user.email = "admin@pinaclefashions.com"
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.first_name = "Pinacle"
            admin_user.last_name = "Admin"
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Superuser created: admin / pinaclefashions123"))
        else:
            admin_user.set_password("pinaclefashions123")
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Admin account updated: admin / pinaclefashions123"))

        # 2. Categories
        categories_data = [
            ("Sarees", "Handcrafted traditional Kanjeevarams, Banarasi weaves, and festive silks.", "#7A1C28", 1),
            ("Kurtis", "Contemporary ethnic and everyday elegant designer kurtis.", "#203A43", 2),
            ("Salwar Suits", "Graceful anarkalis, festive shararas, and straight suit sets.", "#4A154B", 3),
            ("Dress Materials", "Unstitched handloom fabrics with artisanal embroidered dupattas.", "#8D5B4C", 4),
            ("Ethnic Wear", "Royal partywear gowns, fusion ethnic ensembles, and lehengas.", "#B8860B", 5),
            ("Accessories", "Traditional temple jewelry, bridal jhumkas, and silk potlis.", "#665C54", 6),
            ("New Arrivals", "Latest seasonal drops and runway-inspired bridal couture.", "#1F2421", 7),
            ("Sale", "Festive discounts and limited-time designer clearance offers.", "#8B0000", 8),
        ]

        cat_objs = {}
        for name, desc, color, order in categories_data:
            cat, c_created = Category.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'is_featured': True,
                    'order': order,
                }
            )
            # Create category cover image if missing
            if not cat.image:
                img_file = create_fashion_image(f"{name} Collection", name, color_hex=color, bg_hex="#F9F6F0", width=600, height=750)
                cat.image.save(f"cat_{cat.slug}.jpg", img_file, save=True)
            cat_objs[name] = cat

        self.stdout.write(self.style.SUCCESS(f"Created {len(cat_objs)} categories."))

        # 3. Products
        products_data = [
            {
                "name": "Royal Maroon Kanjeevaram Pure Silk Saree",
                "sku": "PF-SR-101",
                "category": "Sarees",
                "description": "An opulent bridal masterpiece woven in pure mulberry silk featuring a rich maroon base interlaced with intricate golden zari temple motifs, peacock borders, and a magnificent brocade pallu. Perfect for muhurtham and auspicious celebrations.",
                "specifications": "Fabric: Pure Kanjeevaram Mulberry Silk\nWork: Traditional 2G Gold Zari Brocade\nLength: 6.3 Metres (Includes 80cm Blouse Piece)\nWeave Type: Handloom Jacquard\nWash Care: Dry Clean Only",
                "regular_price": Decimal("4999.00"),
                "sale_price": Decimal("3899.00"),
                "stock": 8,
                "sizes": "Free Size",
                "colours": "Royal Maroon & Gold, Deep Crimson, Wine",
                "color_hex": "#6D1A24",
                "featured": True,
                "new": True,
                "bestseller": True,
            },
            {
                "name": "Peacock Blue Banarasi Brocade Bridal Saree",
                "sku": "PF-SR-102",
                "category": "Sarees",
                "description": "Immerse in the regal grandeur of Varanasi craftsmanship. This exquisite peacock blue katan silk saree dazzles with fine antique silver-gold zari floral jaal, scalloped borders, and an ornate rich pallu.",
                "specifications": "Fabric: Pure Katan Banarasi Silk\nWork: Kadwa Antique Zari Jaal\nLength: 6.3 Metres with Contrast Blouse\nWash Care: Strictly Dry Clean\nOrigin: Varanasi, India",
                "regular_price": Decimal("5499.00"),
                "sale_price": Decimal("4299.00"),
                "stock": 6,
                "sizes": "Free Size",
                "colours": "Peacock Blue, Royal Teal, Royal Navy",
                "color_hex": "#1B3B59",
                "featured": True,
                "new": True,
                "bestseller": True,
            },
            {
                "name": "Champagne Gold Tissue Silk Festive Saree",
                "sku": "PF-SR-103",
                "category": "Sarees",
                "description": "Shimmer like moonlight with this ethereal tissue silk drape. Woven with dual-tone metallic gold threads and trimmed with fine micro-sequins and scalloped borders. Extremely lightweight, fluid, and chic.",
                "specifications": "Fabric: Metallic Tissue Silk\nWork: Thread Embroidery & Sequins\nLength: 5.5 Metres + 0.8 Metres Designer Blouse\nFeel: Ultralight, Semi-Sheer Glamour\nWash Care: Dry Clean Only",
                "regular_price": Decimal("3999.00"),
                "sale_price": Decimal("3199.00"),
                "stock": 12,
                "sizes": "Free Size",
                "colours": "Champagne Gold, Soft Rose Gold, Antique Gold",
                "color_hex": "#A88B4D",
                "featured": True,
                "new": True,
                "bestseller": False,
            },
            {
                "name": "Emerald Green Handloom Chanderi Saree",
                "sku": "PF-SR-104",
                "category": "Sarees",
                "description": "Breathtaking hand-woven Chanderi cotton silk saree adorned with delicate Meenakari floral buttas, a gleaming gold zari border, and comfortable airy texture for festive daytime gatherings.",
                "specifications": "Fabric: Handloom Chanderi Cotton-Silk\nBorder: Zari Border with Meenakari Inlay\nLength: 6.2 Metres with Blouse\nOccasion: Puja, Daytime Weddings, Festivals\nWash Care: Dry Clean Only",
                "regular_price": Decimal("3299.00"),
                "sale_price": None,
                "stock": 2,  # Low stock test case
                "sizes": "Free Size",
                "colours": "Emerald Green, Bottle Green, Mint",
                "color_hex": "#1E4D2B",
                "featured": False,
                "new": False,
                "bestseller": True,
            },
            {
                "name": "Dusty Rose Floral Embroidered Anarkali Suit",
                "sku": "PF-SS-201",
                "category": "Salwar Suits",
                "description": "A fairytale pastel silhouette crafted from premium flowy georgette. Embellished with resham threadwork, micro pearls, and subtle gold sequins on the yoke, paired with matching pants and a sheer dupatta.",
                "specifications": "Top Fabric: Heavy Viscose Georgette (With Inner Lining)\nBottom: Santoon Cigarette Pants\nDupatta: Organza with Scallop Zari Border\nStitch: Semi-Stitched (Fits up to 44 Bust)\nWash Care: Dry Clean Only",
                "regular_price": Decimal("3899.00"),
                "sale_price": Decimal("2999.00"),
                "stock": 9,
                "sizes": "S, M, L, XL, XXL",
                "colours": "Dusty Rose, Blush Pink, Lavender",
                "color_hex": "#8B5A63",
                "featured": True,
                "new": True,
                "bestseller": True,
            },
            {
                "name": "Royal Navy Blue Velvet Embroidered Kurti Set",
                "sku": "PF-KT-301",
                "category": "Kurtis",
                "description": "Opulence redefined in deep navy plush micro-velvet. Features intricate tilla and zari work along the mandarin collar and cuffs, paired with straight velvet pants and a regal banarasi zari dupatta.",
                "specifications": "Fabric: Premium 9000 Micro Velvet\nWork: Golden Tilla & Zari Hand Embroidery\nSleeve: Full Length with Embroidered Cuffs\nSet Includes: Kurti + Trousers + Dupatta\nWash Care: Dry Clean Only",
                "regular_price": Decimal("2799.00"),
                "sale_price": Decimal("2199.00"),
                "stock": 14,
                "sizes": "M, L, XL, XXL",
                "colours": "Royal Navy Blue, Wine, Bottle Green",
                "color_hex": "#182635",
                "featured": True,
                "new": True,
                "bestseller": True,
            },
            {
                "name": "Mustard Yellow Festive Georgette Kurti",
                "sku": "PF-KT-302",
                "category": "Kurtis",
                "description": "Bright, cheerful, and festive! Pure georgette straight-cut kurti with handcrafted gotta patti work on the neckline, delicate potli buttons, and quarter sleeves. Ideal for Haldi and festive celebrations.",
                "specifications": "Fabric: Pure Viscose Georgette with Crepe Lining\nWork: Traditional Gotta Patti & Mirror Finish\nLength: 46 Inches Calf Length\nWash Care: Gentle Hand Wash or Dry Clean",
                "regular_price": Decimal("1899.00"),
                "sale_price": Decimal("1499.00"),
                "stock": 15,
                "sizes": "S, M, L, XL, XXL",
                "colours": "Mustard Yellow, Marigold Orange, Ochre",
                "color_hex": "#9E7B1A",
                "featured": False,
                "new": False,
                "bestseller": True,
            },
            {
                "name": "Wine Red Unstitched Chanderi Dress Material",
                "sku": "PF-DM-401",
                "category": "Dress Materials",
                "description": "Customize your dream ethnic attire with this three-piece unstitched Chanderi silk suite. Comes with an embroidered kurta piece, comfortable cotton-silk bottom fabric, and a printed digital floral dupatta.",
                "specifications": "Top Cut: 2.5 Metres Pure Chanderi Silk\nBottom Cut: 2.5 Metres Cotton-Silk Blend\nDupatta: 2.25 Metres Digital Printed Organza\nWash Care: Dry Clean Recommended",
                "regular_price": Decimal("2199.00"),
                "sale_price": Decimal("1799.00"),
                "stock": 10,
                "sizes": "Unstitched (2.5m Fabric)",
                "colours": "Wine Red, Burgundy, Plum",
                "color_hex": "#581825",
                "featured": False,
                "new": True,
                "bestseller": False,
            },
            {
                "name": "Ivory & Gold Chikankari Handcrafted Kurta",
                "sku": "PF-KT-303",
                "category": "Kurtis",
                "description": "Authentic Lucknowi hand-embroidery featuring bakhiya and phanda stitches over soothing modal cotton fabric, accented with delicate golden mukaish dots. The epitome of subtle luxury.",
                "specifications": "Fabric: Breathable Modal Cotton\nCraft: Handcrafted Lucknowi Chikankari & Mukaish\nFit: Straight Comfort Fit\nWash Care: Gentle Hand Wash with Mild Detergent",
                "regular_price": Decimal("2499.00"),
                "sale_price": None,
                "stock": 7,
                "sizes": "S, M, L, XL",
                "colours": "Ivory White, Pearl Cream",
                "color_hex": "#4A4742",
                "featured": True,
                "new": True,
                "bestseller": False,
            },
            {
                "name": "Traditional Temple Antique Gold Jhumka Set",
                "sku": "PF-AC-501",
                "category": "Accessories",
                "description": "Handcrafted south-Indian antique temple jewelry jhumkas featuring goddess Lakshmi motifs, ruby red kemp stones, and cascading matte gold pearl drops. Complements both Kanjeevarams and bridal suits.",
                "specifications": "Material: High-Grade Brass Alloy\nPlating: 24K Antique Matte Gold Finish\nStone Type: Kemp Red & Green Hydro Pearls\nWeight: 35 Grams (Pair)\nCare: Keep Away from Perfume & Moisture",
                "regular_price": Decimal("1299.00"),
                "sale_price": Decimal("999.00"),
                "stock": 20,
                "sizes": "Standard Size",
                "colours": "Antique Gold with Kemp Red",
                "color_hex": "#7A5E24",
                "featured": False,
                "new": False,
                "bestseller": True,
            },
            {
                "name": "Crimson Red Banarasi Raw Silk Lehanga Skirt",
                "sku": "PF-EW-601",
                "category": "Ethnic Wear",
                "description": "A flared wedding lehenga skirt tailored from pure raw silk with woven zari arches, paired with an unstitched blouse piece. Outstanding royal presence.",
                "specifications": "Fabric: Pure Raw Silk with Cancan Lining\nFlare: 4.2 Metres Full Circle\nWaist: Semi-Stitched up to 42 Inches\nWash Care: Dry Clean Only",
                "regular_price": Decimal("6999.00"),
                "sale_price": Decimal("5499.00"),
                "stock": 0,  # OUT OF STOCK test case!
                "sizes": "Semi-Stitched (Free Size)",
                "colours": "Crimson Red, Scarlet",
                "color_hex": "#8A1822",
                "featured": True,
                "new": False,
                "bestseller": False,
            },
            {
                "name": "Blush Pink Silk Organza Partywear Saree",
                "sku": "PF-SR-105",
                "category": "Sarees",
                "description": "Featherlight silk organza drape in delicate blush pink with hand-cutwork embroidered borders and pastel floral motifs throughout. Modern, youthful, and ravishing.",
                "specifications": "Fabric: Pure Silk Organza\nWork: Cutwork Embroidery with Resham & Pearl Details\nLength: 5.5 Metres with Satin Silk Blouse Piece\nWash Care: Dry Clean Only",
                "regular_price": Decimal("4199.00"),
                "sale_price": Decimal("3499.00"),
                "stock": 5,
                "sizes": "Free Size",
                "colours": "Blush Pink, Powder Blue, Mint",
                "color_hex": "#7E4957",
                "featured": True,
                "new": True,
                "bestseller": True,
            },
        ]

        for p_data in products_data:
            cat = cat_objs.get(p_data["category"])
            prod, p_created = Product.objects.get_or_create(
                sku=p_data["sku"],
                defaults={
                    "category": cat,
                    "name": p_data["name"],
                    "description": p_data["description"],
                    "specifications": p_data["specifications"],
                    "regular_price": p_data["regular_price"],
                    "sale_price": p_data["sale_price"],
                    "stock_quantity": p_data["stock"],
                    "available_sizes": p_data["sizes"],
                    "available_colours": p_data["colours"],
                    "is_active": True,
                    "is_featured": p_data["featured"],
                    "is_new_arrival": p_data["new"],
                    "is_best_seller": p_data["bestseller"],
                }
            )

            # Generate multiple images per product (primary front view + detail view)
            if prod.images.count() == 0:
                # 1. Primary view image
                img1 = create_fashion_image(prod.name, cat.name, color_hex=p_data["color_hex"], bg_hex="#FAF7F2", width=800, height=1000)
                pi1 = ProductImage(product=prod, is_primary=True, order=0)
                pi1.image.save(f"{prod.sku}_primary.jpg", img1, save=True)

                # 2. Detail weave image
                img2 = create_fashion_image(f"{prod.name} (Zari Detail)", cat.name, color_hex=p_data["color_hex"], bg_hex="#F0ECE4", width=800, height=1000)
                pi2 = ProductImage(product=prod, is_primary=False, order=1)
                pi2.image.save(f"{prod.sku}_detail.jpg", img2, save=True)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(products_data)} luxury products with multiple images."))

        # 4. Sample Test Orders
        if Order.objects.count() == 0:
            addr1 = CustomerAddress.objects.create(
                full_name="Pooja Lakshmi",
                mobile_number="9847123456",
                house_name_number="Anjali Villa, No. 14",
                street_location="MG Road, Near Central Temple",
                city="Kochi",
                district="Ernakulam",
                state="Kerala",
                pin_code="682016",
                delivery_instructions="Call on WhatsApp before delivery."
            )
            ord1 = Order.objects.create(
                address=addr1,
                customer_name=addr1.full_name,
                customer_phone=addr1.mobile_number,
                subtotal=Decimal("3899.00"),
                shipping_cost=Decimal("0.00"),
                total_price=Decimal("3899.00"),
                status=Order.STATUS_CONFIRMED,
                order_source=Order.SOURCE_BUY_NOW,
                notes="Confirmed via WhatsApp chat."
            )
            p1 = Product.objects.get(sku="PF-SR-101")
            OrderItem.objects.create(
                order=ord1,
                product=p1,
                product_name=p1.name,
                product_code=p1.sku,
                product_image_url=p1.primary_image.image.url if p1.primary_image else "",
                selected_size="Free Size",
                selected_colour="Royal Maroon & Gold",
                unit_price=p1.price,
                quantity=1,
                total_price=p1.price
            )

            addr2 = CustomerAddress.objects.create(
                full_name="Revathy Nair",
                mobile_number="9447654321",
                house_name_number="Rosewood Apt 3B",
                street_location="Kowdiar Avenue",
                city="Thiruvananthapuram",
                district="Thiruvananthapuram",
                state="Kerala",
                pin_code="695003",
                delivery_instructions="Leave with security guard if unavailable."
            )
            ord2 = Order.objects.create(
                address=addr2,
                customer_name=addr2.full_name,
                customer_phone=addr2.mobile_number,
                subtotal=Decimal("5198.00"),
                shipping_cost=Decimal("0.00"),
                total_price=Decimal("5198.00"),
                status=Order.STATUS_PENDING,
                order_source=Order.SOURCE_CART,
                notes="Waiting for customer WhatsApp message."
            )
            p2 = Product.objects.get(sku="PF-KT-301")
            OrderItem.objects.create(
                order=ord2,
                product=p2,
                product_name=p2.name,
                product_code=p2.sku,
                product_image_url=p2.primary_image.image.url if p2.primary_image else "",
                selected_size="M",
                selected_colour="Royal Navy Blue",
                unit_price=p2.price,
                quantity=1,
                total_price=p2.price
            )
            p3 = Product.objects.get(sku="PF-SS-201")
            OrderItem.objects.create(
                order=ord2,
                product=p3,
                product_name=p3.name,
                product_code=p3.sku,
                product_image_url=p3.primary_image.image.url if p3.primary_image else "",
                selected_size="L",
                selected_colour="Dusty Rose",
                unit_price=p3.price,
                quantity=1,
                total_price=p3.price
            )
            self.stdout.write(self.style.SUCCESS("Created sample test orders."))

        self.stdout.write(self.style.SUCCESS("PINACLE FASHIONS seed data completed successfully!"))

