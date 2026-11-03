"""
Account model - base class for Customer and Admin user types.
Created by AccountFactory (Factory Pattern).
"""
from datetime import datetime
from typing import Optional


class Account:
    """Base account class for all system users."""

    def __init__(self, account_id: str, username: str, email: str, password_hash: str):
        self.account_id = account_id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at: datetime = datetime.now()
        self.is_active: bool = True

    def deactivate(self):
        self.is_active = False

    def activate(self):
        self.is_active = True

    def update_email(self, new_email: str):
        self.email = new_email

    def change_password(self, new_password_hash: str):
        self.password_hash = new_password_hash

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }

    def __repr__(self):
        return f"<Account {self.account_id}: {self.username}>"