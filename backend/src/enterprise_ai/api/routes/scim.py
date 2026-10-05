"""Minimal SCIM 2.0 provisioning endpoints."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.api.dependencies import get_app_settings, get_db_session
from enterprise_ai.domain.value_objects.role import Role
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.database.models.scim_group import ScimGroupModel
from enterprise_ai.infrastructure.database.models.user import UserModel
from enterprise_ai.infrastructure.security.password import hash_password

router = APIRouter(prefix="/scim/v2.0", tags=["SCIM"])


class ScimName(BaseModel):
    formatted: str | None = None


class ScimUserRequest(BaseModel):
    userName: str | None = None
    active: bool = True
    name: ScimName | None = None
    schemas: list[str] = Field(default_factory=list)
    Operations: list[dict] = Field(default_factory=list)


class ScimGroupRequest(BaseModel):
    displayName: str | None = None
    members: list[dict] = Field(default_factory=list)
    schemas: list[str] = Field(default_factory=list)
    Operations: list[dict] = Field(default_factory=list)


async def _scope(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_app_settings),
) -> UUID:
    if not settings.scim_bearer_token or authorization != f"Bearer {settings.scim_bearer_token}":
        raise HTTPException(status_code=401, detail="Invalid SCIM bearer token")
    try:
        return UUID(settings.scim_organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="SCIM organization is not configured") from exc


def _user_response(user: UserModel) -> dict:
    return {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"], "id": str(user.id), "userName": user.email, "active": user.is_active, "name": {"formatted": user.full_name}, "meta": {"resourceType": "User"}}


@router.post("/Users", status_code=status.HTTP_201_CREATED)
async def create_user(request: ScimUserRequest, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict:
    existing = (await session.execute(select(UserModel).where(UserModel.email == request.userName, UserModel.organization_id == organization_id))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    user = UserModel(id=uuid4(), email=request.userName, hashed_password=hash_password(uuid4().hex), full_name=(request.name.formatted if request.name and request.name.formatted else request.userName), role=Role.VIEWER.value, is_active=request.active, organization_id=organization_id)
    session.add(user)
    await session.flush()
    return _user_response(user)


@router.get("/Users")
async def list_users(organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)], filter: Annotated[str | None, Query()] = None, start_index: Annotated[int, Query(alias="startIndex", ge=1)] = 1, count: Annotated[int, Query(ge=1, le=1000)] = 100) -> dict:
    return await _list_resources(UserModel, organization_id, session, filter, start_index, count)


async def _list_resources(model, organization_id: UUID, session: AsyncSession, filter_value: str | None = None, start_index: int = 1, count: int = 100) -> dict:
    query = select(model).where(model.organization_id == organization_id)
    if filter_value and model is UserModel:
        value = filter_value.split(" eq ", 1)[-1].strip(' "')
        query = query.where(func.lower(UserModel.email) == value.lower())
    elif filter_value and model is ScimGroupModel:
        value = filter_value.split(" eq ", 1)[-1].strip(' "')
        query = query.where(func.lower(ScimGroupModel.display_name) == value.lower())
    total = len((await session.execute(query)).scalars().all())
    rows = (await session.execute(query)).scalars().all()
    rows = rows[max(start_index - 1, 0) : max(start_index - 1, 0) + count]
    resources = [_user_response(row) if model is UserModel else _group_response(row) for row in rows]
    return {"schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"], "totalResults": total, "startIndex": start_index, "itemsPerPage": len(resources), "Resources": resources}


@router.get("/Users/{user_id}")
async def get_user(user_id: UUID, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict:
    user = await _get_user(user_id, organization_id, session)
    return _user_response(user)


@router.patch("/Users/{user_id}")
async def update_user(user_id: UUID, request: ScimUserRequest, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict:
    user = await _get_user(user_id, organization_id, session)
    if request.Operations:
        _apply_operations(user, request.Operations)
    else:
        if request.userName is not None:
            user.email = request.userName
        user.is_active = request.active
        if request.name and request.name.formatted:
            user.full_name = request.name.formatted
    await session.flush()
    return _user_response(user)


@router.put("/Users/{user_id}")
async def replace_user(user_id: UUID, request: ScimUserRequest, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict:
    return await update_user(user_id, request, organization_id, session)


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> None:
    user = await _get_user(user_id, organization_id, session)
    user.is_active = False
    await session.flush()


async def _get_user(user_id: UUID, organization_id: UUID, session: AsyncSession) -> UserModel:
    user = (await session.execute(select(UserModel).where(UserModel.id == user_id, UserModel.organization_id == organization_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _apply_operations(user: UserModel, operations: list[dict]) -> None:
    for operation in operations:
        path = str(operation.get("path", "")).lower()
        value = operation.get("value")
        if path in {"active", ""} and isinstance(value, bool):
            user.is_active = value
        elif path in {"username", "username.value"} and isinstance(value, str):
            user.email = value
        elif path in {"name.formatted", "displayname"} and isinstance(value, str):
            user.full_name = value


@router.post("/Groups", status_code=status.HTTP_201_CREATED)
async def create_group(request: ScimGroupRequest, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict:
    group = ScimGroupModel(organization_id=organization_id, display_name=request.displayName, member_ids=[str(member["value"]) for member in request.members if member.get("value")])
    session.add(group)
    await session.flush()
    return _group_response(group)


@router.get("/Groups")
async def list_groups(organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)], filter: Annotated[str | None, Query()] = None, start_index: Annotated[int, Query(alias="startIndex", ge=1)] = 1, count: Annotated[int, Query(ge=1, le=1000)] = 100) -> dict:
    return await _list_resources(ScimGroupModel, organization_id, session, filter, start_index, count)


def _group_response(group: ScimGroupModel) -> dict:
    return {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"], "id": str(group.id), "displayName": group.display_name, "members": [{"value": value} for value in group.member_ids], "meta": {"resourceType": "Group"}}


@router.get("/Groups/{group_id}")
async def get_group(group_id: UUID, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict:
    group = await _get_group(group_id, organization_id, session)
    return _group_response(group)


@router.put("/Groups/{group_id}")
async def replace_group(group_id: UUID, request: ScimGroupRequest, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict:
    group = await _get_group(group_id, organization_id, session)
    group.display_name = request.displayName or group.display_name
    group.member_ids = [str(member["value"]) for member in request.members if member.get("value")]
    await session.flush()
    return _group_response(group)


@router.patch("/Groups/{group_id}")
async def update_group(group_id: UUID, request: ScimGroupRequest, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict:
    group = await _get_group(group_id, organization_id, session)
    for operation in request.Operations:
        path = str(operation.get("path", "")).lower()
        values = operation.get("value", [])
        if path == "displayname" and isinstance(values, str):
            group.display_name = values
        elif path in {"members", ""}:
            members = values if isinstance(values, list) else [values]
            if operation.get("op", "replace").lower() == "remove":
                removed = {str(item.get("value", item)) for item in members}
                group.member_ids = [value for value in group.member_ids if value not in removed]
            elif operation.get("op", "replace").lower() == "add":
                group.member_ids = list(dict.fromkeys(group.member_ids + [str(item.get("value", item)) for item in members]))
            else:
                group.member_ids = [str(item.get("value", item)) for item in members]
    await session.flush()
    return _group_response(group)


@router.delete("/Groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: UUID, organization_id: Annotated[UUID, Depends(_scope)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> None:
    group = await _get_group(group_id, organization_id, session)
    await session.delete(group)
    await session.flush()


async def _get_group(group_id: UUID, organization_id: UUID, session: AsyncSession) -> ScimGroupModel:
    group = (await session.execute(select(ScimGroupModel).where(ScimGroupModel.id == group_id, ScimGroupModel.organization_id == organization_id))).scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group