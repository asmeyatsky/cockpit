"""
Cloud Cost Value Object

Architectural Intent:
- Immutable value object representing monetary values with currency
- Encapsulates cost calculation and formatting logic
- Used throughout the system for cost tracking and optimization
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self):
        if isinstance(self.amount, float):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} to {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, multiplier: float) -> "Money":
        return Money(self.amount * Decimal(str(multiplier)), self.currency)

    def __lt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare {self.currency} to {other.currency}")
        return self.amount < other.amount

    def __gt__(self, other: "Money") -> bool:
        return other < self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def format(self) -> str:
        return f"{self.currency} {self.amount:,.2f}"

    @staticmethod
    def zero(currency: str = "USD") -> "Money":
        return Money(Decimal("0"), currency)
