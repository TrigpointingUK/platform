"""
Photo endpoints (CRuD) and user photo count, plus filtered collections.
"""

import io
import logging

import requests
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from PIL import Image
from sqlalchemy.orm import Session

from api.api.deps import get_current_user, get_db
from api.api.lifecycle import openapi_lifecycle
from api.core.config import settings
from api.crud import tphoto as tphoto_crud
from api.models.server import Server
from api.models.trig import Trig
from api.models.user import TLog, User
from api.schemas.tphoto import (
    TPhotoEvaluationResponse,
    TPhotoResponse,
    TPhotoRotateRequest,
    TPhotoUpdate,
)
from api.services.image_processor import ImageProcessor
from api.services.rekognition import RekognitionService, get_image_dimensions
from api.services.s3_service import S3Service
from api.utils.cache_decorator import cached
from api.utils.url import join_url

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", openapi_extra=openapi_lifecycle("beta"))
@cached(resource_type="photos", ttl=3600, subresource="list")  # 1 hour
def list_photos(
    trig_id: int | None = Query(None),
    log_id: int | None = Query(None),
    user_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = tphoto_crud.list_photos_filtered(
        db, trig_id=trig_id, log_id=log_id, user_id=user_id, skip=skip, limit=limit
    )
    # total estimate with same filters - properly exclude deleted photos
    if len(items) < limit:
        total = len(items)
    else:
        # Need to count with same filters as list_photos_filtered
        total_query = db.query(tphoto_crud.TPhoto).filter(
            tphoto_crud.TPhoto.deleted_ind != "Y"
        )
        if log_id is not None:
            total_query = total_query.filter(tphoto_crud.TPhoto.tlog_id == log_id)
        if user_id is not None:
            total_query = total_query.join(
                TLog, TLog.id == tphoto_crud.TPhoto.tlog_id
            ).filter(TLog.user_id == user_id)
        if trig_id is not None:
            total_query = total_query.join(
                TLog, TLog.id == tphoto_crud.TPhoto.tlog_id
            ).filter(TLog.trig_id == trig_id)
        total = total_query.count()

    # Serialise with URLs populated
    result_items = []
    for p in items:
        # Resolve user via TLog
        tlog = db.query(TLog).filter(TLog.id == p.tlog_id).first()
        user = db.query(User).filter(User.id == tlog.user_id).first() if tlog else None
        trig = db.query(Trig).filter(Trig.id == tlog.trig_id).first() if tlog else None
        server: Server | None = (
            db.query(Server).filter(Server.id == p.server_id).first()
        )
        base_url = str(server.url) if server and server.url else ""
        result_items.append(
            {
                "id": int(p.id),
                "log_id": int(p.tlog_id),
                "user_id": int(tlog.user_id) if tlog else 0,
                "type": str(p.type),
                "filesize": int(p.filesize),
                "height": int(p.height),
                "width": int(p.width),
                "icon_filesize": int(p.icon_filesize),
                "icon_height": int(p.icon_height),
                "icon_width": int(p.icon_width),
                "caption": str(p.name),
                "text_desc": str(p.text_desc),
                "license": str(p.public_ind),
                "photo_url": join_url(base_url, str(p.filename)),
                "icon_url": join_url(base_url, str(p.icon_filename)),
                "user_name": str(user.name) if user else None,
                "trig_id": int(tlog.trig_id) if tlog and tlog.trig_id else None,
                "trig_name": str(trig.name) if trig else None,
                "log_date": tlog.date if tlog else None,
            }
        )

    has_more = (skip + len(items)) < total
    base = "/v1/photos"
    params = [f"limit={limit}"]
    if trig_id is not None:
        params.append(f"trig_id={trig_id}")
    if log_id is not None:
        params.append(f"log_id={log_id}")
    if user_id is not None:
        params.append(f"user_id={user_id}")
    self_link = base + "?" + "&".join(params + [f"skip={skip}"])
    next_link = (
        base + "?" + "&".join(params + [f"skip={skip + limit}"]) if has_more else None
    )
    prev_offset = max(skip - limit, 0)
    prev_link = (
        base + "?" + "&".join(params + [f"skip={prev_offset}"]) if skip > 0 else None
    )
    return {
        "items": result_items,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }


@router.post(
    "",
    response_model=TPhotoResponse,
    status_code=201,
    openapi_extra={
        **openapi_lifecycle("beta"),
        "security": [{"OAuth2": []}],
    },
)
def create_photo(
    request: Request,
    log_id: int = Query(..., description="Parent log ID"),
    file: UploadFile = File(..., description="Image file (JPEG)"),
    caption: str = Form(..., description="Photo caption"),
    text_desc: str = Form("", description="Photo description"),
    type: str = Form(..., regex="^[TFLPO]$", description="Photo type"),
    license: str = Form(..., regex="^[YCN]$", description="License"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a photo with metadata.

    - **file**: JPEG image file
    - **caption**: Photo caption (required)
    - **text_desc**: Photo description (optional)
    - **type**: Photo type (T=trigpoint, F=flush bracket, L=landscape, P=people, O=other)
    - **license**: License (Y=public domain, C=creative commons, N=private)
    """
    # Authorise based on log ownership or admin
    tlog: TLog | None = db.query(TLog).filter(TLog.id == log_id).first()
    if not tlog:
        raise HTTPException(status_code=404, detail="Log not found")
    if int(current_user.id) != int(tlog.user_id):
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

    client_ip = request.client.host if request.client else "127.0.0.1"

    # Read file contents
    try:
        file_contents = file.file.read()
        if not file_contents:
            raise HTTPException(status_code=400, detail="Empty file")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Validate image
    image_processor = ImageProcessor()
    is_valid, validation_message = image_processor.validate_image(file_contents)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)

    # Process image
    processed_photo, processed_thumbnail, image_dims, thumbnail_dims = (
        image_processor.process_image(file_contents)
    )

    if (
        not processed_photo
        or not processed_thumbnail
        or not image_dims
        or not thumbnail_dims
    ):
        raise HTTPException(status_code=500, detail="Failed to process image")

    # Create optimistic database record
    try:
        created = tphoto_crud.create_photo(
            db,
            log_id=log_id,
            values={
                "server_id": settings.PHOTOS_SERVER_ID,
                "type": type,
                "filename": "",  # Will be updated after S3 upload
                "filesize": len(processed_photo),
                "height": image_dims[1],
                "width": image_dims[0],
                "icon_filename": "",  # Will be updated after S3 upload
                "icon_filesize": len(processed_thumbnail),
                "icon_height": thumbnail_dims[1],
                "icon_width": thumbnail_dims[0],
                "name": caption,
                "text_desc": text_desc,
                "ip_addr": client_ip,
                "public_ind": license,
                "deleted_ind": "N",
                "source": "F",
            },
        )
    except Exception as e:
        logger.error(f"Failed to create photo record: {e}")
        raise HTTPException(status_code=500, detail="Failed to create photo record")

    # Upload to S3
    s3_service = S3Service()
    photo_key, thumbnail_key = s3_service.upload_photo_and_thumbnail(
        int(created.id), processed_photo, processed_thumbnail
    )

    if not photo_key or not thumbnail_key:
        # Rollback: delete the database record
        try:
            db.delete(created)
            db.commit()
        except Exception as rollback_error:
            logger.error(f"Failed to rollback database record: {rollback_error}")

        raise HTTPException(status_code=500, detail="Failed to upload files")

    # Update database record with S3 paths
    try:
        setattr(created, "filename", photo_key)
        setattr(created, "icon_filename", thumbnail_key)
        db.add(created)
        db.commit()
        db.refresh(created)
    except Exception as e:
        logger.error(f"Failed to update photo record: {e}")
        # Clean up S3 files
        s3_service.delete_photo_and_thumbnail(int(created.id))
        # Delete database record
        try:
            db.delete(created)
            db.commit()
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup database record: {cleanup_error}")

        raise HTTPException(status_code=500, detail="Failed to update photo record")

    # Trigger async content moderation
    try:
        # Import here to avoid circular imports
        from api.services.content_moderation import moderate_photo_async

        moderate_photo_async(int(created.id))
    except Exception as e:
        logger.warning(f"Failed to trigger content moderation: {e}")
        # Don't fail the upload, just log the warning

    # Return response
    server: Server | None = (
        db.query(Server).filter(Server.id == created.server_id).first()
    )
    base_url = str(server.url) if server and server.url else ""

    def join_url(base: str, path: str) -> str:
        if not base:
            return path
        if base.endswith("/"):
            return f"{base}{path}"
        return f"{base}/{path}"

    return {
        "id": created.id,
        "log_id": created.tlog_id,
        "user_id": int(tlog.user_id),
        "type": str(created.type),
        "filesize": int(created.filesize),
        "height": int(created.height),
        "width": int(created.width),
        "icon_filesize": int(created.icon_filesize),
        "icon_height": int(created.icon_height),
        "icon_width": int(created.icon_width),
        "caption": str(created.name),
        "text_desc": str(created.text_desc),
        "license": str(created.public_ind),
        "photo_url": join_url(base_url, str(created.filename)),
        "icon_url": join_url(base_url, str(created.icon_filename)),
        "user_name": str(current_user.name) if hasattr(current_user, "name") else None,
        "trig_id": int(tlog.trig_id) if tlog else None,
        "trig_name": (
            db.query(Trig.name).filter(Trig.id == tlog.trig_id).scalar()
            if tlog
            else None
        ),
        "log_date": tlog.date if tlog else None,
    }


@router.get(
    "/{photo_id}",
    response_model=TPhotoResponse,
    openapi_extra=openapi_lifecycle("beta"),
)
@cached(resource_type="photo", ttl=43200, resource_id_param="photo_id")  # 12 hours
def get_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = tphoto_crud.get_photo_by_id(db, photo_id=photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Build URLs by joining server.url with filenames
    server: Server | None = (
        db.query(Server).filter(Server.id == photo.server_id).first()
    )
    base_url = str(server.url) if server and server.url else ""

    # Ensure single slash joining
    def join_url(base: str, path: str) -> str:
        if not base:
            return path
        if base.endswith("/"):
            return f"{base}{path}"
        return f"{base}/{path}"

    # Lookup user_id from tlog
    tlog: TLog | None = db.query(TLog).filter(TLog.id == photo.tlog_id).first()
    user = db.query(User).filter(User.id == tlog.user_id).first() if tlog else None
    trig = db.query(Trig).filter(Trig.id == tlog.trig_id).first() if tlog else None
    response = {
        "id": photo.id,
        "log_id": photo.tlog_id,
        "user_id": int(tlog.user_id) if tlog else 0,
        "type": str(photo.type),
        "filesize": int(photo.filesize),
        "height": int(photo.height),
        "width": int(photo.width),
        "icon_filesize": int(photo.icon_filesize),
        "icon_height": int(photo.icon_height),
        "icon_width": int(photo.icon_width),
        "caption": str(photo.name),
        "text_desc": str(photo.text_desc),
        "license": str(photo.public_ind),
        "photo_url": join_url(base_url, str(photo.filename)),
        "icon_url": join_url(base_url, str(photo.icon_filename)),
        "user_name": str(user.name) if user else None,
        "trig_id": int(tlog.trig_id) if tlog and tlog.trig_id else None,
        "trig_name": str(trig.name) if trig else None,
        "log_date": tlog.date if tlog else None,
    }
    return response


@router.patch(
    "/{photo_id}",
    response_model=TPhotoResponse,
    openapi_extra={
        **openapi_lifecycle("beta"),
        "security": [{"OAuth2": []}],
    },
)
def update_photo(
    photo_id: int,
    payload: TPhotoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Load current photo and authorise BEFORE applying updates
    existing = tphoto_crud.get_photo_by_id(db, photo_id=photo_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Authorisation: owner or api:admin
    tlog: TLog | None = db.query(TLog).filter(TLog.id == existing.tlog_id).first()
    if not tlog:
        raise HTTPException(status_code=404, detail="TLog not found for photo")

    # If not owner, require admin scope
    if int(current_user.id) != int(tlog.user_id):
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

    # Proceed with update
    updated = tphoto_crud.update_photo(
        db, photo_id=photo_id, updates=payload.model_dump(exclude_none=True)
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    server: Server | None = (
        db.query(Server).filter(Server.id == updated.server_id).first()
    )
    base_url = str(server.url) if server and server.url else ""

    def join_url(base: str, path: str) -> str:
        if not base:
            return path
        if base.endswith("/"):
            return f"{base}{path}"
        return f"{base}/{path}"

    response = {
        "id": updated.id,
        "log_id": updated.tlog_id,
        "user_id": int(tlog.user_id),
        "type": str(updated.type),
        "filesize": int(updated.filesize),
        "height": int(updated.height),
        "width": int(updated.width),
        "icon_filesize": int(updated.icon_filesize),
        "icon_height": int(updated.icon_height),
        "icon_width": int(updated.icon_width),
        "caption": str(updated.name),
        "text_desc": str(updated.text_desc),
        "license": str(updated.public_ind),
        "photo_url": join_url(base_url, str(updated.filename)),
        "icon_url": join_url(base_url, str(updated.icon_filename)),
        "user_name": str(current_user.name) if hasattr(current_user, "name") else None,
        "trig_id": int(tlog.trig_id) if tlog else None,
        "trig_name": (
            db.query(Trig.name).filter(Trig.id == tlog.trig_id).scalar()
            if tlog
            else None
        ),
        "log_date": tlog.date if tlog else None,
    }
    return response


@router.delete(
    "/{photo_id}",
    status_code=204,
    openapi_extra={
        **openapi_lifecycle("beta"),
        "security": [{"OAuth2": []}],
    },
)
def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Load and authorise BEFORE delete
    existing = tphoto_crud.get_photo_by_id(db, photo_id=photo_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Photo not found")

    tlog = db.query(TLog).filter(TLog.id == existing.tlog_id).first()
    if not tlog:
        raise HTTPException(status_code=404, detail="TLog not found for photo")

    if int(current_user.id) != int(tlog.user_id):
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

    ok = tphoto_crud.delete_photo(db, photo_id=photo_id, soft=True)
    if not ok:
        raise HTTPException(status_code=404, detail="Photo not found")
    return None


@router.get(
    "/{photo_id}/evaluate",
    response_model=TPhotoEvaluationResponse,
    openapi_extra=openapi_lifecycle("alpha"),
)
def evaluate_photo(photo_id: int, db: Session = Depends(get_db)):
    """
    Evaluate a photo by downloading it and running AWS Rekognition analysis.

    Checks:
    - Photo and icon accessibility
    - Dimension validation against database
    - Orientation analysis (90°, 180°, 270° rotation detection)
    - Content moderation (inappropriate content detection)
    """
    # Look up photo in database
    photo = tphoto_crud.get_photo_by_id(db, photo_id=photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Get server URL for constructing full URLs
    server: Server | None = (
        db.query(Server).filter(Server.id == photo.server_id).first()
    )
    base_url = str(server.url) if server and server.url else ""

    def join_url(base: str, path: str) -> str:
        if not base:
            return path
        if base.endswith("/"):
            return f"{base}{path}"
        return f"{base}/{path}"

    photo_url = join_url(base_url, str(photo.filename))
    icon_url = join_url(base_url, str(photo.icon_filename))

    # Initialise response
    response = TPhotoEvaluationResponse(
        photo_id=photo_id,
        photo_accessible=False,
        icon_accessible=False,
        photo_dimension_match=False,
        icon_dimension_match=False,
        errors=[],
    )

    # Initialise Rekognition service
    rekognition = RekognitionService()

    # Download and analyse main photo
    photo_bytes = None
    try:
        logger.info(f"Downloading photo from: {photo_url}")
        photo_response = requests.get(photo_url, timeout=30)
        photo_response.raise_for_status()
        photo_bytes = photo_response.content
        response.photo_accessible = True

        # Check dimensions
        actual_width, actual_height = get_image_dimensions(photo_bytes)
        if actual_width is not None and actual_height is not None:
            response.photo_width_actual = actual_width
            response.photo_height_actual = actual_height
            response.photo_dimension_match = (
                actual_width == photo.width and actual_height == photo.height
            )
            if not response.photo_dimension_match:
                response.errors.append(
                    f"Photo dimensions mismatch: DB({photo.width}x{photo.height}) "
                    f"vs Actual({actual_width}x{actual_height})"
                )
        else:
            response.errors.append("Could not determine photo dimensions")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download photo {photo_url}: {e}")
        response.errors.append(f"Photo download failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing photo {photo_url}: {e}")
        response.errors.append(f"Photo processing error: {str(e)}")

    # Download and analyse icon
    try:
        logger.info(f"Downloading icon from: {icon_url}")
        icon_response = requests.get(icon_url, timeout=30)
        icon_response.raise_for_status()
        icon_bytes = icon_response.content
        response.icon_accessible = True

        # Check dimensions
        actual_width, actual_height = get_image_dimensions(icon_bytes)
        if actual_width is not None and actual_height is not None:
            response.icon_width_actual = actual_width
            response.icon_height_actual = actual_height
            response.icon_dimension_match = (
                actual_width == photo.icon_width and actual_height == photo.icon_height
            )
            if not response.icon_dimension_match:
                response.errors.append(
                    f"Icon dimensions mismatch: DB({photo.icon_width}x{photo.icon_height}) "
                    f"vs Actual({actual_width}x{actual_height})"
                )
        else:
            response.errors.append("Could not determine icon dimensions")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download icon {icon_url}: {e}")
        response.errors.append(f"Icon download failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing icon {icon_url}: {e}")
        response.errors.append(f"Icon processing error: {str(e)}")

    # Run AWS Rekognition analysis on main photo if available
    if photo_bytes and len(photo_bytes) > 0:
        try:
            # Orientation analysis
            orientation_result = rekognition.analyse_orientation(photo_bytes)
            if orientation_result:
                response.orientation_analysis = orientation_result
            else:
                response.errors.append(
                    "Orientation analysis unavailable (AWS configuration issue)"
                )

            # Content moderation
            moderation_result = rekognition.moderate_content(photo_bytes)
            if moderation_result:
                response.content_moderation = moderation_result
            else:
                response.errors.append(
                    "Content moderation unavailable (AWS configuration issue)"
                )

        except Exception as e:
            logger.error(f"AWS Rekognition analysis failed: {e}")
            response.errors.append(f"AWS analysis error: {str(e)}")
    else:
        response.errors.append("No photo data available for AWS analysis")

    return response


@router.post(
    "/{photo_id}/rotate",
    response_model=TPhotoResponse,
    openapi_extra=openapi_lifecycle("beta"),
)
def rotate_photo(
    photo_id: int,
    rotate_request: TPhotoRotateRequest,
    db: Session = Depends(get_db),
):
    """
    Rotate a photo by the specified angle and create a new version.

    - **angle**: Rotation angle in degrees (90, 180, 270)

    The original photo is soft-deleted and a new photo record is created.
    This endpoint is open to all users to allow collaborative photo correction.
    """
    logger.info(f"Rotating photo {photo_id} by {rotate_request.angle} degrees")

    # Get the existing photo
    existing_photo = tphoto_crud.get_photo_by_id(db, photo_id=photo_id)
    if not existing_photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Authorization: open to all users (trust-based)
    tlog: TLog | None = db.query(TLog).filter(TLog.id == existing_photo.tlog_id).first()
    if not tlog:
        raise HTTPException(status_code=404, detail="TLog not found for photo")

    # Get server URL for constructing full URLs
    server: Server | None = (
        db.query(Server).filter(Server.id == existing_photo.server_id).first()
    )
    base_url = str(server.url) if server and server.url else ""
    photo_url = join_url(base_url, str(existing_photo.filename))

    # Download the existing photo
    try:
        logger.info(f"Downloading photo from: {photo_url}")
        photo_response = requests.get(photo_url, timeout=30)
        photo_response.raise_for_status()
        photo_bytes = photo_response.content

        if not photo_bytes:
            raise HTTPException(status_code=500, detail="Failed to download photo")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download photo {photo_url}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to download photo: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error downloading photo {photo_url}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error downloading photo: {str(e)}"
        )

    # Load and rotate the image
    try:
        image = Image.open(io.BytesIO(photo_bytes))

        # Rotate the image
        rotated_image = image.rotate(-rotate_request.angle, expand=True)

        # Process the rotated image
        image_processor = ImageProcessor()

        # Convert rotated image to bytes
        rotated_buffer = io.BytesIO()
        rotated_image.save(rotated_buffer, format="JPEG", quality=95)
        rotated_bytes = rotated_buffer.getvalue()

        # Process image to get final photo and thumbnail
        processed_photo, processed_thumbnail, image_dims, thumbnail_dims = (
            image_processor.process_image(rotated_bytes)
        )

        if (
            not processed_photo
            or not processed_thumbnail
            or not image_dims
            or not thumbnail_dims
        ):
            raise HTTPException(
                status_code=500, detail="Failed to process rotated image"
            )

    except Exception as e:
        logger.error(f"Failed to rotate image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rotate image: {str(e)}")

    # Generate new revision filenames
    s3_service = S3Service()
    new_photo_key = s3_service.generate_revision_filename(str(existing_photo.filename))
    new_thumbnail_key = s3_service.generate_revision_filename(
        str(existing_photo.icon_filename)
    )

    # Upload rotated images to S3 with new revision filenames
    photo_key, thumbnail_key = s3_service.upload_photo_and_thumbnail_with_keys(
        processed_photo, processed_thumbnail, new_photo_key, new_thumbnail_key
    )

    if not photo_key or not thumbnail_key:
        raise HTTPException(status_code=500, detail="Failed to upload rotated files")

    # Update existing photo record with new file information
    try:
        logger.info(
            f"Updating photo {existing_photo.id}: server_id {existing_photo.server_id} -> {settings.PHOTOS_SERVER_ID}"
        )
        updated_photo = tphoto_crud.update_photo(
            db,
            photo_id=int(existing_photo.id),
            updates={
                "server_id": settings.PHOTOS_SERVER_ID,
                "filename": photo_key,
                "icon_filename": thumbnail_key,
                "filesize": len(processed_photo),
                "icon_filesize": len(processed_thumbnail),
                "height": image_dims[1],
                "width": image_dims[0],
                "icon_height": thumbnail_dims[1],
                "icon_width": thumbnail_dims[0],
                "source": "R",  # R for revised/rotated
            },
        )

        if updated_photo:
            logger.info(
                f"Photo {updated_photo.id} updated: server_id now {updated_photo.server_id}"
            )

        if not updated_photo:
            # Rollback S3 uploads if database update fails
            logger.error("Failed to update photo record in database")
            # Note: We keep original S3 objects, only new ones need cleanup
            # But since they're revisions, they're safe to keep as backups
            raise HTTPException(status_code=500, detail="Failed to update photo record")

    except Exception as e:
        logger.error(f"Failed to update photo record: {e}")
        raise HTTPException(status_code=500, detail="Failed to update photo record")

    logger.info(
        f"Successfully rotated photo {photo_id}: {existing_photo.filename} -> {photo_key}"
    )

    # Get updated server URL for response (fetch after update since server_id was updated)
    updated_server: Server | None = (
        db.query(Server).filter(Server.id == updated_photo.server_id).first()
    )
    base_url = str(updated_server.url) if updated_server and updated_server.url else ""

    # Return response with updated photo
    return {
        "id": updated_photo.id,
        "log_id": updated_photo.tlog_id,
        "user_id": int(tlog.user_id),
        "type": str(updated_photo.type),
        "filesize": int(updated_photo.filesize),
        "height": int(updated_photo.height),
        "width": int(updated_photo.width),
        "icon_filesize": int(updated_photo.icon_filesize),
        "icon_height": int(updated_photo.icon_height),
        "icon_width": int(updated_photo.icon_width),
        "caption": str(updated_photo.name),
        "text_desc": str(updated_photo.text_desc),
        "license": str(updated_photo.public_ind),
        "photo_url": join_url(base_url, str(updated_photo.filename)),
        "icon_url": join_url(base_url, str(updated_photo.icon_filename)),
        "user_name": (
            db.query(User.name).filter(User.id == tlog.user_id).scalar()
            if tlog
            else None
        ),
        "trig_id": int(tlog.trig_id) if tlog else None,
        "trig_name": (
            db.query(Trig.name).filter(Trig.id == tlog.trig_id).scalar()
            if tlog
            else None
        ),
        "log_date": tlog.date if tlog else None,
    }
