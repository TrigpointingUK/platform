"""
Logs endpoints under /v1/logs (create, read, update, delete) and nested photos.

Only PATCH (no PUT). DELETE is hard-delete for logs and soft-deletes their photos.
"""

from datetime import date as date_type
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.api.deps import get_current_user, get_db
from api.api.lifecycle import openapi_lifecycle
from api.crud import tlog as tlog_crud
from api.crud import tphoto as tphoto_crud
from api.models.server import Server
from api.models.trig import Trig
from api.models.user import TLog as TLogModel
from api.models.user import User
from api.schemas.tlog import TLogCreate, TLogResponse, TLogUpdate, TLogWithIncludes
from api.schemas.tphoto import TPhotoResponse
from api.utils.cache_decorator import cached
from api.utils.url import join_url

router = APIRouter()


def enrich_logs_with_names(db: Session, logs: List[TLogModel]) -> List[Dict]:
    """
    Add trig_name and user_name to logs using bulk queries to avoid N+1.
    Returns list of dictionaries.
    """
    if not logs:
        return []

    # Bulk fetch trig names and user names
    trig_ids = list(set(log.trig_id for log in logs))
    user_ids = list(set(log.user_id for log in logs))

    trigs = (
        db.query(Trig.id, Trig.name).filter(Trig.id.in_(trig_ids)).all()
        if trig_ids
        else []
    )
    users = (
        db.query(User.id, User.name).filter(User.id.in_(user_ids)).all()
        if user_ids
        else []
    )

    trig_names = {t.id: t.name for t in trigs}
    user_names = {u.id: u.name for u in users}

    # Convert to dicts and add denormalized fields
    result = []
    for log in logs:
        log_dict = TLogResponse.model_validate(log).model_dump()
        log_dict["trig_name"] = trig_names.get(log.trig_id)
        log_dict["user_name"] = user_names.get(log.user_id)
        result.append(log_dict)

    return result


@router.get("", openapi_extra=openapi_lifecycle("beta"))
@cached(resource_type="logs", ttl=3600, subresource="list")  # 1 hour
def list_logs(
    trig_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    order: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    include: Optional[str] = Query(
        None, description="Comma-separated list of includes: photos"
    ),
    db: Session = Depends(get_db),
):
    items = tlog_crud.list_logs_filtered(
        db, trig_id=trig_id, user_id=user_id, order=order, skip=skip, limit=limit
    )
    total = tlog_crud.count_logs_filtered(db, trig_id=trig_id, user_id=user_id)

    # Add denormalized trig_name and user_name fields
    items_serialized = enrich_logs_with_names(db, items)

    # Handle includes
    if include:
        tokens = {t.strip() for t in include.split(",") if t.strip()}

        # Validate include tokens
        valid_includes = {"photos"}
        invalid_tokens = tokens - valid_includes
        if invalid_tokens:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options: {', '.join(sorted(valid_includes))}",
            )
        if "photos" in tokens:
            # Attach photos list for each log item
            for out, orig in zip(items_serialized, items):
                photos = tphoto_crud.list_all_photos_for_log(db, log_id=int(orig.id))
                # Build base URLs per photo server
                out["photos"] = []

                # Get trig info for this log once (to populate photo metadata)
                trig = (
                    db.query(Trig).filter(Trig.id == orig.trig_id).first()
                    if orig.trig_id
                    else None
                )

                for p in photos:
                    server: Server | None = (
                        db.query(Server).filter(Server.id == p.server_id).first()
                    )
                    base_url = str(server.url) if server and server.url else ""
                    # Handle empty type field by defaulting to 'O' (other)
                    photo_type = str(p.type) if p.type and p.type.strip() else "O"
                    out["photos"].append(
                        TPhotoResponse(
                            id=int(p.id),
                            log_id=int(p.tlog_id),
                            user_id=int(orig.user_id),
                            type=photo_type,
                            filesize=int(p.filesize),
                            height=int(p.height),
                            width=int(p.width),
                            icon_filesize=int(p.icon_filesize),
                            icon_height=int(p.icon_height),
                            icon_width=int(p.icon_width),
                            name=str(p.name),
                            text_desc=str(p.text_desc),
                            public_ind=str(p.public_ind),
                            photo_url=join_url(base_url, str(p.filename)),
                            icon_url=join_url(base_url, str(p.icon_filename)),
                            user_name=out.get("user_name"),
                            trig_id=int(orig.trig_id) if orig.trig_id else None,
                            trig_name=str(trig.name) if trig else None,
                            log_date=(
                                date_type(
                                    orig.date.year, orig.date.month, orig.date.day
                                )
                                if orig.date
                                else None
                            ),
                        ).model_dump()
                    )
    has_more = (skip + len(items)) < total
    base = "/v1/logs"
    params = [f"limit={limit}"]
    if trig_id is not None:
        params.append(f"trig_id={trig_id}")
    if user_id is not None:
        params.append(f"user_id={user_id}")
    if order:
        params.append(f"order={order}")
    self_link = base + "?" + "&".join(params + [f"skip={skip}"])
    next_link = (
        base + "?" + "&".join(params + [f"skip={skip + limit}"]) if has_more else None
    )
    prev_offset = max(skip - limit, 0)
    prev_link = (
        base + "?" + "&".join(params + [f"skip={prev_offset}"]) if skip > 0 else None
    )
    return {
        "items": items_serialized,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }


@router.get(
    "/{log_id}",
    response_model=TLogWithIncludes,
    openapi_extra=openapi_lifecycle("beta"),
)
@cached(resource_type="log", ttl=21600, resource_id_param="log_id")  # 6 hours
def get_log(
    log_id: int,
    include: Optional[str] = Query(
        None, description="Comma-separated list of includes: photos"
    ),
    db: Session = Depends(get_db),
) -> TLogWithIncludes:
    log = tlog_crud.get_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    # Use helper to add denormalized fields
    log_dicts = enrich_logs_with_names(db, [log])
    base = log_dicts[0] if log_dicts else TLogResponse.model_validate(log).model_dump()

    photos_out: Optional[list[TPhotoResponse]] = None
    if include:
        tokens = {t.strip() for t in include.split(",") if t.strip()}

        # Validate include tokens
        valid_includes = {"photos"}
        invalid_tokens = tokens - valid_includes
        if invalid_tokens:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options: {', '.join(sorted(valid_includes))}",
            )
        if "photos" in tokens:
            photos = tphoto_crud.list_all_photos_for_log(db, log_id=int(log.id))
            photos_out = []

            # Get trig info for this log once (to populate photo metadata)
            trig = (
                db.query(Trig).filter(Trig.id == log.trig_id).first()
                if log.trig_id
                else None
            )

            for p in photos:
                server: Server | None = (
                    db.query(Server).filter(Server.id == p.server_id).first()
                )
                base_url = str(server.url) if server and server.url else ""
                photos_out.append(
                    TPhotoResponse(
                        id=int(p.id),
                        log_id=int(p.tlog_id),
                        user_id=int(log.user_id),
                        type=str(p.type) if p.type and p.type.strip() else "O",
                        filesize=int(p.filesize),
                        height=int(p.height),
                        width=int(p.width),
                        icon_filesize=int(p.icon_filesize),
                        icon_height=int(p.icon_height),
                        icon_width=int(p.icon_width),
                        name=str(p.name),
                        text_desc=str(p.text_desc),
                        public_ind=str(p.public_ind),
                        photo_url=join_url(base_url, str(p.filename)),
                        icon_url=join_url(base_url, str(p.icon_filename)),
                        user_name=base.get("user_name"),
                        trig_id=int(log.trig_id) if log.trig_id else None,
                        trig_name=str(trig.name) if trig else None,
                        log_date=(
                            date_type(log.date.year, log.date.month, log.date.day)
                            if log.date
                            else None
                        ),
                    )
                )

    return TLogWithIncludes(**base, photos=photos_out)


@router.post(
    "",
    response_model=TLogResponse,
    status_code=201,
    openapi_extra={
        **openapi_lifecycle("beta"),
        "security": [{"OAuth2": []}],
    },
)
def create_log(
    trig_id: int = Query(..., description="Parent trig ID"),
    payload: TLogCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = tlog_crud.create_log(
        db, trig_id=trig_id, user_id=int(current_user.id), values=payload.model_dump()
    )
    return TLogResponse.model_validate(log)


@router.patch(
    "/{log_id}",
    response_model=TLogResponse,
    openapi_extra={
        **openapi_lifecycle("beta"),
        "security": [{"OAuth2": []}],
    },
)
def update_log_endpoint(
    log_id: int,
    payload: TLogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing: Optional[TLogModel] = tlog_crud.get_log_by_id(db, log_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Log not found")
    if int(existing.user_id) != int(current_user.id):
        # Require admin scope if not owner
        # Check admin privileges using token payload from current_user
        token_payload = getattr(current_user, "_token_payload", None)
        if not token_payload:
            raise HTTPException(status_code=403, detail="Access denied")

        from api.core.security import extract_scopes

        pass  # Auth0 only - no legacy admin check needed

        if token_payload.get("token_type") == "auth0":
            scopes = extract_scopes(token_payload)
            if "api:admin" not in scopes:
                raise HTTPException(
                    status_code=403, detail="Missing required scope: api:admin"
                )
        # Legacy tokens not supported - Auth0 only

    updated = tlog_crud.update_log(
        db, log_id=log_id, updates=payload.model_dump(exclude_none=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Log not found")
    return TLogResponse.model_validate(updated)


@router.delete(
    "/{log_id}",
    status_code=204,
    openapi_extra={
        **openapi_lifecycle("beta"),
        "security": [{"OAuth2": []}],
    },
)
def delete_log_endpoint(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = tlog_crud.get_log_by_id(db, log_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Log not found")
    if int(existing.user_id) != int(current_user.id):
        # Check admin privileges using token payload from current_user
        token_payload = getattr(current_user, "_token_payload", None)
        if not token_payload:
            raise HTTPException(status_code=403, detail="Access denied")

        from api.core.security import extract_scopes

        pass  # Auth0 only - no legacy admin check needed

        if token_payload.get("token_type") == "auth0":
            scopes = extract_scopes(token_payload)
            if "api:admin" not in scopes:
                raise HTTPException(
                    status_code=403, detail="Missing required scope: api:admin"
                )
        # Legacy tokens not supported - Auth0 only

    # Soft-delete photos then hard-delete log
    tlog_crud.soft_delete_photos_for_log(db, log_id=log_id)
    ok = tlog_crud.delete_log_hard(db, log_id=log_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Log not found")
    return None


@router.get(
    "/{log_id}/photos",
    openapi_extra=openapi_lifecycle("beta"),
)
def list_photos_for_log(
    log_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = tphoto_crud.list_photos_filtered(db, log_id=log_id, skip=skip, limit=limit)
    # Note: total is estimated as count of non-deleted photos for log
    total = (
        db.query(tphoto_crud.TPhoto)
        .filter(
            tphoto_crud.TPhoto.tlog_id == log_id, tphoto_crud.TPhoto.deleted_ind != "Y"
        )
        .count()
    )
    # Build response shape similar to other collections
    # Need user_id from joining TLog for each photo
    photos = []
    for p in items:
        # fetch user_id via TLog
        tlog = db.query(TLogModel).filter(TLogModel.id == p.tlog_id).first()
        server: Server | None = (
            db.query(Server).filter(Server.id == p.server_id).first()
        )
        base_url = str(server.url) if server and server.url else ""
        # Handle empty type field by defaulting to 'O' (other)
        photo_type = str(p.type) if p.type and p.type.strip() else "O"
        photos.append(
            TPhotoResponse(
                id=int(p.id),
                log_id=int(p.tlog_id),
                user_id=int(tlog.user_id) if tlog else 0,
                type=photo_type,
                filesize=int(p.filesize),
                height=int(p.height),
                width=int(p.width),
                icon_filesize=int(p.icon_filesize),
                icon_height=int(p.icon_height),
                icon_width=int(p.icon_width),
                name=str(p.name),
                text_desc=str(p.text_desc),
                public_ind=str(p.public_ind),
                photo_url=join_url(base_url, str(p.filename)),
                icon_url=join_url(base_url, str(p.icon_filename)),
            ).model_dump()
        )
    has_more = (skip + len(items)) < total
    base = f"/v1/logs/{log_id}/photos"
    self_link = base + f"?limit={limit}&skip={skip}"
    next_link = base + f"?limit={limit}&skip={skip + limit}" if has_more else None
    prev_offset = max(skip - limit, 0)
    prev_link = base + f"?limit={limit}&skip={prev_offset}" if skip > 0 else None
    return {
        "items": photos,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }
