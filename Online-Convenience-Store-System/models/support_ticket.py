"""
SupportTicket model - raised by Customer, related to Orders and Feedback.
Resolved by Admin.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from .customer import Customer
    from .order import Order
    from .admin import Admin


class SupportTicket:
    STATUS_CHOICES = ["open", "in_progress", "resolved", "closed"]

    def __init__(self, ticket_id: str, customer: Customer,
                 subject: str, description: str,
                 order: Optional[Order] = None):
        self.ticket_id = ticket_id
        self.customer = customer
        self.subject = subject
        self.description = description
        self.order = order
        self.status = "open"
        self.created_at = datetime.now()
        self.resolved_at: Optional[datetime] = None
        self.resolution_notes: str = ""
        self.assigned_to: Optional[Admin] = None

    def assign(self, admin: Admin):
        self.assigned_to = admin
        self.status = "in_progress"

    def resolve(self, notes: str = ""):
        self.status = "resolved"
        self.resolved_at = datetime.now()
        self.resolution_notes = notes

    def close(self):
        self.status = "closed"

    def reopen(self):
        self.status = "open"
        self.resolved_at = None

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "customer_id": self.customer.account_id,
            "customer_name": self.customer.username,
            "subject": self.subject,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
            "assigned_to": self.assigned_to.username if self.assigned_to else None,
            "order_id": self.order.order_id if self.order else None,
        }

    def __repr__(self):
        return f"<SupportTicket {self.ticket_id} [{self.status}]: {self.subject}>"