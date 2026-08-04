"""Unit tests for API update request builder and reconciler."""

# ruff: noqa: D101

from __future__ import annotations

from typing import Annotated, Literal

import pytest
from pydantic import Field, ValidationError

from fastapi_factory_utilities.core.utils.api import ApiField, ApiResponseModelAbstract


class ProfileEntity(ApiResponseModelAbstract):
    display_name: Annotated[str, ApiField(updateable=True)]
    nickname: Annotated[str, ApiField()]


class AccountEntity(ApiResponseModelAbstract):
    name: Annotated[str, ApiField(updateable=True)]
    profile: Annotated[ProfileEntity, ApiField(updateable=True)]
    role: Annotated[str, ApiField()]
    internal_token: str


class FrIdentity(ApiResponseModelAbstract):
    jurisdiction: Literal["fr"] = "fr"
    siret: Annotated[str, ApiField()]


class UsIdentity(ApiResponseModelAbstract):
    jurisdiction: Literal["us"] = "us"
    ein: Annotated[str, ApiField()]


LegalIdentity = Annotated[FrIdentity | UsIdentity, Field(discriminator="jurisdiction")]


class CompanyEntity(ApiResponseModelAbstract):
    legal_name: Annotated[str, ApiField(updateable=True)]
    legal_identity: Annotated[LegalIdentity, ApiField(updateable=True)]


class AddressEntity(ApiResponseModelAbstract):
    city: Annotated[str, ApiField(updateable=True)]
    postal_code: Annotated[str, ApiField(updateable=True)]


class OrgEntity(ApiResponseModelAbstract):
    name: Annotated[str, ApiField(updateable=True)]
    address: Annotated[AddressEntity, ApiField(updateable=True)]


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


def test_reconcile_replaces_union_typed_updateable_field_wholesale() -> None:
    """Replace a union leaf wholesale so the previous variant's keys disappear."""
    original = CompanyEntity(
        legal_name="Acme SAS",
        legal_identity=FrIdentity(siret="73282932000074"),
    )
    put_model = CompanyEntity.build_update_request_model()
    put_request = put_model.model_validate(
        {
            "legal_name": "Acme SAS",
            "legal_identity": {"jurisdiction": "us", "ein": "123456789"},
        }
    )

    result = CompanyEntity.reconcile_update_request(
        entity_original=original,
        put_request=put_request,
        strict=True,
    )

    updated = result.entity_updated.legal_identity
    assert isinstance(updated, UsIdentity)
    assert updated.ein == "123456789"
    assert not hasattr(updated, "siret")
    assert "siret" not in updated.model_dump()
    assert len(result.changed) == 1
    assert result.changed[0].path == "legal_identity"
    assert not result.ignored_paths


def test_reconcile_still_patches_ordinary_nested_updateable_leaves() -> None:
    """Keep per-leaf patching for an ordinary nested model with updateable leaves."""
    original = OrgEntity(
        name="Acme",
        address=AddressEntity(city="Paris", postal_code="75001"),
    )
    put_model = OrgEntity.build_update_request_model()
    put_request = put_model.model_validate(
        {
            "name": "Acme",
            "address": {"city": "Lyon", "postal_code": "75001"},
        }
    )

    result = OrgEntity.reconcile_update_request(
        entity_original=original,
        put_request=put_request,
        strict=True,
    )

    assert result.entity_updated.address.city == "Lyon"
    assert result.entity_updated.address.postal_code == "75001"
    assert {change.path for change in result.changed} == {"address.city"}
    assert not result.ignored_paths
