"""
app.py — ACE Mart e-commerce store built on the UML class models.
Authentication: session-based login for Customers and Admin (Manager/Staff roles).
"""

import sqlite3
import os
import json
import uuid
import hashlib
from datetime import datetime
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    abort,
    session,
    redirect,
    url_for,
)

from models import (
    AccountFactory,
    Manager,
    Catalogue,
    Category,
    Product,
    CreditCardGateway,
    EWalletGateway,
    Payment,
    Shipment,
    Order,
    Invoice,
    Feedback,
    SupportTicket,
    Customer,
    Admin,
    Report,
    ShoppingCart,
    CartItem,
    PaymentGateway,
    Account,
)

app = Flask(__name__)
app.secret_key = "acemart-secret-2024"

SNACK_PRODUCTS = [
    (
        "p-001",
        "Truffle Chips",
        "Black truffle & sea salt kettle chips",
        4.99,
        80,
        "🍟",
        "chips",
    ),
    (
        "p-002",
        "Mango Chili Gummies",
        "Sweet-heat mango gummy bears",
        3.49,
        120,
        "🥭",
        "candy",
    ),
    (
        "p-003",
        "Matcha Pocky",
        "Japanese matcha cream biscuit sticks",
        2.99,
        95,
        "🍵",
        "biscuits",
    ),
    (
        "p-004",
        "Ghost Pepper Puffs",
        "Dangerously spicy corn puffs",
        3.99,
        3,
        "🌶️",
        "chips",
    ),
    (
        "p-005",
        "Birthday Cake Oreos",
        "Limited edition birthday cake filling",
        4.49,
        45,
        "🎂",
        "biscuits",
    ),
    (
        "p-006",
        "Salted Caramel Nuts",
        "Mixed nuts in salted caramel glaze",
        6.99,
        70,
        "🥜",
        "nuts",
    ),
    (
        "p-007",
        "Watermelon Sour Belts",
        "Chewy sour watermelon candy strips",
        2.49,
        150,
        "🍉",
        "candy",
    ),
    (
        "p-008",
        "Wasabi Peas",
        "Crunchy green peas with wasabi kick",
        3.29,
        85,
        "🟢",
        "nuts",
    ),
    (
        "p-009",
        "Cheddar Popcorn",
        "Extra sharp aged cheddar popcorn",
        3.79,
        110,
        "🍿",
        "chips",
    ),
    (
        "p-010",
        "Strawberry Mochi",
        "Soft Japanese rice cake, strawberry cream",
        5.99,
        40,
        "🍓",
        "sweets",
    ),
    (
        "p-011",
        "Dark Choc Almonds",
        "70% dark chocolate coated almonds",
        7.49,
        65,
        "🍫",
        "sweets",
    ),
    (
        "p-012",
        "Tajin Mangonadas",
        "Dried mango with tajin chili lime",
        4.29,
        90,
        "🌮",
        "candy",
    ),
    (
        "p-013",
        "Korean Seaweed Snack",
        "Crispy sesame roasted seaweed sheets",
        2.79,
        130,
        "🌊",
        "biscuits",
    ),
    (
        "p-014",
        "Honey Butter Chips",
        "Korean honey butter flavoured chips",
        4.49,
        75,
        "🍯",
        "chips",
    ),
    (
        "p-015",
        "Pistachio Baklava",
        "Flaky honey-soaked pistachio pastry bites",
        8.99,
        0,
        "🥐",
        "sweets",
    ),
]

# ── SQLite Database Helper Functions ──────────────────────────────────────────


def get_db_connection():
    # Connects directly to a local project file. No server setup needed!
    conn = sqlite3.connect("acemart.db")
    conn.row_factory = sqlite3.Row  # Enables dictionary-like row indexing
    return conn


def init_db():
    """Initializes the database schema inside acemart.db on startup."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_state_to_db():
    store = get_store()
    if not store:
        return

    mgr = Manager.get_instance()

    # 1. Serialize Products
    products_data = [p.to_dict() for p in mgr.products]

    # 2. Serialize Categories
    categories_data = [c.to_dict() for c in store["categories"].values()]

    # 3. Serialize Accounts (Customers and Admins)
    accounts_data = []
    for acc in store["accounts"].values():
        acc_dict = acc.to_dict()
        acc_dict["password_hash"] = acc.password_hash
        if isinstance(acc, Customer):
            acc_dict["addresses"] = acc.addresses
            acc_dict["notifications"] = acc.notifications
            acc_dict["support_tickets"] = [t.to_dict() for t in acc.support_tickets]
            # Serialize active shopping cart items
            cart = acc.get_or_create_cart()
            acc_dict["shopping_cart"] = cart.to_dict() if cart else None
        accounts_data.append(acc_dict)

    # 4. Serialize Orders (including nested payments & shipments)
    orders_data = []
    for o in mgr.orders:
        o_dict = o.to_dict()
        o_dict["payments"] = [p.to_dict() for p in o.payments]
        o_dict["shipments"] = [s.to_dict() for s in o.shipments]
        o_dict["feedback"] = o.feedback.to_dict() if o.feedback else None
        orders_data.append(o_dict)

    # 5. Serialize Notifications
    alerts_data = {
        "staff_notifications": mgr.staff_notifications,
        "manager_notifications": mgr.manager_notifications,
    }

    # 6. Serialize Reports
    reports_data = [r.to_dict() for r in mgr.reports]

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql = (
            "INSERT OR REPLACE INTO store_state (state_key, state_value) VALUES (?, ?)"
        )
        cursor.execute(sql, ("products", json.dumps(products_data)))
        cursor.execute(sql, ("categories", json.dumps(categories_data)))
        cursor.execute(sql, ("accounts", json.dumps(accounts_data)))
        cursor.execute(sql, ("orders", json.dumps(orders_data)))
        cursor.execute(sql, ("alerts", json.dumps(alerts_data)))
        cursor.execute(sql, ("reports", json.dumps(reports_data)))
        conn.commit()
    except Exception as e:
        print("Failed to save state to SQLite database:", e)
    finally:
        conn.close()


def load_state_from_db() -> bool:
    """Loads and reconstructs python object graphs from SQLite. Returns False if DB is empty."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM store_state")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        print("Database read error:", e)
        return False

    if not rows:
        return False

    # Reconstruct dict from SQLite Rows
    state = {row["state_key"]: json.loads(row["state_value"]) for row in rows}

    Manager.reset()
    mgr = Manager.get_instance()

    # 1. Reconstruct Products
    products = {}
    for p_dict in state.get("products", []):
        p = Product(
            p_dict["product_id"],
            p_dict["name"],
            p_dict["description"],
            p_dict["price"],
            p_dict["stock_quantity"],
        )
        p.image_url = p_dict["image_url"]
        p.category_id = p_dict["category_id"]
        p.is_active = p_dict.get("is_active", True)
        mgr.manage_product(p)
        products[p.product_id] = p

    # 2. Reconstruct Categories
    categories = {}
    for c_dict in state.get("categories", []):
        c = Category(c_dict["category_id"], c_dict["name"], c_dict["description"])
        c.is_active = c_dict.get("is_active", True)
        for p_dict in c_dict.get("products", []):
            p = products.get(p_dict["product_id"])
            if p:
                c.add_product(p)
        categories[c.category_id] = c

    # 3. Reconstruct Accounts (Customers and Admins)
    accounts = {}
    for a_dict in state.get("accounts", []):
        email = a_dict["email"]
        if "role" in a_dict:
            acc = AccountFactory.create(
                "admin", a_dict["username"], email, "dummy", role=a_dict["role"]
            )
        else:
            acc = AccountFactory.create(
                "customer",
                a_dict["username"],
                email,
                "dummy",
                phone=a_dict["phone"],
                address=a_dict["address"],
            )
            acc.addresses = a_dict.get(
                "addresses", [acc.address] if acc.address else []
            )
            acc.notifications = a_dict.get("notifications", [])

            cart_data = a_dict.get("shopping_cart")
            if cart_data and "items" in cart_data:
                cart = acc.get_or_create_cart()
                for item_dict in cart_data["items"]:
                    p = products.get(item_dict["product_id"])
                    if p:
                        cart.items[p.product_id] = CartItem(p, item_dict["quantity"])

        acc.account_id = a_dict["account_id"]
        acc.password_hash = a_dict["password_hash"]
        if a_dict.get("created_at"):
            try:
                acc.created_at = datetime.fromisoformat(a_dict["created_at"])
            except Exception:
                pass
        accounts[email] = acc

    # 4. Reconstruct Orders, Invoices, Payments, Shipments, and Feedbacks
    for o_dict in state.get("orders", []):
        cust_email = next(
            (
                email
                for email, acc in accounts.items()
                if acc.account_id == o_dict["customer_id"]
            ),
            None,
        )
        customer = accounts.get(cust_email)
        if not customer:
            continue

        order_items = []
        for item_dict in o_dict["items"]:
            p = products.get(item_dict["product_id"])
            if p:
                order_items.append(CartItem(p, item_dict["quantity"]))

        order = Order(o_dict["order_id"], customer, order_items)
        order.status = o_dict["status"]
        order.total_amount = o_dict["total_amount"]
        if o_dict.get("placed_at"):
            try:
                order.placed_at = datetime.fromisoformat(o_dict["placed_at"])
            except Exception:
                pass

        if o_dict.get("invoice_id"):
            order.generate_invoice()
            order.invoice.invoice_id = o_dict["invoice_id"]
            order.invoice.is_paid = o_dict.get("is_paid", False)

        for p_dict in o_dict.get("payments", []):
            gw_name = p_dict["gateway"]
            if "CreditCard" in gw_name:
                gw = CreditCardGateway(p_dict.get("card_masked", "****"), "00/00")
            else:
                gw = EWalletGateway("wallet", p_dict.get("provider", "TouchNGo"))
            pmt = Payment(p_dict["payment_id"], order, p_dict["amount"], gw)
            pmt.status = p_dict["status"]
            pmt.transaction_id = p_dict.get("transaction_id")
            order.add_payment(pmt)

        for s_dict in o_dict.get("shipments", []):
            ship = Shipment(
                s_dict["shipment_id"],
                order,
                s_dict["carrier"],
                s_dict["tracking_number"],
                s_dict["destination_address"],
            )
            ship.status = s_dict["status"]
            if s_dict.get("shipped_at"):
                try:
                    ship.shipped_at = datetime.fromisoformat(s_dict["shipped_at"])
                except Exception:
                    pass
            if s_dict.get("delivered_at"):
                try:
                    ship.delivered_at = datetime.fromisoformat(s_dict["delivered_at"])
                except Exception:
                    pass
            order.shipments.append(ship)

        if o_dict.get("feedback"):
            f_dict = o_dict["feedback"]
            order.receive_feedback(f_dict["rating"], f_dict["comment"])
            order.feedback.feedback_id = f_dict["feedback_id"]
            if f_dict.get("submitted_at"):
                try:
                    order.feedback.submitted_at = datetime.fromisoformat(
                        f_dict["submitted_at"]
                    )
                except Exception:
                    pass
            customer.feedback_list.append(order.feedback)

        customer.orders.append(order)
        mgr.orders.append(order)

    # 5. Reconstruct Support Tickets
    for a_dict in state.get("accounts", []):
        email = a_dict["email"]
        customer = accounts.get(email)
        if not customer:
            continue
        for t_dict in a_dict.get("support_tickets", []):
            ticket = customer.raise_support_ticket(
                t_dict["subject"], t_dict["description"]
            )
            ticket.ticket_id = t_dict["ticket_id"]
            ticket.status = t_dict["status"]
            ticket.resolution_notes = t_dict.get("resolution_notes", "")
            if t_dict.get("created_at"):
                try:
                    ticket.created_at = datetime.fromisoformat(t_dict["created_at"])
                except Exception:
                    pass
            if t_dict.get("resolved_at"):
                try:
                    ticket.resolved_at = datetime.fromisoformat(t_dict["resolved_at"])
                except Exception:
                    pass
            if t_dict.get("assigned_to"):
                admin_email = next(
                    (
                        email
                        for email, acc in accounts.items()
                        if acc.username == t_dict["assigned_to"]
                    ),
                    None,
                )
                admin_acc = accounts.get(admin_email)
                if admin_acc:
                    ticket.assign(admin_acc)
            if t_dict.get("order_id"):
                order = next(
                    (o for o in mgr.orders if o.order_id == t_dict["order_id"]), None
                )
                if order:
                    ticket.order = order
                    order.support_tickets.append(ticket)

    # 6. Reconstruct Notifications
    alerts_data = state.get("alerts", {})
    mgr.staff_notifications = alerts_data.get("staff_notifications", [])
    mgr.manager_notifications = alerts_data.get("manager_notifications", [])

    # 7. Reconstruct Reports
    for r_dict in state.get("reports", []):
        admin_name = r_dict.get("requested_by")
        # Find the Admin who compiled this report
        admin_acc = next(
            (acc for acc in accounts.values() if acc.username == admin_name), None
        )
        try:
            gen_time = datetime.fromisoformat(r_dict["generated_at"])
        except Exception:
            gen_time = datetime.now()

        # Parse start and end date boundaries safely (CRC 4.19)
        try:
            s_date = datetime.fromisoformat(r_dict["start_date"])
            e_date = datetime.fromisoformat(r_dict["end_date"])
        except Exception:
            s_date = datetime(2000, 1, 1)
            e_date = datetime.now()

        report = Report(
            r_dict["report_id"],
            r_dict["report_type"],
            gen_time,
            r_dict["data"],
            admin_acc,
            s_date,
            e_date,
        )
        mgr.reports.append(report)

    catalogue = Catalogue("main", "ACE Mart Store")
    for cat in categories.values():
        catalogue.add_category(cat)

    app.config["STORE"] = {
        "catalogue": catalogue,
        "customer": accounts.get("alex@acemart.com"),
        "admin": accounts.get("sam@acemart.com"),
        "staff": accounts.get("lee@acemart.com"),
        "products": products,
        "categories": categories,
        "accounts": accounts,
    }
    return True


# ── Helpers ───────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_store():
    return app.config.get("STORE", {})


def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    store = get_store()
    accounts = store.get("accounts", {})
    for acc in accounts.values():
        if acc.account_id == uid:
            return acc
    session.clear()
    return None


def login_required_customer(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_role") != "customer" or not session.get("user_id"):
            session["next"] = request.url
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)

    return decorated


def login_required_admin(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_role") not in (
            "admin",
            "manager",
            "staff",
        ) or not session.get("user_id"):
            session["next"] = request.url
            return redirect(url_for("login_page") + "?mode=staff")
        return f(*args, **kwargs)

    return decorated


# ── Seed data ─────────────────────────────────────────────────────────────────


@app.before_request
def ensure_seeded():
    """Ensures memory state remains populated during Flask live-reloads."""
    if not app.config.get("STORE"):
        try:
            loaded = load_state_from_db()
            if not loaded:
                seed_data()
        except Exception as e:
            print("Before-request load failed. Defaulting to memory seed. Error:", e)
            seed_data()


def seed_data():
    Manager.reset()
    mgr = Manager.get_instance()

    customer = AccountFactory.create(
        "customer",
        "Alex Kim",
        "alex@acemart.com",
        "pw1234",
        phone="555-0101",
        address="42 Crunch Lane",
    )
    # Seed multiple sample addresses
    customer.addresses = [
        "42 Crunch Lane",
        "Suite 4B, 100 Gourmet Blvd",
        "Snack Locker #12, Railway St",
    ]
    admin = AccountFactory.create(
        "admin", "Sam Store", "sam@acemart.com", "admin123", role="manager"
    )
    staff = AccountFactory.create(
        "admin", "Lee Staff", "lee@acemart.com", "staff123", role="staff"
    )

    categories = {
        "chips": Category("c-01", "Chips & Crisps", "Crunchy, salty, irresistible"),
        "candy": Category("c-02", "Candy & Gummies", "Sweet, sour, chewy & wild"),
        "biscuits": Category("c-03", "Biscuits & Sticks", "Cookies, crackers & more"),
        "nuts": Category("c-04", "Nuts & Seeds", "Roasted, spiced & glazed"),
        "sweets": Category("c-05", "Sweets & Chocolate", "Indulgent treats & desserts"),
    }

    products = {}
    for pid, name, desc, price, stock, emoji, cat_key in SNACK_PRODUCTS:
        p = Product(pid, name, desc, price, stock)
        p.image_url = emoji
        categories[cat_key].add_product(p)
        mgr.manage_product(p)
        products[pid] = p

    catalogue = Catalogue("main", "ACE Mart Store")
    for cat in categories.values():
        catalogue.add_category(cat)

    app.config["STORE"] = {
        "catalogue": catalogue,
        "customer": customer,
        "admin": admin,
        "staff": staff,
        "products": products,
        "categories": categories,
        "accounts": {
            customer.email: customer,
            admin.email: admin,
            staff.email: staff,
        },
    }


@app.after_request
def auto_save_to_db(response):
    """Automatically persist state to SQLite after any modifying API request."""
    if request.method in ["POST", "PUT", "DELETE"]:
        try:
            save_state_to_db()
        except Exception as e:
            print("Auto-save state to SQLite failed:", e)
    return response


# ── Auth Routes ───────────────────────────────────────────────────────────────


@app.route("/login")
def login_page():
    if get_current_user():
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role_hint = data.get("role", "customer")
    staff_role = data.get("staff_role", "manager")

    if not email or not password:
        return (
            jsonify({"success": False, "error": "Email and password are required"}),
            400,
        )

    store = get_store()
    accounts = store.get("accounts", {})
    account = accounts.get(email)

    if not account:
        return (
            jsonify({"success": False, "error": "No account found with that email"}),
            401,
        )
    if not account.is_active:
        return (
            jsonify({"success": False, "error": "This account has been deactivated"}),
            403,
        )
    if account.password_hash != hash_password(password):
        return jsonify({"success": False, "error": "Incorrect password"}), 401

    is_customer = isinstance(account, Customer)
    is_admin = isinstance(account, Admin)

    if role_hint == "customer" and not is_customer:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "This is a staff account. Use the Staff tab.",
                }
            ),
            403,
        )
    if role_hint == "admin" and not is_admin:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "This is a customer account. Use the Shopper tab.",
                }
            ),
            403,
        )

    session["user_id"] = account.account_id
    session["username"] = account.username
    if is_admin:
        session["user_role"] = account.role  # "manager" or "staff"
        redirect_url = "/admin"
    else:
        session["user_role"] = "customer"
        redirect_url = session.pop("next", "/")

    return jsonify(
        {
            "success": True,
            "username": account.username,
            "role": session["user_role"],
            "redirect": redirect_url,
        }
    )


@app.route("/api/auth/signup", methods=["POST"])
def api_signup():
    data = request.get_json(force=True) or {}
    name = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()
    pw = data.get("password", "")

    if not name:
        return jsonify({"success": False, "error": "Name cannot be blank"}), 400
    if not email or "@" not in email:
        return jsonify({"success": False, "error": "Enter a valid email address"}), 400
    if not address:
        return jsonify({"success": False, "error": "Delivery address is required"}), 400
    if len(pw) < 6:
        return (
            jsonify(
                {"success": False, "error": "Password must be at least 6 characters"}
            ),
            400,
        )

    store = get_store()
    accounts = store.get("accounts", {})
    if email in accounts:
        return (
            jsonify(
                {"success": False, "error": "An account with that email already exists"}
            ),
            409,
        )

    new_customer = AccountFactory.create(
        "customer", name, email, pw, phone=phone, address=address
    )
    accounts[email] = new_customer
    session["user_id"] = new_customer.account_id
    session["username"] = new_customer.username
    session["user_role"] = "customer"

    return (
        jsonify({"success": True, "username": new_customer.username, "redirect": "/"}),
        201,
    )


# ── Page Routes ───────────────────────────────────────────────────────────────


@app.route("/")
def index():
    store = get_store()
    mgr = Manager.get_instance()
    cat_filter = request.args.get("category", "all")
    search_q = request.args.get("q", "").strip()

    if search_q:
        products = store["catalogue"].search(search_q)
    elif cat_filter != "all":
        cat = next(
            (c for c in store["catalogue"].categories if c.category_id == cat_filter),
            None,
        )
        products = cat.products if cat else []
    else:
        products = store["catalogue"].all_products()

    # Filter out inactive products so shoppers cannot see them
    products = [p for p in products if p.is_active]

    current_user = get_current_user()
    customer = current_user if isinstance(current_user, Customer) else None
    cart = customer.get_or_create_cart() if customer else None

    return render_template(
        "store.html",
        catalogue=store["catalogue"],
        products=products,
        categories=store["catalogue"].categories,
        cat_filter=cat_filter,
        search_q=search_q,
        cart=cart,
        customer=customer,
        is_logged_in=current_user is not None,
        user_role=session.get("user_role", ""),
    )


@app.route("/cart")
@login_required_customer
def cart_page():
    customer = get_current_user()
    cart = customer.get_or_create_cart()
    return render_template("cart.html", cart=cart, customer=customer)


@app.route("/payment")
@login_required_customer
def payment_page():
    """Standalone payment page — used by payment.html standalone flow."""
    customer = get_current_user()
    cart = customer.get_or_create_cart()
    if not cart.items:
        return redirect(url_for("cart_page"))
    return render_template("payment.html", cart=cart, customer=customer)


@app.route("/orders")
@login_required_customer
def orders_page():
    mgr = Manager.get_instance()
    customer = get_current_user()
    my_orders = [o for o in mgr.orders if o.customer.account_id == customer.account_id]
    return render_template("orders.html", orders=my_orders, customer=customer)


@app.route("/support")
@login_required_customer
def support_page():
    mgr = Manager.get_instance()
    customer = get_current_user()
    my_orders = [o for o in mgr.orders if o.customer.account_id == customer.account_id]
    return render_template(
        "support.html",
        customer=customer,
        tickets=customer.support_tickets,
        orders=my_orders,
    )


@app.route("/admin")
@login_required_admin
def admin_page():
    store = get_store()
    mgr = Manager.get_instance()
    admin = get_current_user()

    # 1. Active Products Count (where p.is_active is True)
    active_products_count = sum(1 for p in mgr.products if p.is_active)

    # 2. Ongoing Orders Count (excluding delivered, cancelled, and refunded finalized states)
    ongoing_orders_count = sum(
        1 for o in mgr.orders if o.status in ("pending", "processing", "shipped")
    )

    # Support Tickets parsing
    all_tickets = []
    for o in mgr.orders:
        all_tickets.extend(o.support_tickets)
    for acc in store["accounts"].values():
        if isinstance(acc, Customer):
            all_tickets.extend(acc.support_tickets)
    seen, unique_tickets = set(), []
    for t in all_tickets:
        if t.ticket_id not in seen:
            unique_tickets.append(t)
            seen.add(t.ticket_id)

    # 3. Ongoing Tickets Count (where status is open or in_progress)
    ongoing_tickets_count = sum(1 for t in unique_tickets if t.status == "open")

    # 4. Feedback rating compiled
    feedbacks = [o.feedback for o in mgr.orders if o.feedback]

    # 5. Inventory reports compiled
    out_of_stock = [p for p in mgr.products if p.stock_quantity == 0]

    staff_members = [
        acc for acc in store["accounts"].values() if isinstance(acc, Admin)
    ]

    return render_template(
        "admin.html",
        admin=admin,
        manager=mgr,
        catalogue=store["catalogue"],
        products=mgr.products,
        categories=store["catalogue"].categories,
        orders=mgr.orders,
        tickets=unique_tickets,
        feedbacks=feedbacks,
        staff_role=session.get("user_role", "admin"),
        staff_members=staff_members,
        # Pass the updated KPI counts to the template
        active_products_count=active_products_count,
        ongoing_orders_count=ongoing_orders_count,
        ongoing_tickets_count=ongoing_tickets_count,
        new_reviews_count=len(feedbacks),
        out_of_stock_count=len(out_of_stock),
    )


# ── Cart API ──────────────────────────────────────────────────────────────────


@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    if session.get("user_role") != "customer":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Please log in to add items to cart",
                    "login_required": True,
                }
            ),
            401,
        )

    data = request.get_json(force=True) or {}
    product_id = data.get("product_id", "").strip()
    quantity = data.get("quantity", 1)
    if not product_id:
        return jsonify({"success": False, "error": "product_id is required"}), 400
    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError
    except (ValueError, TypeError):
        return (
            jsonify({"success": False, "error": "quantity must be a positive integer"}),
            400,
        )

    mgr = Manager.get_instance()
    customer = get_current_user()
    catalogue = get_store()["catalogue"]
    p = next((p for p in mgr.products if p.product_id == product_id), None)
    if not p:
        return jsonify({"success": False, "error": "Product not found"}), 404
    cart = customer.get_or_create_cart()
    ok = cart.add_product(p, quantity, catalogue=catalogue)
    if not ok:
        return jsonify({"success": False, "error": "Product is out of stock"}), 409
    return jsonify(
        {"success": True, "item_count": cart.item_count(), "total": cart.total()}
    )


@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():
    if session.get("user_role") != "customer":
        return jsonify({"success": False, "error": "Not logged in"}), 401
    data = request.get_json(force=True) or {}
    product_id = data.get("product_id", "").strip()
    customer = get_current_user()
    cart = customer.get_or_create_cart()
    ok = cart.remove_product(product_id)
    return jsonify(
        {"success": ok, "item_count": cart.item_count(), "total": cart.total()}
    )


@app.route("/api/cart/update", methods=["POST"])
def api_cart_update():
    if session.get("user_role") != "customer":
        return jsonify({"success": False, "error": "Not logged in"}), 401
    data = request.get_json(force=True) or {}
    product_id = data.get("product_id", "").strip()
    quantity = data.get("quantity", 1)
    try:
        quantity = int(quantity)
    except:
        return jsonify({"success": False, "error": "quantity must be an integer"}), 400
    customer = get_current_user()
    cart = customer.get_or_create_cart()
    ok = cart.update_quantity(product_id, quantity)

    if not ok:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Requested quantity exceeds available stock",
                }
            ),
            409,
        )

    return jsonify(
        {"success": True, "item_count": cart.item_count(), "total": cart.total()}
    )


@app.route("/api/cart/checkout", methods=["POST", "GET"])
def api_checkout():
    if request.method == "GET":
        return jsonify({"error": "Use POST to checkout"}), 405
    if session.get("user_role") != "customer":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Please log in to checkout",
                    "login_required": True,
                }
            ),
            401,
        )
    customer = get_current_user()
    if not customer:
        session.clear()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Session expired. Please log in again.",
                    "login_required": True,
                }
            ),
            401,
        )
    mgr = Manager.get_instance()
    cart = customer.get_or_create_cart()
    if not cart.items:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Cart is empty. Add items before checking out.",
                }
            ),
            400,
        )

    order = cart.convert_to_order()
    if not order:
        return (
            jsonify(
                {"success": False, "error": "Insufficient stock for one or more items"}
            ),
            409,
        )

    customer.orders.append(order)
    mgr.process_order(order)
    order.generate_invoice()

    # Trigger Staff Notification
    mgr.add_staff_notification(
        f"🛍️ New Order #{order.order_id[:8].upper()} placed by {customer.username}!"
    )

    # Calculate grand total including shipping to return to frontend gateways
    shipping = 0 if order.total_amount >= 25 else 3.99
    grand_total = round(order.total_amount + shipping, 2)

    return jsonify(
        {"success": True, "order_id": order.order_id, "total": grand_total}
    )  # Return grand_total


@app.route("/api/cart")
def api_cart():
    customer = get_current_user()
    if not customer or not isinstance(customer, Customer):
        return jsonify({"items": [], "total": 0, "item_count": 0})
    return jsonify(customer.get_or_create_cart().to_dict())


# ── Product / Order APIs ──────────────────────────────────────────────────────


@app.route("/api/products")
def api_products():
    return jsonify([p.to_dict() for p in Manager.get_instance().products])


@app.route("/api/orders")
def api_orders():
    return jsonify([o.to_dict() for o in Manager.get_instance().orders])


# ── Admin APIs ────────────────────────────────────────────────────────────────


@app.route("/api/admin/product/add", methods=["POST"])
@login_required_admin
def api_admin_add_product():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can add products.",
                }
            ),
            403,
        )
    store = get_store()
    admin = get_current_user()
    mgr = Manager.get_instance()
    data = request.get_json(force=True) or {}
    name = data.get("name", "").strip()
    desc = data.get("description", "").strip()
    cat_id = data.get("category_id", "").strip()
    emoji = data.get("emoji", "📦").strip() or "📦"
    if not name:
        return jsonify({"success": False, "error": "Product name cannot be blank"}), 400
    if not cat_id:
        return jsonify({"success": False, "error": "Category is required"}), 400
    try:
        price = float(data.get("price", 0))
        if price <= 0:
            raise ValueError
    except:
        return (
            jsonify({"success": False, "error": "Price must be a positive number"}),
            400,
        )
    try:
        stock = int(data.get("stock", 0))
        if stock < 0:
            raise ValueError
    except:
        return jsonify({"success": False, "error": "Stock must be non-negative"}), 400
    category = store["catalogue"].get_category(cat_id)
    if not category:
        return jsonify({"success": False, "error": "Category not found"}), 404
    p = Product("p-" + str(uuid.uuid4())[:6], name, desc, round(price, 2), stock)
    p.image_url = emoji
    category.add_product(p)
    admin.add_product(p)
    mgr.manage_product(p)
    return jsonify({"success": True, "product": p.to_dict()}), 201


@app.route("/api/admin/product/restock", methods=["POST"])
@login_required_admin
def api_admin_restock():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can restock products.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    pid = data.get("product_id", "").strip()
    if not pid:
        return jsonify({"success": False, "error": "product_id is required"}), 400
    try:
        qty = int(data.get("quantity", 0))
        if qty <= 0:
            raise ValueError
    except:
        return (
            jsonify({"success": False, "error": "quantity must be a positive integer"}),
            400,
        )
    p = next((p for p in Manager.get_instance().products if p.product_id == pid), None)
    if not p:
        return jsonify({"success": False, "error": "Product not found"}), 404
    p.restock(qty)
    return jsonify({"success": True, "product": p.to_dict()})


@app.route("/api/admin/product/remove", methods=["POST"])
@login_required_admin
def api_admin_remove_product():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can delete products.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    pid = data.get("product_id", "").strip()
    if not pid:
        return jsonify({"success": False, "error": "product_id is required"}), 400
    store = get_store()
    for cat in store["catalogue"].categories:
        cat.remove_product(pid)
    get_current_user().remove_product(pid)
    ok = Manager.get_instance().remove_product(pid)
    return jsonify({"success": ok})


@app.route("/api/admin/report/<report_type>")
@login_required_admin
def api_admin_report(report_type):
    if report_type not in {"inventory", "orders", "sales", "feedback", "support"}:
        return jsonify({"error": "Unknown report type"}), 400

    period = request.args.get("period", "all").strip().lower()
    compile_new = request.args.get("compile", "false").strip().lower() == "true"

    # Calculate period date boundaries dynamically (CRC 4.19)
    from datetime import datetime, timedelta

    end_date = datetime.now()

    if period == "day":
        start_date = end_date - timedelta(days=1)
    elif period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    elif period == "ytd":
        start_date = datetime(end_date.year, 1, 1)
    else:
        start_date = datetime(2000, 1, 1)  # All time

    admin = get_current_user()
    mgr = Manager.get_instance()

    if admin.role == "manager":
        if compile_new:
            # Compiles a brand new, fresh report version
            report = mgr.create_report(
                report_type,
                requested_by=admin,
                start_date=start_date,
                end_date=end_date,
            )
            mgr.add_staff_notification(
                f'📊 Manager ({admin.username}) has compiled the latest "{report_type.upper()}" ({period.upper()}) report. You can now view the updated metrics!'
            )
            save_state_to_db()
        else:
            # Just view/retrieve the latest compiled report from memory/database
            report = mgr.get_latest_report(report_type)
            if not report:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "No report of this type has been compiled by the Manager yet. Click 'Compile New' to generate the first version.",
                        }
                    ),
                    404,
                )
        return jsonify(report.to_dict())
    else:
        # Standard staff can only view/request the latest compiled report from the Manager
        report = mgr.get_latest_report(report_type)
        if not report:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No report of this type has been compiled by the Manager yet. Standard staff cannot trigger new compilations.",
                    }
                ),
                404,
            )
        return jsonify(report.to_dict())


@app.route("/api/admin/ticket/assign", methods=["POST"])
@login_required_admin
def api_admin_assign_ticket():
    data = request.get_json(force=True) or {}
    tid = data.get("ticket_id", "").strip()
    assignee_id = data.get("assignee_id", "").strip()

    if not tid:
        return jsonify({"success": False, "error": "ticket_id is required"}), 400

    # Role Enforcement: Only managers are allowed to assign tickets
    admin = get_current_user()
    if admin.role != "manager":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only managers can assign tickets.",
                }
            ),
            403,
        )

    store = get_store()

    # Locate the target assignee (staff member)
    assignee = None
    for acc in store["accounts"].values():
        if acc.account_id == assignee_id:
            assignee = acc
            break
    if not assignee:
        assignee = admin  # Fallback to self-assignment

    ticket = None
    for acc in store["accounts"].values():
        if isinstance(acc, Customer):
            ticket = next((t for t in acc.support_tickets if t.ticket_id == tid), None)
            if ticket:
                break
    if not ticket:
        return jsonify({"success": False, "error": "Ticket not found"}), 404

    ticket.assign(assignee)
    return jsonify({"success": True, "ticket": ticket.to_dict()})


@app.route("/api/admin/ticket/resolve", methods=["POST"])
@login_required_admin
def api_admin_resolve_ticket():
    data = request.get_json(force=True) or {}
    tid = data.get("ticket_id", "").strip()
    notes = data.get("notes", "").strip()
    if not tid:
        return jsonify({"success": False, "error": "ticket_id is required"}), 400
    if not notes:
        return (
            jsonify({"success": False, "error": "Resolution notes cannot be blank"}),
            400,
        )

    # Role Enforcement: Only operational staff can resolve tickets
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only store staff can resolve support tickets.",
                }
            ),
            403,
        )

    store = get_store()
    ticket = None
    for acc in store["accounts"].values():
        if isinstance(acc, Customer):
            ticket = next((t for t in acc.support_tickets if t.ticket_id == tid), None)
            if ticket:
                break
    if not ticket:
        return jsonify({"success": False, "error": "Ticket not found"}), 404

    ticket.resolve(notes)
    return jsonify({"success": True, "ticket": ticket.to_dict()})


# ── Support Ticket API ────────────────────────────────────────────────────────


@app.route("/api/tickets", methods=["GET"])
def api_tickets():
    customer = get_current_user()
    if not customer or not isinstance(customer, Customer):
        return jsonify([])
    return jsonify([t.to_dict() for t in customer.support_tickets])


@app.route("/api/tickets", methods=["POST"])
def api_create_ticket():
    if session.get("user_role") != "customer":
        return jsonify({"success": False, "error": "Please log in first"}), 401
    data = request.get_json(force=True) or {}
    subject = data.get("subject", "").strip()
    desc = data.get("description", "").strip()
    oid = data.get("order_id", "").strip()
    if not subject:
        return jsonify({"success": False, "error": "Subject cannot be blank"}), 400
    if not desc:
        return jsonify({"success": False, "error": "Description cannot be blank"}), 400
    customer = get_current_user()
    mgr = Manager.get_instance()
    ticket = customer.raise_support_ticket(subject, desc)
    # Trigger Staff Notification
    mgr.add_staff_notification(
        f'🎫 New Support Ticket raised by {customer.username}: "{subject}"'
    )
    if oid:
        order = next((o for o in mgr.orders if o.order_id == oid), None)
        if order:
            ticket.order = order
            order.support_tickets.append(ticket)
    return jsonify({"success": True, "ticket": ticket.to_dict()}), 201


# ── Feedback API ──────────────────────────────────────────────────────────────


@app.route("/api/feedback", methods=["POST"])
def api_submit_feedback():
    if session.get("user_role") != "customer":
        return jsonify({"success": False, "error": "Please log in first"}), 401
    data = request.get_json(force=True) or {}
    oid = data.get("order_id", "").strip()
    comment = data.get("comment", "").strip()
    if not oid:
        return jsonify({"success": False, "error": "order_id is required"}), 400
    if not comment:
        return jsonify({"success": False, "error": "Comment cannot be blank"}), 400
    try:
        rating = int(data.get("rating", 0))
        if not 1 <= rating <= 5:
            raise ValueError
    except:
        return (
            jsonify({"success": False, "error": "Rating must be between 1 and 5"}),
            400,
        )
    customer = get_current_user()
    mgr = Manager.get_instance()
    order = next((o for o in mgr.orders if o.order_id == oid), None)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404
    if order.feedback:
        return jsonify({"success": False, "error": "Feedback already submitted"}), 409
    fb = order.receive_feedback(rating, comment)
    # Trigger Staff Notification
    mgr.add_staff_notification(
        f"⭐ New Review submitted by {customer.username}! Rating: {rating}/5"
    )
    customer.feedback_list.append(fb)
    return jsonify({"success": True, "feedback": fb.to_dict()}), 201


@app.route("/api/feedback", methods=["GET"])
def api_get_feedback():
    return jsonify(
        [o.feedback.to_dict() for o in Manager.get_instance().orders if o.feedback]
    )


# ── Payment Process API (Scenario 1, Steps 11–24) ────────────────────────────
#
# A2 Scenario 1 sequence:
#   Steps 11-13: Payment routes through PaymentGateway (Strategy Pattern)
#   Steps 14-17 (success): Invoice generated, status → "Paid", Shipment triggered
#   Steps 19-24 (failure): Order reverts to "Pending", customer may reattempt (Assumption A5)


@app.route("/api/payment/process", methods=["POST"])
def api_payment_process():
    if session.get("user_role") != "customer":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Please log in first",
                    "login_required": True,
                }
            ),
            401,
        )

    data = request.get_json(force=True) or {}
    order_id = data.get("order_id", "").strip()
    gw_type = data.get("gateway", "credit_card")
    sim_fail = data.get("simulate_failure", False)

    if not order_id:
        return jsonify({"success": False, "error": "order_id is required"}), 400

    mgr = Manager.get_instance()
    order = next((o for o in mgr.orders if o.order_id == order_id), None)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404
    if order.is_paid():
        return jsonify({"success": False, "error": "Order is already paid"}), 409

    # Calculate actual grand total including shipping for the gateway Payment log
    shipping = 0 if order.total_amount >= 25 else 3.99
    grand_total = round(order.total_amount + shipping, 2)

    # Select PaymentGateway strategy at runtime (Strategy Pattern)
    if gw_type == "ewallet":
        provider = data.get("provider", "TouchNGo")
        wallet_id = data.get("wallet_id", "wallet-demo-001")
        gateway = EWalletGateway(wallet_id, provider)
    else:
        card_num = data.get("card_number", "**** **** **** 0000")
        expiry = data.get("expiry", "00/00")
        digits = card_num.replace(" ", "")
        masked = "**** **** **** " + digits[-4:] if len(digits) >= 4 else card_num
        gateway = CreditCardGateway(masked, expiry)

    # Create Payment using the calculated grand_total
    payment = Payment(str(uuid.uuid4()), order, grand_total, gateway)
    order.add_payment(payment)

    # Demo failure simulation (Assumption A5: multiple attempts allowed)
    if sim_fail:
        payment.status = "failed"
        order.update_status("pending")  # Steps 23-24: revert to Pending
        return jsonify(
            {
                "success": False,
                "error": "Payment declined by provider. Please try a different method.",
                "order_id": order.order_id,
                "status": "pending",
            }
        )

    processed = payment.process()  # Steps 11-13: routes through gateway

    if processed:
        # Confirm order: reduce stock + clear cart
        order.customer.get_or_create_cart().confirm_order()
        order.update_status("pending")  # Remains pending, awaiting Admin acceptance

        return jsonify(
            {  # Step 17: Order Confirmed
                "success": True,
                "payment_status": "completed",
                "order_id": order.order_id,
                "total": order.total_amount,
                "transaction_id": payment.transaction_id,
                "gateway": gateway.gateway_name(),
                "invoice_id": order.invoice.invoice_id if order.invoice else None,
                "message": "Payment authorised! Your order is being processed.",
            }
        )
    else:
        # Steps 22-24: declined — revert to Pending, allow reattempt
        order.update_status("pending")
        return jsonify(
            {
                "success": False,
                "error": "Payment declined by provider. Please try a different method.",
                "order_id": order.order_id,
                "status": "pending",
            }
        )


@app.route("/invoice/<invoice_id>")
@login_required_customer
def invoice_page(invoice_id):
    mgr = Manager.get_instance()
    # Find the order that owns this invoice
    order = next(
        (o for o in mgr.orders if o.invoice and o.invoice.invoice_id == invoice_id),
        None,
    )
    if not order:
        abort(404)

    # Security check: Ensure this invoice belongs to the logged-in customer
    customer = get_current_user()
    if order.customer.account_id != customer.account_id:
        abort(403)

    # Find the completed payment for this order (Strategy Pattern)
    payment = next((p for p in order.payments if p.status == "completed"), None)

    return render_template(
        "invoice.html", order=order, invoice=order.invoice, payment=payment
    )


@app.route("/api/customer/addresses", methods=["GET"])
@login_required_customer
def api_get_addresses():
    customer = get_current_user()
    return jsonify({"addresses": customer.addresses, "active": customer.address})


@app.route("/api/customer/addresses/add", methods=["POST"])
@login_required_customer
def api_add_address():
    data = request.get_json(force=True) or {}
    address = data.get("address", "").strip()
    if not address:
        return jsonify({"success": False, "error": "Address cannot be blank"}), 400
    customer = get_current_user()
    if address not in customer.addresses:
        customer.addresses.append(address)
    if not customer.address:
        customer.address = address
    return jsonify(
        {"success": True, "addresses": customer.addresses, "active": customer.address}
    )


@app.route("/api/customer/addresses/select", methods=["POST"])
@login_required_customer
def api_select_address():
    data = request.get_json(force=True) or {}
    address = data.get("address", "").strip()
    customer = get_current_user()
    if address in customer.addresses:
        customer.address = address
        return jsonify({"success": True, "active": customer.address})
    return jsonify({"success": False, "error": "Address not found"}), 404


@app.route("/api/customer/addresses/edit", methods=["POST"])
@login_required_customer
def api_edit_address():
    data = request.get_json(force=True) or {}
    old_address = data.get("old_address", "").strip()
    new_address = data.get("new_address", "").strip()
    if not new_address:
        return jsonify({"success": False, "error": "New address cannot be blank"}), 400
    customer = get_current_user()
    if old_address in customer.addresses:
        idx = customer.addresses.index(old_address)
        customer.addresses[idx] = new_address
        if customer.address == old_address:
            customer.address = new_address
        return jsonify(
            {
                "success": True,
                "addresses": customer.addresses,
                "active": customer.address,
            }
        )
    return jsonify({"success": False, "error": "Original address not found"}), 404


@app.route("/profile")
def profile_page():
    user = get_current_user()
    if not user:
        return redirect(url_for("login_page"))
    # Detect if the logged-in user is a customer or admin/staff
    is_admin = isinstance(user, Admin)
    return render_template("profile.html", user=user, is_admin=is_admin)


@app.route("/api/customer/profile/update", methods=["POST"])
def api_update_profile():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip()
    phone = data.get("phone", "").strip()

    if not username:
        return jsonify({"success": False, "error": "Username cannot be blank"}), 400

    user.username = username
    # Phone only exists on Customer accounts
    if not isinstance(user, Admin):
        user.phone = phone

    return jsonify(
        {"success": True, "message": "Profile details updated successfully!"}
    )


@app.route("/api/profile/password/reset", methods=["POST"])
def api_password_reset():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    data = request.get_json(force=True) or {}
    old_pw = data.get("current_password", "").strip()
    new_pw = data.get("new_password", "").strip()

    if not old_pw or not new_pw:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Both current and new passwords are required",
                }
            ),
            400,
        )
    if len(new_pw) < 6:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "New password must be at least 6 characters",
                }
            ),
            400,
        )

    # Verify current password hash
    if user.password_hash != hash_password(old_pw):
        return (
            jsonify({"success": False, "error": "Current password is incorrect"}),
            401,
        )

    # Set new password
    user.change_password(hash_password(new_pw))
    return jsonify({"success": True, "message": "Password updated successfully!"})


@app.route("/api/customer/addresses/delete", methods=["POST"])
@login_required_customer
def api_delete_address():
    data = request.get_json(force=True) or {}
    address = data.get("address", "").strip()
    customer = get_current_user()
    if address in customer.addresses:
        customer.addresses.remove(address)
        # Reset active address if the active one was deleted
        if customer.address == address:
            customer.address = customer.addresses[0] if customer.addresses else ""
        return jsonify(
            {
                "success": True,
                "addresses": customer.addresses,
                "active": customer.address,
            }
        )
    return jsonify({"success": False, "error": "Address not found"}), 404


@app.route("/api/admin/order/accept", methods=["POST"])
@login_required_admin
def api_admin_accept_order():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can accept orders.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    order_id = data.get("order_id", "").strip()
    mgr = Manager.get_instance()
    order = next((o for o in mgr.orders if o.order_id == order_id), None)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404
    order.update_status("processing")
    # Trigger Customer Notification
    order.customer.add_notification(
        f"Your order #{order.order_id[:8].upper()} has been accepted and is now being packed! ⏳",
        order.order_id,
    )
    return jsonify({"success": True, "status": order.status})


@app.route("/api/admin/order/ship", methods=["POST"])
@login_required_admin
def api_admin_ship_order():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {"success": False, "error": "Unauthorized: Only staff can ship orders."}
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    order_id = data.get("order_id", "").strip()
    carrier = data.get("carrier", "SnackExpress").strip()
    tracking = data.get("tracking_number", "").strip()
    if not tracking:
        return jsonify({"success": False, "error": "Tracking number is required"}), 400

    mgr = Manager.get_instance()
    order = next((o for o in mgr.orders if o.order_id == order_id), None)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404

    # Create the shipment manually
    ship = Shipment(
        shipment_id=str(uuid.uuid4()),
        order=order,
        carrier=carrier,
        tracking_number=tracking,
        destination_address=order.customer.address,
    )
    order.add_shipment(ship)
    ship.ship()  # This updates order.status to "shipped"
    # Trigger Customer Notification
    order.customer.add_notification(
        f"Great news! Your order #{order.order_id[:8].upper()} has been shipped via {carrier}! Tracking: {tracking} 🚚",
        order.order_id,
    )
    return jsonify({"success": True, "status": order.status, "tracking": tracking})


@app.route("/api/admin/order/deliver", methods=["POST"])
@login_required_admin
def api_admin_deliver_order():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can deliver orders.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    order_id = data.get("order_id", "").strip()
    mgr = Manager.get_instance()
    order = next((o for o in mgr.orders if o.order_id == order_id), None)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404

    if order.shipments:
        order.shipments[0].mark_delivered()
    else:
        order.update_status("delivered")
    # Trigger Customer Notification
    order.customer.add_notification(
        f"Your order #{order.order_id[:8].upper()} has been delivered successfully! Please leave a review. ⭐",
        order.order_id,
    )
    return jsonify({"success": True, "status": order.status})


@app.route("/api/admin/order/cancel", methods=["POST"])
@login_required_admin
def api_admin_cancel_order():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can cancel orders.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    order_id = data.get("order_id", "").strip()
    mgr = Manager.get_instance()
    order = next((o for o in mgr.orders if o.order_id == order_id), None)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404

    if order.status in ("cancelled", "refunded"):
        return (
            jsonify(
                {"success": False, "error": "Order is already cancelled or refunded"}
            ),
            400,
        )

    # Standard operational flow: Restores inventory stock level for each purchased item
    for item in order.items:
        item.product.restock(item.quantity)

    order.update_status("cancelled")
    # Trigger Customer Notification
    order.customer.add_notification(
        f"Your order #{order.order_id[:8].upper()} was cancelled and stock has been returned to inventory.",
        order.order_id,
    )
    return jsonify({"success": True, "status": order.status})


@app.route("/api/admin/order/refund", methods=["POST"])
@login_required_admin
def api_admin_refund_order():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can refund orders.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    order_id = data.get("order_id", "").strip()
    mgr = Manager.get_instance()
    order = next((o for o in mgr.orders if o.order_id == order_id), None)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404

    if order.status == "refunded":
        return jsonify({"success": False, "error": "Order is already refunded"}), 400
    if order.status == "shipped":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Cannot refund an order that has already been shipped. It must be delivered or cancelled first.",
                }
            ),
            400,
        )

    # If transitioning directly to refunded (e.g., from delivered, bypassing the cancel step)
    # we return stock to inventory. If transitioning from cancelled, stock was already returned.
    if order.status != "cancelled":
        for item in order.items:
            item.product.restock(item.quantity)

    order.update_status("refunded")
    # Trigger Customer Notification
    order.customer.add_notification(
        f"Your order #{order.order_id[:8].upper()} has been refunded and stock returned to inventory. 💰",
        order.order_id,
    )
    return jsonify({"success": True, "status": order.status})


@app.route("/api/admin/product/toggle_active", methods=["POST"])
@login_required_admin
def api_admin_toggle_product_active():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can toggle product visibility.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    pid = data.get("product_id", "").strip()
    mgr = Manager.get_instance()
    p = next((p for p in mgr.products if p.product_id == pid), None)
    if not p:
        return jsonify({"success": False, "error": "Product not found"}), 404
    p.is_active = not p.is_active
    return jsonify({"success": True, "is_active": p.is_active})


@app.route("/api/tickets/reopen", methods=["POST"])
@login_required_customer
def api_reopen_ticket():
    data = request.get_json(force=True) or {}
    tid = data.get("ticket_id", "").strip()
    if not tid:
        return jsonify({"success": False, "error": "ticket_id is required"}), 400

    customer = get_current_user()
    # Find the ticket inside the logged-in customer's own list for security
    ticket = next((t for t in customer.support_tickets if t.ticket_id == tid), None)
    if not ticket:
        return (
            jsonify({"success": False, "error": "Ticket not found or unauthorized"}),
            404,
        )

    if ticket.status != "resolved":
        return (
            jsonify(
                {"success": False, "error": "Only resolved tickets can be reopened."}
            ),
            400,
        )

    ticket.reopen()
    return jsonify({"success": True, "ticket": ticket.to_dict()})


@app.route("/api/admin/category/add", methods=["POST"])
@login_required_admin
def api_admin_add_category():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can add categories.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    name = data.get("name", "").strip()
    desc = data.get("description", "").strip()
    if not name:
        return (
            jsonify({"success": False, "error": "Category name cannot be blank"}),
            400,
        )

    store = get_store()
    catalogue = store["catalogue"]

    # Avoid duplicate names
    if any(c.name.lower() == name.lower() for c in catalogue.categories):
        return (
            jsonify(
                {"success": False, "error": "A category with that name already exists"}
            ),
            409,
        )

    cat_id = "c-" + str(uuid.uuid4())[:6]
    new_cat = Category(cat_id, name, desc)

    # Register the new category in both the active catalogue AND the serialization dictionary
    catalogue.add_category(new_cat)
    store["categories"][cat_id] = new_cat

    return jsonify({"success": True, "category": new_cat.to_dict()}), 201


@app.route("/api/admin/category/rename", methods=["POST"])
@login_required_admin
def api_admin_rename_category():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can rename categories.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    cid = data.get("category_id", "").strip()
    new_name = data.get("name", "").strip()
    if not cid:
        return jsonify({"success": False, "error": "category_id is required"}), 400
    if not new_name:
        return (
            jsonify({"success": False, "error": "New category name cannot be blank"}),
            400,
        )

    store = get_store()
    catalogue = store["catalogue"]
    cat = catalogue.get_category(cid)
    if not cat:
        return jsonify({"success": False, "error": "Category not found"}), 404

    cat.name = new_name
    # Removed manual save_state_to_db() to let @app.after_request handle it safely once
    return jsonify({"success": True, "category": cat.to_dict()})


@app.route("/api/admin/category/toggle_active", methods=["POST"])
@login_required_admin
def api_admin_toggle_category_active():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unauthorized: Only staff can toggle category visibility.",
                }
            ),
            403,
        )
    data = request.get_json(force=True) or {}
    cid = data.get("category_id", "").strip()
    if not cid:
        return jsonify({"success": False, "error": "category_id is required"}), 400

    store = get_store()
    catalogue = store["catalogue"]
    cat = catalogue.get_category(cid)
    if not cat:
        return jsonify({"success": False, "error": "Category not found"}), 404

    cat.is_active = not cat.is_active
    # Removed manual save_state_to_db() to let @app.after_request handle it safely once
    return jsonify({"success": True, "category": cat.to_dict()})


@app.route("/api/admin/notifications", methods=["GET"])
@login_required_admin
def api_admin_get_notifications():
    admin = get_current_user()

    # Defensive Check: If session is stale/None, return unauthorized instantly
    if not admin:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Session expired. Please log in again.",
                    "login_required": True,
                }
            ),
            401,
        )

    mgr = Manager.get_instance()

    # Return context-aware notifications based on active role (Manager vs Staff)
    if admin.role == "manager":
        notifs = mgr.manager_notifications[::-1]
        unread = sum(1 for n in mgr.manager_notifications if not n["read"])
    else:
        notifs = mgr.staff_notifications[::-1]
        unread = sum(1 for n in mgr.staff_notifications if not n["read"])

    return jsonify({"notifications": notifs, "unread_count": unread})


@app.route("/api/admin/notifications/read", methods=["POST"])
@login_required_admin
def api_admin_read_notifications():
    admin = get_current_user()

    # Defensive Check: If session is stale/None, return unauthorized instantly
    if not admin:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Session expired. Please log in again.",
                    "login_required": True,
                }
            ),
            401,
        )

    mgr = Manager.get_instance()

    if admin.role == "manager":
        for n in mgr.manager_notifications:
            n["read"] = True
    else:
        for n in mgr.staff_notifications:
            n["read"] = True

    return jsonify({"success": True})


@app.route("/api/admin/report/request", methods=["POST"])
@login_required_admin
def api_admin_request_report_notification():
    admin = get_current_user()
    if admin.role != "staff":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Only operational staff can request latest reports.",
                }
            ),
            403,
        )

    data = request.get_json(force=True) or {}
    report_type = data.get("report_type", "").strip()
    if not report_type:
        return jsonify({"success": False, "error": "report_type is required"}), 400

    mgr = Manager.get_instance()
    # Notify Manager of the staff request
    mgr.add_manager_notification(
        f'📊 {admin.username} (staff) requested compiling the latest "{report_type.upper()}" report.'
    )
    return jsonify({"success": True})


@app.route("/api/customer/notifications", methods=["GET"])
@login_required_customer
def api_customer_get_notifications():
    customer = get_current_user()
    return jsonify(
        {
            "notifications": (
                customer.notifications[::-1]
                if hasattr(customer, "notifications")
                else []
            ),
            "unread_count": (
                sum(1 for n in customer.notifications if not n["read"])
                if hasattr(customer, "notifications")
                else 0
            ),
        }
    )


@app.route("/api/customer/notifications/read", methods=["POST"])
@login_required_customer
def api_customer_read_notifications():
    customer = get_current_user()
    if hasattr(customer, "notifications"):
        for n in customer.notifications:
            n["read"] = True
    return jsonify({"success": True})


# ── Heath Check End Point ───────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "OK"}, 200


@app.route("/version")
def version():
    return jsonify(sha=os.environ.get("GIT_SHA", "unknown"))


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Initialize SQLite database and populate schema on startup
    try:
        init_db()  # Creates the local database file and its table schema
        loaded = load_state_from_db()  # Reconstructs state from the database
        if not loaded:
            seed_data()  # Fallback to seed default memory data
            save_state_to_db()  # Persist the seeded state to SQLite immediately
            print("SQLite database successfully initialized and seeded! ✓")
        else:
            print("SQLite database successfully loaded state from 'acemart.db'! ✓")
    except Exception as e:
        print("Critical database startup error. Defaulting to memory seed. Error:", e)
        seed_data()

    app.run(debug=True, port=5000)
