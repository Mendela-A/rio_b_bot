"""Shared singletons and constants for the admin app."""
import os

from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_IMAGE_WIDTH = 1280
IMAGE_QUALITY   = 85
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
