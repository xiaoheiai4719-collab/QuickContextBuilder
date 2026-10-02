from billing import apply_discount


def checkout_total(cart, discount):
    """Compute checkout_total after a coupon."""
    subtotal = sum(item["price"] * item["quantity"] for item in cart)
    return apply_discount(subtotal, discount)
