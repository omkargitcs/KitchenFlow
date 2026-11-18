from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import models  # noqa: F401  (registers tables)
from .database import Base, engine
from .routers import menu, orders, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="KitchenFlow",
    description="Restaurant orders, menu and inventory API.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(menu.router)
app.include_router(orders.router)
app.include_router(reports.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
