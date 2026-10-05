"""
Admin endpoints for managing trig variants (see api.models.trig_variant).

Variants belong to groups (e.g. "Detector material"); a type offers a group
through trig_type.variant_group. Codes are fixed once created, as filter
links use variant codes and types refer to group codes. A variant recorded
on any trig can't be deleted, nor can a group's last variant while types
still offer the group.
"""

import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.api.deps import get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.logging import get_logger
from api.crud import trig_variant as variant_crud
from api.models.trig_variant import NOT_RECORDED_CODE
from api.models.user import User
from api.schemas.trig_variant import (
    TrigVariantAdmin,
    TrigVariantCreate,
    TrigVariantResponse,
    TrigVariantUpdate,
    VariantGroupAdmin,
    VariantGroupResponse,
    VariantGroupUpdate,
)
from api.services.cache_invalidator import invalidate_patterns

logger = get_logger(__name__)
router = APIRouter()

_REFERENCE_CACHE_PATTERN = "reference_variant_groups*"
# Trig pages, lists and exports embed variant and group names, so a rename
# clears them too
_RENAME_CACHE_PATTERNS = ["trig:*", "trigs:*", "user:*"]

_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _not_found(variant_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Variant with ID {variant_id} not found",
    )


def _check_code(code: str, what: str) -> str:
    """Upper-case a code and check it's letters, digits and underscores."""
    code = code.strip().upper()
    if not _CODE_PATTERN.match(code):
        raise _bad_request(
            f"{what} must start with a letter and use only letters, digits and underscores"
        )
    return code


def _check_name(name: str, what: str) -> str:
    name = name.strip()
    if not name:
        raise _bad_request(f"{what} cannot be blank")
    return name


def _check_unique_in_group(
    db: Session, group_code: str, name: str, exclude_id: Optional[int] = None
) -> None:
    for variant in variant_crud.get_group(db, group_code):
        if (
            int(variant.id) != exclude_id  # type: ignore[arg-type]
            and str(variant.name).lower() == name.lower()
        ):
            raise _bad_request(f'"{name}" already exists in this group')


def _check_group_name_free(db: Session, name: str, group_code: str) -> None:
    for code, existing in variant_crud.get_group_names(db).items():
        if code != group_code and existing.lower() == name.lower():
            raise _bad_request(f'A group called "{name}" already exists')


@router.get(
    "",
    response_model=list[VariantGroupAdmin],
    openapi_extra=openapi_lifecycle(
        "beta", note="Get all variant groups and their variants for admin management."
    ),
)
def get_variant_groups_admin(
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> list[VariantGroupAdmin]:
    """
    Every group with its variants in display order, the number of trigs
    recording each variant, and the types offering each group.
    """
    trig_counts = variant_crud.get_trig_counts(db)
    type_names = variant_crud.get_type_names(db)

    groups: dict[str, VariantGroupAdmin] = {}
    for v in variant_crud.get_all(db):
        group = groups.setdefault(
            str(v.group_code),
            VariantGroupAdmin(
                code=str(v.group_code),
                name=str(v.group_name),
                type_names=type_names.get(str(v.group_code), []),
                variants=[],
            ),
        )
        group.variants.append(
            TrigVariantAdmin(
                id=int(v.id),  # type: ignore[arg-type]
                code=str(v.code),
                name=str(v.name),
                sort_order=int(v.sort_order),  # type: ignore[arg-type]
                trig_count=trig_counts.get(int(v.id), 0),  # type: ignore[arg-type]
            )
        )
    return list(groups.values())


@router.post(
    "",
    response_model=TrigVariantResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=openapi_lifecycle(
        "beta", note="Create a variant, in an existing or a new group."
    ),
)
def create_variant(
    data: TrigVariantCreate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigVariantResponse:
    """
    Create a variant. A group code that doesn't exist yet starts a new group,
    which needs a group name; an existing group keeps its name.
    """
    group_code = _check_code(data.group_code, "Group code")
    code = _check_code(data.code, "Code")
    name = _check_name(data.name, "Name")
    if code == NOT_RECORDED_CODE:
        raise _bad_request(f"{NOT_RECORDED_CODE} is reserved for the filter")
    if variant_crud.get_by_code(db, code):
        raise _bad_request(f"A variant with code {code} already exists")

    group = variant_crud.get_group(db, group_code)
    if group:
        group_name = str(group[0].group_name)
        _check_unique_in_group(db, group_code, name)
    else:
        group_name = _check_name(data.group_name or "", "Group name")
        _check_group_name_free(db, group_name, group_code)

    logger.info(
        json.dumps(
            {
                "event": "admin_create_variant",
                "admin_user_id": int(admin_user.id),
                "group_code": group_code,
                "new_group": not group,
                "code": code,
                "name": name,
            }
        )
    )

    try:
        variant = variant_crud.create(
            db,
            group_code=group_code,
            group_name=group_name,
            code=code,
            name=name,
            sort_order=data.sort_order,
        )
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating variant: {e}")
        raise _bad_request(
            "Failed to create variant. Please check for duplicate values."
        ) from e

    invalidate_patterns([_REFERENCE_CACHE_PATTERN])
    return TrigVariantResponse.model_validate(variant)


@router.patch(
    "/groups/{group_code}",
    response_model=VariantGroupResponse,
    openapi_extra=openapi_lifecycle("beta", note="Rename a variant group."),
)
def rename_variant_group(
    group_code: str,
    data: VariantGroupUpdate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> VariantGroupResponse:
    """Rename a group. Its code, which types refer to, stays the same."""
    if not variant_crud.get_group(db, group_code):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variant group {group_code} not found",
        )
    name = _check_name(data.name, "Group name")
    _check_group_name_free(db, name, group_code)

    updated = variant_crud.rename_group(db, group_code, name)
    logger.info(
        json.dumps(
            {
                "event": "admin_rename_variant_group",
                "admin_user_id": int(admin_user.id),
                "group_code": group_code,
                "name": name,
                "rows_updated": updated,
            }
        )
    )

    invalidate_patterns([_REFERENCE_CACHE_PATTERN, *_RENAME_CACHE_PATTERNS])
    return VariantGroupResponse(code=group_code, name=name)


@router.patch(
    "/{variant_id}",
    response_model=TrigVariantResponse,
    openapi_extra=openapi_lifecycle("beta", note="Update a variant."),
)
def update_variant(
    variant_id: int,
    data: TrigVariantUpdate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigVariantResponse:
    """Update a variant's name and/or display order."""
    variant = variant_crud.get_by_id(db, variant_id)
    if not variant:
        raise _not_found(variant_id)

    name = None
    if data.name is not None:
        name = _check_name(data.name, "Name")
        _check_unique_in_group(db, str(variant.group_code), name, exclude_id=variant_id)
    renamed = name is not None and name != variant.name

    updated = variant_crud.update(db, variant_id, name=name, sort_order=data.sort_order)
    if updated is None:
        raise _not_found(variant_id)

    logger.info(
        json.dumps(
            {
                "event": "admin_update_variant",
                "admin_user_id": int(admin_user.id),
                "variant_id": variant_id,
                "updates": data.model_dump(exclude_none=True),
            }
        )
    )

    patterns = [_REFERENCE_CACHE_PATTERN]
    if renamed:
        patterns += _RENAME_CACHE_PATTERNS
    invalidate_patterns(patterns)
    return TrigVariantResponse.model_validate(updated)


@router.delete(
    "/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=openapi_lifecycle("beta", note="Delete a variant."),
)
def delete_variant(
    variant_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a variant. Fails if any trigs record it, or if it's the last in a
    group that types still offer.
    """
    variant = variant_crud.get_by_id(db, variant_id)
    if not variant:
        raise _not_found(variant_id)

    usage_count = variant_crud.get_usage_count(db, variant_id)
    if usage_count > 0:
        raise _bad_request(f"Cannot delete: it is used by {usage_count} trig(s)")

    group_code = str(variant.group_code)
    if len(variant_crud.get_group(db, group_code)) == 1:
        type_names = variant_crud.get_type_names(db).get(group_code, [])
        if type_names:
            raise _bad_request(
                f"Cannot delete the last {variant.group_name} value while "
                f"{', '.join(type_names)} offer the group"
            )

    logger.info(
        json.dumps(
            {
                "event": "admin_delete_variant",
                "admin_user_id": int(admin_user.id),
                "variant_id": variant_id,
                "code": str(variant.code),
            }
        )
    )

    variant_crud.delete(db, variant_id)
    invalidate_patterns([_REFERENCE_CACHE_PATTERN])
