"""Integration tests for CSFLE (Client-Side Field Level Encryption) via the ODM plugin.

Requires `mongocryptd` on PATH (the `mongodb-enterprise-cryptd` package): PyMongo spawns it as a
subprocess for automatic query analysis on the very first encrypted operation. Skipped when it is
not installed — see the `mongocryptd delivery` section of the CSFLE change's `design.md`.
"""

import shutil
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from beanie import init_beanie  # pyright: ignore[reportUnknownVariableType]
from bson import Binary
from pydantic import Field
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument

CIPHERTEXT_SUBTYPE = 6

requires_mongocryptd = pytest.mark.skipif(
    shutil.which("mongocryptd") is None,
    reason="Requires mongocryptd on PATH (mongodb-enterprise-cryptd); see design.md decision 3.",
)

EncryptingOdmFactory = Callable[
    [list[type[BaseDocument]]], Awaitable[tuple[AsyncMongoClient[Any], AsyncDatabase[Any], AsyncDatabase[Any]]]
]


class _CsfleDocumentForTest(BaseDocument):
    """Test document with a single declared encrypted field."""

    label: str = Field(description="Unencrypted discriminator field.")
    secret_value: str = Field(description="Declared encrypted field.")

    class Settings(BaseDocument.Settings):
        """Settings for ``_CsfleDocumentForTest``."""

        encrypted_fields = ["secret_value"]  # noqa: RUF012


@requires_mongocryptd
class TestCsfleEncryption:
    """Integration tests proving CSFLE round-trips through Beanie and encrypts at rest."""

    @pytest.mark.asyncio()
    async def test_declared_field_round_trips_and_is_ciphertext_via_plain_client(
        self,
        encrypting_odm_factory: EncryptingOdmFactory,
    ) -> None:
        """A declared encrypted field decrypts transparently, but is ciphertext at rest."""
        encrypting_client, encrypting_database, plain_database = await encrypting_odm_factory([_CsfleDocumentForTest])
        await init_beanie(database=encrypting_database, document_models=[_CsfleDocumentForTest])

        document: _CsfleDocumentForTest = await _CsfleDocumentForTest(
            label="round-trip", secret_value="super-secret"
        ).insert()

        fetched: _CsfleDocumentForTest | None = await _CsfleDocumentForTest.get(document.id)
        assert fetched is not None
        assert fetched.secret_value == "super-secret"

        raw: dict[str, Any] | None = await plain_database[_CsfleDocumentForTest.get_collection_name()].find_one(
            {"_id": document.id}
        )
        assert raw is not None
        assert isinstance(raw["secret_value"], Binary)
        assert raw["secret_value"].subtype == CIPHERTEXT_SUBTYPE
        assert raw["label"] == "round-trip"

        await encrypting_client.close()

    @pytest.mark.asyncio()
    async def test_mixed_plaintext_and_ciphertext_documents_both_read_correctly(
        self,
        encrypting_odm_factory: EncryptingOdmFactory,
    ) -> None:
        """A collection holding both legacy plaintext and CSFLE ciphertext reads correctly."""
        encrypting_client, encrypting_database, plain_database = await encrypting_odm_factory([_CsfleDocumentForTest])

        # A "legacy" document, written before CSFLE was enabled: through the plain client,
        # secret_value is stored (and stays) as an ordinary string.
        await init_beanie(database=plain_database, document_models=[_CsfleDocumentForTest])
        legacy_document: _CsfleDocumentForTest = await _CsfleDocumentForTest(
            label="legacy", secret_value="written-before-csfle"
        ).insert()

        # A new document, written through the encrypting client.
        await init_beanie(database=encrypting_database, document_models=[_CsfleDocumentForTest])
        encrypted_document: _CsfleDocumentForTest = await _CsfleDocumentForTest(
            label="current", secret_value="via-encrypting-client"
        ).insert()

        fetched_legacy: _CsfleDocumentForTest | None = await _CsfleDocumentForTest.get(legacy_document.id)
        fetched_encrypted: _CsfleDocumentForTest | None = await _CsfleDocumentForTest.get(encrypted_document.id)
        assert fetched_legacy is not None
        assert fetched_encrypted is not None
        assert fetched_legacy.secret_value == "written-before-csfle"
        assert fetched_encrypted.secret_value == "via-encrypting-client"

        collection = plain_database[_CsfleDocumentForTest.get_collection_name()]
        raw_legacy: dict[str, Any] | None = await collection.find_one({"_id": legacy_document.id})
        raw_encrypted: dict[str, Any] | None = await collection.find_one({"_id": encrypted_document.id})
        assert raw_legacy is not None
        assert raw_encrypted is not None
        assert isinstance(raw_legacy["secret_value"], str)
        assert isinstance(raw_encrypted["secret_value"], Binary)
        assert raw_encrypted["secret_value"].subtype == CIPHERTEXT_SUBTYPE

        await encrypting_client.close()
