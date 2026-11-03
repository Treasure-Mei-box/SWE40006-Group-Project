"""
Catalogue model - aggregates Categories and Products. Managed by Manager.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .category import Category
    from .product import Product


class Catalogue:
    def __init__(self, catalogue_id: str, name: str):
        self.catalogue_id = catalogue_id
        self.name = name
        self.categories: List[Category] = []

    def add_category(self, category: Category):
        if not any(c.category_id == category.category_id for c in self.categories):
            self.categories.append(category)

    def remove_category(self, category_id: str) -> bool:
        before = len(self.categories)
        self.categories = [c for c in self.categories if c.category_id != category_id]
        return len(self.categories) < before

    def get_category(self, category_id: str) -> Optional[Category]:
        return next((c for c in self.categories if c.category_id == category_id), None)

    def all_products(self) -> List[Product]:
        products = []
        seen: set = set()
        for cat in self.categories:
            for p in cat.products:
                if p.product_id not in seen:
                    products.append(p)
                    seen.add(p.product_id)
        return products

    def search(self, query: str) -> List[Product]:
        q = query.lower()
        return [p for p in self.all_products() if q in p.name.lower() or q in p.description.lower()]

    def filter_by_category(self, category_id: str) -> List[Product]:
        cat = self.get_category(category_id)
        return cat.products if cat else []

    def to_dict(self) -> dict:
        return {
            "catalogue_id": self.catalogue_id,
            "name": self.name,
            "category_count": len(self.categories),
            "categories": [c.to_dict() for c in self.categories],
        }

    def __repr__(self):
        return f"<Catalogue {self.catalogue_id}: {self.name}>"