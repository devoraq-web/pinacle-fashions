# PINACLE FASHIONS – Premium E-Commerce Website

An exquisite, modern, fully functional luxury fashion e-commerce platform built for the clothing brand **PINACLE FASHIONS** using Python Django, MySQL / SQLite, Bootstrap 5, and vanilla JavaScript.

Designed with an aesthetic inspired by high-end Indian ethnic couture, featuring cream & beige palettes, champagne gold accents, charcoal serif typography, and an automated **WhatsApp Order System** without third-party payment gateways.

---

## 🌟 Brand Identity

- **Brand Name**: PINACLE FASHIONS
- **Instagram**: [@pinaclefashions](https://www.instagram.com/pinaclefashions/)
- **WhatsApp Order & Support Line**: `+919292247815`
- **Brand Aesthetic**: Regal Indian handloom, Kanjeevarams, Banarasi brocades, designer kurtis, and festive bridal couture.
- **Logo**: Features the official circular gold-crested PINACLE FASHIONS insignia with the regal silhouette drape.

---

## 🚀 Key Features

### 1. Customer Shopping Experience (No Login Required)
- **Guest Browsing & Purchasing**: Seamless shopping experience without mandatory registration.
- **Dynamic Catalog Navigation**:
  - **Homepage**: Hero banner, Shop by Categories, New Arrivals, Best Sellers, Featured Collections, Special Offers, Instagram Showcase (`@pinaclefashions`), Customer Testimonials, and VIP Club Newsletter.
  - **Shop All**: Live keyword search, category filters, min/max price sliders, in-stock filter, and multi-option sorting (Newest, Price: Low to High, Price: High to Low, Name: A–Z).
  - **Category Archives**: Dedicated landing pages for Sarees, Kurtis, Salwar Suits, Dress Materials, Ethnic Wear, Accessories, and New Arrivals.
  - **Product Details Showcase**: Multi-image interactive thumbnail gallery, image zoom, size selector, colour picker, stock availability badges, line-by-line specifications table (Fabric, Work, Length, Wash Care), related collections, and instant **Buy Now** / **Add to Bag** triggers.
  - **Shopping Bag**: Full guest session cart with AJAX quantity increment/decrement, subtotal recalculation, item removal, and multi-product WhatsApp checkout.
  - **Wishlist**: Real-time heart toggle with persistent session storage.
  - **About Us & Story**: Brand heritage showcasing the signature PINACLE FASHIONS customer love note.
  - **Contact Us**: Direct WhatsApp chat launcher, inquiry form, studio location, and store hours.

### 2. WhatsApp Order System (Zero Gateway Friction)
- **No Third-Party Payment Gateways**: Eliminates drop-offs, payment failures, and transaction fees.
- **Two Flexible Entry Points**:
  1. **Direct Buy Now**: Immediate one-click checkout from any product card or detail page.
  2. **Shopping Bag Checkout**: Multi-product checkout combining all cart items.
- **5-Step Checkout Architecture**:
  1. **Checkout Overview**: Instant form displaying item quantities, sizes, and colors.
  2. **Product Snapshots**: Previews product thumbnails, SKU codes, unit prices, and subtotal.
  3. **Customer Address Collection**: Full Name, WhatsApp Number, House/Villa No., Street/Area, City, District, State, PIN Code, and Delivery Notes.
  4. **Order Summary**: Subtotal, Free Shipping, and Grand Total.
  5. **Confirm on WhatsApp**: Creates an immutable order record with price snapshots in the Django database, decrements inventory stock, and redirects to:
     `https://wa.me/919292247815?text=ENCODED_ORDER_MESSAGE`
- **Formatted WhatsApp Order Message Example**:
  ```text
  🌟 *NEW ORDER - PINACLE FASHIONS* 🌟
  Order Ref: *#PF-2611-A1B2C3*

  Hello PINACLE FASHIONS!
  I would like to place an order.

  👤 *CUSTOMER DETAILS:*
  • Name: Ananya Menon
  • Phone: 9847123456
  • House / Building: Anjali Villa, No. 14
  • Street / Area: MG Road
  • City: Kochi
  • District: Ernakulam
  • State: Kerala
  • PIN Code: 682016

  🛍️ *ORDER DETAILS:*
  *1. Royal Maroon Kanjeevaram Pure Silk Saree*
     • Code: PF-SR-101
     • Size: Free Size | Colour: Royal Maroon & Gold
     • Qty: 1 × ₹3899.00
     • Item Total: ₹3899.00

  💰 *PAYMENT & BILLING:*
  • Items Subtotal: ₹3899.00
  • Shipping: FREE
  • *Grand Total: ₹3899.00*

  Please confirm my order and share delivery details.
  Thank you! ✨
  ```

### 3. Executive Admin Dashboard (`/dashboard/`)
- **Secure Authentication**: Dedicated staff-only login separate from customer views.
- **Executive Overview**: Total Revenue, Total Orders, Pending Orders, Confirmed Orders, Live Products, Out of Stock Counter, Low Stock Alerts, and Recent Orders.
- **Product Management**:
  - Add unlimited products.
  - Multi-image bulk file upload with primary thumbnail selector and individual image deletion.
  - Price management with automatic discount percentage calculation (`sale_price` vs `regular_price`).
  - Inventory quantity tracking with automatic **OUT OF STOCK** trigger when quantity reaches 0.
  - Visibility toggles: Active, Featured, New Arrival, Best Seller.
- **Category Management**: Create, edit, and delete categories with custom cover photos and display sort orders.
- **Inventory Control**: Dedicated stock table with in-place inline stock updates and low-stock filters.
- **Order Management**:
  - Filter orders by status (Pending, Confirmed, Processing, Shipped, Delivered, Cancelled) and order date.
  - Search by Order #, Customer Name, Phone, or City.
  - Order detail view showing customer address, items snapshot, status update dropdown, and one-click **"Chat With Customer on WhatsApp"** link.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, Django 5.x, Django ORM
- **Database**: MySQL (production-ready via `PyMySQL`) with seamless SQLite default fallback
- **Frontend**: HTML5, CSS3, Bootstrap 5.3, Font Awesome 6, Vanilla ES6 JavaScript
- **Typography**: Playfair Display (Serif) & Plus Jakarta Sans (Modern Clean Sans)
- **Image Processing**: Pillow (PIL)

---

## 📂 Project Directory Structure

```text
PINACLE FASHIONS/
├── manage.py                     # Django management script
├── requirements.txt              # Project dependencies
├── .env.example                  # Environment configuration template
├── .env                          # Local environment settings
├── README.md                     # Documentation
├── config/                       # Project configuration
│   ├── __init__.py               # PyMySQL adapter hook
│   ├── settings.py               # Django settings (DB, Static, Media, Context Processors)
│   ├── urls.py                   # Global URL routing
│   ├── wsgi.py                   # WSGI server entry
│   └── asgi.py                   # ASGI server entry
├── store/                        # Catalog & customer store app
│   ├── models.py                 # Category, Product, ProductImage, ContactMessage, Subscriber
│   ├── views.py                  # Home, Shop, Product Detail, Cart, Wishlist, About, Contact
│   ├── urls.py                   # Store URL mappings
│   ├── forms.py                  # Contact & Newsletter forms
│   ├── cart.py                   # Guest session cart management
│   ├── wishlist.py               # Guest session wishlist management
│   ├── context_processors.py     # Global categories, cart count, wishlist, brand info
│   ├── tests.py                  # Comprehensive test suite
│   └── management/commands/
│       └── seed_data.py          # Database seeding command (catalog, products, admin)
├── orders/                       # Orders & WhatsApp checkout app
│   ├── models.py                 # Order, OrderItem (snapshots), CustomerAddress
│   ├── views.py                  # Checkout view (Buy Now & Cart), Order Success
│   ├── urls.py                   # Order URL routing
│   ├── forms.py                  # CheckoutForm (Address & Customer details)
│   └── whatsapp.py               # WhatsApp message encoder and URL generator
├── dashboard/                    # Custom executive admin dashboard
│   ├── views.py                  # Overview, Products CRUD, Categories CRUD, Inventory, Orders
│   ├── urls.py                   # Dashboard routing
│   └── forms.py                  # ProductForm, CategoryForm, OrderStatusForm
├── static/                       # Static assets
│   ├── css/
│   │   ├── style.css             # Luxury customer store styling
│   │   └── admin_dashboard.css   # Executive admin dashboard styling
│   ├── js/
│   │   ├── main.js               # UI interactions, wishlist toggle, gallery, quick-view, toasts
│   │   └── cart.js               # AJAX cart quantity updates & totals
│   └── images/
│       ├── pinacle-logo.jpg      # Official brand logo
│       └── pinacle-thank-you.jpg # Official customer thank-you card
├── media/                        # Dynamic uploads
│   ├── categories/               # Category cover images
│   └── products/                 # Product photography
└── templates/                    # Django HTML Templates
    ├── base.html                 # Master template
    ├── components/               # Navbar, Footer, Announcement Bar, Product Card, Toasts
    ├── store/                    # Home, Shop, Product Detail, Categories, Cart, Wishlist, About, Contact
    ├── orders/                   # Checkout, Order Success
    └── dashboard/                # Base Dashboard, Login, Overview, Product List/Form, Category List/Form, Inventory, Order List/Detail
```

---

## 💻 Installation & Setup Instructions

### 1. Prerequisites
- Python 3.10 or higher
- pip (Python package installer)
- MySQL Server (optional for MySQL mode; SQLite works out-of-the-box)

### 2. Clone or Open Workspace
```bash
cd "PINACLE FASHIONS"
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# On Windows PowerShell:
Copy-Item .env.example .env
```

To use **MySQL**, update `.env`:
```env
DB_ENGINE=mysql
DB_NAME=pinacle_fashions
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```
*(Leave `DB_ENGINE=sqlite` to run immediately with zero setup on any computer.)*

### 5. Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. (Optional Demo Data Only — Pre-Launch Setup)
To populate sample categories and products strictly for an empty local demo (never run after pre-launch cleanup or on live data):
```bash
python manage.py seed_data --allow-demo-seed
```

### 7. Run Automated Tests
```bash
python manage.py test
```

### 8. Start the Development Server
```bash
python manage.py runserver
```

---

## 🔑 Login Credentials & Access URLs

### Customer Website
- **Store Homepage**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Shop Catalog**: [http://127.0.0.1:8000/shop/](http://127.0.0.1:8000/shop/)
- **New Arrivals**: [http://127.0.0.1:8000/new-arrivals/](http://127.0.0.1:8000/new-arrivals/)
- **Categories**: [http://127.0.0.1:8000/categories/](http://127.0.0.1:8000/categories/)
- **Shopping Bag**: [http://127.0.0.1:8000/cart/](http://127.0.0.1:8000/cart/)
- **Saved Wishlist**: [http://127.0.0.1:8000/wishlist/](http://127.0.0.1:8000/wishlist/)
- **About Us**: [http://127.0.0.1:8000/about/](http://127.0.0.1:8000/about/)
- **Contact Us**: [http://127.0.0.1:8000/contact/](http://127.0.0.1:8000/contact/)

### Executive Admin Dashboard
- **Admin Dashboard URL**: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
- **Admin Login URL**: [http://127.0.0.1:8000/dashboard/login/](http://127.0.0.1:8000/dashboard/login/)
- **Username**: `admin`
- **Password**: `pinaclefashions123`

*(Standard Django Admin also accessible at [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/))*

---

## 🛡️ Security & Architecture Best Practices

- **CSRF Protection**: All forms (Add to Bag, Checkout, Contact, Admin CRUD) strictly validate Django CSRF tokens.
- **Stock Integrity**: Atomic database transactions (`transaction.atomic()` with `select_for_update()`) ensure stock cannot go negative during concurrent orders.
- **Price Immutability**: Historical orders store price and SKU snapshots in `OrderItem` so later catalog price changes never corrupt previous orders.
- **Credential Safety**: `SECRET_KEY` and database credentials loaded via `python-dotenv`.
- **RBAC**: Custom admin views require both `@login_required` and `is_staff` privileges.

