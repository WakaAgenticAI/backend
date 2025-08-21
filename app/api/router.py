from fastapi import APIRouter

from app.api.v1.endpoints import health, testall, ai
from app.api.v1.endpoints import orders, chat
from app.api.v1.endpoints import auth, products, roles
from app.api.v1.endpoints import inventory

api_router = APIRouter()

# Versioned API routes
api_router.include_router(health.router, tags=["health"])  # /healthz, /readyz
api_router.include_router(testall.router, prefix="/demo", tags=["demo"])  # /demo/testall
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])  # /ai/complete
api_router.include_router(orders.router, tags=["orders"])  # /orders
api_router.include_router(chat.router, tags=["chat"])  # /chat/route
api_router.include_router(auth.router, tags=["auth"])  # /auth/login, /auth/refresh
api_router.include_router(products.router, tags=["products"])  # /products
api_router.include_router(roles.router, tags=["roles"])  # /roles
api_router.include_router(inventory.router, tags=["inventory"])  # /warehouses, /inventory
