import os
import json
import sqlite3
import unittest
from app import app, init_db, get_db, BILLS_DIR, get_order_qr_content

class TestManChisEcommerce(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = app.test_client()

    def test_01_homepage_loads(self):
        """1 & 2: Homepage loads successfully with HTML"""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"ManChi", res.data)
        self.assertIn(b"Deal Type", res.data)
        print("[PASS] Test 1: Homepage loads successfully with branding and deal types")

    def test_02_registration_and_welcome_rewards(self):
        """3: Registration gives 100 welcome reward points"""
        unique_email = f"test_shopper_{os.urandom(3).hex()}@test.com"
        res = self.client.post("/api/auth/register", json={
            "name": "Ananya Roy",
            "email": unique_email,
            "password": "password123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["reward_points"], 100)
        print(f"[PASS] Test 2: User registration successful with 100 welcome reward points ({unique_email})")

    def test_03_login(self):
        """4: User login works and returns session"""
        res = self.client.post("/api/auth/login", json={
            "email": "user@manchis.com",
            "password": "user123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["role"], "user")
        print("[PASS] Test 3: Normal user login verified")

    def test_04_product_browsing_and_deal_types(self):
        """5: Product browsing with category and deal type filtering"""
        # All products
        res = self.client.get("/api/products")
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["products"]), 0)

        # Filter by deal_type = 'Festival'
        res_fest = self.client.get("/api/products?deal_type=Festival")
        fest_data = res_fest.get_json()
        self.assertTrue(all(p["deal_type"] == "Festival" for p in fest_data["products"]))

        # Check that all 4 categories have at least 5 products each
        import urllib.parse
        for cat in ["Women", "Men", "Accessories", "Beauty & Health"]:
            res_cat = self.client.get(f"/api/products?category={urllib.parse.quote(cat)}")
            cat_items = res_cat.get_json()["products"]
            self.assertGreaterEqual(len(cat_items), 5, f"Category '{cat}' should have at least 5 products")

        print("[PASS] Test 4: Product browsing, category filtering (5 products per category), and deal type filtering verified")

    def test_05_coupons_and_validation(self):
        """6 & 7: Coupon validation, error handling, and discount calculation"""
        # Valid coupon MANCHI20 (20% off on >500)
        res = self.client.post("/api/coupons/apply", json={
            "code": "MANCHI20",
            "subtotal": 1000.0
        })
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["discount"], 200.0)
        self.assertEqual(data["final_amount"], 800.0)

        # Invalid coupon
        res_inv = self.client.post("/api/coupons/apply", json={
            "code": "INVALID_CODE_999",
            "subtotal": 1000.0
        })
        self.assertEqual(res_inv.status_code, 400)
        self.assertFalse(res_inv.get_json()["success"])

        # Min order condition check (FESTIVAL50 requires min 1500)
        res_min = self.client.post("/api/coupons/apply", json={
            "code": "FESTIVAL50",
            "subtotal": 500.0
        })
        self.assertEqual(res_min.status_code, 400)
        self.assertIn("Minimum order amount", res_min.get_json()["message"])
        print("[PASS] Test 5: Coupon validation, min order checks, and discount calculations verified")

    def test_06_checkout_order_placement_and_pdf_qr_bill(self):
        """8, 9, 10, 16: Checkout, order placement, reward points, delivery date, PDF bill with QR"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2  # user@manchis.com
            sess["role"] = "user"
            sess["name"] = "Priya Sharma"
            sess["email"] = "user@manchis.com"

        # 1. Test Mobile Validation: Not entered
        res_no_phone = self.client.post("/api/orders", json={
            "customer_name": "Priya Sharma",
            "customer_email": "user@manchis.com",
            "customer_phone": "",
            "customer_address": "MG Road, Bengaluru",
            "items": [{"id": 1, "name": "Kurta", "price": 1000.0, "quantity": 1}]
        })
        self.assertEqual(res_no_phone.status_code, 400)
        self.assertIn("Mobile number is required", res_no_phone.get_json()["message"])

        # 2. Test Mobile Validation: Less than 10 digits
        res_short_phone = self.client.post("/api/orders", json={
            "customer_name": "Priya Sharma",
            "customer_email": "user@manchis.com",
            "customer_phone": "987654321",  # 9 digits
            "customer_address": "MG Road, Bengaluru",
            "items": [{"id": 1, "name": "Kurta", "price": 1000.0, "quantity": 1}]
        })
        self.assertEqual(res_short_phone.status_code, 400)
        self.assertIn("cannot be less than 10 digits", res_short_phone.get_json()["message"])

        # 3. Test Mobile Validation: Greater than 10 digits
        res_long_phone = self.client.post("/api/orders", json={
            "customer_name": "Priya Sharma",
            "customer_email": "user@manchis.com",
            "customer_phone": "987654321099",  # 12 digits
            "customer_address": "MG Road, Bengaluru",
            "items": [{"id": 1, "name": "Kurta", "price": 1000.0, "quantity": 1}]
        })
        self.assertEqual(res_long_phone.status_code, 400)
        self.assertIn("cannot be greater than 10 digits", res_long_phone.get_json()["message"])

        # 4. Test Mobile Validation: Valid 10-digit number succeeds
        order_payload = {
            "customer_name": "Priya Sharma",
            "customer_email": "user@manchis.com",
            "customer_phone": "9876543210",  # exactly 10 digits
            "customer_address": "Flat 402, Lotus Orchid, MG Road, Bengaluru - 560001",
            "items": [
                {
                    "id": 1,
                    "name": "Royal Rose Anarkali Kurta Set",
                    "price": 1899.0,
                    "quantity": 1
                }
            ],
            "payment_method": "Cash on Delivery",
            "coupon_code": "MANCHI20",
            "points_used": 50
        }

        res = self.client.post("/api/orders", json=order_payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        order_id = data["order_id"]
        self.assertIsNotNone(order_id)
        self.assertIsNotNone(data["estimated_delivery_date"])

        # 5. Verify PDF bill was generated in bills/
        pdf_file = os.path.join(BILLS_DIR, f"MC_Bill_{order_id}.pdf")
        self.assertTrue(os.path.exists(pdf_file))
        self.assertGreater(os.path.getsize(pdf_file), 1000)

        # 6. Test download bill endpoint
        res_bill = self.client.get(f"/api/orders/{order_id}/bill")
        self.assertEqual(res_bill.status_code, 200)
        self.assertEqual(res_bill.mimetype, "application/pdf")

        # 7. Test QR code image endpoint
        res_qr = self.client.get(f"/api/orders/{order_id}/qrcode")
        self.assertEqual(res_qr.status_code, 200)
        self.assertEqual(res_qr.mimetype, "image/png")
        self.assertGreater(len(res_qr.data), 500)

        # 8. Test QR code text content contains 'THANK YOU'
        qr_text = get_order_qr_content({
            "order_id": order_id,
            "customer_name": "Priya Sharma",
            "order_date": "14 Oct 2026, 08:30 PM",
            "final_total": 1469.20,
            "status": "Order Placed",
            "estimated_delivery_date": data["estimated_delivery_date"]
        })
        self.assertIn("THANK YOU FOR SHOPPING AT MANCHI'S!", qr_text)

        print(f"[PASS] Test 6: Mobile validation (empty, <10, >10, =10), Order #{order_id}, Delivery Date, QR Code PNG, and Scannable 'THANK YOU' content verified")

    def test_07_order_tracking_and_timeline(self):
        """14 & 15: Order tracking and stage milestones"""
        # Fetch order list for user
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["role"] = "user"
            sess["name"] = "Priya Sharma"
            sess["email"] = "user@manchis.com"

        res = self.client.get("/api/orders")
        orders = res.get_json()["orders"]
        self.assertGreater(len(orders), 0)
        order_id = orders[0]["order_id"]

        # Track single order
        res_track = self.client.get(f"/api/orders/{order_id}")
        data = res_track.get_json()
        self.assertTrue(data["success"])
        order = data["order"]
        self.assertEqual(order["status"], "Order Placed")
        self.assertGreater(len(order["tracking_history"]), 0)
        print(f"[PASS] Test 7: Order tracking retrieved with stages for #{order_id}")

    def test_08_admin_login_and_order_status_update(self):
        """11, 14: Admin login and order tracking status update"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "admin"
            sess["name"] = "ManChi Admin"
            sess["email"] = "admin@manchis.com"

        res_orders = self.client.get("/api/admin/orders")
        orders = res_orders.get_json()["orders"]
        self.assertGreater(len(orders), 0)
        order_id = orders[0]["order_id"]

        # Update status to 'Shipped'
        res_upd = self.client.put(f"/api/admin/orders/{order_id}/status", json={
            "status": "Shipped",
            "note": "Handed over to BlueDart express courier with Tracking AWB #987654"
        })
        self.assertEqual(res_upd.status_code, 200)
        self.assertTrue(res_upd.get_json()["success"])

        # Verify tracking history now has the new status
        res_track = self.client.get(f"/api/orders/{order_id}")
        track_data = res_track.get_json()["order"]
        self.assertEqual(track_data["status"], "Shipped")
        statuses = [h["status"] for h in track_data["tracking_history"]]
        self.assertIn("Shipped", statuses)
        print(f"[PASS] Test 8: Admin updated order status to 'Shipped', tracking history updated")

    def test_09_admin_product_crud(self):
        """12: Admin Product CRUD (Add, Edit, Delete)"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "admin"

        # Add Product
        res_add = self.client.post("/api/admin/products", json={
            "name": "Designer Velvet Dupatta",
            "category": "Accessories",
            "deal_type": "Ethnic",
            "price": 899.0,
            "original_price": 1499.0,
            "stock": 18,
            "status": "In Stock",
            "delivery_info": "Free delivery in 2 days",
            "image_url": "https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?w=600",
            "description": "Rich velvet dupatta with gold zari embroidery border."
        })
        self.assertEqual(res_add.status_code, 200)
        prod_id = res_add.get_json()["product_id"]

        # Edit Product
        res_edit = self.client.put(f"/api/admin/products/{prod_id}", json={
            "name": "Designer Velvet Royal Dupatta",
            "category": "Accessories",
            "deal_type": "Festival",
            "price": 799.0,
            "original_price": 1499.0,
            "stock": 25,
            "status": "In Stock",
            "delivery_info": "Express delivery in 1 day",
            "image_url": "https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?w=600",
            "description": "Updated luxury velvet dupatta."
        })
        self.assertEqual(res_edit.status_code, 200)

        # Delete Product
        res_del = self.client.delete(f"/api/admin/products/{prod_id}")
        self.assertEqual(res_del.status_code, 200)
        print("[PASS] Test 9: Admin Product CRUD (Create, Edit, Delete) verified")

    def test_10_admin_coupon_crud(self):
        """13: Admin Coupon CRUD"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "admin"

        res_add = self.client.post("/api/admin/coupons", json={
            "code": "DIWALI30",
            "discount_type": "percentage",
            "discount_value": 30.0,
            "min_order_amount": 1000.0,
            "max_discount": 600.0,
            "expiry_date": "2026-11-30",
            "active": 1,
            "description": "Diwali Festival 30% OFF"
        })
        self.assertEqual(res_add.status_code, 200)

        # List Coupons
        res_list = self.client.get("/api/admin/coupons")
        coupons = res_list.get_json()["coupons"]
        diwali_cp = next((c for c in coupons if c["code"] == "DIWALI30"), None)
        self.assertIsNotNone(diwali_cp)

        # Delete Coupon
        res_del = self.client.delete(f"/api/admin/coupons/{diwali_cp['id']}")
        self.assertEqual(res_del.status_code, 200)
        print("[PASS] Test 10: Admin Coupon CRUD verified")

    def test_11_admin_page_loads(self):
        """11: Dedicated /admin page loads with admin login and controls"""
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"ADMIN PORTAL", res.data)
        self.assertIn(b"Administrator Sign In", res.data)
        print("[PASS] Test 11: Dedicated Admin Portal page (/admin) loads successfully")

if __name__ == "__main__":
    unittest.main()
