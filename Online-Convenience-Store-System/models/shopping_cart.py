"""
ShoppingCart model - owned by Customer (composition), contains CartItems,
queries Catalogue for stock availability, and converts to an Order.
ShoppingCart ..> Catalogue : queries stock  (UML dependency)
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Optional
from datetime import datetime

if TYPE_CHECKING:
    from .customer import Customer
    from .product import Product
    from .catalogue import Catalogue
    from .order import Order


class CartItem:
    def __init__(self, product: Product, quantity: int):
        self.product = product
        self.quantity = quantity

    def subtotal(self) -> float:
        return round(self.product.price * self.quantity, 2)

    def to_dict(self) -> dict:
        return {
            "product_id": self.product.product_id,
            "product_name": self.product.name,
            "price": self.product.price,
            "quantity": self.quantity,
            "subtotal": self.subtotal(),
        }


class ShoppingCart:
    def __init__(self, owner: Customer):
        self.owner = owner
        self.items: Dict[str, CartItem] = {}
        self.created_at = datetime.now()

    def add_product(self, product: Product, quantity: int = 1,
                    catalogue: Optional[Catalogue] = None) -> bool:
        """
        Add a product to the cart.
        Optionally accepts a Catalogue reference to verify system-wide
        availability (UML: ShoppingCart ..> Catalogue : queries stock).
        Falls back to direct product.is_available() check.
        """
        # Delegate to Catalogue if provided (Information Expert for inventory)
        if catalogue is not None:
            all_products = catalogue.all_products()
            live_product = next((p for p in all_products
                                 if p.product_id == product.product_id), None)
            if live_product is None or not live_product.is_available():
                return False
        else:
            if not product.is_available():
                return False

        if product.product_id in self.items:
            self.items[product.product_id].quantity += quantity
        else:
            self.items[product.product_id] = CartItem(product, quantity)
        return True

    def remove_product(self, product_id: str) -> bool:
        if product_id in self.items:
            del self.items[product_id]
            return True
        return False

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

    def total(self) -> float:
        return round(sum(item.subtotal() for item in self.items.values()), 2)

    def item_count(self) -> int:
        return sum(item.quantity for item in self.items.values())

    def clear(self):
        self.items = {}

    def convert_to_order(self) -> Optional[Order]:
        """
        Snapshots cart items into a pending Order WITHOUT clearing the cart
        or reducing stock. Stock reduction and cart clear happen only after
        payment is confirmed via confirm_order(). This prevents the cart from
        being wiped if the customer cancels the payment modal and retries.

        CRC 4.9: 'Converts cart contents to an Order — Order, Customer'
        CRC 4.9: 'Clear all items after successful order placement — Order'
        A2 Scenario 1: cart clears only after Steps 14-16 (payment authorised).
        """
        if not self.items:
            return None

        # Validate sufficient stock for every item before creating the Order
        for item in self.items.values():
            if item.product.stock_quantity < item.quantity:
                return None  # Abort — insufficient stock

        from .order import Order
        import uuid

        # Snapshot cart items (cart NOT cleared until payment confirmed)
        order_items = list(self.items.values())

        order = Order(
            order_id=str(uuid.uuid4()),
            customer=self.owner,
            items=order_items,
        )
        return order

    def confirm_order(self) -> None:
        """
        Called after payment succeeds (A2 Scenario 1 Step 16).
        Reduces stock for each product and clears the cart.
        CRC 4.9: 'Clear all items after successful order placement'
        """
        for item in self.items.values():
            item.product.reduce_stock(item.quantity)
        self.clear()

    def to_dict(self) -> dict:
        return {
            "owner_id": self.owner.account_id,
            "items": [item.to_dict() for item in self.items.values()],
            "total": self.total(),
            "item_count": self.item_count(),
        }

    def __repr__(self):
        return (f"<ShoppingCart owner={self.owner.username} "
                f"items={self.item_count()} total=${self.total()}>")