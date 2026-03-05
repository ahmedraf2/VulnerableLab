from flask import Flask, render_template, request, redirect, session, jsonify, url_for, render_template_string, g
import sqlite3
import hashlib
import os
import requests

app = Flask(__name__)
app.secret_key = "SecretPassword"
app.config["UPLOAD_FOLDER"] = "uploads"


DATABASE = "marketplace.db"

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

# creating tables

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT,
        bio TEXT DEFAULT '',
        role TEXT DEFAULT 'user',
        balance REAL DEFAULT 100.0,
        avatar_url TEXT DEFAULT '/static/img/default_avatar.png'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        price REAL,
        stock INTEGER,
        seller_id INTEGER,
        category TEXT DEFAULT 'general'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        total_price REAL,
        shipping_address TEXT,
        status TEXT DEFAULT 'processing',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        user_id INTEGER,
        body TEXT,
        rating INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        subject TEXT,
        body TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        discount_pct REAL,
        max_uses INTEGER DEFAULT 1,
        times_used INTEGER DEFAULT 0
    )""")

    # Adding Users
    users = [
        ("admin", "admin@marketplace.io", hashlib.md5(b"admin123").hexdigest(), "", "admin", 9999.0),
        ("ahmed", "ahmed@gmail.com", hashlib.md5(b"ahmed2026").hexdigest(), "Hi! I sell electronics.", "seller", 500.0),
        ("adem", "adem@yahoo.com", hashlib.md5(b"adem2026").hexdigest(), "Just a buyer.", "user", 250.0),
        ("douaa", "douaa@hotmail.com", hashlib.md5(b"password123").hexdigest(), "", "user", 100.0),
        ("khayem", "khayem@gmail.com", hashlib.md5(b"SecurePassword").hexdigest(), "", "user", 75.0)
    ]
    for u in users:
        try:
            c.execute("INSERT INTO users (username, email, password, bio, role, balance) VALUES (?,?,?,?,?,?)", u)
        except sqlite3.IntegrityError:
            pass

    products = [
        ("Razer BlackWidow V3", "Mechanical gaming keyboard with RGB lighting and green switches", 139.99, 24, 2, "electronics"),
        ("Sony WH-1000XM5", "Premium noise-cancelling wireless headphones", 349.99, 12, 2, "electronics"),
        ("Logitech MX Master 3S", "Ergonomic wireless mouse for productivity", 99.99, 45, 2, "electronics"),
        ("Samsung T7 SSD 1TB", "Portable external SSD, USB 3.2", 109.99, 30, 2, "electronics"),
        ("Anker 65W Charger", "GaN USB-C fast charger, 3 ports", 35.99, 100, 2, "accessories"),
        ("Cable Management Kit", "Desk cable organizer clips and sleeves", 12.99, 200, 2, "accessories"),
        ("LED Desk Lamp", "Adjustable brightness desk lamp with USB port", 28.99, 60, 2, "accessories"),
        ("Webcam 1080p", "Full HD webcam with built-in microphone", 45.99, 40, 2, "electronics"),
    ]
    for p in products:
        try:
            c.execute("INSERT INTO products (name, description, price, stock, seller_id, category) VALUES (?,?,?,?,?,?)", p)
        except:
            pass

    coupons = [
        ("WELCOME10", 10.0, 999, 0),
        ("VIP50", 50.0, 5, 0),
        ("STAFF100", 100.0, 3, 0),
    ]
    for cp in coupons:
        try:
            c.execute("INSERT INTO coupons (code, discount_pct, max_uses, times_used) VALUES (?,?,?,?)", cp)
        except:
            pass

    conn.commit()
    conn.close()


# -------------------------------------------------------
# helpers
# -------------------------------------------------------
def current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


# -------------------------------------------------------
# routes - pages
# -------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    featured = db.execute("SELECT * FROM products ORDER BY id DESC LIMIT 8").fetchall()
    return render_template("index.html", products=featured, user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", user=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("login.html", user=None, error="Fill in both fields.")

    pw_hash = hashlib.md5(password.encode()).hexdigest()
    db = get_db()

    row = db.execute(
        "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + pw_hash + "'"
    ).fetchone()

    if row:
        session["user_id"] = row["id"]
        session["username"] = row["username"]
        session["role"] = row["role"]
        return redirect("/dashboard")

    return render_template("login.html", user=None, error="Wrong username or password.")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", user=None)

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("register.html", user=None, error="Username and password required.")

    pw_hash = hashlib.md5(password.encode()).hexdigest()
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                   (username, email, pw_hash))
        db.commit()
    except sqlite3.IntegrityError:
        return render_template("register.html", user=None, error="Username taken.")

    return redirect("/login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user = current_user()
    orders = db.execute("""
        SELECT o.*, p.name as product_name
        FROM orders o JOIN products p ON o.product_id = p.id
        WHERE o.buyer_id = ?
        ORDER BY o.created_at DESC
    """, (user["id"],)).fetchall()
    msg_count = db.execute(
        "SELECT COUNT(*) as cnt FROM messages WHERE receiver_id = ? AND is_read = 0",
        (user["id"],)
    ).fetchone()["cnt"]
    return render_template("dashboard.html", user=user, orders=orders, unread=msg_count)


@app.route("/user/<int:uid>")
def user_profile(uid):
    db = get_db()
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if not user_data:
        return "not found", 404
    listings = db.execute("SELECT * FROM products WHERE seller_id = ?", (uid,)).fetchall()
    return render_template("profile.html", profile=user_data, listings=listings, user=current_user())


Black_list = {'role','balance','id','avatar_url'}

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    db = get_db()
    user = current_user()

    if request.method == "POST":
        # just loop over whatever the form sends
        options = request.form.to_dict()
        for field, value in options.items():
            if field.lower() in Black_list:
                continue
            try:
                db.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user["id"]))
            except Exception as e:
                pass  # skip errors
        db.commit()
        return redirect("/settings")

    return render_template("settings.html", user=user)

@app.route("/products")
def products_list():
    db = get_db()
    cat = request.args.get("category", "")
    q = request.args.get("q", "")

    if q:
        rows = db.execute(
            "SELECT * FROM products WHERE name LIKE '%" + q + "%' OR description LIKE '%" + q + "%'"
        ).fetchall()
    elif cat:
        rows = db.execute("SELECT * FROM products WHERE category = ?", (cat,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM products ORDER BY id").fetchall()

    return render_template("products.html", products=rows, user=current_user(), query=q)


@app.route("/product/<int:pid>")
def product_detail(pid):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not product:
        return "not found", 404
    reviews = db.execute("""
        SELECT r.*, u.username FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.product_id = ?
        ORDER BY r.created_at DESC
    """, (pid,)).fetchall()
    seller = db.execute("SELECT username FROM users WHERE id = ?", (product["seller_id"],)).fetchone()
    return render_template("product_detail.html", product=product, reviews=reviews,
                           seller=seller, user=current_user())


@app.route("/product/<int:pid>/review", methods=["POST"])
@login_required
def post_review(pid):
    body = request.form.get("body", "")
    rating = request.form.get("rating", 5)
    db = get_db()
    db.execute("INSERT INTO reviews (product_id, user_id, body, rating) VALUES (?, ?, ?, ?)",
               (pid, session["user_id"], body, rating))
    db.commit()
    return redirect(f"/product/{pid}")


@app.route("/buy/<int:pid>", methods=["POST"])
@login_required
def buy_product(pid):
    db = get_db()
    user = current_user()
    product = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not product:
        return "product not found", 404

    quantity = int(request.form.get("quantity", 1))
    coupon_code = request.form.get("coupon", "").strip()

    unit_price = float(request.form.get("price", product["price"]))
    total = unit_price * quantity

    # coupon logic
    if coupon_code:
        coupon = db.execute("SELECT * FROM coupons WHERE code = ?", (coupon_code,)).fetchone()
        if coupon:
            discount = coupon["discount_pct"] / 100.0
            total = total - (total * discount)
            db.execute("UPDATE coupons SET times_used = times_used + 1 WHERE id = ?", (coupon["id"],))

    if user["balance"] < total and total > 0:
        return render_template("error.html", message="Not enough balance.", user=user)

    db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (total, user["id"]))
    if product["seller_id"]:
        db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (total, product["seller_id"]))

    db.execute("""INSERT INTO orders (buyer_id, product_id, quantity, total_price, shipping_address)
                  VALUES (?, ?, ?, ?, ?)""",
               (user["id"], pid, quantity, total,
                request.form.get("address", "not provided")))
    db.commit()

    return redirect("/dashboard")

@app.route("/order/<int:oid>")
@login_required
def order_detail(oid):
    db = get_db()
    order = db.execute("""
        SELECT o.*, p.name as product_name, u.username as buyer_name, u.email as buyer_email
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users u ON o.buyer_id = u.id
        WHERE o.id = ?
    """, (oid,)).fetchone()
    if not order:
        return "not found", 404
    return render_template("order_detail.html", order=order, user=current_user())


@app.route("/messages")
@login_required
def messages_inbox():
    db = get_db()
    msgs = db.execute("""
        SELECT m.*, u.username as sender_name
        FROM messages m JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = ?
        ORDER BY m.created_at DESC
    """, (session["user_id"],)).fetchall()
    return render_template("messages.html", messages=msgs, user=current_user())


@app.route("/messages/send", methods=["POST"])
@login_required
def send_message():
    receiver = request.form.get("to", "").strip()
    subject = request.form.get("subject", "")
    body = request.form.get("body", "")

    db = get_db()
    recv_user = db.execute("SELECT id FROM users WHERE username = ?", (receiver,)).fetchone()
    if not recv_user:
        return render_template("error.html", message="User not found.", user=current_user())

    db.execute("INSERT INTO messages (sender_id, receiver_id, subject, body) VALUES (?,?,?,?)",
               (session["user_id"], recv_user["id"], subject, body))
    db.commit()
    return redirect("/messages")


@app.route("/seller/preview-banner")
@login_required
def preview_banner():
    text = request.args.get("text", "My Shop")
    color = request.args.get("color", "#3b82f6")
    tpl = f"""
    <div style="background:{color};padding:2rem;border-radius:12px;text-align:center;margin:2rem 0;">
        <h1 style="color:white;margin:0;">{text}</h1>
    </div>
    """
    return render_template_string("""
    {{% extends "base.html" %}}
    {{% block title %}}Banner Preview{{% endblock %}}
    {{% block content %}}
    <h2>Banner Preview</h2>
    <p style="color:#94a3b8;">This is how your shop banner will look:</p>
    {}
    <a href="/dashboard" style="color:#3b82f6;">← back to dashboard</a>
    {{% endblock %}}
    """.format(tpl))


@app.route("/api/check-image")
def check_image_url():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "no url given"}), 400
    try:
        r = requests.get(url, timeout=5)
        ctype = r.headers.get("Content-Type", "")
        return jsonify({
            "url": url,
            "reachable": True,
            "status": r.status_code,
            "content_type": ctype,
            "size": len(r.content),
            "Content": r.json()
        })
    except Exception as e:
        return jsonify({"url": url, "reachable": False, "error": str(e)})


# "protected" Only admin can view this
@app.route("/internal/admin-stats")
def internal_stats():
    if not (session.get('user_id') == 1 or request.remote_addr in ("127.0.0.1", "::1")):
        return jsonify({"error": "Forbidden"}), 403

    db = get_db()
    users = db.execute("SELECT id, username, email, role, balance FROM users").fetchall()
    return jsonify({
        "users": [dict(u) for u in users],
        "total_revenue": db.execute("SELECT SUM(total_price) FROM orders").fetchone()[0] or 0,
        "db_path": os.path.abspath(DATABASE),
        "secret_key": app.secret_key,
    })


# -------------------------------------------------------
# transfer balance between users
# -------------------------------------------------------
@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    if request.method == "GET":
        return render_template("transfer.html", user=current_user())

    recipient = request.form.get("recipient", "").strip()
    amount = float(request.form.get("amount", 0))

    if amount <= 0:
        return render_template("transfer.html", user=current_user(), error="Invalid amount.")

    db = get_db()
    user = current_user()

    if user["balance"] < amount:
        return render_template("transfer.html", user=current_user(), error="Insufficient balance.")

    recv = db.execute("SELECT * FROM users WHERE username = ?", (recipient,)).fetchone()
    if not recv:
        return render_template("transfer.html", user=current_user(), error="User not found.")

    db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user["id"]))
    db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, recv["id"]))
    db.commit()

    return render_template("transfer.html", user=current_user(),
                           success=f"Sent ${amount:.2f} to {recipient}")


# -------------------------------------------------------
# error page
# -------------------------------------------------------
@app.route("/error")
def error_page():
    return render_template("error.html", message="Something went wrong.", user=current_user())


# -------------------------------------------------------
# run
# -------------------------------------------------------
if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
