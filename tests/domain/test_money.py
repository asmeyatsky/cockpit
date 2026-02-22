"""
Domain Tests - Value Objects

Architectural Intent:
- Domain model tests - no mocks needed, pure logic
- Tests verify value object behavior and invariants
"""

import pytest
from decimal import Decimal

from domain.value_objects.money import Money


class TestMoney:
    def test_create_money(self):
        money = Money(Decimal("100.50"), "USD")

        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"

    def test_add_money(self):
        money1 = Money(Decimal("100.00"), "USD")
        money2 = Money(Decimal("50.00"), "USD")

        result = money1 + money2

        assert result.amount == Decimal("150.00")
        assert result.currency == "USD"

    def test_add_money_different_currency(self):
        money1 = Money(Decimal("100.00"), "USD")
        money2 = Money(Decimal("50.00"), "EUR")

        with pytest.raises(ValueError):
            money1 + money2

    def test_subtract_money(self):
        money1 = Money(Decimal("100.00"), "USD")
        money2 = Money(Decimal("30.00"), "USD")

        result = money1 - money2

        assert result.amount == Decimal("70.00")

    def test_multiply_money(self):
        money = Money(Decimal("100.00"), "USD")

        result = money * 0.5

        assert result.amount == Decimal("50.00")

    def test_compare_money(self):
        money1 = Money(Decimal("100.00"), "USD")
        money2 = Money(Decimal("50.00"), "USD")
        money3 = Money(Decimal("100.00"), "USD")

        assert money1 > money2
        assert money2 < money1
        assert money1 == money3

    def test_format(self):
        money = Money(Decimal("1234.56"), "USD")

        formatted = money.format()

        assert formatted == "USD 1,234.56"

    def test_zero(self):
        zero = Money.zero()

        assert zero.amount == Decimal("0")
        assert zero.currency == "USD"

    def test_immutability(self):
        money = Money(Decimal("100.00"), "USD")
        original_amount = money.amount

        money + Money(Decimal("50.00"), "USD")

        assert money.amount == original_amount
