"""
Shipment model - linked to Order, updates order status.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from .order import Order


class Shipment:
    STATUS_CHOICES = ["preparing", "shipped", "in_transit", "delivered", "returned"]

    def __init__(self, shipment_id: str, order: Order,
                 carrier: str, tracking_number: str,
                 destination_address: str):
        self.shipment_id = shipment_id
        self.order = order
        self.carrier = carrier
        self.tracking_number = tracking_number
        self.destination_address = destination_address
        self.status = "preparing"
        self.shipped_at: Optional[datetime] = None
        self.delivered_at: Optional[datetime] = None
        self.estimated_delivery: Optional[datetime] = None

    def ship(self):
        self.status = "shipped"
        self.shipped_at = datetime.now()
        self.order.update_status("shipped")

    def mark_in_transit(self):
        self.status = "in_transit"

    def mark_delivered(self):
        self.status = "delivered"
        self.delivered_at = datetime.now()
        self.order.update_status("delivered")

    def mark_returned(self):
        self.status = "returned"
        self.order.update_status("refunded")

    def to_dict(self) -> dict:
        return {
            "shipment_id": self.shipment_id,
            "order_id": self.order.order_id,
            "carrier": self.carrier,
            "tracking_number": self.tracking_number,
            "destination_address": self.destination_address,
            "status": self.status,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
        }

    def __repr__(self):
        return f"<Shipment {self.shipment_id} [{self.status}] via {self.carrier}>"