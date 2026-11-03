"""
Customer model - extends Account. Owns a ShoppingCart, places Orders,
receives Feedback, submits SupportTickets, and can be analyzed.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from .account import Account

if TYPE_CHECKING:
    from .shopping_cart import ShoppingCart
    from .order import Order
    from .feedback import Feedback
    from .support_ticket import SupportTicket


class Customer(Account):
    """Registered customer with shopping and support capabilities."""

    def __init__(self, account_id: str, username: str, email: str,
                 password_hash: str, phone: str = "", address: str = ""):
        super().__init__(account_id, username, email, password_hash)
        self.phone = phone
        self.address = address
        #to initialize the address book with the signup address
        self.addresses: List[str] = [address] if address else []
        self.shopping_cart: Optional[ShoppingCart] = None
        self.orders: List[Order] = []
        self.feedback_list: List[Feedback] = []
        self.support_tickets: List[SupportTicket] = []
        self.notifications: List[dict] = []

    def get_or_create_cart(self) -> ShoppingCart:
        from .shopping_cart import ShoppingCart
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
        from .support_ticket import SupportTicket
        import uuid
        ticket = SupportTicket(
            ticket_id=str(uuid.uuid4()),
            customer=self,
            subject=subject,
            description=description,
        )
        self.support_tickets.append(ticket)
        return ticket
    
    def add_notification(self, message: str, order_id: str = None):
        import uuid
        from datetime import datetime
        self.notifications.append({
            "notification_id": str(uuid.uuid4())[:8].upper(),
            "message": message,
            "order_id": order_id,
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "read": False
        })

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "phone": self.phone,
            "address": self.address,
            "addresses": self.addresses, 
            "notifications": self.notifications,
            "order_count": len(self.orders),
            "ticket_count": len(self.support_tickets),
        })
        return base

    def __repr__(self):
        return f"<Customer {self.account_id}: {self.username}>"