"""
Admin model - extends Account. Manages Products, analyzes inventory,
and requests Reports from the Manager singleton.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List
from .account import Account

if TYPE_CHECKING:
    from .product import Product
    from .report import Report


class Admin(Account):
    """Platform administrator with product and report management capabilities."""

    def __init__(self, account_id: str, username: str, email: str,
                 password_hash: str, role: str = "admin"):
        super().__init__(account_id, username, email, password_hash)
        self.role = role
        self.managed_products: List[Product] = []

    def add_product(self, product: Product):
        self.managed_products.append(product)

    def remove_product(self, product_id: str) -> bool:
        before = len(self.managed_products)
        self.managed_products = [p for p in self.managed_products if p.product_id != product_id]
        return len(self.managed_products) < before

    def update_product_stock(self, product: Product, quantity: int):
        product.stock_quantity = quantity

    def analyze_inventory(self) -> dict:
        total = sum(p.stock_quantity for p in self.managed_products)
        out_of_stock = [p for p in self.managed_products if p.stock_quantity == 0]
        return {
            "total_units": total,
            "total_products": len(self.managed_products),
            "out_of_stock": [p.to_dict() for p in out_of_stock],
        }

    def request_report(self, report_type: str) -> Report:
        from .manager import Manager
        manager = Manager.get_instance()
        return manager.create_report(report_type, requested_by=self)

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({"role": self.role})
        return base

    def __repr__(self):
        return f"<Admin {self.account_id}: {self.username} ({self.role})>"