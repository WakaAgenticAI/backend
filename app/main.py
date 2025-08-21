from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.router import api_router
from app.agents.orchestrator import Orchestrator
from app.agents.orders_agent import OrdersAgent
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.users import User
from app.models.roles import Role, UserRole
from app.core.logging import setup_json_logging
from app.realtime.server import Realtime
from app.models.inventory import Warehouse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_json_logging()
    # Initialize orchestrator and register domain agents
    app.state.orchestrator = Orchestrator()
    app.state.orchestrator.register(OrdersAgent())
    # Initialize realtime (stubbed)
    app.state.realtime = Realtime()

    # Seed roles and an admin user (idempotent)
    db = SessionLocal()
    try:
        # Roles
        default_roles = ["Admin", "Sales", "Ops", "Finance"]
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
        has_wh = db.query(Warehouse).first()
        if not has_wh:
            db.add(Warehouse(name="Main"))
            db.commit()
    finally:
        db.close()
    yield
    # Shutdown


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    # CORS
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()


def run():
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
