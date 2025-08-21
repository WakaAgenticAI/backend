"""
Simple demo script to exercise the API via HTTP (curl-style).
Usage:
  python api_demo.py --base http://localhost:8000/api/v1
"""
from __future__ import annotations
import argparse
import sys
import httpx
import os


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000/api/v1", help="Base URL prefix")
    parser.add_argument("--ai", nargs="?", const="Say hello in one short sentence.", help="Optional: call /ai/complete with a prompt. Uses GROQ_API_KEY from env.")
    args = parser.parse_args()

    base = args.base.rstrip("/")

    with httpx.Client(timeout=10) as client:
        r1 = client.get(f"{base}/healthz")
        print("GET /healthz:", r1.status_code, r1.json())

        r2 = client.get(f"{base}/readyz")
        print("GET /readyz:", r2.status_code, r2.json())

        r3 = client.get(f"{base}/demo/testall")
        print("GET /demo/testall:", r3.status_code, r3.json())

        if args.ai is not None:
            if not os.getenv("GROQ_API_KEY"):
                print("Skipping /ai/complete: GROQ_API_KEY not set in environment.")
            else:
                r4 = client.post(f"{base}/ai/complete", json={"prompt": args.ai})
                print("POST /ai/complete:", r4.status_code, r4.json())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
