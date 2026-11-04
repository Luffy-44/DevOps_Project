"""
Zestora – Flask Backend
Online Food Ordering API backed by MongoDB
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING
from bson import ObjectId
from datetime import datetime, timezone
import bcrypt
import jwt
import os
import logging

# ─── App & Config ────────────────────────────────────────────────────────────

app = Flask(__name__)

cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    allowed_origins = ["http://localhost:3000", "http://localhost:3001", "http://localhost:5173", "http://frontend:3000", "*"]

CORS(app, origins=allowed_origins)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URI  = os.getenv("MONGO_URI", "mongodb://mongo:27017/zestora")
JWT_SECRET = os.getenv("JWT_SECRET", "zestora_super_secret_key_change_in_production")

client = MongoClient(MONGO_URI)
db     = client.get_database()

# Collections
users_col   = db["users"]
foods_col   = db["foods"]
orders_col  = db["orders"]
reviews_col = db["reviews"]

# Indexes
users_col.create_index([("email", ASCENDING)], unique=True)
orders_col.create_index([("user_id", ASCENDING)])
reviews_col.create_index([("food_id", ASCENDING)])

# Available Promo Coupons
COUPONS = {
    "AWS20": {"type": "percent", "value": 20, "description": "20% off for AWS Cloud Presentation!"},
    "CLOUD50": {"type": "flat", "value": 50, "description": "₹50 flat off on meals above ₹299"},
    "FREEDEL": {"type": "free_delivery", "value": 40, "description": "Free delivery anywhere in town"},
    "ZESTORA10": {"type": "percent", "value": 10, "description": "10% off welcome bonus"}
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def serial(doc: dict) -> dict:
    """Convert MongoDB ObjectId to string."""
    doc["_id"] = str(doc["_id"])
    return doc


def decode_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "Missing or invalid Authorization header"
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"


def require_auth():
    """Return (user_id, error_response) tuple."""
    payload, err = decode_token(request.headers.get("Authorization"))
    if err:
        return None, (jsonify({"error": err}), 401)
    return payload["sub"], None


# ─── Auth endpoints ───────────────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if users_col.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user = {
        "name":       name,
        "email":      email,
        "password":   hashed,
        "created_at": datetime.now(timezone.utc),
    }
    result = users_col.insert_one(user)
    user_id = str(result.inserted_id)

    token = jwt.encode({"sub": user_id, "email": email}, JWT_SECRET, algorithm="HS256")
    return jsonify({"token": token, "user": {"id": user_id, "name": name, "email": email}}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = users_col.find_one({"email": email})
    if not user or not bcrypt.checkpw(password.encode(), user["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    user_id = str(user["_id"])
    token = jwt.encode({"sub": user_id, "email": email}, JWT_SECRET, algorithm="HS256")
    return jsonify({
        "token": token,
        "user": {"id": user_id, "name": user["name"], "email": email},
    }), 200


@app.route("/api/auth/me", methods=["GET"])
def me():
    user_id, err = require_auth()
    if err:
        return err
    user = users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"id": user_id, "name": user["name"], "email": user["email"]}), 200


# ─── Food / Menu endpoints ───────────────────────────────────────────────────

@app.route("/api/foods", methods=["GET"])
def list_foods():
    category = request.args.get("category", "")
    query = {}
    if category and category.lower() != "all":
        query["category"] = category
    items = [serial(f) for f in foods_col.find(query)]
    return jsonify(items), 200


@app.route("/api/foods/<food_id>", methods=["GET"])
def get_food(food_id):
    try:
        food = foods_col.find_one({"_id": ObjectId(food_id)})
    except Exception:
        return jsonify({"error": "Invalid food id"}), 400
    if not food:
        return jsonify({"error": "Food not found"}), 404
    return jsonify(serial(food)), 200


@app.route("/api/foods", methods=["POST"])
def create_food():
    """Admin endpoint – no auth check for demo simplicity."""
    data = request.get_json(silent=True) or {}
    required = ["name", "category", "price"]
    if not all(k in data for k in required):
        return jsonify({"error": "Required fields: name, category, price"}), 400
    data.setdefault("rating", "4.5")
    data.setdefault("tag", "New")
    data.setdefault("description", "")
    data.setdefault("image", "")
    data.setdefault("color", "#e9f1df")
    result = foods_col.insert_one(data)
    data["_id"] = str(result.inserted_id)
    return jsonify(data), 201


# ─── Cart endpoints ───────────────────────────────────────────────────────────

@app.route("/api/cart", methods=["GET"])
def get_cart():
    """Returns the current user's last active (pending) order as a cart."""
    user_id, err = require_auth()
    if err:
        return err
    order = orders_col.find_one({"user_id": user_id, "status": "pending"}, sort=[("created_at", -1)])
    if not order:
        return jsonify({"items": [], "total": 0}), 200
    return jsonify(serial(order)), 200


# ─── Order endpoints ──────────────────────────────────────────────────────────

@app.route("/api/orders", methods=["POST"])
def place_order():
    user_id, err = require_auth()
    if err:
        return err

    data           = request.get_json(silent=True) or {}
    items          = data.get("items", [])
    address        = data.get("address", "")
    payment_method = data.get("payment_method", "Cash on Delivery")
    coupon_code    = (data.get("coupon_code") or "").strip().upper()

    if not items:
        return jsonify({"error": "Order must contain at least one item"}), 400

    enriched = []
    subtotal = 0.0
    for item in items:
        food_id  = item.get("food_id") or item.get("_id")
        quantity = int(item.get("quantity", 1))
        name     = item.get("name", "Unknown")
        price    = float(item.get("price", 0))

        if food_id:
            try:
                db_food = foods_col.find_one({"_id": ObjectId(str(food_id))})
                if db_food:
                    name  = db_food["name"]
                    price = float(db_food["price"])
            except Exception:
                pass

        item_total = price * quantity
        subtotal  += item_total
        enriched.append({
            "food_id":  str(food_id) if food_id else None,
            "name":     name,
            "price":    price,
            "quantity": quantity,
            "subtotal": item_total,
        })

    # Calculate delivery fee & coupon discount
    delivery_fee = 0 if subtotal >= 499 else 40
    discount = 0.0

    if coupon_code and coupon_code in COUPONS:
        c = COUPONS[coupon_code]
        if c["type"] == "percent":
            discount = round(subtotal * (c["value"] / 100.0), 2)
        elif c["type"] == "flat":
            discount = min(float(c["value"]), subtotal)
        elif c["type"] == "free_delivery":
            delivery_fee = 0

    final_total = max(0.0, round(subtotal + delivery_fee - discount, 2))

    order = {
        "user_id":        user_id,
        "items":          enriched,
        "subtotal":       round(subtotal, 2),
        "delivery_fee":   delivery_fee,
        "discount":       discount,
        "coupon_code":    coupon_code if discount > 0 or (coupon_code == "FREEDEL") else None,
        "total":          final_total,
        "address":        address,
        "payment_method": payment_method,
        "status":         "confirmed", # confirmed -> preparing -> out_for_delivery -> delivered
        "eta_minutes":    25,
        "created_at":     datetime.now(timezone.utc),
        "updated_at":     datetime.now(timezone.utc),
    }
    result = orders_col.insert_one(order)
    order["_id"] = str(result.inserted_id)

    logger.info("Order placed: %s by user %s — Rs.%.2f", order["_id"], user_id, final_total)
    return jsonify(order), 201


# ─── Coupon Validation ────────────────────────────────────────────────────────

@app.route("/api/coupons/validate", methods=["POST"])
def validate_coupon():
    data        = request.get_json(silent=True) or {}
    code        = (data.get("code") or "").strip().upper()
    subtotal    = float(data.get("subtotal", 0.0))

    if not code or code not in COUPONS:
        return jsonify({"valid": False, "error": "Invalid or expired promo code"}), 400

    c = COUPONS[code]
    discount = 0.0
    if c["type"] == "percent":
        discount = round(subtotal * (c["value"] / 100.0), 2)
    elif c["type"] == "flat":
        discount = min(float(c["value"]), subtotal)
    elif c["type"] == "free_delivery":
        discount = 40.0

    return jsonify({
        "valid":       True,
        "code":        code,
        "discount":    discount,
        "type":        c["type"],
        "description": c["description"],
    }), 200


# ─── Order Tracking & Status Update ───────────────────────────────────────────

@app.route("/api/orders/<order_id>/track", methods=["GET"])
def track_order(order_id):
    try:
        order = orders_col.find_one({"_id": ObjectId(order_id)})
    except Exception:
        return jsonify({"error": "Invalid order id"}), 400
    if not order:
        return jsonify({"error": "Order not found"}), 404

    # Calculate status progression based on time created
    created_at = order.get("created_at")
    current_status = order.get("status", "confirmed")

    steps = [
        {"status": "confirmed",        "title": "Order Confirmed",    "icon": "📝", "done": True},
        {"status": "preparing",        "title": "Kitchen Preparing",  "icon": "👨‍🍳", "done": current_status in ["preparing", "out_for_delivery", "delivered"]},
        {"status": "out_for_delivery", "title": "Out for Delivery",   "icon": "🛵", "done": current_status in ["out_for_delivery", "delivered"]},
        {"status": "delivered",        "title": "Delivered",          "icon": "🎉", "done": current_status == "delivered"},
    ]

    return jsonify({
        "order_id":       str(order["_id"]),
        "status":         current_status,
        "eta_minutes":    order.get("eta_minutes", 25),
        "steps":          steps,
        "delivery_rider": {"name": "Rohan Sharma", "phone": "+91 98765 43210", "vehicle": "Honda Activa (MH-02-1234)"},
        "order":          serial(order),
    }), 200


@app.route("/api/orders/<order_id>/status", methods=["PATCH"])
def update_order_status(order_id):
    data       = request.get_json(silent=True) or {}
    new_status = data.get("status")
    allowed    = ["confirmed", "preparing", "out_for_delivery", "delivered", "cancelled"]

    if new_status not in allowed:
        return jsonify({"error": f"Invalid status. Allowed: {allowed}"}), 400

    try:
        res = orders_col.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc)}}
        )
    except Exception:
        return jsonify({"error": "Invalid order id"}), 400

    if res.matched_count == 0:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({"message": f"Order status updated to {new_status}", "status": new_status}), 200


# ─── Reviews & Ratings ────────────────────────────────────────────────────────

@app.route("/api/foods/<food_id>/reviews", methods=["GET"])
def get_food_reviews(food_id):
    reviews = list(reviews_col.find({"food_id": food_id}).sort("created_at", -1))
    for r in reviews:
        r["_id"] = str(r["_id"])
    return jsonify(reviews), 200


@app.route("/api/foods/<food_id>/reviews", methods=["POST"])
def add_food_review(food_id):
    data      = request.get_json(silent=True) or {}
    user_name = data.get("user_name", "Foodie Guest").strip()
    rating    = int(data.get("rating", 5))
    comment   = data.get("comment", "").strip()

    if not comment:
        return jsonify({"error": "Comment cannot be empty"}), 400

    review = {
        "food_id":    food_id,
        "user_name":  user_name,
        "rating":     max(1, min(5, rating)),
        "comment":    comment,
        "created_at": datetime.now(timezone.utc),
    }
    reviews_col.insert_one(review)
    review["_id"] = str(review["_id"])
    return jsonify(review), 201


# ─── Admin Dashboard & Analytics ─────────────────────────────────────────────

@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    all_orders = list(orders_col.find())
    total_revenue = sum(o.get("total", 0.0) for o in all_orders if o.get("status") != "cancelled")
    total_orders  = len(all_orders)
    active_orders = len([o for o in all_orders if o.get("status") in ["confirmed", "preparing", "out_for_delivery"]])

    return jsonify({
        "total_revenue": round(total_revenue, 2),
        "total_orders":  total_orders,
        "active_orders": active_orders,
        "total_foods":   foods_col.count_documents({}),
    }), 200


@app.route("/api/admin/orders", methods=["GET"])
def admin_orders():
    orders = [serial(o) for o in orders_col.find().sort("created_at", -1).limit(50)]
    return jsonify(orders), 200


@app.route("/api/orders", methods=["GET"])
def list_orders():
    user_id, err = require_auth()
    if err:
        return err
    orders = [serial(o) for o in orders_col.find(
        {"user_id": user_id},
        sort=[("created_at", -1)]
    )]
    return jsonify(orders), 200


@app.route("/api/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    user_id, err = require_auth()
    if err:
        return err
    try:
        order = orders_col.find_one({"_id": ObjectId(order_id), "user_id": user_id})
    except Exception:
        return jsonify({"error": "Invalid order id"}), 400
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(serial(order)), 200


@app.route("/api/orders/<order_id>/cancel", methods=["PATCH"])
def cancel_order(order_id):
    user_id, err = require_auth()
    if err:
        return err
    try:
        res = orders_col.update_one(
            {"_id": ObjectId(order_id), "user_id": user_id, "status": "confirmed"},
            {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}},
        )
    except Exception:
        return jsonify({"error": "Invalid order id"}), 400
    if res.matched_count == 0:
        return jsonify({"error": "Order not found or cannot be cancelled"}), 404
    return jsonify({"message": "Order cancelled"}), 200


# ─── Health ───────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    try:
        client.admin.command("ping")
        db_status = "ok"
    except Exception as exc:
        db_status = str(exc)
    return jsonify({"status": "ok", "db": db_status}), 200


# ─── Prometheus Metrics Exporter Endpoint ──────────────────────────────────
@app.route("/api/metrics", methods=["GET"])
def prometheus_metrics():
    """Exports application and system metrics in Prometheus format."""
    total_foods = foods_col.count_documents({})
    total_orders = orders_col.count_documents({})
    active_orders = orders_col.count_documents({"status": {"$in": ["confirmed", "preparing", "out_for_delivery"]}})
    total_reviews = reviews_col.count_documents({})
    
    # Calculate revenue
    pipeline = [{"$match": {"status": {"$ne": "cancelled"}}}, {"$group": {"_id": None, "total": {"$sum": "$total"}}}]
    rev_agg = list(orders_col.aggregate(pipeline))
    revenue = float(rev_agg[0]["total"]) if rev_agg else 0.0

    lines = [
        "# HELP zestora_up Shows whether the Zestora backend application is healthy",
        "# TYPE zestora_up gauge",
        "zestora_up 1",
        "",
        "# HELP zestora_foods_total Total count of food items in catalog",
        "# TYPE zestora_foods_total gauge",
        f"zestora_foods_total {total_foods}",
        "",
        "# HELP zestora_orders_total Total number of orders placed",
        "# TYPE zestora_orders_total counter",
        f"zestora_orders_total {total_orders}",
        "",
        "# HELP zestora_active_orders Number of orders currently being prepared or delivered",
        "# TYPE zestora_active_orders gauge",
        f"zestora_active_orders {active_orders}",
        "",
        "# HELP zestora_revenue_total Total revenue collected in INR",
        "# TYPE zestora_revenue_total counter",
        f"zestora_revenue_total {revenue:.2f}",
        "",
        "# HELP zestora_reviews_total Total customer reviews submitted",
        "# TYPE zestora_reviews_total counter",
        f"zestora_reviews_total {total_reviews}",
        "",
        "# HELP zestora_app_info Application build and version metadata",
        "# TYPE zestora_app_info gauge",
        'zestora_app_info{version="2.0.0",env="production",cloud="aws"} 1',
    ]

    return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4; charset=utf-8"}


# ─── Seed helper (development) ────────────────────────────────────────────────

@app.route("/api/seed", methods=["POST"])
def seed():
    """Seed the DB with sample food items -- call once after first launch."""
    force = request.args.get("force", "false").lower() == "true" or (request.get_json(silent=True) or {}).get("force", False)
    if foods_col.count_documents({}) > 0 and not force:
        return jsonify({"message": "DB already seeded. Pass ?force=true to re-seed."}), 200

    if force:
        foods_col.delete_many({})

    sample_foods = [
        {
            "name": "Ambur Chicken Dum Biryani",
            "category": "South Indian",
            "price": 279,
            "image": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=900&q=85",
            "description": "Aromatic Seeraga Samba rice cooked with tender spiced chicken, mint & boiled egg in traditional Ambur style",
            "rating": "4.9",
            "tag": "Tamil Bestseller ⭐",
            "color": "#fff1dc",
        },
        {
            "name": "Madurai Bun Parotta & Salna",
            "category": "South Indian",
            "price": 169,
            "image": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=900&q=85",
            "description": "Crispy flaky Madurai special multi-layered bun parotta served with piping hot spicy chicken salna",
            "rating": "4.9",
            "tag": "Must Try 🔥",
            "color": "#fef3c7",
        },
        {
            "name": "Chicken Kothu Parotta",
            "category": "South Indian",
            "price": 219,
            "image": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=900&q=85",
            "description": "Shredded crispy parotta beaten on cast-iron tawa with eggs, tender chicken pieces, curry leaves & rich gravy",
            "rating": "4.8",
            "tag": "Street Icon",
            "color": "#fee2e2",
        },
        {
            "name": "Dindigul Mutton Biryani",
            "category": "South Indian",
            "price": 349,
            "image": "https://images.unsplash.com/photo-1633945274405-b6c8069047b0?auto=format&fit=crop&w=900&q=85",
            "description": "Iconic Tamil Nadu delicacy made with short-grain Seeraga Samba rice, tender baby mutton & mild whole spices",
            "rating": "5.0",
            "tag": "Chef Signature 👑",
            "color": "#fed7aa",
        },
        {
            "name": "Chettinad Pepper Chicken Fry",
            "category": "South Indian",
            "price": 249,
            "image": "https://images.unsplash.com/photo-1610057099431-d73a1c9d2f2f?auto=format&fit=crop&w=900&q=85",
            "description": "Fiery dry roast chicken tossed in freshly roasted stone-ground Chettinad pepper masala & crispy curry leaves",
            "rating": "4.8",
            "tag": "Spicy Delight",
            "color": "#ffe4e6",
        },
        {
            "name": "Ghee Podi Roast Dosa",
            "category": "South Indian",
            "price": 149,
            "image": "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=900&q=85",
            "description": "Golden paper-thin crispy fermented rice crepe smeared with fragrant spicy gunpowder podi & pure desi ghee",
            "rating": "4.9",
            "tag": "Crispy Gold",
            "color": "#fef08a",
        },
        {
            "name": "Paneer Butter Masala",
            "category": "Indian",
            "price": 229,
            "image": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=900&q=85",
            "description": "Creamy paneer curry with rich spices",
            "rating": "4.9",
            "tag": "Bestseller",
            "color": "#f8e9d7",
        },
        {
            "name": "Margherita Pizza",
            "category": "Italian",
            "price": 249,
            "image": "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=900&q=85",
            "description": "Classic tomato, mozzarella and basil",
            "rating": "4.7",
            "tag": "10% OFF",
            "color": "#fff0dc",
        },
        {
            "name": "Classic Zest Burger",
            "category": "Burgers",
            "price": 199,
            "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=85",
            "description": "Crispy lettuce, cheese and signature sauce",
            "rating": "4.9",
            "tag": "Must try",
            "color": "#fff0df",
        },
        {
            "name": "Kumbakonam Degree Filter Coffee",
            "category": "Beverages",
            "price": 59,
            "image": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=900&q=85",
            "description": "Authentic South Indian chicory blend filter coffee frothed with thick whole milk in a dabarah",
            "rating": "4.9",
            "tag": "Authentic ☕",
            "color": "#ebd5c1",
        },
        {
            "name": "Chocolate Lava Cake",
            "category": "Desserts",
            "price": 149,
            "image": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=900&q=85",
            "description": "Warm chocolate cake with a soft centre",
            "rating": "4.8",
            "tag": "Popular",
            "color": "#f1e8f4",
        },
    ]
    foods_col.insert_many(sample_foods)
    return jsonify({"message": "Seeded {} food items".format(len(sample_foods))}), 201


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
