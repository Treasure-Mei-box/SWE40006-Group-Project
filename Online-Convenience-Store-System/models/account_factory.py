"""
AccountFactory - Factory Pattern for creating Account instances (Customer or Admin).
"""
from __future__ import annotations
import uuid
import hashlib
from typing import TYPE_CHECKING
from .account import Account

if TYPE_CHECKING:
    from .customer import Customer
    from .admin import Admin


class AccountFactory:
    """
    Factory class for creating Account subclasses (Customer or Admin).
    Implements the Factory design pattern.
    """

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def create(account_type: str, username: str, email: str, password: str, **kwargs) -> Account:
        from .customer import Customer
        from .admin import Admin

        account_id = str(uuid.uuid4())
        password_hash = AccountFactory._hash_password(password)

        if account_type.lower() == "customer":
            return Customer(account_id, username, email, password_hash, **kwargs)
        elif account_type.lower() == "admin":
            return Admin(account_id, username, email, password_hash, **kwargs)
        else:
            raise ValueError(f"Unknown account type: '{account_type}'. Use 'customer' or 'admin'.")

    def __repr__(self):
        return "<AccountFactory>"