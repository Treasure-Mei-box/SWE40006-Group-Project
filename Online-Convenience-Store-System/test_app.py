from app import app


def test_home():
    res = app.test_client().get("/")
    assert res.status_code == 200
    assert b"ACE Mart" in res.data


def test_login_page():
    res = app.test_client().get("/login")
    assert res.status_code == 200


def test_products_api():
    res = app.test_client().get("/api/products")
    assert res.status_code == 200
    assert res.get_json() is not None


def test_health():
    res = app.test_client().get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "OK"
