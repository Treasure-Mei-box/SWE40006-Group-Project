import sqlite3

import pytest

import app as app_module
from app import app
from models import Product

_save_state_to_db = app_module.save_state_to_db


@pytest.fixture
def client(monkeypatch):
    app.config["TESTING"] = True
    app_module.seed_data()
    monkeypatch.setattr(app_module, "save_state_to_db", lambda: None)
    with app.test_client() as test_client:
        yield test_client


def login(client, email="alex@acemart.com", password="pw1234", role="customer"):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password, "role": role},
    )


def add_cart_item(client, product_id="p-001", quantity=1):
    return client.post(
        "/api/cart/add",
        json={"product_id": product_id, "quantity": quantity},
    )


def checkout(client):
    add_cart_item(client)
    response = client.post("/api/cart/checkout")
    assert response.status_code == 200
    return response.get_json()["order_id"]


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ACE Mart" in response.data


def test_home_search_and_category_filter(client):
    search_response = client.get("/?q=Truffle")
    category_response = client.get("/?category=c-01")
    missing_category_response = client.get("/?category=missing")

    assert search_response.status_code == 200
    assert b"Truffle Chips" in search_response.data
    assert b"Mango Chili Gummies" not in search_response.data
    assert category_response.status_code == 200
    assert b"Truffle Chips" in category_response.data
    assert b"Mango Chili Gummies" not in category_response.data
    assert missing_category_response.status_code == 200


def test_login_page_and_customer_pages(client):
    for path in ("/cart", "/payment", "/orders", "/support"):
        response = client.get(path)
        assert response.status_code == 302
        assert "/login" in response.location

    assert login(client).status_code == 200
    for path in ("/cart", "/orders", "/support", "/profile"):
        assert client.get(path).status_code == 200
    assert client.get("/payment").status_code == 302
    assert client.get("/login").status_code == 302


def test_login_validation_and_failed_authentication(client):
    empty = client.post("/api/auth/login", json={})
    missing_account = login(client, email="missing@example.com")
    wrong_password = login(client, password="wrong-password")
    wrong_role = login(client, role="admin")

    assert empty.status_code == 400
    assert missing_account.status_code == 401
    assert wrong_password.status_code == 401
    assert wrong_role.status_code == 403


def test_login_customer_and_staff(client):
    customer_response = login(client)
    assert customer_response.status_code == 200
    assert customer_response.get_json()["role"] == "customer"

    logout_response = client.get("/logout")
    assert logout_response.status_code == 302

    staff_response = login(
        client,
        email="lee@acemart.com",
        password="staff123",
        role="admin",
    )
    assert staff_response.status_code == 200
    assert staff_response.get_json()["role"] == "staff"
    assert client.get("/admin").status_code == 200


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({}, 400),
        (
            {
                "username": "New User",
                "email": "not-an-email",
                "password": "long-enough",
                "address": "1 Main Street",
            },
            400,
        ),
        (
            {
                "username": "New User",
                "email": "new@example.com",
                "password": "short",
                "address": "1 Main Street",
            },
            400,
        ),
        (
            {
                "username": "New User",
                "email": "new@example.com",
                "password": "long-enough",
            },
            400,
        ),
    ],
)
def test_signup_rejects_invalid_details(client, payload, expected_status):
    assert client.post("/api/auth/signup", json=payload).status_code == expected_status


def test_signup_creates_account_and_rejects_duplicate(client):
    payload = {
        "username": "New User",
        "email": "new@example.com",
        "password": "secure123",
        "phone": "555-0123",
        "address": "1 Main Street",
    }

    created = client.post("/api/auth/signup", json=payload)
    duplicate = client.post("/api/auth/signup", json=payload)

    assert created.status_code == 201
    assert created.get_json()["success"] is True
    assert duplicate.status_code == 409


def test_product_and_order_listing_endpoints(client):
    products = client.get("/api/products")
    orders = client.get("/api/orders")
    anonymous_cart = client.get("/api/cart")

    assert products.status_code == 200
    assert len(products.get_json()) == 15
    assert orders.get_json() == []
    assert anonymous_cart.get_json() == {"items": [], "total": 0, "item_count": 0}


def test_cart_add_validation_and_success(client):
    assert client.post("/api/cart/add", json={}).status_code == 401
    login(client)
    assert client.post("/api/cart/add", json={}).status_code == 400
    assert add_cart_item(client, quantity=0).status_code == 400
    assert add_cart_item(client, product_id="missing").status_code == 404

    added = add_cart_item(client, quantity=2)
    assert added.status_code == 200
    assert added.get_json()["item_count"] == 2
    assert client.get("/api/cart").get_json()["item_count"] == 2


def test_cart_update_remove_and_checkout_validation(client):
    login(client)
    assert client.post("/api/cart/update", json={}).status_code == 404
    assert (
        client.post(
            "/api/cart/update",
            json={"product_id": "p-001", "quantity": "not-a-number"},
        ).status_code
        == 400
    )
    assert client.post("/api/cart/checkout").status_code == 400
    assert client.get("/api/cart/checkout").status_code == 405

    add_cart_item(client)
    updated = client.post(
        "/api/cart/update", json={"product_id": "p-001", "quantity": 3}
    )
    removed = client.post("/api/cart/remove", json={"product_id": "p-001"})
    assert updated.get_json()["item_count"] == 3
    assert removed.get_json()["success"] is True
    assert client.post("/api/cart/remove", json={"product_id": "missing"}).get_json()[
        "success"
    ] is False


def test_checkout_and_payment_success(client):
    login(client)
    order_id = checkout(client)
    payment = client.post(
        "/api/payment/process",
        json={"order_id": order_id, "gateway": "credit_card"},
    )
    duplicate_payment = client.post(
        "/api/payment/process", json={"order_id": order_id}
    )

    assert payment.status_code == 200
    assert payment.get_json()["payment_status"] == "completed"
    assert duplicate_payment.status_code == 409


def test_payment_validation_decline_and_cash_on_delivery(client):
    assert client.post("/api/payment/process", json={}).status_code == 401
    login(client)
    assert client.post("/api/payment/process", json={}).status_code == 400
    assert (
        client.post(
            "/api/payment/process", json={"order_id": "missing"}
        ).status_code
        == 404
    )

    failed_order = checkout(client)
    declined = client.post(
        "/api/payment/process",
        json={"order_id": failed_order, "simulate_failure": True},
    )
    assert declined.get_json()["success"] is False
    assert declined.get_json()["status"] == "pending"

    cod_order = checkout(client)
    cod_payment = client.post(
        "/api/payment/process",
        json={"order_id": cod_order, "gateway": "cod"},
    )
    assert cod_payment.get_json()["payment_method"] == "cod"
    assert cod_payment.get_json()["payment_status"] == "pending"


def test_payment_rejects_unknown_gateway(client):
    login(client)
    order_id = checkout(client)
    response = client.post(
        "/api/payment/process",
        json={"order_id": order_id, "gateway": "unsupported"},
    )
    assert response.status_code == 400


def test_customer_address_management(client):
    login(client)
    assert client.get("/api/customer/addresses").status_code == 200
    assert (
        client.post("/api/customer/addresses/add", json={"address": " "}).status_code
        == 400
    )

    added = client.post(
        "/api/customer/addresses/add", json={"address": "10 New Street"}
    )
    selected = client.post(
        "/api/customer/addresses/select", json={"address": "10 New Street"}
    )
    edited = client.post(
        "/api/customer/addresses/edit",
        json={"old_address": "10 New Street", "new_address": "11 New Street"},
    )
    deleted = client.post(
        "/api/customer/addresses/delete", json={"address": "11 New Street"}
    )

    assert added.get_json()["success"] is True
    assert selected.get_json()["active"] == "10 New Street"
    assert edited.get_json()["active"] == "11 New Street"
    assert deleted.get_json()["success"] is True
    assert (
        client.post(
            "/api/customer/addresses/select", json={"address": "missing"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/customer/addresses/edit",
            json={"old_address": "missing", "new_address": "new"},
        ).status_code
        == 404
    )


def test_profile_update_and_password_reset(client):
    assert (
        client.post("/api/customer/profile/update", json={"username": "Updated"}).status_code
        == 401
    )
    login(client)
    assert (
        client.post("/api/customer/profile/update", json={"username": " "}).status_code
        == 400
    )
    updated = client.post(
        "/api/customer/profile/update",
        json={"username": "Alex Updated", "phone": "555-0199"},
    )
    assert updated.get_json()["success"] is True

    assert client.post("/api/profile/password/reset", json={}).status_code == 400
    assert (
        client.post(
            "/api/profile/password/reset",
            json={"current_password": "wrong", "new_password": "newpass123"},
        ).status_code
        == 401
    )
    changed = client.post(
        "/api/profile/password/reset",
        json={"current_password": "pw1234", "new_password": "newpass123"},
    )
    assert changed.get_json()["success"] is True


def test_support_ticket_create_resolve_and_reopen(client):
    assert client.get("/api/tickets").get_json() == []
    assert client.post("/api/tickets", json={}).status_code == 401
    login(client)
    assert client.post("/api/tickets", json={"subject": " "}).status_code == 400
    created = client.post(
        "/api/tickets",
        json={"subject": "Delivery", "description": "Where is my order?"},
    )
    ticket_id = created.get_json()["ticket"]["ticket_id"]
    assert created.status_code == 201
    assert len(client.get("/api/tickets").get_json()) == 1

    assert client.post("/api/tickets/reopen", json={}).status_code == 400
    staff_login = client
    staff_login.get("/logout")
    login(staff_login, "lee@acemart.com", "staff123", "admin")
    assert (
        staff_login.post(
            "/api/admin/ticket/resolve",
            json={"ticket_id": ticket_id, "notes": "Resolved"},
        ).status_code
        == 200
    )
    staff_login.get("/logout")
    login(staff_login)
    reopened = staff_login.post(
        "/api/tickets/reopen", json={"ticket_id": ticket_id}
    )
    assert reopened.status_code == 200
    assert reopened.get_json()["ticket"]["status"] != "resolved"


def test_feedback_submission_and_listing(client):
    assert client.get("/api/feedback").get_json() == []
    assert client.post("/api/feedback", json={}).status_code == 401
    login(client)
    order_id = checkout(client)
    assert client.post("/api/feedback", json={"order_id": order_id}).status_code == 400
    invalid_rating = client.post(
        "/api/feedback",
        json={"order_id": order_id, "comment": "Good", "rating": 9},
    )
    assert invalid_rating.status_code == 400

    submitted = client.post(
        "/api/feedback",
        json={"order_id": order_id, "comment": "Good", "rating": 5},
    )
    duplicate = client.post(
        "/api/feedback",
        json={"order_id": order_id, "comment": "Again", "rating": 4},
    )
    assert submitted.status_code == 201
    assert duplicate.status_code == 409
    assert len(client.get("/api/feedback").get_json()) == 1


def test_admin_product_and_category_management(client):
    assert client.post("/api/admin/product/add", json={}).status_code == 302
    login(client, "lee@acemart.com", "staff123", "admin")
    assert client.get("/admin").status_code == 200
    assert client.post("/api/admin/product/add", json={}).status_code == 400

    added_product = client.post(
        "/api/admin/product/add",
        json={
            "name": "Test Snack",
            "description": "A test product",
            "category_id": "c-01",
            "price": 2.5,
            "stock": 5,
        },
    )
    product_id = added_product.get_json()["product"]["product_id"]
    restocked = client.post(
        "/api/admin/product/restock",
        json={"product_id": product_id, "quantity": 4},
    )
    assert added_product.status_code == 201
    assert restocked.get_json()["product"]["stock_quantity"] == 9

    assert (
        client.post(
            "/api/admin/product/toggle_active", json={"product_id": product_id}
        ).get_json()["is_active"]
        is False
    )
    assert (
        client.post(
            "/api/admin/product/remove", json={"product_id": product_id}
        ).get_json()["success"]
        is True
    )

    added_category = client.post(
        "/api/admin/category/add", json={"name": "Seasonal", "description": "Limited"}
    )
    category_id = added_category.get_json()["category"]["category_id"]
    assert added_category.status_code == 201
    assert client.post(
        "/api/admin/category/add", json={"name": "Seasonal"}
    ).status_code == 409
    renamed = client.post(
        "/api/admin/category/rename",
        json={"category_id": category_id, "name": "Seasonal Items"},
    )
    toggled = client.post(
        "/api/admin/category/toggle_active", json={"category_id": category_id}
    )
    assert renamed.get_json()["category"]["name"] == "Seasonal Items"
    assert toggled.get_json()["category"]["is_active"] is False


def test_admin_report_and_notifications(client):
    login(client, "sam@acemart.com", "admin123", "admin")
    assert client.get("/api/admin/report/unknown").status_code == 400
    assert client.get("/api/admin/report/sales").status_code == 404

    compiled = client.get("/api/admin/report/inventory?period=week&compile=true")
    assert compiled.status_code == 200
    assert client.get("/api/admin/notifications").status_code == 200
    assert (
        client.post("/api/admin/notifications/read").get_json()["success"] is True
    )


def test_health_and_version(client, monkeypatch):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.get_json()["status"] == "OK"

    monkeypatch.setenv("GIT_SHA", "test-commit")
    version = client.get("/version")
    assert version.status_code == 200
    assert version.get_json()["sha"] == "test-commit"


def test_before_request_seeds_empty_store(client, monkeypatch):
    app.config["STORE"] = {}
    monkeypatch.setattr(app_module, "load_state_from_db", lambda: False)

    response = client.get("/api/products")

    assert response.status_code == 200
    assert len(response.get_json()) == 15


def test_database_state_can_be_initialized_saved_and_loaded(
    client, monkeypatch, tmp_path
):
    database_path = tmp_path / "store.db"

    def connect_to_test_database():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        return connection

    monkeypatch.setattr(app_module, "get_db_connection", connect_to_test_database)
    monkeypatch.setattr(app_module, "save_state_to_db", _save_state_to_db)
    app_module.init_db()
    assert app_module.load_state_from_db() is False

    assert app.config["STORE"]
    assert len(app_module.Manager.get_instance().products) == 15
    app_module.save_state_to_db()
    connection = connect_to_test_database()
    try:
        saved_rows = connection.execute("SELECT COUNT(*) FROM store_state").fetchone()[0]
    finally:
        connection.close()
    assert saved_rows == 6
    app.config["STORE"] = {}
    assert app_module.load_state_from_db() is True
    assert len(app.config["STORE"]["products"]) == 15
    assert app_module.load_state_from_db() is True


def test_database_connection_uses_current_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    connection = app_module.get_db_connection()
    try:
        connection.execute("CREATE TABLE connection_check (value INTEGER)")
        connection.execute("INSERT INTO connection_check VALUES (1)")
        assert connection.execute("SELECT value FROM connection_check").fetchone()[0] == 1
    finally:
        connection.close()


def test_product_stock_reduction_and_low_stock_alert(client):
    product = Product("test-product", "Test Product", "Description", 2.0, 12)

    assert product.reduce_stock(1) is True
    assert product.stock_quantity == 11
    assert product.reduce_stock(1) is True
    assert product.stock_quantity == 10
    notification_count = len(app_module.Manager.get_instance().staff_notifications)

    assert product.reduce_stock(0) is True
    assert (
        len(app_module.Manager.get_instance().staff_notifications)
        == notification_count
    )
    assert product.reduce_stock(20) is False
    assert product.apply_discount(10) == 1.8


def test_admin_ticket_assignment_and_customer_ticket_access(client):
    login(client)
    created = client.post(
        "/api/tickets",
        json={"subject": "Order help", "description": "Please check my order"},
    )
    ticket_id = created.get_json()["ticket"]["ticket_id"]
    client.get("/logout")

    login(client, "sam@acemart.com", "admin123", "admin")
    assert client.post("/api/admin/ticket/assign", json={}).status_code == 400
    assert (
        client.post(
            "/api/admin/ticket/assign",
            json={"ticket_id": "missing", "assignee_id": "missing"},
        ).status_code
        == 404
    )
    assigned = client.post(
        "/api/admin/ticket/assign",
        json={
            "ticket_id": ticket_id,
            "assignee_id": app.config["STORE"]["staff"].account_id,
        },
    )
    assert assigned.status_code == 200

    client.get("/logout")
    login(client, "lee@acemart.com", "staff123", "admin")
    assert (
        client.post(
            "/api/admin/ticket/assign",
            json={"ticket_id": ticket_id},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/admin/ticket/resolve",
            json={"ticket_id": ticket_id, "notes": "Resolved"},
        ).status_code
        == 200
    )


def test_admin_order_lifecycle(client):
    login(client)
    order_id = checkout(client)
    client.get("/logout")
    login(client, "lee@acemart.com", "staff123", "admin")

    accepted = client.post("/api/admin/order/accept", json={"order_id": order_id})
    shipped = client.post(
        "/api/admin/order/ship",
        json={"order_id": order_id, "tracking_number": "TRACK-123"},
    )
    delivered = client.post(
        "/api/admin/order/deliver", json={"order_id": order_id}
    )

    assert accepted.get_json()["status"] == "processing"
    assert shipped.get_json()["tracking"] == "TRACK-123"
    assert delivered.get_json()["status"] == "delivered"
    assert client.get("/api/admin/notifications").status_code == 200
    assert client.post("/api/admin/notifications/read").status_code == 200


def test_admin_order_cancel_and_refund_rules(client):
    login(client)
    cancel_order_id = checkout(client)
    refund_order_id = checkout(client)
    client.get("/logout")
    login(client, "lee@acemart.com", "staff123", "admin")

    cancelled = client.post(
        "/api/admin/order/cancel", json={"order_id": cancel_order_id}
    )
    cancel_again = client.post(
        "/api/admin/order/cancel", json={"order_id": cancel_order_id}
    )
    refunded = client.post(
        "/api/admin/order/refund", json={"order_id": refund_order_id}
    )
    refund_again = client.post(
        "/api/admin/order/refund", json={"order_id": refund_order_id}
    )
    unknown_refund = client.post(
        "/api/admin/order/refund", json={"order_id": "missing"}
    )

    assert cancelled.get_json()["status"] == "cancelled"
    assert cancel_again.status_code == 400
    assert refunded.get_json()["status"] == "refunded"
    assert refund_again.status_code == 400
    assert unknown_refund.status_code == 404


def test_invoice_ownership_and_page_access(client):
    login(client)
    checkout(client)
    invoice_id = app_module.Manager.get_instance().orders[0].invoice.invoice_id
    assert client.get(f"/invoice/{invoice_id}").status_code == 200
    assert client.get("/invoice/missing").status_code == 404

    client.get("/logout")
    other_customer = client.post(
        "/api/auth/signup",
        json={
            "username": "Other Customer",
            "email": "other@example.com",
            "password": "secure123",
            "address": "2 Main Street",
        },
    )
    assert other_customer.status_code == 201
    forbidden = client.get(f"/invoice/{invoice_id}")
    assert forbidden.status_code == 403


def test_customer_notifications_and_staff_report_request(client):
    login(client)
    assert client.get("/api/customer/notifications").status_code == 200
    assert client.post("/api/customer/notifications/read").status_code == 200
    assert (
        client.post(
            "/api/admin/report/request", json={"report_type": "sales"}
        ).status_code
        == 302
    )

    client.get("/logout")
    login(client, "lee@acemart.com", "staff123", "admin")
    assert client.post("/api/admin/report/request", json={}).status_code == 400
    requested = client.post(
        "/api/admin/report/request", json={"report_type": "sales"}
    )
    assert requested.status_code == 200
    assert client.get("/api/customer/notifications").status_code == 302
