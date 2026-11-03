"""
Order model - placed by Customer, processed by Manager.
Generates Invoice, Paid By Payment, Updates Status via Shipment,
Ships, Receives Feedback, and Raises SupportTickets.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from datetime import datetime

if TYPE_CHECKING:
    from .customer import Customer
    from .shopping_cart import CartItem
    from .invoice import Invoice
    from .payment import Payment
    from .shipment import Shipment
    from .feedback import Feedback
    from .support_ticket import SupportTicket


class Order:
    STATUS_CHOICES = ["pending", "processing", "shipped", "delivered", "cancelled", "refunded"]

    def __init__(self, order_id: str, customer: Customer, items: List[CartItem]):
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

    def update_status(self, new_status: str) -> bool:
        if new_status in self.STATUS_CHOICES:
            self.status = new_status
            return True
        return False

    def generate_invoice(self) -> Invoice:
        from .invoice import Invoice
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

    def add_payment(self, payment: Payment):
        self.payments.append(payment)

    def is_paid(self) -> bool:
        paid = sum(p.amount for p in self.payments if p.status == "completed")
        return paid >= self.total_amount

    def add_shipment(self, shipment: Shipment):
        self.shipments.append(shipment)
    
    def add_support_ticket(self, ticket: SupportTicket):
        self.support_tickets.append(ticket)    

    def receive_feedback(self, rating: int, comment: str) -> Feedback:
        from .feedback import Feedback
        import uuid
        self.feedback = Feedback(
            feedback_id=str(uuid.uuid4()),
            order=self,
            customer=self.customer,
            rating=rating,
            comment=comment,
        )
        return self.feedback

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "customer_id": self.customer.account_id,
            "customer_name": self.customer.username,
            "status": self.status,
            "placed_at": self.placed_at.isoformat(),
            "total_amount": self.total_amount,
            "items": [item.to_dict() for item in self.items],
            "is_paid": self.is_paid(),
            "invoice_id": self.invoice.invoice_id if self.invoice else None,
        }

    def __repr__(self):
        return f"<Order {self.order_id} [{self.status}] ${self.total_amount}>"