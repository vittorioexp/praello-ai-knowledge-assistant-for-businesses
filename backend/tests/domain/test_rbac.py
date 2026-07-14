"""Tests for domain RBAC."""

import pytest

from enterprise_ai.domain.value_objects.role import Permission, Role


class TestRolePermissions:
    def test_viewer_has_read_permissions(self) -> None:
        role = Role.VIEWER
        assert role.has_permission(Permission.DOCUMENTS_READ.value)
        assert role.has_permission(Permission.KNOWLEDGE_QUERY.value)
        assert not role.has_permission(Permission.DOCUMENTS_UPLOAD.value)
        assert not role.has_permission(Permission.USERS_MANAGE.value)

    def test_contributor_can_upload(self) -> None:
        role = Role.CONTRIBUTOR
        assert role.has_permission(Permission.DOCUMENTS_UPLOAD.value)
        assert not role.has_permission(Permission.USERS_MANAGE.value)

    def test_analyst_can_execute_agent(self) -> None:
        role = Role.ANALYST
        assert role.has_permission(Permission.AGENT_EXECUTE.value)
        assert role.has_permission(Permission.AGENT_APPROVE.value)

    def test_admin_has_management_permissions(self) -> None:
        role = Role.ADMIN
        assert role.has_permission(Permission.USERS_MANAGE.value)
        assert role.has_permission(Permission.DOCUMENTS_DELETE.value)
        assert role.has_permission(Permission.KNOWLEDGE_ADMIN.value)

    def test_super_admin_has_all_permissions(self) -> None:
        role = Role.SUPER_ADMIN
        for perm in Permission:
            assert role.has_permission(perm.value)

    def test_invalid_permission_returns_false(self) -> None:
        role = Role.VIEWER
        assert not role.has_permission("invalid:permission")
