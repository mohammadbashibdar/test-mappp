from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import tms, database

app = FastAPI(
    title="GIS Map Game Backend FastAPI",
    description="A FastAPI backend for GIS map game with TMS support from PostgreSQL database",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Health check operations"},
        {"name": "TMS", "description": "Tile Map Service operations"},
        {"name": "Database", "description": "Database operations for Persian Gulf data"},
    ],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در production محدود کنید
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tms.router, prefix="/api/v1")
app.include_router(database.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "Welcome to GIS Map Game Backend FastAPI", 
        "version": "1.0.0",
        "features": [
            "Tile Map Service (TMS)",
            "Shapefile processing",
            "OpenLayers compatibility",
            "QGIS preview support"
        ]
    }
