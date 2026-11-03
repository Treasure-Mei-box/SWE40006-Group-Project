"""
ecommerce_app.models — all domain classes from the UML diagram.
Import from here for convenience.
"""

from .account import Account
from .account_factory import AccountFactory
from .customer import Customer
from .admin import Admin
from .manager import Manager
from .report import Report
from .product import Product
from .category import Category
from .catalogue import Catalogue
from .shopping_cart import ShoppingCart, CartItem
from .order import Order
from .invoice import Invoice
from .payment_gateway import PaymentGateway, CreditCardGateway, EWalletGateway
from .payment import Payment
from .shipment import Shipment
from .feedback import Feedback
from .support_ticket import SupportTicket

__all__ = [
    "Account", "AccountFactory",
    "Customer", "Admin",
    "Manager", "Report",
    "Product", "Category", "Catalogue",
    "ShoppingCart", "CartItem",
    "Order", "Invoice",
    "PaymentGateway", "CreditCardGateway", "EWalletGateway",
    "Payment", "Shipment", "Feedback", "SupportTicket",
]