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
    from app.api.v1.endpoints import customers
    from app.api.v1.endpoints import inventory, tools
    from app.api.v1.endpoints import reports
    from app.api.v1.endpoints import debts
    from app.api.v1.endpoints import forecasts
    from app.api.v1.endpoints import notifications

    api_router = APIRouter()

    # Versioned API routes
    api_router.include_router(health.router, tags=["health"])  # /healthz, /readyz
    api_router.include_router(testall.router, prefix="/demo", tags=["demo"])  # /demo/testall
    api_router.include_router(ai.router, prefix="/ai", tags=["ai"])  # /ai/complete
    api_router.include_router(orders.router, tags=["orders"])  # /orders
    api_router.include_router(chat.router, prefix="/chat", tags=["chat"])  # /chat/route
    if auth is not None:
        api_router.include_router(auth.router, tags=["auth"])  # /auth/login, /auth/refresh
    api_router.include_router(products.router, tags=["products"])  # /products
    api_router.include_router(customers.router, tags=["customers"])  # /customers
    api_router.include_router(roles.router, tags=["roles"])  # /roles
    api_router.include_router(inventory.router, tags=["inventory"])  # /warehouses, /inventory
    api_router.include_router(tools.router, tags=["tools"])  # /tools/execute
    api_router.include_router(reports.router, tags=["reports"])  # /admin/reports/*, /reports/{id}
    api_router.include_router(debts.router, tags=["debts"])  # /debts
    api_router.include_router(forecasts.router, tags=["forecasts"])  # /forecasts
    api_router.include_router(notifications.router, tags=["notifications"])  # /notifications

    return api_router
