"""Unit tests for the CSFLE schema-map builder and index-collision validation."""

from typing import Annotated

import pytest
from beanie import Indexed  # pyright: ignore[reportUnknownVariableType]
from bson import Binary
from pydantic import BaseModel
from pymongo import IndexModel

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.encryption.schema import (
    ENCRYPT_ALGORITHM,
    build_schema_map,
    validate_no_index_collisions,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import (
    EncryptedFieldIndexCollisionError,
)

DATABASE_NAME = "test-database"
KEY_ID = Binary(b"k" * 16, subtype=4)


class _Creds(BaseModel):
    client_id: str
    client_secret: str


class _NoEncryptedFieldsDocument(BaseDocument):
    label: str


class _CredsDocument(BaseDocument):
    creds: _Creds

    class Settings(BaseDocument.Settings):
        encrypted_fields = ["creds.client_secret"]  # noqa: RUF012


class _TopLevelEncryptedDocument(BaseDocument):
    processor_vault_token: str

    class Settings(BaseDocument.Settings):
        name = "payment_methods"
        encrypted_fields = ["processor_vault_token"]  # noqa: RUF012


class _AnnotatedIndexCollisionDocument(BaseDocument):
    access_token: Annotated[str, Indexed()]

    class Settings(BaseDocument.Settings):
        encrypted_fields = ["access_token"]  # noqa: RUF012


class _SettingsIndexCollisionDocument(BaseDocument):
    processor_vault_token: str

    class Settings(BaseDocument.Settings):
        encrypted_fields = ["processor_vault_token"]  # noqa: RUF012
        indexes = [IndexModel([("processor_vault_token", 1)])]  # noqa: RUF012


class TestValidateNoIndexCollisions:
    """Tests for ``validate_no_index_collisions``."""

    def test_passes_when_no_document_declares_encrypted_fields(self) -> None:
        """Documents without any encrypted field declaration are not inspected further."""
        validate_no_index_collisions([_NoEncryptedFieldsDocument])

    def test_passes_when_encrypted_field_is_not_indexed(self) -> None:
        """A nested encrypted field with no matching index passes validation."""
        validate_no_index_collisions([_CredsDocument, _TopLevelEncryptedDocument])

    def test_rejects_annotated_indexed_field(self) -> None:
        """A field carrying ``Annotated[..., Indexed()]`` collides with its own encryption."""
        with pytest.raises(EncryptedFieldIndexCollisionError, match="access_token"):
            validate_no_index_collisions([_AnnotatedIndexCollisionDocument])

    def test_rejects_field_covered_by_settings_indexes(self) -> None:
        """A field referenced by ``Settings.indexes`` collides with its own encryption."""
        with pytest.raises(EncryptedFieldIndexCollisionError, match="processor_vault_token"):
            validate_no_index_collisions([_SettingsIndexCollisionDocument])


class TestBuildSchemaMap:
    """Tests for ``build_schema_map``."""

    def test_skips_documents_without_encrypted_fields(self) -> None:
        """A document with no ``encrypted_fields`` contributes nothing to the schema map."""
        schema_map = build_schema_map([_NoEncryptedFieldsDocument], database_name=DATABASE_NAME, key_id=KEY_ID)

        assert not schema_map

    def test_builds_nested_property_for_dotted_path(self) -> None:
        """A dotted path becomes a nested ``bsonType: object`` schema, leaf-encrypted."""
        schema_map = build_schema_map([_CredsDocument], database_name=DATABASE_NAME, key_id=KEY_ID)

        collection_schema = schema_map[f"{DATABASE_NAME}.{_CredsDocument.__name__}"]
        assert collection_schema["bsonType"] == "object"
        assert collection_schema["encryptMetadata"] == {"keyId": [KEY_ID]}
        creds_schema = collection_schema["properties"]["creds"]
        assert creds_schema["bsonType"] == "object"
        assert creds_schema["properties"]["client_secret"]["encrypt"] == {
            "bsonType": "string",
            "algorithm": ENCRYPT_ALGORITHM,
        }

    def test_uses_settings_name_when_set(self) -> None:
        """The schema map key uses ``Settings.name`` rather than the class name when set."""
        schema_map = build_schema_map([_TopLevelEncryptedDocument], database_name=DATABASE_NAME, key_id=KEY_ID)

        assert f"{DATABASE_NAME}.payment_methods" in schema_map

    def test_all_documents_share_the_same_key_id(self) -> None:
        """Every collection's schema references the single service-wide DEK."""
        schema_map = build_schema_map(
            [_CredsDocument, _TopLevelEncryptedDocument], database_name=DATABASE_NAME, key_id=KEY_ID
        )

        for collection_schema in schema_map.values():
            assert collection_schema["encryptMetadata"] == {"keyId": [KEY_ID]}
