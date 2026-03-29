"""
API v1 router that includes all endpoint routers.
"""

from fastapi import APIRouter

from api.api.v1.endpoints import (
    admin,
    areas,
    chat,
    condition_admin,
    conditions,
    coordinates,
    debug,
    downloads,
    experiment,
    ireland_import_admin,
    legacy,
    locations,
    logs,
    maps,
    opengraph,
    osnet_admin,
    photos,
    reference,
    sitemap,
    stats,
    status_admin,
    tiles,
    trigs,
    types,
    types_admin,
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
api_router.include_router(types.router, prefix="/types", tags=["type"])
api_router.include_router(conditions.router, prefix="/conditions", tags=["condition"])
api_router.include_router(reference.router, prefix="/reference", tags=["reference"])
api_router.include_router(
    types_admin.router, prefix="/admin/types", tags=["admin-types"]
)
api_router.include_router(
    status_admin.router, prefix="/admin/status", tags=["admin-status"]
)
api_router.include_router(
    condition_admin.router, prefix="/admin/condition", tags=["admin-condition"]
)
api_router.include_router(
    osnet_admin.router, prefix="/admin/osnet", tags=["admin-osnet"]
)
api_router.include_router(
    ireland_import_admin.router,
    prefix="/admin/ireland-import",
    tags=["admin-ireland-import"],
)
api_router.include_router(experiment.router, prefix="/experiment", tags=["experiment"])
api_router.include_router(opengraph.trigs_router, prefix="/trigs", tags=["opengraph"])
api_router.include_router(opengraph.logs_router, prefix="/logs", tags=["opengraph"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(sitemap.router, prefix="/sitemap", tags=["sitemap"])
