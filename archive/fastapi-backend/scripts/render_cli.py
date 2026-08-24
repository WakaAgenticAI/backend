#!/usr/bin/env python3
"""
Simple Render API CLI for local automation.

Usage:
  export RENDER_API_KEY=...
  python backend/scripts/render_cli.py workspaces
  python backend/scripts/render_cli.py services [--workspace-id <ID>]
"""
from __future__ import annotations
import os
import sys
import argparse
import json
from typing import Any, Dict, List

try:
    import httpx  # type: ignore
except Exception as e:
    print("httpx is required. Install in backend env: pip install httpx", file=sys.stderr)
    sys.exit(2)

API_BASE = os.environ.get("RENDER_API_BASE", "https://api.render.com/v1")
API_KEY = os.environ.get("RENDER_API_KEY")


def _client() -> httpx.Client:
    if not API_KEY:
        print("RENDER_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    return httpx.Client(
        base_url=API_BASE,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json",
            "User-Agent": "wakaagent-render-cli/1.0",
        },
        timeout=30.0,
    )


def list_workspaces() -> List[Dict[str, Any]]:
    with _client() as c:
        r = c.get("/workspaces")
        r.raise_for_status()
        return r.json()


def list_services(workspace_id: str | None = None) -> List[Dict[str, Any]]:
    services: List[Dict[str, Any]] = []
    with _client() as c:
        cursor = None
        while True:
            params = {"limit": 100}
            if cursor:
                params["cursor"] = cursor
            # Render services list
            r = c.get("/services", params=params)
            r.raise_for_status()
            data = r.json()
            items = data if isinstance(data, list) else data.get("items", [])
            services.extend(items)
            cursor = (data.get("cursor") if isinstance(data, dict) else None) or None
            if not cursor:
                break

    if workspace_id:
        # Best-effort filter by owner/workspace id across possible shapes
        filtered = []
        for s in services:
            if s.get("ownerId") == workspace_id:
                filtered.append(s)
                continue
            owner = s.get("owner") or {}
            if owner.get("id") == workspace_id:
                filtered.append(s)
                continue
            ws = s.get("workspace") or {}
            if ws.get("id") == workspace_id:
                filtered.append(s)
        services = filtered
    return services


def main() -> None:
    ap = argparse.ArgumentParser(description="Render API CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("workspaces", help="List workspaces")

    p_services = sub.add_parser("services", help="List services (optionally filter by workspace id)")
    p_services.add_argument("--workspace-id", dest="workspace_id", help="Workspace ID to filter services", default=None)

    args = ap.parse_args()

    if args.cmd == "workspaces":
        ws = list_workspaces()
        print(json.dumps(ws, indent=2))
        return

    if args.cmd == "services":
        svcs = list_services(args.workspace_id)
        print(json.dumps(svcs, indent=2))
        return

    ap.print_help()


if __name__ == "__main__":
    main()
