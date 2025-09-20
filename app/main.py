from fastapi import FastAPI


app = FastAPI(
    title="map-game Backend FastAPI",
    description="A FastAPI backend for motor management system",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Health check operations"},
        {"name": "auth", "description": "Authentication operations"},
    ],
)


@app.get("/")
async def root():
    return {"message": "Welcome to map-game Backend FastAPI", "version": "1.0.0"}
