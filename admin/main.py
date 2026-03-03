import os

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin.base import BaseAdmin

from auth import MyAuthProvider
from db import lifespan
from views.info_pages import InfoPageView
from views.services import ServiceView

load_dotenv()

SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "changeme-set-in-env")

app = FastAPI(lifespan=lifespan)

admin = BaseAdmin(
    title="РІО Адмін",
    auth_provider=MyAuthProvider(),
    middlewares=[Middleware(SessionMiddleware, secret_key=SECRET_KEY)],
)

admin.add_view(ServiceView())
admin.add_view(InfoPageView())
admin.mount_to(app)
