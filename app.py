import os
import sqlite3
import json
import io
import re
import datetime
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# ReportLab & QRCode imports
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "manchis.db")
BILLS_DIR = os.path.join(BASE_DIR, "bills")
os.makedirs(BILLS_DIR, exist_ok=True)

app = Flask(__name__, static_folder=".", static_url_path="")
app.secret_key = "manchis_super_secret_ecom_key_2026"
CORS(app, supports_credentials=True)

# -------------------------------------------------------------
# Database Helpers & Initialization
# -------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        reward_points INTEGER NOT NULL DEFAULT 100,
        created_at TEXT NOT NULL
    )
    """)

    # 2. Products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        deal_type TEXT NOT NULL DEFAULT 'Regular',
        price REAL NOT NULL,
        original_price REAL NOT NULL,
        description TEXT,
        image_url TEXT NOT NULL,
        stock INTEGER NOT NULL DEFAULT 20,
        status TEXT NOT NULL DEFAULT 'In Stock',
        delivery_info TEXT DEFAULT 'Free delivery in 3-5 business days',
        rating REAL DEFAULT 4.5,
        is_featured INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)

    # 3. Combos table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS combos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        original_price REAL NOT NULL,
        image_url TEXT NOT NULL,
        items_included TEXT NOT NULL,
        deal_type TEXT NOT NULL DEFAULT 'Combo Deals',
        stock INTEGER DEFAULT 15,
        active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    # 4. Coupons table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_type TEXT NOT NULL,
        discount_value REAL NOT NULL,
        min_order_amount REAL DEFAULT 0,
        max_discount REAL DEFAULT 0,
        expiry_date TEXT,
        active INTEGER DEFAULT 1,
        description TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # 5. Orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT,
        customer_address TEXT NOT NULL,
        items_json TEXT NOT NULL,
        subtotal REAL NOT NULL,
        coupon_code TEXT,
        discount REAL DEFAULT 0,
        points_used INTEGER DEFAULT 0,
        points_earned INTEGER DEFAULT 0,
        final_total REAL NOT NULL,
        payment_method TEXT NOT NULL,
        order_date TEXT NOT NULL,
        estimated_delivery_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Order Placed',
        pdf_path TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # 6. Order Tracking History table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_tracking_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        status TEXT NOT NULL,
        status_time TEXT NOT NULL,
        note TEXT
    )
    """)

    conn.commit()

    # Seed Default Data
    seed_data(conn)
    conn.close()

def seed_data(conn):
    cursor = conn.cursor()

    # Seed Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        admin_pass = generate_password_hash("admin123")
        user_pass = generate_password_hash("user123")
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, reward_points, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("ManChi Admin", "admin@manchis.com", admin_pass, "admin", 500, now))
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, reward_points, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("Priya Sharma", "user@manchis.com", user_pass, "user", 250, now))

    # Seed Products: 5 products for EACH category (Women, Men, Accessories, Beauty & Health)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sample_products = [
        # Women - 5 Products
        ("Royal Rose Anarkali Kurta Set", "Women", "Ethnic", 1899.0, 2999.0,
         "Exquisite embroidered Anarkali suit with matching dupatta and pants. Perfect for celebrations.",
         "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&auto=format&fit=crop&q=80",
         25, "In Stock", "Free delivery in 2-3 days", 4.8, 1),
        ("Pastel Floral Tiered Maxi Dress", "Women", "Casual", 1299.0, 1999.0,
         "Breezy cotton tiered dress with subtle floral prints and smocked waist. Casual chic comfort.",
         "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=600&auto=format&fit=crop&q=80",
         30, "In Stock", "Free delivery in 3-4 days", 4.6, 1),
        ("Zari Brocade Festive Lehenga", "Women", "Festival", 3499.0, 5499.0,
         "Handcrafted gold and blush zari lehenga choli with ornate borders and lightweight net veil.",
         "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=600&auto=format&fit=crop&q=80",
         15, "In Stock", "Express delivery in 2 days", 4.9, 1),
        ("Pure Silk Chanderi Saree", "Women", "Special Deals", 1999.0, 3299.0,
         "Traditional handloom Chanderi saree with woven zari bootis and elegant contrast pallu.",
         "https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?w=600&auto=format&fit=crop&q=80",
         20, "In Stock", "Free delivery in 3-5 days", 4.7, 0),
        ("Embroidered Georgette Sharara Suit", "Women", "Combo Deals", 2199.0, 3499.0,
         "Designer georgette peplum kurti with flared tiered sharara pants and embellished dupatta.",
         "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&auto=format&fit=crop&q=80",
         22, "In Stock", "Free delivery in 2-3 days", 4.9, 1),

        # Men - 5 Products
        ("Embroidered Raw Silk Kurta", "Men", "Festival", 1499.0, 2499.0,
         "Mandarin collar royal kurta in soft raw silk blend with intricate thread embroidery.",
         "https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?w=600&auto=format&fit=crop&q=80",
         35, "In Stock", "Free delivery in 3-4 days", 4.7, 1),
        ("Classic Linen Casual Shirt", "Men", "Casual", 999.0, 1599.0,
         "100% breathable organic linen shirt tailored in a modern regular fit for everyday sophistication.",
         "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600&auto=format&fit=crop&q=80",
         40, "In Stock", "Free delivery in 2-3 days", 4.5, 0),
        ("Designer Nehru Bandhgala Jacket", "Men", "Ethnic", 1799.0, 2899.0,
         "Tailored textured jacquard Nehru jacket with metal buttons. Layers handsomely over kurtas.",
         "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=600&auto=format&fit=crop&q=80",
         20, "In Stock", "Free delivery in 3-4 days", 4.8, 1),
        ("Premium Tailored Chino Trousers", "Men", "Special Deals", 1199.0, 1899.0,
         "Stretch cotton versatile chinos crafted for all-day comfort from work to evening gatherings.",
         "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=600&auto=format&fit=crop&q=80",
         28, "In Stock", "Free delivery in 3-5 days", 4.6, 0),
        ("Royal Jodhpur Sherwani Blazer", "Men", "Combo Deals", 2799.0, 4299.0,
         "Heritage royal Jodhpuri structured bandhgala blazer crafted with antique gold crest buttons.",
         "https://images.unsplash.com/photo-1506630448388-4e683c67ddb0?w=600&auto=format&fit=crop&q=80",
         18, "In Stock", "Express delivery in 2 days", 4.8, 1),

        # Accessories - 5 Products
        ("Handcrafted Kundan Jhumka Earrings", "Accessories", "Festival", 699.0, 1299.0,
         "Traditional 22K gold plated Kundan jhumkas adorned with freshwater pearl drops.",
         "https://images.unsplash.com/photo-1630019852942-f89202989a59?w=600&auto=format&fit=crop&q=80",
         50, "In Stock", "Free delivery in 2-3 days", 4.9, 1),
        ("Vegan Leather Quilted Shoulder Bag", "Accessories", "Casual", 1399.0, 2299.0,
         "Elegant rose gold chain strap crossbody shoulder bag with partitioned interior.",
         "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600&auto=format&fit=crop&q=80",
         22, "In Stock", "Free delivery in 3-4 days", 4.7, 0),
        ("Handwoven Zari Potli Bag", "Accessories", "Ethnic", 599.0, 999.0,
         "Stunning velvet embroidered potli clutch with drawstring tassels for festive attire.",
         "https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?w=600&auto=format&fit=crop&q=80",
         30, "In Stock", "Free delivery in 2-4 days", 4.6, 0),
        ("Rose Gold Minimalist Mesh Watch", "Accessories", "Special Deals", 1299.0, 2199.0,
         "Sleek ultra-thin analog timepiece in rose gold stainless steel mesh with scratch-resistant glass.",
         "https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=600&auto=format&fit=crop&q=80",
         35, "In Stock", "Free delivery in 2-3 days", 4.7, 1),
        ("Temple Gold Plated Choker Necklace Set", "Accessories", "Combo Deals", 1499.0, 2699.0,
         "Antique temple jewelry choker with red stones and matching drop earrings for festive ceremonies.",
         "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=600&auto=format&fit=crop&q=80",
         24, "In Stock", "Free delivery in 3-4 days", 4.9, 1),

        # Beauty & Health - 5 Products
        ("Rose Gold Radiance Facial Serum", "Beauty & Health", "Special Deals", 799.0, 1299.0,
         "Infused with botanical rosehip oil and 24K gold flakes for radiant, youthful glow.",
         "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600&auto=format&fit=crop&q=80",
         45, "In Stock", "Free delivery in 2-3 days", 4.8, 1),
        ("Ayurvedic Kumkumadi Night Oil", "Beauty & Health", "Ethnic", 999.0, 1599.0,
         "Authentic saffron and herbal night elixir that visibly brightens and revitalizes skin.",
         "https://images.unsplash.com/photo-1608248597359-54848039755f?w=600&auto=format&fit=crop&q=80",
         25, "In Stock", "Free delivery in 3-5 days", 4.9, 0),
        ("Velvet Matte Berry Lip Tint", "Beauty & Health", "Casual", 449.0, 699.0,
         "Non-drying velvety formula with rich berry pigment that lasts all day.",
         "https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=600&auto=format&fit=crop&q=80",
         60, "In Stock", "Free delivery in 2-3 days", 4.5, 0),
        ("Pure Saffron & Sandalwood Glow Cream", "Beauty & Health", "Festival", 899.0, 1499.0,
         "Infused with Kashmiri saffron and red sandalwood for deep nourishment and luminous complexion.",
         "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=600&auto=format&fit=crop&q=80",
         40, "In Stock", "Free delivery in 2-3 days", 4.8, 1),
        ("Botanical Jasmine Hydrating Face Mist", "Beauty & Health", "Combo Deals", 499.0, 799.0,
         "Refreshing botanical toner and facial mist with pure jasmine extract and hyaluronic acid.",
         "https://images.unsplash.com/photo-1608248597359-54848039755f?w=600&auto=format&fit=crop&q=80",
         50, "In Stock", "Free delivery in 2-4 days", 4.6, 0)
    ]
    for p in sample_products:
        cursor.execute("SELECT id FROM products WHERE name = ?", (p[0],))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO products (name, category, deal_type, price, original_price, description,
                                      image_url, stock, status, delivery_info, rating, is_featured, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (*p, now))

    # Seed Combos
    cursor.execute("SELECT COUNT(*) FROM combos")
    if cursor.fetchone()[0] == 0:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        combos = [
            ("Royal Festive Ethnic Combo",
             "Complete festive attire pairing royal Anarkali kurta set with handcrafted Kundan jhumkas and potli bag.",
             2499.0, 4299.0,
             "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&auto=format&fit=crop&q=80",
             "Anarkali Kurta Set + Kundan Jhumkas + Zari Potli Bag", "Combo Deals", 18, 1, now),
            ("Urban Chic Weekend Casual Bundle",
             "Effortless weekend styling featuring our floral tiered maxi dress with quilted vegan leather shoulder bag.",
             1999.0, 3299.0,
             "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=600&auto=format&fit=crop&q=80",
             "Tiered Maxi Dress + Quilted Crossbody Bag + Matte Lip Tint", "Combo Deals", 20, 1, now),
            ("Gentleman's Royal Festive Pair",
             "Handcrafted raw silk men's kurta paired with luxury textured Nehru jacket for wedding & festival grace.",
             2699.0, 4399.0,
             "https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?w=600&auto=format&fit=crop&q=80",
             "Raw Silk Kurta + Designer Nehru Jacket", "Combo Deals", 15, 1, now),
            ("Glow & Radiance Complete Beauty Kit",
             "Ultimate skincare indulgence combining our 24K Rose Gold Radiance Serum with Ayurvedic Kumkumadi Night Oil.",
             1399.0, 2299.0,
             "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600&auto=format&fit=crop&q=80",
             "Rose Gold Serum + Kumkumadi Night Oil + Berry Lip Tint", "Combo Deals", 25, 1, now)
        ]
        for c in combos:
            cursor.execute("""
                INSERT INTO combos (name, description, price, original_price, image_url, items_included, deal_type, stock, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, c)

    # Seed Coupons
    cursor.execute("SELECT COUNT(*) FROM coupons")
    if cursor.fetchone()[0] == 0:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        coupons = [
            ("MANCHI20", "percentage", 20.0, 500.0, 400.0, "2026-12-31", 1, "20% OFF on orders above Rs. 500 (Max Rs. 400)", now),
            ("FESTIVAL50", "percentage", 50.0, 1500.0, 1000.0, "2026-12-31", 1, "Special Festive Mega 50% OFF (Min order Rs. 1500)", now),
            ("FLAT150", "fixed", 150.0, 800.0, 150.0, "2026-12-31", 1, "Flat Rs. 150 discount on orders above Rs. 800", now),
            ("WELCOME10", "percentage", 10.0, 0.0, 200.0, "2026-12-31", 1, "Welcome 10% OFF for all shoppers", now)
        ]
        for cp in coupons:
            cursor.execute("""
                INSERT INTO coupons (code, discount_type, discount_value, min_order_amount, max_discount, expiry_date, active, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, cp)

    conn.commit()

# -------------------------------------------------------------
# Auth Middleware
# -------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Authentication required. Please login."}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin privileges required."}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_order_qr_content(order_data):
    order_id = order_data["order_id"]
    return (
        f"THANK YOU FOR SHOPPING AT MANCHI'S!\n\n"
        f"Order ID: {order_id}\n"
        f"Customer: {order_data['customer_name']}\n"
        f"Order Date: {order_data['order_date']}\n"
        f"Final Amount: Rs. {order_data['final_total']:.2f}\n"
        f"Status: {order_data['status']}\n"
        f"Estimated Delivery: {order_data['estimated_delivery_date']}\n\n"
        f"Thank you for choosing ManChi's Fashion! We look forward to serving you again."
    )

# -------------------------------------------------------------
# Bill Generation with Real QR Code
# -------------------------------------------------------------
def generate_bill_pdf(order_data, items):
    order_id = order_data["order_id"]
    pdf_filename = f"MC_Bill_{order_id}.pdf"
    pdf_path = os.path.join(BILLS_DIR, pdf_filename)

    # 1. Generate QR Code image in memory with Thank You header
    qr_content = get_order_qr_content(order_data)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(qr_content)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#2c2c2c", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    # 2. Build PDF Document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#e91e63")
    dark_color = colors.HexColor("#2c2c2c")
    light_pink = colors.HexColor("#fff0f3")
    border_color = colors.HexColor("#ffd1dc")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=primary_color,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=dark_color,
        spaceAfter=15
    )
    section_title = ParagraphStyle(
        'SecTitle',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=primary_color,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        textColor=dark_color,
        leading=14
    )
    bold_body = ParagraphStyle(
        'BoldBody',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        textColor=dark_color,
        leading=14
    )

    elements = []

    # Header with Brand Name and Invoice Tag
    header_data = [
        [
            Paragraph("<b>ManChi's</b><br/><font size=9 color='#888888'>Luxury Fashion & Lifestyle Store</font>", title_style),
            Paragraph(f"<font size=16 color='#e91e63'><b>TAX INVOICE</b></font><br/><b>Invoice No:</b> {order_id}<br/><b>Date:</b> {order_data['order_date']}", ParagraphStyle('RightH', parent=body_style, alignment=2))
        ]
    ]
    header_table = Table(header_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # Customer & Shipping details + Delivery Information
    cust_info = (
        f"<b>Billed & Shipped To:</b><br/>"
        f"<b>Name:</b> {order_data['customer_name']}<br/>"
        f"<b>Email:</b> {order_data['customer_email']}<br/>"
        f"<b>Phone:</b> {order_data.get('customer_phone', 'N/A')}<br/>"
        f"<b>Shipping Address:</b> {order_data['customer_address']}"
    )
    order_meta = (
        f"<b>Order Information:</b><br/>"
        f"<b>Payment Method:</b> {order_data['payment_method']}<br/>"
        f"<b>Current Status:</b> <font color='#e91e63'><b>{order_data['status']}</b></font><br/>"
        f"<b>Estimated Delivery:</b> <b>{order_data['estimated_delivery_date']}</b><br/>"
        f"<b>Reward Points Earned:</b> +{order_data.get('points_earned', 0)} pts"
    )
    info_data = [
        [Paragraph(cust_info, body_style), Paragraph(order_meta, body_style)]
    ]
    info_table = Table(info_data, colWidths=[280, 260])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_pink),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # Items Table
    table_headers = [
        Paragraph("<b>#</b>", bold_body),
        Paragraph("<b>Item Description</b>", bold_body),
        Paragraph("<b>Qty</b>", ParagraphStyle('C', parent=bold_body, alignment=1)),
        Paragraph("<b>Unit Price</b>", ParagraphStyle('R', parent=bold_body, alignment=2)),
        Paragraph("<b>Total (Rs.)</b>", ParagraphStyle('R', parent=bold_body, alignment=2))
    ]
    table_rows = [table_headers]

    for idx, item in enumerate(items, 1):
        item_total = float(item.get("price", 0)) * int(item.get("quantity", 1))
        table_rows.append([
            Paragraph(str(idx), body_style),
            Paragraph(f"<b>{item.get('name', 'Product')}</b>", body_style),
            Paragraph(str(item.get("quantity", 1)), ParagraphStyle('C', parent=body_style, alignment=1)),
            Paragraph(f"Rs. {float(item.get('price', 0)):.2f}", ParagraphStyle('R', parent=body_style, alignment=2)),
            Paragraph(f"Rs. {item_total:.2f}", ParagraphStyle('R', parent=body_style, alignment=2))
        ])

    items_table = Table(table_rows, colWidths=[30, 270, 50, 95, 95])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#fffbfb")]),
        ('PADDING', (0, 1), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 12))

    # Summary and QR Code Section
    qr_flowable = RLImage(qr_buffer, width=95, height=95)
    qr_caption = Paragraph(
        "<font size=8 color='#555555'><b>Scan QR Code</b><br/>Thank you for shopping at ManChi's!</font>",
        ParagraphStyle('QRC', parent=body_style, alignment=1)
    )

    qr_block = [
        [qr_flowable],
        [qr_caption]
    ]
    qr_subtable = Table(qr_block, colWidths=[120])
    qr_subtable.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 2),
    ]))

    summary_rows = [
        [Paragraph("Subtotal:", bold_body), Paragraph(f"Rs. {order_data['subtotal']:.2f}", ParagraphStyle('R', parent=body_style, alignment=2))],
        [Paragraph(f"Coupon Discount ({order_data.get('coupon_code') or 'None'}):", body_style), Paragraph(f"- Rs. {order_data.get('discount', 0):.2f}", ParagraphStyle('R', parent=body_style, alignment=2))],
        [Paragraph(f"Reward Points Redeemed ({order_data.get('points_used', 0)} pts):", body_style), Paragraph(f"- Rs. {order_data.get('points_used', 0):.2f}", ParagraphStyle('R', parent=body_style, alignment=2))],
        [Paragraph("Delivery Charges:", body_style), Paragraph("<font color='#008800'>FREE</font>", ParagraphStyle('R', parent=body_style, alignment=2))],
        [Paragraph("<b>Grand Final Total:</b>", ParagraphStyle('Tot', parent=bold_body, fontSize=11, textColor=primary_color)),
         Paragraph(f"<b>Rs. {order_data['final_total']:.2f}</b>", ParagraphStyle('TotR', parent=bold_body, fontSize=11, textColor=primary_color, alignment=2))]
    ]
    summary_table = Table(summary_rows, colWidths=[220, 100])
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('BACKGROUND', (0, -1), (-1, -1), light_pink),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    bottom_data = [
        [qr_subtable, summary_table]
    ]
    bottom_table = Table(bottom_data, colWidths=[200, 340])
    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(bottom_table)
    elements.append(Spacer(1, 20))

    # Footer note
    footer_text = (
        "<b>Thank you for shopping with ManChi's!</b><br/>"
        "All items come with our genuine quality guarantee and easy 7-day exchange policy.<br/>"
        "Customer Support: care@manchis.com | +91 98765 43210 | www.manchis.com"
    )
    elements.append(Paragraph(footer_text, ParagraphStyle('Foot', parent=body_style, alignment=1, textColor=colors.HexColor("#777777"), fontSize=8.5)))

    doc.build(elements)
    return pdf_filename

# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------

# --- Authentication ---
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"success": False, "message": "All fields are required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"success": False, "message": "Email is already registered. Please login."}), 400

    password_hash = generate_password_hash(password)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # New user gets 100 reward points welcome bonus
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, reward_points, created_at)
        VALUES (?, ?, ?, 'user', 100, ?)
    """, (name, email, password_hash, now))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    session["user_id"] = user_id
    session["role"] = "user"
    session["name"] = name
    session["email"] = email

    return jsonify({
        "success": True,
        "message": "Welcome to ManChi's! You received 100 Reward Points as a welcome gift.",
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "role": "user",
            "reward_points": 100
        }
    })

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["name"] = user["name"]
    session["email"] = user["email"]

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['name']}!",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "reward_points": user["reward_points"]
        }
    })

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})

@app.route("/api/auth/me", methods=["GET"])
def get_current_user():
    if "user_id" not in session:
        return jsonify({"success": False, "user": None})

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, reward_points FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    conn.close()

    if not user:
        session.clear()
        return jsonify({"success": False, "user": None})

    return jsonify({
        "success": True,
        "user": dict(user)
    })

# --- Products ---
@app.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    deal_type = request.args.get("deal_type")
    search = request.args.get("search")

    query = "SELECT * FROM products WHERE status != 'Inactive'"
    params = []

    if category and category.lower() != "all":
        query += " AND category = ?"
        params.append(category)

    if deal_type and deal_type.lower() != "all":
        query += " AND deal_type = ?"
        params.append(deal_type)

    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY id DESC"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify({"success": True, "products": products})

@app.route("/api/products/<int:prod_id>", methods=["GET"])
def get_single_product(prod_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
    product = cursor.fetchone()
    conn.close()

    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    return jsonify({"success": True, "product": dict(product)})

# --- Combos ---
@app.route("/api/combos", methods=["GET"])
def get_combos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM combos WHERE active = 1 ORDER BY id DESC")
    combos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "combos": combos})

# --- Coupons ---
@app.route("/api/coupons", methods=["GET"])
def get_public_coupons():
    now_date = datetime.date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, code, discount_type, discount_value, min_order_amount, max_discount, expiry_date, description
        FROM coupons
        WHERE active = 1 AND (expiry_date IS NULL OR expiry_date >= ?)
        ORDER BY id DESC
    """, (now_date,))
    coupons = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "coupons": coupons})

@app.route("/api/coupons/apply", methods=["POST"])
def apply_coupon():
    data = request.get_json() or {}
    code = data.get("code", "").strip().upper()
    subtotal = float(data.get("subtotal", 0))

    if not code:
        return jsonify({"success": False, "message": "Please enter a coupon code."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coupons WHERE code = ?", (code,))
    coupon = cursor.fetchone()
    conn.close()

    if not coupon:
        return jsonify({"success": False, "message": "Invalid coupon code."}), 400

    if not coupon["active"]:
        return jsonify({"success": False, "message": "This coupon is currently inactive."}), 400

    if coupon["expiry_date"]:
        today = datetime.date.today().isoformat()
        if coupon["expiry_date"] < today:
            return jsonify({"success": False, "message": f"This coupon expired on {coupon['expiry_date']}."}), 400

    min_order = float(coupon["min_order_amount"] or 0)
    if subtotal < min_order:
        return jsonify({
            "success": False,
            "message": f"Minimum order amount of Rs. {min_order:.2f} required to use coupon '{code}'."
        }), 400

    # Calculate discount
    discount_val = float(coupon["discount_value"])
    if coupon["discount_type"] == "percentage":
        discount = (subtotal * discount_val) / 100.0
        max_disc = float(coupon["max_discount"] or 0)
        if max_disc > 0 and discount > max_disc:
            discount = max_disc
    else: # fixed
        discount = min(discount_val, subtotal)

    discount = round(discount, 2)
    final_amount = round(max(0.0, subtotal - discount), 2)

    return jsonify({
        "success": True,
        "message": f"Coupon '{code}' applied successfully!",
        "coupon_code": code,
        "discount": discount,
        "subtotal": subtotal,
        "final_amount": final_amount
    })

# --- Orders & Tracking ---
@app.route("/api/orders", methods=["POST"])
@login_required
def create_order():
    data = request.get_json() or {}
    user_id = session["user_id"]
    customer_name = data.get("customer_name", "").strip()
    customer_email = data.get("customer_email", "").strip()
    customer_phone = data.get("customer_phone", "").strip()
    customer_address = data.get("customer_address", "").strip()
    items = data.get("items", [])
    payment_method = data.get("payment_method", "Cash on Delivery")
    coupon_code = data.get("coupon_code", "").strip().upper()
    points_used = int(data.get("points_used", 0))

    if not customer_name or not customer_email or not customer_address:
        return jsonify({"success": False, "message": "Please provide full customer details and address."}), 400

    # Mobile number conditions:
    # 1. If mobile number is not entered, do not place order
    # 2. Cannot be greater than 10 or less than 10 digits
    if not customer_phone:
        return jsonify({"success": False, "message": "Mobile number is required to place an order."}), 400

    clean_phone = customer_phone.replace(" ", "").replace("-", "")
    if not clean_phone.isdigit():
        return jsonify({"success": False, "message": "Mobile number must contain digits only."}), 400

    if len(clean_phone) < 10:
        return jsonify({"success": False, "message": "Mobile number cannot be less than 10 digits."}), 400

    if len(clean_phone) > 10:
        return jsonify({"success": False, "message": "Mobile number cannot be greater than 10 digits."}), 400

    customer_phone = clean_phone

    if not items or len(items) == 0:
        return jsonify({"success": False, "message": "Your cart is empty."}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Calculate subtotal
    subtotal = 0.0
    for item in items:
        subtotal += float(item.get("price", 0)) * int(item.get("quantity", 1))

    # Apply Coupon Discount safely
    discount = 0.0
    if coupon_code:
        cursor.execute("SELECT * FROM coupons WHERE code = ? AND active = 1", (coupon_code,))
        coupon = cursor.fetchone()
        if coupon:
            today = datetime.date.today().isoformat()
            if not coupon["expiry_date"] or coupon["expiry_date"] >= today:
                if subtotal >= float(coupon["min_order_amount"] or 0):
                    if coupon["discount_type"] == "percentage":
                        d = (subtotal * float(coupon["discount_value"])) / 100.0
                        max_d = float(coupon["max_discount"] or 0)
                        discount = min(d, max_d) if max_d > 0 else d
                    else:
                        discount = min(float(coupon["discount_value"]), subtotal)

    # Check Reward Points
    cursor.execute("SELECT reward_points FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    current_points = user_row["reward_points"] if user_row else 0

    if points_used > current_points:
        points_used = current_points

    # Max points used cannot exceed remaining balance
    max_redeemable = max(0.0, subtotal - discount)
    if points_used > max_redeemable:
        points_used = int(max_redeemable)

    final_total = round(max(0.0, subtotal - discount - points_used), 2)

    # Calculate points earned (5% of final total, rounded)
    points_earned = max(1, int(final_total * 0.05))

    # Generate unique Order ID
    now_dt = datetime.datetime.now()
    order_id = f"MC-{now_dt.strftime('%Y%m%d')}-{now_dt.strftime('%H%M%S')}"
    order_date = now_dt.strftime("%d %b %Y, %I:%M %p")
    # Estimated delivery date is 4 business days later
    delivery_dt = now_dt + datetime.timedelta(days=4)
    estimated_delivery_date = delivery_dt.strftime("%d %b %Y")

    initial_status = "Order Placed"
    items_json = json.dumps(items)

    # Insert Order
    cursor.execute("""
        INSERT INTO orders (
            order_id, user_id, customer_name, customer_email, customer_phone, customer_address,
            items_json, subtotal, coupon_code, discount, points_used, points_earned,
            final_total, payment_method, order_date, estimated_delivery_date, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_id, user_id, customer_name, customer_email, customer_phone, customer_address,
        items_json, subtotal, coupon_code if discount > 0 else None, discount, points_used, points_earned,
        final_total, payment_method, order_date, estimated_delivery_date, initial_status,
        now_dt.strftime("%Y-%m-%d %H:%M:%S")
    ))

    # Insert initial tracking stage
    cursor.execute("""
        INSERT INTO order_tracking_history (order_id, status, status_time, note)
        VALUES (?, ?, ?, ?)
    """, (order_id, initial_status, order_date, "Your order has been received and confirmed."))

    # Deduct points used & add points earned
    new_points_balance = current_points - points_used + points_earned
    cursor.execute("UPDATE users SET reward_points = ? WHERE id = ?", (new_points_balance, user_id))

    # Reduce product stock safely
    for item in items:
        if "id" in item and item.get("id"):
            cursor.execute("UPDATE products SET stock = MAX(0, stock - ?) WHERE id = ?", (item.get("quantity", 1), item["id"]))

    conn.commit()

    # Generate PDF Bill with QR Code
    order_summary = {
        "order_id": order_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "customer_address": customer_address,
        "order_date": order_date,
        "estimated_delivery_date": estimated_delivery_date,
        "status": initial_status,
        "payment_method": payment_method,
        "subtotal": subtotal,
        "coupon_code": coupon_code if discount > 0 else None,
        "discount": discount,
        "points_used": points_used,
        "points_earned": points_earned,
        "final_total": final_total
    }

    try:
        pdf_file = generate_bill_pdf(order_summary, items)
        cursor.execute("UPDATE orders SET pdf_path = ? WHERE order_id = ?", (pdf_file, order_id))
        conn.commit()
    except Exception as e:
        print(f"Error generating PDF invoice: {e}")

    conn.close()

    return jsonify({
        "success": True,
        "message": f"Order #{order_id} placed successfully!",
        "order_id": order_id,
        "points_earned": points_earned,
        "new_reward_balance": new_points_balance,
        "estimated_delivery_date": estimated_delivery_date
    })

@app.route("/api/orders", methods=["GET"])
@login_required
def get_user_orders():
    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,))
    orders = []
    for row in cursor.fetchall():
        ord_dict = dict(row)
        ord_dict["items"] = json.loads(ord_dict["items_json"])
        orders.append(ord_dict)
    conn.close()
    return jsonify({"success": True, "orders": orders})

@app.route("/api/orders/<order_id>", methods=["GET"])
def get_order_tracking(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    order = cursor.fetchone()

    if not order:
        conn.close()
        return jsonify({"success": False, "message": "Order not found."}), 404

    # Security check: if logged in as user, can only view own order; admin can view all
    if "user_id" in session and session.get("role") != "admin":
        if order["user_id"] != session["user_id"]:
            conn.close()
            return jsonify({"success": False, "message": "Unauthorized access to order."}), 403

    cursor.execute("SELECT * FROM order_tracking_history WHERE order_id = ? ORDER BY id ASC", (order_id,))
    history = [dict(h) for h in cursor.fetchall()]
    conn.close()

    order_dict = dict(order)
    order_dict["items"] = json.loads(order_dict["items_json"])
    order_dict["tracking_history"] = history

    return jsonify({"success": True, "order": order_dict})

@app.route("/api/orders/<order_id>/bill", methods=["GET"])
def download_order_bill(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()

    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404

    pdf_filename = f"MC_Bill_{order_id}.pdf"
    file_path = os.path.join(BILLS_DIR, pdf_filename)

    if not os.path.exists(file_path):
        # Regenerate if missing
        items = json.loads(order["items_json"])
        generate_bill_pdf(dict(order), items)

    return send_file(file_path, as_attachment=False, download_name=pdf_filename, mimetype='application/pdf')

@app.route("/api/orders/<order_id>/qrcode", methods=["GET"])
def get_order_qr_image(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()

    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404

    qr_content = get_order_qr_content(dict(order))
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=7,
        border=2,
    )
    qr.add_data(qr_content)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#2c2c2c", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    return send_file(qr_buffer, mimetype="image/png")

# --- Admin Operations ---

@app.route("/api/admin/products", methods=["POST"])
@admin_required
def admin_add_product():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    category = data.get("category", "").strip()
    deal_type = data.get("deal_type", "Regular").strip()
    price = float(data.get("price", 0))
    original_price = float(data.get("original_price", price))
    description = data.get("description", "").strip()
    image_url = data.get("image_url", "").strip()
    stock = int(data.get("stock", 10))
    status = data.get("status", "In Stock").strip()
    delivery_info = data.get("delivery_info", "Free delivery in 3-5 days").strip()

    if not name or not category or price <= 0 or not image_url:
        return jsonify({"success": False, "message": "Please provide valid product name, category, price, and image."}), 400

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (name, category, deal_type, price, original_price, description,
                              image_url, stock, status, delivery_info, rating, is_featured, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 4.8, 0, ?)
    """, (name, category, deal_type, price, original_price, description, image_url, stock, status, delivery_info, now))
    prod_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Product added successfully!", "product_id": prod_id})

@app.route("/api/admin/products/<int:prod_id>", methods=["PUT"])
@admin_required
def admin_edit_product(prod_id):
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    category = data.get("category", "").strip()
    deal_type = data.get("deal_type", "Regular").strip()
    price = float(data.get("price", 0))
    original_price = float(data.get("original_price", price))
    description = data.get("description", "").strip()
    image_url = data.get("image_url", "").strip()
    stock = int(data.get("stock", 0))
    status = data.get("status", "In Stock").strip()
    delivery_info = data.get("delivery_info", "Free delivery in 3-5 days").strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE products
        SET name = ?, category = ?, deal_type = ?, price = ?, original_price = ?,
            description = ?, image_url = ?, stock = ?, status = ?, delivery_info = ?
        WHERE id = ?
    """, (name, category, deal_type, price, original_price, description, image_url, stock, status, delivery_info, prod_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Product updated successfully!"})

@app.route("/api/admin/products/<int:prod_id>", methods=["DELETE"])
@admin_required
def admin_delete_product(prod_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Product deleted successfully!"})

@app.route("/api/admin/combos", methods=["POST"])
@admin_required
def admin_add_combo():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    price = float(data.get("price", 0))
    original_price = float(data.get("original_price", price))
    image_url = data.get("image_url", "").strip()
    items_included = data.get("items_included", "").strip()
    stock = int(data.get("stock", 10))

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO combos (name, description, price, original_price, image_url, items_included, deal_type, stock, active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Combo Deals', ?, 1, ?)
    """, (name, description, price, original_price, image_url, items_included, stock, now))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Combo Deal added successfully!"})

@app.route("/api/admin/combos/<int:combo_id>", methods=["DELETE"])
@admin_required
def admin_delete_combo(combo_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM combos WHERE id = ?", (combo_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Combo deleted successfully!"})

@app.route("/api/admin/coupons", methods=["GET"])
@admin_required
def admin_get_coupons():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coupons ORDER BY id DESC")
    coupons = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "coupons": coupons})

@app.route("/api/admin/coupons", methods=["POST"])
@admin_required
def admin_add_coupon():
    data = request.get_json() or {}
    code = data.get("code", "").strip().upper()
    discount_type = data.get("discount_type", "percentage")
    discount_value = float(data.get("discount_value", 0))
    min_order_amount = float(data.get("min_order_amount", 0))
    max_discount = float(data.get("max_discount", 0))
    expiry_date = data.get("expiry_date", None)
    description = data.get("description", "").strip()
    active = int(data.get("active", 1))

    if not code or discount_value <= 0:
        return jsonify({"success": False, "message": "Coupon code and positive discount value are required."}), 400

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO coupons (code, discount_type, discount_value, min_order_amount, max_discount, expiry_date, active, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (code, discount_type, discount_value, min_order_amount, max_discount, expiry_date, active, description, now))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"success": False, "message": "A coupon with this code already exists."}), 400
    conn.close()
    return jsonify({"success": True, "message": f"Coupon '{code}' created successfully!"})

@app.route("/api/admin/coupons/<int:coupon_id>", methods=["PUT"])
@admin_required
def admin_edit_coupon(coupon_id):
    data = request.get_json() or {}
    code = data.get("code", "").strip().upper()
    discount_type = data.get("discount_type", "percentage")
    discount_value = float(data.get("discount_value", 0))
    min_order_amount = float(data.get("min_order_amount", 0))
    max_discount = float(data.get("max_discount", 0))
    expiry_date = data.get("expiry_date", None)
    description = data.get("description", "").strip()
    active = int(data.get("active", 1))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE coupons
        SET code = ?, discount_type = ?, discount_value = ?, min_order_amount = ?,
            max_discount = ?, expiry_date = ?, active = ?, description = ?
        WHERE id = ?
    """, (code, discount_type, discount_value, min_order_amount, max_discount, expiry_date, active, description, coupon_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Coupon updated successfully!"})

@app.route("/api/admin/coupons/<int:coupon_id>", methods=["DELETE"])
@admin_required
def admin_delete_coupon(coupon_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM coupons WHERE id = ?", (coupon_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Coupon deleted successfully!"})

@app.route("/api/admin/orders", methods=["GET"])
@admin_required
def admin_get_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = []
    for row in cursor.fetchall():
        ord_dict = dict(row)
        ord_dict["items"] = json.loads(ord_dict["items_json"])
        orders.append(ord_dict)
    conn.close()
    return jsonify({"success": True, "orders": orders})

@app.route("/api/admin/orders/<order_id>/status", methods=["PUT"])
@admin_required
def admin_update_order_status(order_id):
    data = request.get_json() or {}
    new_status = data.get("status", "").strip()
    note = data.get("note", "").strip()

    valid_statuses = [
        "Order Placed", "Order Confirmed", "Processing",
        "Packed", "Shipped", "Out for Delivery", "Delivered", "Cancelled"
    ]
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": "Invalid order status."}), 400

    now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    default_notes = {
        "Order Placed": "Order received and queued.",
        "Order Confirmed": "Order has been confirmed by ManChi's team.",
        "Processing": "Order is being reviewed and prepared.",
        "Packed": "Your items have been safely packed and labeled.",
        "Shipped": "Order handed over to courier partner.",
        "Out for Delivery": "Package is out for delivery with courier agent.",
        "Delivered": "Package successfully delivered to customer.",
        "Cancelled": "Order has been cancelled."
    }
    if not note:
        note = default_notes.get(new_status, f"Status updated to {new_status}")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))

    cursor.execute("""
        INSERT INTO order_tracking_history (order_id, status, status_time, note)
        VALUES (?, ?, ?, ?)
    """, (order_id, new_status, now_str, note))
    conn.commit()

    # Re-generate PDF Bill with updated status
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    updated_order = cursor.fetchone()
    if updated_order:
        items = json.loads(updated_order["items_json"])
        try:
            generate_bill_pdf(dict(updated_order), items)
        except Exception as e:
            print(f"Error updating PDF: {e}")

    conn.close()

    return jsonify({
        "success": True,
        "message": f"Order #{order_id} status updated to '{new_status}' successfully!",
        "new_status": new_status,
        "status_time": now_str,
        "note": note
    })

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_get_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, reward_points, created_at FROM users ORDER BY id DESC")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "users": users})

# --- Static Frontend Serving ---
@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.route("/admin")
def serve_admin():
    return send_from_directory(".", "admin.html")

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(".", filename)

if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print(" ManChi's E-Commerce Server Starting...")
    print(" Running at: http://127.0.0.1:5000")
    print(" Admin Login: admin@manchis.com / admin123")
    print(" User Login:  user@manchis.com / user123")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
