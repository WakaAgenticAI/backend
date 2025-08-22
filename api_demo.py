"""
Simple demo script to exercise the API via HTTP (curl-style).
Usage:
  python api_demo.py --base http://localhost:8000/api/v1 \
    --email admin@example.com --password admin123 \
    --ai "Say hello in one short sentence." \
    --create-product --create-order

Notes:
- Uses seeded Admin user from app.main (email: admin@example.com, password: admin123)
- Sends Authorization: Bearer <access_token> for protected routes
"""
from __future__ import annotations
import argparse
import sys
import httpx
import os
import random
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000/api/v1", help="Base URL prefix")
    parser.add_argument("--email", default="admin@example.com", help="Login email for /auth/login")
    parser.add_argument("--password", default="admin123", help="Login password for /auth/login")
    parser.add_argument("--ai", nargs="?", const="Say hello in one short sentence.", help="Optional: call /ai/complete with a prompt. Uses GROQ_API_KEY from env.")
    parser.add_argument("--create-product", action="store_true", help="Attempt to create a sample product")
    parser.add_argument("--create-order", action="store_true", help="Attempt to create a sample order for first product")
    parser.add_argument("--create-customer", action="store_true", help="Attempt to create a sample customer")
    args = parser.parse_args()

    base = args.base.rstrip("/")

    def p(label: str, resp: httpx.Response):
        try:
            print(label, resp.status_code, resp.json())
        except Exception:
            print(label, resp.status_code, resp.text)

    with httpx.Client(timeout=15) as client:
        # Public health & diagnostics
        p("GET /healthz:", client.get(f"{base}/healthz"))
        p("GET /readyz:", client.get(f"{base}/readyz"))
        p("GET /demo/testall:", client.get(f"{base}/demo/testall"))

        # Auth: login to get bearer tokens
        tokens = None
        try:
            r = client.post(f"{base}/auth/login", json={"email": args.email, "password": args.password})
            p("POST /auth/login:", r)
            if r.status_code == 200:
                tokens = r.json()
        except Exception as e:
            print("Login error:", e)

        headers = {}
        if tokens and tokens.get("access_token"):
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        if headers:
            # Customers: list and optionally create
            p("GET /customers:", client.get(f"{base}/customers", headers=headers))
            if args.create_customer:
                rnd = random.randint(1000, 9999)
                cust = {
                    "email": f"demo{rnd}@example.com",
                    "name": f"Demo User {rnd}",
                    "phone": None,
                    "segment": "regular",
                    "status": "active",
                    "location": None,
                }
                p("POST /customers:", client.post(f"{base}/customers", headers=headers, json=cust))

            # Authenticated: /auth/me
            p("GET /auth/me:", client.get(f"{base}/auth/me", headers=headers))

            # Products: list and optionally create
            p("GET /products:", client.get(f"{base}/products", headers=headers))
            if args.create_product:
                sku = f"SKU-DEMO-{random.randint(1000,9999)}"
                prod = {
                    "sku": sku,
                    "name": f"Demo Product {sku[-4:]}",
                    "unit": "unit",
                    "price_ngn": 1234.0,
                    "tax_rate": 7.5,
                }
                p("POST /products:", client.post(f"{base}/products", headers=headers, json=prod))

            # Inventory: warehouses and inventory list
            p("GET /warehouses:", client.get(f"{base}/warehouses", headers=headers))
            p("GET /inventory:", client.get(f"{base}/inventory", headers=headers))

            # Orders: list and optionally create + fulfill
            p("GET /orders:", client.get(f"{base}/orders", headers=headers))
            created_order_id = None
            if args.create_order:
                # naive: create order with one line item for first product id=1 if exists
                order_body = {
                    "currency": "NGN",
                    "items": [
                        {"product_id": 1, "quantity": 1, "unit_price": 1000.0},
                    ],
                }
                resp = client.post(f"{base}/orders", headers=headers, json=order_body)
                p("POST /orders:", resp)
                if resp.status_code == 200:
                    created_order_id = resp.json().get("id")
                    # Try fulfill
                    if created_order_id:
                        time.sleep(0.3)
                        p(
                            f"POST /orders/{created_order_id}/fulfill:",
                            client.post(f"{base}/orders/{created_order_id}/fulfill", headers=headers),
                        )

            # Chat routing minimal check
            p(
                "POST /chat/route:",
                client.post(
                    f"{base}/chat/route",
                    headers=headers,
                    json={"intent": "help", "payload": {"text": "hello"}},
                ),
            )

            # Tools execute (example payload)
            p(
                "POST /tools/execute:",
                client.post(
                    f"{base}/tools/execute",
                    headers=headers,
                    json={"intent": "echo", "payload": {"message": "demo"}},
                ),
            )

        # Optional AI completion
        if args.ai is not None:
            if not os.getenv("GROQ_API_KEY"):
                print("Skipping /ai/complete: GROQ_API_KEY not set in environment.")
            else:
                p("POST /ai/complete:", client.post(f"{base}/ai/complete", json={"prompt": args.ai}))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
