"""
Stub out heavy runtime dependencies so pure-function tests can import
handlers without a real .env / database / bot token.
"""
import sys
from unittest.mock import MagicMock
from types import ModuleType

# ── dotenv ────────────────────────────────────────────────────────────────────
dotenv_stub = ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *a, **kw: None
sys.modules.setdefault("dotenv", dotenv_stub)

# ── app.config ────────────────────────────────────────────────────────────────
config_stub = ModuleType("app.config")
config_stub.load_config = lambda: MagicMock()
sys.modules.setdefault("app.config", config_stub)
