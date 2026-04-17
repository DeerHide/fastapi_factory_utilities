"""Unit tests for API update request builder and reconciler."""

# ruff: noqa: D101

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import ValidationError

from fastapi_factory_utilities.core.utils.api import ApiResponseField, ApiResponseModelAbstract, UpdateableField


class ProfileEntity(ApiResponseModelAbstract):
    display_name: Annotated[str, UpdateableField]
    nickname: Annotated[str, ApiResponseField]


class AccountEntity(ApiResponseModelAbstract):
    name: Annotated[str, UpdateableField]
    profile: Annotated[ProfileEntity, UpdateableField]
    role: Annotated[str, ApiResponseField]
    internal_token: str


def test_build_update_request_model_requires_all_exposed_fields() -> None:
    """Require all API-exposed fields in the generated PUT model."""
    update_model = AccountEntity.build_update_request_model()

    with pytest.raises(ValidationError):
        update_model.model_validate({"name": "alice"})


def test_reconcile_put_updates_only_updateable_fields() -> None:
    """Apply PUT values only on fields marked as updateable."""
    original = AccountEntity(
        name="alice",
        profile=ProfileEntity(display_name="Alice", nickname="ali"),
        role="operator",
        internal_token="server-only",
    )
    put_model = AccountEntity.build_update_request_model()
    put_request = put_model.model_validate(
        {
            "name": "bob",
            "profile": {"display_name": "Bob", "nickname": "bobby"},
            "role": "admin",
        }
    )

    result = AccountEntity.reconcile_update_request(
        entity_original=original,
        put_request=put_request,
    )

    assert result.entity_updated.name == "bob"
    assert result.entity_updated.profile.display_name == "Bob"
    assert result.entity_updated.profile.nickname == "ali"
    assert result.entity_updated.role == "operator"
    assert result.entity_updated.internal_token == "server-only"
    assert {change.path for change in result.changed} == {"name", "profile.display_name"}
    assert set(result.ignored_paths) == {"profile.nickname", "role"}


def test_reconcile_put_strict_rejects_non_updateable_fields() -> None:
    """Raise in strict mode when payload includes non-updateable fields."""
    original = AccountEntity(
        name="alice",
        profile=ProfileEntity(display_name="Alice", nickname="ali"),
        role="operator",
        internal_token="server-only",
    )
    put_model = AccountEntity.build_update_request_model()
    put_request = put_model.model_validate(
        {
            "name": "alice",
            "profile": {"display_name": "Alice", "nickname": "ali"},
            "role": "admin",
        }
    )

    with pytest.raises(ValueError, match="non-updateable fields"):
        AccountEntity.reconcile_update_request(
            entity_original=original,
            put_request=put_request,
            strict=True,
        )
