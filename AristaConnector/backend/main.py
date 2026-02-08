from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, init_db
from app.routers import devices, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Arista vEOS Connector API",
    description="REST API for Arista vEOS device management",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/devices", tags=["devices"])
app.include_router(health.router, prefix="/health", tags=["health"])


@app.get("/")
async def root():
    return {"message": "Arista vEOS Connector API", "version": "0.1.0"}
