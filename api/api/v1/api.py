"""
API v1 router that includes all endpoint routers.
"""

from fastapi import APIRouter

from api.api.v1.endpoints import (
    admin,
    areas,
    coordinates,
    debug,
    downloads,
    legacy,
    locations,
    logs,
    maps,
    photos,
    stats,
    tiles,
    trigs,
    users,
)

api_router = APIRouter()

api_router.include_router(trigs.router, prefix="/trigs", tags=["trig"])
api_router.include_router(users.router, prefix="/users", tags=["user"])
api_router.include_router(logs.router, prefix="/logs", tags=["log"])
api_router.include_router(photos.router, prefix="/photos", tags=["photo"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(locations.router, prefix="/locations", tags=["location"])
api_router.include_router(areas.router, prefix="/areas", tags=["area"])
api_router.include_router(tiles.router, prefix="/tiles/os", tags=["tiles"])
api_router.include_router(maps.router, prefix="/maps", tags=["map"])
api_router.include_router(legacy.router, prefix="/legacy", tags=["legacy"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(downloads.router, prefix="/downloads", tags=["download"])
api_router.include_router(
    coordinates.router, prefix="/coordinates", tags=["coordinates"]
)
