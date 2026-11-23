"""Fake order database + tools. search_orders is deliberately unforgiving:
a misspelled name returns 'No results' -> this is what makes agents loop."""

ORDERS = {
    "john smith": ("ORD-1001", "shipped, arrives Friday"),
    "priya sharma": ("ORD-1002", "processing, ships tomorrow"),
    "ananya rao": ("ORD-1003", "delivered on Monday"),
    "rahul verma": ("ORD-1004", "out for delivery today"),
    "meera iyer": ("ORD-1005", "shipped, arrives Thursday"),
    "arjun nair": ("ORD-1006", "delayed, new ETA next week"),
    "kavya reddy": ("ORD-1007", "processing, ships today"),
    "sanjay gupta": ("ORD-1008", "delivered on Sunday"),
    "divya menon": ("ORD-1009", "shipped, arrives Saturday"),
    "vikram singh": ("ORD-1010", "out for delivery today"),
}
STATUS = {oid: s for oid, s in ORDERS.values()}


def search_orders(customer_name: str) -> str:
    hit = ORDERS.get(customer_name.strip().lower())
    return f"Found order {hit[0]}" if hit else "No results found."


def get_order_status(order_id: str) -> str:
    return STATUS.get(order_id, "Unknown order id.")


TOOL_FUNCS = {"search_orders": search_orders, "get_order_status": get_order_status}

TOOL_SCHEMAS = [
    {"name": "search_orders",
     "description": "Find a customer's order id by their full name.",
     "input_schema": {"type": "object",
                      "properties": {"customer_name": {"type": "string"}},
                      "required": ["customer_name"]}},
    {"name": "get_order_status",
     "description": "Get shipping status for an order id like ORD-1001.",
     "input_schema": {"type": "object",
                      "properties": {"order_id": {"type": "string"}},
                      "required": ["order_id"]}},
]


def run_tool(name: str, args: dict) -> str:
    try:
        return TOOL_FUNCS[name](**args)
    except Exception as e:  # tool errors go back to the model, not a crash
        return f"Tool error: {e}"
