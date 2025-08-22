from fastapi import APIRouter


def get_api_router() -> APIRouter:
    """Lazily build the API router to avoid importing optional deps at import time."""
    from app.api.v1.endpoints import health, testall, ai
    from app.api.v1.endpoints import orders, chat
    # Auth may require optional extras (email-validator). Make it optional for tests.
    try:
        from app.api.v1.endpoints import auth
    except ImportError:  # pragma: no cover - optional during tests
        auth = None  # type: ignore
    from app.api.v1.endpoints import products, roles
    from app.api.v1.endpoints import inventory, tools

    api_router = APIRouter()

    # Versioned API routes
    api_router.include_router(health.router, tags=["health"])  # /healthz, /readyz
    api_router.include_router(testall.router, prefix="/demo", tags=["demo"])  # /demo/testall
    api_router.include_router(ai.router, prefix="/ai", tags=["ai"])  # /ai/complete
    api_router.include_router(orders.router, tags=["orders"])  # /orders
    api_router.include_router(chat.router, tags=["chat"])  # /chat/route
    if auth is not None:
        api_router.include_router(auth.router, tags=["auth"])  # /auth/login, /auth/refresh
    api_router.include_router(products.router, tags=["products"])  # /products
    api_router.include_router(roles.router, tags=["roles"])  # /roles
    api_router.include_router(inventory.router, tags=["inventory"])  # /warehouses, /inventory
    api_router.include_router(tools.router, tags=["tools"])  # /tools/execute

    return api_router
