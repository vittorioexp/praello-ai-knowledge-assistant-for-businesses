"""Resolve effective document ACL principals for an authenticated user."""

import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.infrastructure.database.models.scim_group import ScimGroupModel


class ACLResolver:
    """Expand SCIM group membership into the principals stored on documents."""

    def __init__(self, ttl_seconds: int = 60) -> None:
        self._ttl = ttl_seconds
        self._cache: dict[tuple[UUID, UUID, str], tuple[float, frozenset[str]]] = {}

    async def principals(
        self, session: AsyncSession, organization_id: UUID | None, user_id: UUID, email: str
    ) -> set[str]:
        result = {str(user_id), email.lower(), "link:anyone", "link:authenticated", "link:organization"}
        if organization_id is None:
            return result
        key = (organization_id, user_id, email.lower())
        cached = self._cache.get(key)
        now = time.monotonic()
        if cached and cached[0] > now:
            return result | set(cached[1])

        groups = (
            await session.execute(
                select(ScimGroupModel).where(ScimGroupModel.organization_id == organization_id)
            )
        ).scalars().all()
        memberships = {str(user_id), email.lower()}
        effective: set[str] = set()
        by_member: dict[str, list[ScimGroupModel]] = {}
        for group in groups:
            for member in group.member_ids or []:
                by_member.setdefault(str(member).lower(), []).append(group)
        pending = list(memberships)
        visited: set[str] = set()
        while pending:
            member = pending.pop()
            if member in visited:
                continue
            visited.add(member)
            for group in by_member.get(member, []):
                identifiers = {str(group.id).lower(), group.display_name.lower(), f"group:{group.display_name.lower()}"}
                effective.update(identifiers)
                pending.extend(identifiers)
        self._cache[key] = (now + self._ttl, frozenset(effective))
        return result | effective

    def invalidate(self, organization_id: UUID | None = None) -> None:
        if organization_id is None:
            self._cache.clear()
        else:
            self._cache = {key: value for key, value in self._cache.items() if key[0] != organization_id}