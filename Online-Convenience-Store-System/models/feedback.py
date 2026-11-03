"""
Feedback model - received by Order from Customer. Linked to SupportTicket.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from .order import Order
    from .customer import Customer
    from .support_ticket import SupportTicket


class Feedback:
    def __init__(self, feedback_id: str, order: Order,
                 customer: Customer, rating: int, comment: str):
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5.")
        self.feedback_id = feedback_id
        self.order = order
        self.customer = customer
        self.rating = rating
        self.comment = comment
        self.submitted_at = datetime.now()
        self.support_ticket: Optional[SupportTicket] = None

    def escalate_to_ticket(self, subject: str = "") -> SupportTicket:
        if not subject:
            subject = f"Feedback escalation — Order {self.order.order_id}"
        ticket = self.customer.raise_support_ticket(
            subject=subject,
            description=self.comment,
        )
        self.support_ticket = ticket
        return ticket

    def to_dict(self) -> dict:
        return {
            "feedback_id": self.feedback_id,
            "order_id": self.order.order_id,
            "customer_id": self.customer.account_id,
            "customer_name": self.customer.username,
            "rating": self.rating,
            "comment": self.comment,
            "submitted_at": self.submitted_at.isoformat(),
            "ticket_id": self.support_ticket.ticket_id if self.support_ticket else None,
        }

    def __repr__(self):
        return f"<Feedback {self.feedback_id} rating={self.rating}/5>"