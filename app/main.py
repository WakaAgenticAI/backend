from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.router import get_api_router
from app.agents.orchestrator import get_orchestrator
from app.agents.orders_agent import orders_agent
from app.agents.orders_lookup_agent import OrdersLookupAgent
from app.agents.inventory_agent import inventory_agent
from app.agents.forecasting_agent import forecasting_agent
from app.agents.fraud_detection_agent import fraud_detection_agent
from app.agents.crm_agent import crm_agent
from app.agents.finance_agent import FinanceAgent
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.users import User
from app.models.roles import Role, UserRole
from app.core.logging import setup_json_logging
from app.realtime.server import Realtime
from app.models.inventory import Warehouse, Inventory
from app.models.products import Product
from app.core.middleware import (
    RequestIDMiddleware,
    SimpleRateLimitMiddleware,
    SecurityHeadersMiddleware,
    InputSanitizationMiddleware,
    LoginRateLimitMiddleware,
)
from app.core.app_state import set_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_json_logging()
    # Expose app globally for subsystems (realtime emitters, etc.)
    set_app(app)
    # Initialize orchestrator and register domain agents
    app.state.orchestrator = get_orchestrator()
    app.state.orchestrator.register_agent(orders_agent)
    app.state.orchestrator.register_agent(OrdersLookupAgent())
    app.state.orchestrator.register_agent(inventory_agent)
    app.state.orchestrator.register_agent(forecasting_agent)
    app.state.orchestrator.register_agent(fraud_detection_agent)
    app.state.orchestrator.register_agent(crm_agent)
    app.state.orchestrator.register_agent(FinanceAgent())
    # Initialize realtime (Socket.IO) with optional Redis manager
    settings = get_settings()
    app.state.realtime = Realtime(redis_url=settings.REDIS_URL)
    # Attach Socket.IO ASGI app to FastAPI
    app.state.realtime.attach_to(app)

    # Seed roles and an admin user (idempotent)
    db = SessionLocal()
    try:
        # Roles
        default_roles = [
            "Admin",
            "Sales",
            "Ops",
            "Finance",
            "Sales Representative",
            "Stock Keeper",
        ]
        existing = {r.name for r in db.query(Role).all()}
        for name in default_roles:
            if name not in existing:
                db.add(Role(name=name))
        db.commit()

        # Admin user
        admin_email = "admin@example.com"
        user = db.query(User).filter(User.email == admin_email).first()
        if not user:
            user = User(
                email=admin_email,
                full_name="Admin",
                password_hash=get_password_hash("admin123"),
                status="active",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Ensure Admin role assigned
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        if admin_role and not db.query(UserRole).filter(
            UserRole.user_id == user.id, UserRole.role_id == admin_role.id
        ).first():
            db.add(UserRole(user_id=user.id, role_id=admin_role.id))
            db.commit()

        # Warehouses: ensure a default exists
        warehouse = db.query(Warehouse).first()
        if not warehouse:
            warehouse = Warehouse(name="Main")
            db.add(warehouse)
            db.commit()
            db.refresh(warehouse)

        # Seed minimal products if none exist
        if db.query(Product).count() == 0:
            seed_products = [
                {"sku": "SKU-APPLE", "name": "Apple", "unit": "unit", "price_ngn": 200, "tax_rate": 7.5},
                {"sku": "SKU-BREAD", "name": "Bread", "unit": "unit", "price_ngn": 850, "tax_rate": 0},
                {"sku": "SKU-MILK", "name": "Milk", "unit": "ltr", "price_ngn": 1200, "tax_rate": 7.5},
            ]
            for p in seed_products:
                db.add(Product(**p))
            db.commit()

        # Ensure initial inventory rows for default warehouse
        prods = db.query(Product).all()
        for p in prods:
            inv = (
                db.query(Inventory)
                .filter(Inventory.product_id == p.id, Inventory.warehouse_id == warehouse.id)
                .first()
            )
            if not inv:
                db.add(Inventory(product_id=p.id, warehouse_id=warehouse.id, on_hand=100, reserved=0))
        db.commit()
    finally:
        db.close()
    yield
    # Shutdown


def create_app() -> FastAPI:
    settings = get_settings()

    # Disable docs in production for security
    is_prod = settings.APP_ENV == "prod"
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if is_prod else f"{settings.API_V1_PREFIX}/docs",
        openapi_url=None if is_prod else f"{settings.API_V1_PREFIX}/openapi.json",
    )

    # CORS — explicit origins, no wildcard in production
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or (["*"] if not is_prod else []),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # Security middleware stack (order matters: outermost runs first)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(InputSanitizationMiddleware, max_body_mb=settings.MAX_REQUEST_SIZE_MB)
    app.add_middleware(LoginRateLimitMiddleware, max_attempts=settings.MAX_LOGIN_ATTEMPTS, window_seconds=settings.LOGIN_LOCKOUT_MINUTES * 60)
    app.add_middleware(SimpleRateLimitMiddleware, max_requests=100, window_seconds=60)

    # Routes
    app.include_router(get_api_router(), prefix=settings.API_V1_PREFIX)

    return app


app = create_app()


def run():
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
