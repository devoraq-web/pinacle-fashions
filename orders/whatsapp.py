import urllib.parse
from django.conf import settings

def format_whatsapp_message(order):
    """
    Constructs a beautifully formatted WhatsApp order message matching PINACLE FASHIONS brand guidelines.
    """
    addr = order.address
    lines = [
        "🌟 *NEW ORDER - PINACLE FASHIONS* 🌟",
        f"Order Ref: *#{order.order_number}*",
        "",
        "Hello PINACLE FASHIONS!",
        "I would like to place an order.",
        "",
        "👤 *CUSTOMER DETAILS:*",
        f"• Name: {addr.full_name}",
        f"• Phone: {addr.mobile_number}",
        f"• House / Building: {addr.house_name_number}",
        f"• Street / Area: {addr.street_location}",
        f"• City: {addr.city}",
        f"• District: {addr.district}",
        f"• State: {addr.state}",
        f"• PIN Code: {addr.pin_code}",
    ]

    if addr.delivery_instructions:
        lines.append(f"• Delivery Notes: {addr.delivery_instructions}")

    lines.append("")
    lines.append("🛍️ *ORDER DETAILS:*")

    for idx, item in enumerate(order.items.all(), 1):
        lines.append(f"*{idx}. {item.product_name}*")
        lines.append(f"   • Code: {item.product_code}")
        lines.append(f"   • Size: {item.selected_size} | Colour: {item.selected_colour}")
        lines.append(f"   • Qty: {item.quantity} × ₹{item.unit_price}")
        lines.append(f"   • Item Total: ₹{item.total_price}")

    lines.append("")
    lines.append("💰 *PAYMENT & BILLING:*")
    lines.append(f"• Items Subtotal: ₹{order.subtotal}")
    lines.append(f"• Shipping: {'FREE' if order.shipping_cost == 0 else f'₹{order.shipping_cost}'}")
    lines.append(f"• *Grand Total: ₹{order.total_price}*")
    lines.append("")
    lines.append("Please confirm my order and share delivery details.")
    lines.append("Thank you! ✨")

    message_text = "\n".join(lines)
    return message_text


def get_whatsapp_order_url(order):
    """
    Returns full encoded wa.me link for direct redirect.
    """
    phone = settings.WHATSAPP_NUMBER
    message = format_whatsapp_message(order)
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{phone}?text={encoded}"

