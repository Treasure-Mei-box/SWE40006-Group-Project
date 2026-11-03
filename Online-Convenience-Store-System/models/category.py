"""
Category model - groups Products. Contained in Catalogue, used to filter products.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .product import Product


class Category:
    """A product classification group."""

    def __init__(self, category_id: str, name: str, description: str = ""):
        self.category_id = category_id
        self.name = name
        self.description = description
        self.products: List[Product] = []
        self.is_active: bool = True

    def add_product(self, product: Product):
        product.category_id = self.category_id
        if not any(p.product_id == product.product_id for p in self.products):
            self.products.append(product)

    def remove_product(self, product_id: str) -> bool:
        before = len(self.products)
        self.products = [p for p in self.products if p.product_id != product_id]
        return len(self.products) < before

    def filter_available(self) -> List[Product]:
        return [p for p in self.products if p.is_available()]

    def to_dict(self) -> dict:
        return {
            "category_id": self.category_id,
            "name": self.name,
            "description": self.description,
            "product_count": len(self.products),
            "is_active": self.is_active,
            "products": [p.to_dict() for p in self.products],
        }

    def __repr__(self):
        return f"<Category {self.category_id}: {self.name}>"