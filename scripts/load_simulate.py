"""
Zestora Traffic Simulator
=========================
Simulates realistic user activity on the live EC2 deployment to generate
meaningful Prometheus metrics and Grafana dashboard data.

Usage:
    python scripts/load_simulate.py              # 5 minutes, default settings
    python scripts/load_simulate.py --minutes 15 # run for 15 minutes
    python scripts/load_simulate.py --rounds 50  # run 50 order cycles

What it simulates:
  - Menu browsing (GET /api/foods)
  - Health checks (GET /api/health)
  - Promo code validation (POST /api/coupons/validate)
  - Order placement with varied items and quantities
  - Order status tracking (GET /api/orders/:id/track)
  - Review submissions (POST /api/reviews)
  - Multiple concurrent user sessions (rotating tokens)
"""

import requests
import random
import time
import argparse
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "http://54.234.169.116"
PROMO_CODES = ["AWS20", "CLOUD50", "", "", ""]   # blank = no promo (weighted)
PAYMENT_METHODS = ["UPI", "Cash on Delivery", "Card"]
ADDRESSES = [
    "14, Anna Nagar, Chennai - 600040",
    "7, T. Nagar, Chennai - 600017",
    "22, Velachery Main Road, Chennai - 600042",
    "5, Coimbatore Road, Erode - 638001",
    "88, Madurai Bypass, Madurai - 625002",
    "3, Gandhi Street, Trichy - 620001",
]
USERS = [
    {"name": "Arjun Kumar",    "email": "arjun.k@zestora.com",    "password": "Pass@1234"},
    {"name": "Priya Ramesh",   "email": "priya.r@zestora.com",    "password": "Pass@1234"},
    {"name": "Karthik Selvan", "email": "karthik.s@zestora.com",  "password": "Pass@1234"},
    {"name": "Divya Nair",     "email": "divya.n@zestora.com",    "password": "Pass@1234"},
    {"name": "Surya Prabhu",   "email": "surya.p@zestora.com",    "password": "Pass@1234"},
]
REVIEWS = [
    "Absolutely delicious! Worth every rupee.",
    "Fresh and well-packed. Will order again!",
    "Perfect spice level, authentic taste.",
    "Great quantity, delivered hot and fast.",
    "Best biryani in town, hands down!",
    "Loved it! My go-to order now.",
    "Good but could use more gravy.",
    "Amazing flavors, very authentic.",
    "Quick delivery and tasty food!",
    "Exceeded expectations, 10/10!",
]

# ─── Helpers ─────────────────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def log(symbol, color, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {color}{symbol}{RESET} {msg}", flush=True)

def ok(msg):   log("[OK]  ", GREEN,  msg)
def warn(msg): log("[WARN]", YELLOW, msg)
def err(msg):  log("[ERR] ", RED,    msg)
def info(msg): log("[INFO]", CYAN,   msg)

# ─── Stats tracker ───────────────────────────────────────────────────────────
stats = {
    "health_checks": 0,
    "menu_views": 0,
    "promo_validations": 0,
    "orders_placed": 0,
    "orders_tracked": 0,
    "reviews_submitted": 0,
    "errors": 0,
    "total_revenue": 0,
}

# ─── Auth ─────────────────────────────────────────────────────────────────────
def get_token(user):
    """Register (if new) or login an existing user, return JWT token."""
    # Try login first
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": user["email"], "password": user["password"]
    })
    if r.status_code == 200:
        return r.json().get("token")

    # Register if not found
    r = session.post(f"{BASE_URL}/api/auth/register", json={
        "name": user["name"], "email": user["email"], "password": user["password"]
    })
    if r.status_code == 201:
        ok(f"Registered new user: {user['name']}")
        return r.json().get("token")

    err(f"Auth failed for {user['email']}: {r.text[:100]}")
    return None

# ─── API actions ─────────────────────────────────────────────────────────────
def check_health():
    try:
        r = session.get(f"{BASE_URL}/api/health", timeout=5)
        if r.status_code == 200:
            stats["health_checks"] += 1
            ok(f"Health check OK — {r.json()}")
        else:
            warn(f"Health check returned {r.status_code}")
    except Exception as e:
        err(f"Health check failed: {e}")
        stats["errors"] += 1

def browse_menu():
    """Simulate a user browsing the menu."""
    try:
        r = session.get(f"{BASE_URL}/api/foods", timeout=8)
        if r.status_code == 200:
            foods = r.json()
            stats["menu_views"] += 1
            ok(f"Menu browsed — {len(foods)} items loaded")
            return foods
        warn(f"Menu returned {r.status_code}")
    except Exception as e:
        err(f"Menu browse failed: {e}")
        stats["errors"] += 1
    return []

def validate_promo(token, promo_code, subtotal):
    """Validate a promo code."""
    if not promo_code:
        return 0
    try:
        r = session.post(
            f"{BASE_URL}/api/coupons/validate",
            json={"code": promo_code, "subtotal": subtotal},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        stats["promo_validations"] += 1
        if r.status_code == 200:
            data = r.json()
            discount = data.get("discount", 0)
            ok(f"Promo '{promo_code}' applied — discount: ₹{discount}")
            return discount
        warn(f"Promo '{promo_code}' invalid: {r.text[:80]}")
    except Exception as e:
        err(f"Promo validation failed: {e}")
        stats["errors"] += 1
    return 0

def place_order(token, foods):
    """Place a realistic random order."""
    # Pick 1–4 random items
    num_items = random.randint(1, 4)
    selected = random.sample(foods, min(num_items, len(foods)))
    items = []
    subtotal = 0
    for food in selected:
        qty = random.randint(1, 3)
        items.append({
            "_id":      food["_id"],
            "name":     food["name"],
            "price":    food["price"],
            "quantity": qty,
        })
        subtotal += food["price"] * qty

    promo   = random.choice(PROMO_CODES)
    discount = validate_promo(token, promo, subtotal) if promo else 0
    total   = max(0, subtotal - discount)
    address = random.choice(ADDRESSES)
    payment = random.choice(PAYMENT_METHODS)

    try:
        r = session.post(
            f"{BASE_URL}/api/orders",
            json={
                "items":          items,
                "address":        address,
                "payment_method": payment,
                "coupon_code":    promo,
                "discount":       discount,
                "total":          total,
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if r.status_code in (200, 201):
            data = r.json()
            order_id = data.get("order_id") or data.get("_id") or data.get("id")
            stats["orders_placed"] += 1
            stats["total_revenue"] += total
            item_names = ", ".join(i["name"][:20] for i in items)
            ok(f"Order placed — ₹{total} | {payment} | {item_names[:60]}...")
            return order_id
        err(f"Order failed ({r.status_code}): {r.text[:150]}")
        stats["errors"] += 1
    except Exception as e:
        err(f"Order exception: {e}")
        stats["errors"] += 1
    return None

def track_order(token, order_id):
    """Poll order tracking status."""
    if not order_id:
        return
    try:
        r = session.get(
            f"{BASE_URL}/api/orders/{order_id}/track",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            status = data.get("status", "unknown")
            eta    = data.get("eta_minutes", "?")
            stats["orders_tracked"] += 1
            ok(f"Order {str(order_id)[:8]}... → status: {status} | ETA: {eta} min")
        else:
            warn(f"Track returned {r.status_code}: {r.text[:80]}")
    except Exception as e:
        err(f"Track failed: {e}")
        stats["errors"] += 1

def submit_review(token, food_id, food_name, user_name="Foodie Customer"):
    """Submit a random food review."""
    rating  = random.randint(4, 5)   # authentic positive reviews
    comment = random.choice(REVIEWS)
    try:
        r = session.post(
            f"{BASE_URL}/api/foods/{food_id}/reviews",
            json={
                "user_name": user_name,
                "rating":    rating,
                "comment":   comment,
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        if r.status_code in (200, 201):
            stats["reviews_submitted"] += 1
            ok(f"Review posted — {food_name[:25]} → {rating}⭐ '{comment[:30]}...'")
        else:
            warn(f"Review returned {r.status_code}: {r.text[:80]}")
    except Exception as e:
        err(f"Review failed: {e}")
        stats["errors"] += 1

def advance_order_status(token, order_id):
    """Simulate kitchen staff updating the order status."""
    if not order_id:
        return
    new_status = random.choice(["preparing", "out_for_delivery", "delivered"])
    try:
        r = session.patch(
            f"{BASE_URL}/api/orders/{order_id}/status",
            json={"status": new_status},
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        if r.status_code == 200:
            ok(f"Order {str(order_id)[:8]}... status updated to: {new_status}")
    except Exception as e:
        pass

def check_admin_stats(token):
    """Simulate Kitchen Display / Admin Dashboard polling."""
    try:
        r = session.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        if r.status_code == 200:
            data = r.json()
            ok(f"Admin KDS polled — Revenue: ₹{data.get('total_revenue', 0)} | Orders: {data.get('total_orders', 0)}")
    except Exception:
        pass

# ─── Simulation loop ─────────────────────────────────────────────────────────
def run_simulation(total_minutes=5, rounds=None):
    print()
    print(f"{BOLD}{'='*65}{RESET}")
    print(f"{BOLD}  ZESTORA TRAFFIC SIMULATOR{RESET}")
    print(f"  Target : {BASE_URL}")
    if rounds:
        print(f"  Mode   : {rounds} order rounds")
    else:
        print(f"  Mode   : {total_minutes} minute(s) continuous")
    print(f"{BOLD}{'='*65}{RESET}")
    print()

    # Pre-fetch all tokens
    info("Authenticating all users...")
    tokens = []
    for user in USERS:
        token = get_token(user)
        if token:
            tokens.append((user["name"], token))
    info(f"{len(tokens)} users authenticated\n")

    if not tokens:
        err("No tokens — cannot proceed. Check the API.")
        return

    start_time    = time.time()
    end_time      = start_time + (total_minutes * 60)
    round_count   = 0
    max_rounds    = rounds or 999999

    try:
        while (time.time() < end_time) and (round_count < max_rounds):
            round_count += 1
            user_name, token = random.choice(tokens)

            print(f"\n{BOLD}-- Round {round_count} | User: {user_name} --{RESET}")

            # 1. Health check (every 3 rounds)
            if round_count % 3 == 1:
                check_health()

            # 2. Browse menu (with quick retry)
            foods = browse_menu()
            if not foods:
                time.sleep(1)
                foods = browse_menu()
                if not foods:
                    time.sleep(2)
                    continue

            # 3. Place order
            order_id = place_order(token, foods)
            time.sleep(random.uniform(0.5, 1.0))

            # 4. Track order & advance kitchen status
            if order_id:
                track_order(token, order_id)
                advance_order_status(token, order_id)
                time.sleep(random.uniform(0.8, 1.5))
                track_order(token, order_id)

            # 5. Submit a review (70% chance)
            if foods and random.random() < 0.7:
                reviewed = random.choice(foods)
                submit_review(token, reviewed["_id"], reviewed["name"], user_name=user_name)

            # 6. Check Admin KDS dashboard (every 2 rounds)
            if round_count % 2 == 0:
                check_admin_stats(token)

            # Realistic pause between user actions
            pause = random.uniform(0.8, 2.5)
            info(f"Pausing {pause:.1f}s before next round...")
            time.sleep(pause)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}⚠️  Simulation interrupted by user{RESET}")

    # ─── Final report ────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print()
    print(f"{BOLD}{'='*65}{RESET}")
    print(f"{BOLD}  SIMULATION COMPLETE -- RESULTS{RESET}")
    print(f"{BOLD}{'='*65}{RESET}")
    print(f"  Duration          : {elapsed/60:.1f} minutes ({round_count} rounds)")
    print(f"  Health checks     : {stats['health_checks']}")
    print(f"  Menu views        : {stats['menu_views']}")
    print(f"  Promo validations : {stats['promo_validations']}")
    print(f"  Orders placed     : {stats['orders_placed']}")
    print(f"  Orders tracked    : {stats['orders_tracked']}")
    print(f"  Reviews submitted : {stats['reviews_submitted']}")
    print(f"  Total revenue     : ₹{stats['total_revenue']}")
    print(f"  Errors            : {stats['errors']}")
    print(f"{BOLD}{'='*65}{RESET}")
    print()
    print(f"  {GREEN}Check Grafana for updated metrics:{RESET}")
    print(f"  → http://54.234.169.116/grafana/  (admin/admin)")
    print(f"  → http://54.234.169.116/prometheus/graph")
    print()

# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zestora Traffic Simulator")
    parser.add_argument("--minutes", type=int, default=5,
                        help="How many minutes to run (default: 5)")
    parser.add_argument("--rounds",  type=int, default=None,
                        help="Run exactly N order rounds instead of time-based")
    args = parser.parse_args()

    run_simulation(total_minutes=args.minutes, rounds=args.rounds)
