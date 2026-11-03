"""
PaymentGateway - Strategy Pattern interface.
CreditCardGateway and EWalletGateway are concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Optional


class PaymentGateway(ABC):
    """
    <<Strategy>> <<Interface>>
    Abstract payment gateway. Concrete strategies: CreditCardGateway, EWalletGateway.
    """

    @abstractmethod
    def process(self, amount: float, reference: str) -> dict:
        """Process a payment. Returns a result dict with 'success' and 'transaction_id'."""
        pass

    @abstractmethod
    def refund(self, transaction_id: str, amount: float) -> bool:
        pass

    @abstractmethod
    def gateway_name(self) -> str:
        pass


class CreditCardGateway(PaymentGateway):
    """Concrete strategy — credit/debit card processing."""

    def __init__(self, card_number_masked: str, expiry: str):
        self.card_number_masked = card_number_masked
        self.expiry = expiry

    def process(self, amount: float, reference: str) -> dict:
        import uuid
        # Simulate processing
        return {
            "success": True,
            "transaction_id": str(uuid.uuid4()),
            "gateway": self.gateway_name(),
            "amount": amount,
            "reference": reference,
        }

    def refund(self, transaction_id: str, amount: float) -> bool:
        return True  # Simulate successful refund

    def gateway_name(self) -> str:
        return "CreditCardGateway"

    def to_dict(self) -> dict:
        return {
            "gateway": self.gateway_name(),
            "card_masked": self.card_number_masked,
            "expiry": self.expiry,
        }

    def __repr__(self):
        return f"<CreditCardGateway card={self.card_number_masked}>"


class EWalletGateway(PaymentGateway):
    """Concrete strategy — e-wallet payment processing."""

    def __init__(self, wallet_id: str, provider: str = "GenericWallet"):
        self.wallet_id = wallet_id
        self.provider = provider

    def process(self, amount: float, reference: str) -> dict:
        import uuid
        return {
            "success": True,
            "transaction_id": str(uuid.uuid4()),
            "gateway": self.gateway_name(),
            "amount": amount,
            "reference": reference,
            "provider": self.provider,
        }

    def refund(self, transaction_id: str, amount: float) -> bool:
        return True

    def gateway_name(self) -> str:
        return f"EWalletGateway({self.provider})"

    def to_dict(self) -> dict:
        return {
            "gateway": self.gateway_name(),
            "wallet_id": self.wallet_id,
            "provider": self.provider,
        }

    def __repr__(self):
        return f"<EWalletGateway provider={self.provider} wallet={self.wallet_id}>"