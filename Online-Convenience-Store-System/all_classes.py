"""
all_classes.py
==============
Self-contained version of every domain class from the UML diagram.
Use this file when you need the full model without the package structure.

Design patterns implemented:
  - Factory   : AccountFactory
  - Singleton : Manager
  - Strategy  : PaymentGateway (CreditCardGateway, EWalletGateway)
  - Composition: Customer ◆—— ShoppingCart
  - Aggregation: Catalogue ◇—— Category ◇—— Product
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import uuid

# ---------------------------------------------------------------------------
# Account (base)
# ---------------------------------------------------------------------------

class Account:
    def __init__(self, account_id: str, username: str, email: str, password_hash: str):
        self.account_id = account_id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = datetime.now()
        self.is_active = True

    def deactivate(self): self.is_active = False
    def activate(self):   self.is_active = True
    def update_email(self, e: str): self.email = e

    def change_password(self, new_password_hash: str):
        self.password_hash = new_password_hash

    def to_dict(self):
        return {"account_id": self.account_id, "username": self.username,
                "email": self.email, "created_at": self.created_at.isoformat(),
                "is_active": self.is_active}

    def __repr__(self): return f"<Account {self.account_id}: {self.username}>"


# ---------------------------------------------------------------------------
# AccountFactory  (Factory Pattern)
# ---------------------------------------------------------------------------

class AccountFactory:
    @staticmethod
    def _hash(pw: str) -> str:
        return hashlib.sha256(pw.encode()).hexdigest()

    @staticmethod
    def create(account_type: str, username: str, email: str, password: str, **kw) -> Account:
        aid = str(uuid.uuid4())
        ph  = AccountFactory._hash(password)
        if account_type.lower() == "customer":
            return Customer(aid, username, email, ph, **kw)
        if account_type.lower() == "admin":
            return Admin(aid, username, email, ph, **kw)
        raise ValueError(f"Unknown account type: {account_type!r}")


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

class Customer(Account):
    def __init__(self, account_id, username, email, password_hash,
                 phone="", address=""):
        super().__init__(account_id, username, email, password_hash)
        self.phone = phone
        self.address = address  # This acts as the currently active address
        self.addresses: List[str] = [address] if address else []  # Saved addresses
        self.notifications: List[dict] = []
        self.shopping_cart: Optional[ShoppingCart] = None
        self.orders: List[Order] = []
        self.feedback_list: List[Feedback] = []
        self.support_tickets: List[SupportTicket] = []

    def get_or_create_cart(self) -> ShoppingCart:
        if self.shopping_cart is None:
            self.shopping_cart = ShoppingCart(owner=self)
        return self.shopping_cart

    def place_order(self) -> Optional[Order]:
        if self.shopping_cart:
            order = self.shopping_cart.convert_to_order()
            if order:
                self.orders.append(order)
            return order
        return None

    def raise_support_ticket(self, subject: str, description: str) -> SupportTicket:
        t = SupportTicket(str(uuid.uuid4()), self, subject, description)
        self.support_tickets.append(t)
        return t

    def to_dict(self):
        d = super().to_dict()
        d.update({"phone": self.phone, "address": self.address, "addresses": self.addresses,"notifications": self.notifications,
                  "order_count": len(self.orders),
                  "ticket_count": len(self.support_tickets)})
        return d

    def __repr__(self): return f"<Customer {self.username}>"


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class Admin(Account):
    def __init__(self, account_id, username, email, password_hash, role="admin"):
        super().__init__(account_id, username, email, password_hash)
        self.role = role
        self.managed_products: List[Product] = []

    def add_product(self, p: Product): self.managed_products.append(p)

    def remove_product(self, pid: str) -> bool:
        n = len(self.managed_products)
        self.managed_products = [p for p in self.managed_products if p.product_id != pid]
        return len(self.managed_products) < n

    def update_product_stock(self, p: Product, qty: int): p.stock_quantity = qty

    def analyze_inventory(self) -> dict:
        return {"total_units": sum(p.stock_quantity for p in self.managed_products),
                "total_products": len(self.managed_products),
                "out_of_stock": [p.to_dict() for p in self.managed_products if p.stock_quantity == 0]}

    def request_report(self, report_type: str) -> Report:
        return Manager.get_instance().create_report(report_type, requested_by=self)

    def to_dict(self):
        d = super().to_dict(); d["role"] = self.role; return d

    def __repr__(self): return f"<Admin {self.username} ({self.role})>"


# ---------------------------------------------------------------------------
# Manager  (Singleton Pattern)
# ---------------------------------------------------------------------------

class Manager:
    _instance: Optional[Manager] = None

    def __init__(self):
        if Manager._instance is not None:
            raise RuntimeError("Use Manager.get_instance() — Manager is a Singleton.")
        self.products: List[Product] = []
        self.orders: List[Order] = []
        self.reports: List[Report] = []
        # Centralized notification registries
        self.staff_notifications: List[dict] = []
        self.manager_notifications: List[dict] = []

    @classmethod
    def get_instance(cls) -> Manager:
        if cls._instance is None:
            cls._instance = Manager()
        return cls._instance

    @classmethod
    def reset(cls): cls._instance = None

    def add_staff_notification(self, message: str):
        import uuid
        from datetime import datetime
        self.staff_notifications.append({
            "id": str(uuid.uuid4())[:8].upper(),
            "message": message,
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "read": False
        })

    def add_manager_notification(self, message: str):
        import uuid
        from datetime import datetime
        self.manager_notifications.append({
            "id": str(uuid.uuid4())[:8].upper(),
            "message": message,
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "read": False
        })

    def manage_product(self, p: Product):
        if not any(x.product_id == p.product_id for x in self.products):
            self.products.append(p)

    def process_order(self, order: Order) -> bool:
        order.update_status("processing")
        self.orders.append(order)
        return True

    def create_report(self, report_type: str, requested_by=None, start_date=None, end_date=None) -> Report:
        data = {}
        
        # Resolve default date boundaries
        s_date = start_date or datetime(2000, 1, 1)
        e_date = end_date or datetime.now()
        
        # SQL-style filter: isolate orders strictly within the selected reporting period
        period_orders = [o for o in self.orders if s_date <= o.placed_at <= e_date]
        
        # Pre-calculate active units sold & category breakdown for this period
        product_sales = {p.name: 0 for p in self.products}
        category_sales = {}
        total_units_sold = 0
        
        for o in period_orders:
            if o.is_paid():
                for item in o.items:
                    product_sales[item.product.name] = product_sales.get(item.product.name, 0) + item.quantity
                    total_units_sold += item.quantity
                    
                    cat_id = item.product.category_id or "Uncategorized"
                    category_sales[cat_id] = round(category_sales.get(cat_id, 0.0) + item.subtotal(), 2)

        if report_type == "inventory":
            out_of_stock = [p for p in self.products if p.stock_quantity == 0]
            low_stock    = [p for p in self.products if 0 < p.stock_quantity <= 5]
            
            # Turnover statistics for this specific period
            current_total_stock = sum(p.stock_quantity for p in self.products)
            avg_inventory = current_total_stock + (total_units_sold / 2.0)
            global_turnover_ratio = round(total_units_sold / avg_inventory, 2) if avg_inventory > 0 else 0.0
            
            turnover_details = []
            for p in self.products:
                p_sold = product_sales.get(p.name, 0)
                p_avg = p.stock_quantity + (p_sold / 2.0)
                p_turnover = round(p_sold / p_avg, 2) if p_avg > 0 else 0.0
                turnover_details.append({
                    "product_id": p.product_id,
                    "name": p.name,
                    "units_sold": p_sold,
                    "turnover_ratio": p_turnover,
                    "stock_left": p.stock_quantity
                })
                
            data = {
                "total_products": len(self.products),
                "total_stock_units": sum(p.stock_quantity for p in self.products),
                "out_of_stock_count": len(out_of_stock),
                "low_stock_count": len(low_stock),
                "global_turnover_ratio": global_turnover_ratio,
                "turnover_details": turnover_details,
                "out_of_stock": [p.to_dict() for p in out_of_stock],
                "low_stock": [p.to_dict() for p in low_stock],
                "products": [p.to_dict() for p in self.products],
            }
            
        elif report_type == "orders":
            status_map = {}
            for o in period_orders:
                status_map[o.status] = status_map.get(o.status, 0) + 1
            data = {
                "total_orders": len(period_orders),
                "by_status": status_map,
                "orders": [o.to_dict() for o in period_orders],
            }
            
        elif report_type == "sales":
            invoices = [o.invoice for o in period_orders if o.invoice]
            total_revenue = round(sum(inv.amount for inv in invoices if inv.is_paid), 2)
            paid_orders   = [o for o in period_orders if o.is_paid()]
            
            sorted_sales = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)
            top_selling = [{"name": name, "qty_sold": qty} for name, qty in sorted_sales[:3]]
            low_performing = [{"name": name, "qty_sold": qty} for name, qty in sorted_sales[-3:]][::-1]
            
            data = {
                "total_revenue": total_revenue,
                "total_paid_orders": len(paid_orders),
                "total_invoices": len(invoices),
                "average_order_value": round(total_revenue / len(paid_orders) if paid_orders else 0, 2),
                "top_selling": top_selling,
                "low_performing": low_performing,
                "category_sales": category_sales,
                "invoice_details": [inv.to_dict() for inv in invoices],
            }
            
        elif report_type == "feedback":
            feedbacks = [o.feedback for o in period_orders if o.feedback]
            avg_rating = round(sum(f.rating for f in feedbacks) / len(feedbacks) if feedbacks else 0, 2)
            data = {
                "total_feedback": len(feedbacks),
                "average_rating": avg_rating,
                "five_star": sum(1 for f in feedbacks if f.rating == 5),
                "four_star": sum(1 for f in feedbacks if f.rating == 4),
                "three_star": sum(1 for f in feedbacks if f.rating == 3),
                "two_star": sum(1 for f in feedbacks if f.rating == 2),
                "one_star": sum(1 for f in feedbacks if f.rating == 1),
                "feedbacks": [f.to_dict() for f in feedbacks],
            }
            
        elif report_type == "support":
            all_tickets = []
            for o in period_orders:
                all_tickets.extend(o.support_tickets)
            resolved = [t for t in all_tickets if t.status == "resolved"]
            data = {
                "total_tickets": len(all_tickets),
                "resolved": len(resolved),
                "open": sum(1 for t in all_tickets if t.status == "open"),
                "in_progress": sum(1 for t in all_tickets if t.status == "in_progress"),
                "resolution_rate": round(len(resolved) / len(all_tickets) * 100 if all_tickets else 0, 1),
            }
            
        r = Report(str(uuid.uuid4()), report_type, datetime.now(), data, requested_by, s_date, e_date)
        self.reports.append(r)
        return r

    def get_latest_report(self, report_type: str) -> Optional[Report]:
        """
        Traverses compiled reports in reverse chronological order
        to fetch the most recently generated instance of a given type.
        """
        for r in reversed(self.reports):
            if r.report_type == report_type:
                return r
        return None

    def to_dict(self):
        return {"products": len(self.products), "orders": len(self.orders),
                "reports": len(self.reports)}

    def __repr__(self): return "<Manager (Singleton)>"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class Report:
    def __init__(self, report_id, report_type, generated_at, data, requested_by=None, start_date=None, end_date=None):
        self.report_id = report_id
        self.report_type = report_type
        self.generated_at = generated_at
        self.data = data
        self.requested_by = requested_by
        self.start_date = start_date or datetime(2000, 1, 1)
        self.end_date = end_date or datetime.now()

    def to_dict(self):
        return {"report_id": self.report_id, "report_type": self.report_type,
                "generated_at": self.generated_at.isoformat(), "data": self.data,
                "requested_by": self.requested_by.username if self.requested_by else None,
                "start_date": self.start_date.isoformat(), "end_date": self.end_date.isoformat(),}

    def __repr__(self): return f"<Report {self.report_id}: {self.report_type}>"


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class Product:
    def __init__(self, product_id, name, description, price, stock_quantity,
                 category_id=None):
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = price
        self.stock_quantity = stock_quantity
        self.category_id = category_id
        self.image_url = ""
        self.is_active = True 

    def is_available(self): return self.stock_quantity > 0

    def reduce_stock(self, quantity: int) -> bool:
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            
            # Low Stock Alert Check: Trigger staff notification if stock falls to 10 or fewer units (CRC 4.6)
            if self.stock_quantity <= 10:
                mgr = Manager.get_instance()
                
                # Check to avoid duplicates
                warning_msg = f"⚠ Stock Warning: {self.image_url} {self.name} is running low! Only {self.stock_quantity} left."
                if not any(warning_msg in n["message"] and not n["read"] for n in mgr.staff_notifications):
                    mgr.add_staff_notification(warning_msg)
            return True
        return False
    def restock(self, qty): self.stock_quantity += qty

    def apply_discount(self, pct): return round(self.price * (1 - pct / 100), 2)

    def to_dict(self):
        return {"product_id": self.product_id, "name": self.name,
                "description": self.description, "price": self.price,
                "stock_quantity": self.stock_quantity, "category_id": self.category_id,
                "is_available": self.is_available(), "image_url": self.image_url,
                "is_active": self.is_active}

    def __repr__(self): return f"<Product {self.name} ${self.price}>"


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class Category:
    def __init__(self, category_id, name, description=""):
        self.category_id = category_id
        self.name = name
        self.description = description
        self.products: List[Product] = []
        self.is_active = True 

    def add_product(self, p: Product):
        p.category_id = self.category_id
        if not any(x.product_id == p.product_id for x in self.products):
            self.products.append(p)

    def remove_product(self, pid):
        self.products = [p for p in self.products if p.product_id != pid]

    def filter_available(self): return [p for p in self.products if p.is_available()]

    def to_dict(self):
        return {"category_id": self.category_id, "name": self.name,
                "description": self.description, "product_count": len(self.products),
                "is_active": self.is_active,     "products": [p.to_dict() for p in self.products]}

    def __repr__(self): return f"<Category {self.name}>"


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

class Catalogue:
    def __init__(self, catalogue_id, name):
        self.catalogue_id = catalogue_id
        self.name = name
        self.categories: List[Category] = []

    def add_category(self, c: Category):
        if not any(x.category_id == c.category_id for x in self.categories):
            self.categories.append(c)

    def get_category(self, cid): return next((c for c in self.categories if c.category_id == cid), None)

    def all_products(self):
        seen, out = set(), []
        for cat in self.categories:
            for p in cat.products:
                if p.product_id not in seen:
                    out.append(p); seen.add(p.product_id)
        return out

    def search(self, query):
        q = query.lower()
        return [p for p in self.all_products() if q in p.name.lower() or q in p.description.lower()]

    def to_dict(self):
        return {"catalogue_id": self.catalogue_id, "name": self.name,
                "categories": [c.to_dict() for c in self.categories]}

    def __repr__(self): return f"<Catalogue {self.name}>"


# ---------------------------------------------------------------------------
# ShoppingCart  (Composition with Customer)
# ---------------------------------------------------------------------------

class CartItem:
    def __init__(self, product: Product, quantity: int):
        self.product = product
        self.quantity = quantity

    def subtotal(self): return round(self.product.price * self.quantity, 2)

    def to_dict(self):
        return {"product_id": self.product.product_id, "product_name": self.product.name,
                "price": self.product.price, "quantity": self.quantity,
                "subtotal": self.subtotal()}


class ShoppingCart:
    def __init__(self, owner: Customer):
        self.owner = owner
        self.items: Dict[str, CartItem] = {}
        self.created_at = datetime.now()
    
    def update_quantity(self, product_id: str, quantity: int) -> bool:
        if product_id in self.items:
            if quantity <= 0:
                return self.remove_product(product_id)
            
            # Stock Validation: block update if quantity exceeds available inventory
            if quantity > self.items[product_id].product.stock_quantity:
                return False
                
            self.items[product_id].quantity = quantity
            return True
        return False

    def add_product(self, p: Product, qty: int = 1, catalogue: Optional[Catalogue] = None) -> bool:
        if catalogue is not None:
            all_products = catalogue.all_products()
            live_product = next((prod for prod in all_products if prod.product_id == p.product_id), None)
            if live_product is None or not live_product.is_available():
                return False
        else:
            if not p.is_available():
                return False
        if p.product_id in self.items:
            self.items[p.product_id].quantity += qty
        else:
            self.items[p.product_id] = CartItem(p, qty)
        return True

    def remove_product(self, pid):
        return bool(self.items.pop(pid, None))

    def total(self): return round(sum(i.subtotal() for i in self.items.values()), 2)

    def item_count(self): return sum(i.quantity for i in self.items.values())

    def clear(self): self.items = {}

    def convert_to_order(self) -> Optional[Order]:
        if not self.items: return None
        order = Order(str(uuid.uuid4()), self.owner, list(self.items.values()))
        self.clear()
        return order

    def to_dict(self):
        return {"owner_id": self.owner.account_id,
                "items": [i.to_dict() for i in self.items.values()],
                "total": self.total(), "item_count": self.item_count()}

    def __repr__(self): return f"<ShoppingCart {self.owner.username} ${self.total()}>"


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class Order:
    STATUS_CHOICES = ["pending","processing","shipped","delivered","cancelled","refunded"]

    def __init__(self, order_id, customer: Customer, items: List[CartItem]):
        self.order_id = order_id
        self.customer = customer
        self.items = items
        self.status = "pending"
        self.placed_at = datetime.now()
        self.total_amount = round(sum(i.subtotal() for i in items), 2)
        self.invoice: Optional[Invoice] = None
        self.payments: List[Payment] = []
        self.shipments: List[Shipment] = []
        self.feedback: Optional[Feedback] = None
        self.support_tickets: List[SupportTicket] = []

    def update_status(self, s):
        if s in self.STATUS_CHOICES: self.status = s; return True
        return False

    def generate_invoice(self) -> Invoice:
        import uuid
        
        # Calculate grand total including shipping
        shipping = 0 if self.total_amount >= 25 else 3.99
        grand_total = round(self.total_amount + shipping, 2)
        
        self.invoice = Invoice(
            invoice_id=str(uuid.uuid4()),
            order=self,
            amount=grand_total,
        )
        return self.invoice

    def add_payment(self, p: Payment): self.payments.append(p)

    def is_paid(self):
        return sum(p.amount for p in self.payments if p.status == "completed") >= self.total_amount

    def add_shipment(self, s: Shipment):
        self.shipments.append(s)

    def add_support_ticket(self, ticket: SupportTicket):
        self.support_tickets.append(ticket)

    def receive_feedback(self, rating, comment) -> Feedback:
        self.feedback = Feedback(str(uuid.uuid4()), self, self.customer, rating, comment)
        return self.feedback

    def to_dict(self):
        return {"order_id": self.order_id, "customer_id": self.customer.account_id,
                "customer_name": self.customer.username, "status": self.status,
                "placed_at": self.placed_at.isoformat(), "total_amount": self.total_amount,
                "items": [i.to_dict() for i in self.items], "is_paid": self.is_paid(),
                "invoice_id": self.invoice.invoice_id if self.invoice else None}

    def __repr__(self): return f"<Order {self.order_id} [{self.status}] ${self.total_amount}>"


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class Invoice:
    def __init__(self, invoice_id, order: Order, amount):
        self.invoice_id = invoice_id
        self.order = order
        self.amount = amount
        self.issued_at = datetime.now()
        self.is_paid = False

    def mark_paid(self): self.is_paid = True

    def to_dict(self):
        return {"invoice_id": self.invoice_id, "order_id": self.order.order_id,
                "amount": self.amount, "issued_at": self.issued_at.isoformat(),
                "is_paid": self.is_paid}

    def __repr__(self): return f"<Invoice {self.invoice_id} ${self.amount}>"


# ---------------------------------------------------------------------------
# PaymentGateway  (Strategy Pattern)
# ---------------------------------------------------------------------------

class PaymentGateway(ABC):
    @abstractmethod
    def process(self, amount, reference) -> dict: pass
    @abstractmethod
    def refund(self, transaction_id, amount) -> bool: pass
    @abstractmethod
    def gateway_name(self) -> str: pass


class CreditCardGateway(PaymentGateway):
    def __init__(self, card_number_masked, expiry):
        self.card_number_masked = card_number_masked
        self.expiry = expiry

    def process(self, amount, reference):
        return {"success": True, "transaction_id": str(uuid.uuid4()),
                "gateway": self.gateway_name(), "amount": amount}

    def refund(self, tid, amount): return True
    def gateway_name(self): return "CreditCardGateway"

    def to_dict(self):
        return {"gateway": self.gateway_name(), "card_masked": self.card_number_masked}

    def __repr__(self): return f"<CreditCardGateway {self.card_number_masked}>"


class EWalletGateway(PaymentGateway):
    def __init__(self, wallet_id, provider="GenericWallet"):
        self.wallet_id = wallet_id
        self.provider = provider

    def process(self, amount, reference):
        return {"success": True, "transaction_id": str(uuid.uuid4()),
                "gateway": self.gateway_name(), "amount": amount}

    def refund(self, tid, amount): return True
    def gateway_name(self): return f"EWalletGateway({self.provider})"

    def to_dict(self):
        return {"gateway": self.gateway_name(), "wallet_id": self.wallet_id,
                "provider": self.provider}

    def __repr__(self): return f"<EWalletGateway {self.provider}>"


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

class Payment:
    def __init__(self, payment_id, order: Order, amount, gateway: PaymentGateway):
        self.payment_id = payment_id
        self.order = order
        self.amount = amount
        self.gateway = gateway
        self.status = "pending"
        self.transaction_id: Optional[str] = None
        self.created_at = datetime.now()
        self.processed_at: Optional[datetime] = None

    def process(self) -> bool:
        r = self.gateway.process(self.amount, self.payment_id)
        if r.get("success"):
            self.status = "completed"
            self.transaction_id = r["transaction_id"]
            self.processed_at = datetime.now()
            if self.order.invoice:
                self.order.invoice.mark_paid()
            return True
        self.status = "failed"; return False

    def refund(self):
        if self.status == "completed" and self.transaction_id:
            ok = self.gateway.refund(self.transaction_id, self.amount)
            if ok: self.status = "refunded"
            return ok
        return False

    def to_dict(self):
        return {"payment_id": self.payment_id, "order_id": self.order.order_id,
                "amount": self.amount, "status": self.status,
                "gateway": self.gateway.gateway_name(),
                "transaction_id": self.transaction_id,
                "created_at": self.created_at.isoformat()}

    def __repr__(self): return f"<Payment {self.payment_id} [{self.status}] ${self.amount}>"


# ---------------------------------------------------------------------------
# Shipment
# ---------------------------------------------------------------------------

class Shipment:
    STATUS_CHOICES = ["preparing","shipped","in_transit","delivered","returned"]

    def __init__(self, shipment_id, order: Order, carrier, tracking_number, destination_address):
        self.shipment_id = shipment_id
        self.order = order
        self.carrier = carrier
        self.tracking_number = tracking_number
        self.destination_address = destination_address
        self.status = "preparing"
        self.shipped_at: Optional[datetime] = None
        self.delivered_at: Optional[datetime] = None

    def ship(self):
        self.status = "shipped"; self.shipped_at = datetime.now()
        self.order.update_status("shipped")

    def mark_delivered(self):
        self.status = "delivered"; self.delivered_at = datetime.now()
        self.order.update_status("delivered")

    def to_dict(self):
        return {"shipment_id": self.shipment_id, "order_id": self.order.order_id,
                "carrier": self.carrier, "tracking_number": self.tracking_number,
                "status": self.status,
                "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
                "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None}

    def __repr__(self): return f"<Shipment {self.shipment_id} [{self.status}]>"


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

class Feedback:
    def __init__(self, feedback_id, order: Order, customer: Customer, rating, comment):
        if not 1 <= rating <= 5: raise ValueError("Rating must be 1–5")
        self.feedback_id = feedback_id
        self.order = order
        self.customer = customer
        self.rating = rating
        self.comment = comment
        self.submitted_at = datetime.now()
        self.support_ticket: Optional[SupportTicket] = None

    def escalate_to_ticket(self, subject="") -> SupportTicket:
        subject = subject or f"Feedback escalation — Order {self.order.order_id}"
        t = self.customer.raise_support_ticket(subject, self.comment)
        self.support_ticket = t
        return t

    def to_dict(self):
        return {"feedback_id": self.feedback_id, "order_id": self.order.order_id,
                "customer_name": self.customer.username, "rating": self.rating,
                "comment": self.comment,
                "submitted_at": self.submitted_at.isoformat()}

    def __repr__(self): return f"<Feedback {self.feedback_id} {self.rating}/5>"


# ---------------------------------------------------------------------------
# SupportTicket
# ---------------------------------------------------------------------------

class SupportTicket:
    STATUS_CHOICES = ["open","in_progress","resolved","closed"]

    def __init__(self, ticket_id, customer: Customer, subject, description, order=None):
        self.ticket_id = ticket_id
        self.customer = customer
        self.subject = subject
        self.description = description
        self.order = order
        self.status = "open"
        self.created_at = datetime.now()
        self.resolved_at: Optional[datetime] = None
        self.resolution_notes = ""
        self.assigned_to = None

    def assign(self, admin: Admin):
        self.assigned_to = admin; self.status = "in_progress"

    def resolve(self, notes=""):
        self.status = "resolved"; self.resolved_at = datetime.now()
        self.resolution_notes = notes

    def close(self): self.status = "closed"

    def reopen(self):
        self.status = "open"
        self.resolved_at = None

    def to_dict(self):
        return {"ticket_id": self.ticket_id, "customer_name": self.customer.username,
                "subject": self.subject, "description": self.description,
                "status": self.status, "created_at": self.created_at.isoformat(),
                "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
                "assigned_to": self.assigned_to.username if self.assigned_to else None}

    def __repr__(self): return f"<SupportTicket [{self.status}] {self.subject}>"


# ---------------------------------------------------------------------------
# Demo / usage example  (run: python all_classes.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("E-Commerce System — Full Demo")
    print("=" * 60)

    # 1. Create accounts via Factory
    customer = AccountFactory.create("customer", "alice", "alice@example.com", "secret", phone="555-0100")
    admin    = AccountFactory.create("admin",    "bob",   "bob@store.com",     "admin123")
    print(f"\n[1] Created: {customer}")
    print(f"    Created: {admin}")

    # 2. Build catalogue
    cat_electronics = Category("cat-1", "Electronics", "Gadgets & devices")
    cat_books       = Category("cat-2", "Books", "Paper & digital books")

    p1 = Product("p-001", "Laptop Pro", "15-inch laptop", 1299.99, 10, "cat-1")
    p2 = Product("p-002", "Python Book", "Learn Python fast", 39.99, 50, "cat-2")
    p3 = Product("p-003", "Wireless Mouse", "Ergonomic mouse", 29.99, 0)  # out of stock

    cat_electronics.add_product(p1)
    cat_electronics.add_product(p3)
    cat_books.add_product(p2)

    catalogue = Catalogue("cat-main", "Main Store Catalogue")
    catalogue.add_category(cat_electronics)
    catalogue.add_category(cat_books)
    print(f"\n[2] Catalogue: {len(catalogue.all_products())} products across {len(catalogue.categories)} categories")

    # 3. Manager manages products
    mgr = Manager.get_instance()
    for p in catalogue.all_products():
        mgr.manage_product(p)
    print(f"\n[3] Manager tracking {len(mgr.products)} products")

    # 4. Customer shops
    cart = customer.get_or_create_cart()
    cart.add_product(p1, 1)
    cart.add_product(p2, 2)
    added_oos = cart.add_product(p3, 1)  # should fail — out of stock
    print(f"\n[4] Cart: {cart.item_count()} items, total=${cart.total()}")
    print(f"    Out-of-stock add succeeded: {added_oos}")

    # 5. Place order
    order = customer.place_order()
    print(f"\n[5] Order placed: {order}")

    # 6. Manager processes order
    mgr.process_order(order)
    print(f"\n[6] Order status after processing: {order.status}")

    # 7. Generate invoice
    invoice = order.generate_invoice()
    print(f"\n[7] Invoice: {invoice}")

    # 8. Pay with credit card
    cc_gw  = CreditCardGateway("**** **** **** 4242", "12/27")
    payment = Payment(str(uuid.uuid4()), order, order.total_amount, cc_gw)
    order.add_payment(payment)
    ok = payment.process()
    print(f"\n[8] Payment processed: {ok}, status={payment.status}, txn={payment.transaction_id[:8]}…")
    print(f"    Invoice paid: {invoice.is_paid}")

    # 9. Shipment
    shipment = Shipment(str(uuid.uuid4()), order, "FastShip", "TRK-9999", customer.address or "123 Main St")
    order.add_shipment(shipment)
    shipment.ship()
    print(f"\n[9] Shipment: {shipment}")

    # 10. Feedback
    fb = order.receive_feedback(5, "Excellent service and fast delivery!")
    print(f"\n[10] Feedback: {fb}")

    # 11. Support ticket
    ticket = customer.raise_support_ticket("Question about warranty", "How long is the laptop warranty?")
    ticket.assign(admin)
    ticket.resolve("Warranty is 2 years. See policy page.")
    print(f"\n[11] Support ticket: {ticket}")

    # 12. Admin requests report
    report = admin.request_report("inventory")
    print(f"\n[12] Report: {report}")
    print(f"     Total products in report: {report.data['total_products']}")

    print("\n" + "=" * 60)
    print("Demo complete — all patterns exercised.")
    print("=" * 60)