# Models package
from .base import Base  # re-export Base for Alembic and metadata discovery

# Import model modules so metadata includes all tables when 'app.models' is imported
# (Used by Alembic env.py and other tooling)
from . import users  # noqa: F401
from . import orders  # noqa: F401
from . import roles  # noqa: F401
from . import products  # noqa: F401
from . import chat  # noqa: F401
from . import inventory  # noqa: F401
from . import forecasts  # noqa: F401
from . import audit  # noqa: F401
from . import auth_tokens  # noqa: F401
