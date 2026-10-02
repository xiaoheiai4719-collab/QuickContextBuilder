"""Small original currency helper, not a production billing library."""
from decimal import Decimal, ROUND_HALF_UP


def round_amount(value):
    """Round currency half up: 2.675 becomes 2.68."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def apply_discount(amount, percent):
    return round_amount(Decimal(str(amount)) * (1 - Decimal(str(percent)) / 100))
