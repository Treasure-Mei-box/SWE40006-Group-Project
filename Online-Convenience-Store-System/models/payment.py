"""
Payment model - associated with an Order, uses a PaymentGateway strategy.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from .order import Order
    from .payment_gateway import PaymentGateway


class Payment:
    def __init__(self, payment_id: str, order: Order, amount: float,
                 gateway: PaymentGateway):
        self.payment_id = payment_id
        self.order = order
        self.amount = amount
        self.gateway = gateway
        self.status = "pending"
        self.transaction_id: Optional[str] = None
        self.created_at = datetime.now()
        self.processed_at: Optional[datetime] = None

    def process(self) -> bool:
        result = self.gateway.process(amount=self.amount, reference=self.payment_id)
        if result.get("success"):
            self.status = "completed"
            self.transaction_id = result.get("transaction_id")
            self.processed_at = datetime.now()
            if self.order.invoice:
                self.order.invoice.mark_paid()
            return True
        self.status = "failed"
        return False

    def refund(self) -> bool:
        if self.status == "completed" and self.transaction_id:
            success = self.gateway.refund(self.transaction_id, self.amount)
            if success:
                self.status = "refunded"
            return success
        return False

    def to_dict(self) -> dict:
        return {
            "payment_id": self.payment_id,
            "order_id": self.order.order_id,
            "amount": self.amount,
            "status": self.status,
            "gateway": self.gateway.gateway_name(),
            "transaction_id": self.transaction_id,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }

    def __repr__(self):
        return f"<Payment {self.payment_id} [{self.status}] ${self.amount}>"