"""Unit tests for the S3 object-URL codec."""

from fastapi_factory_utilities.core.plugins.s3_plugin.urls import (
    build_object_url,
    inject_public_path_prefix,
    key_from_url,
    parse_bucket_and_key,
)


class TestBuildObjectUrl:
    """Tests for ``build_object_url``."""

    def test_path_style_with_encoding(self) -> None:
        """Writer emits path-style URLs with percent-encoded keys."""
        assert (
            build_object_url(
                endpoint_url="http://minio:9000",
                bucket_name="videos",
                key="realm/vid/summary.json",
            )
            == "http://minio:9000/videos/realm/vid/summary.json"
        )
        assert (
            build_object_url(
                endpoint_url="http://minio:9000/",
                bucket_name="videos",
                key="a b/c#d",
            )
            == "http://minio:9000/videos/a%20b/c%23d"
        )


class TestParseBucketAndKey:
    """Tests for ``parse_bucket_and_key``."""

    def test_path_style(self) -> None:
        """Path-style URLs yield bucket and key; host is ignored."""
        assert parse_bucket_and_key("http://old-host/invoices/realms/x.pdf") == (
            "invoices",
            "realms/x.pdf",
        )

    def test_percent_encoded_legacy(self) -> None:
        """Percent-encoded keys (youtube MinIO legacy) are unquoted."""
        assert parse_bucket_and_key("http://minio/videos/realm%2Fvid%2Fsummary.json") == (
            "videos",
            "realm/vid/summary.json",
        )

    def test_incomplete_returns_none(self) -> None:
        """URLs without a key return None."""
        assert parse_bucket_and_key("http://host/bucket-only") is None
        assert parse_bucket_and_key("http://host/") is None


class TestKeyFromUrl:
    """Tests for ``key_from_url``."""

    def test_subscription_raw_path_style(self) -> None:
        """Legacy subscription raw path-style URLs resolve."""
        assert (
            key_from_url(
                url="http://minio.minio-tenant.svc/velmios-stg-invoices/realms/r/invoices/i.pdf",
                bucket_name="velmios-stg-invoices",
            )
            == "realms/r/invoices/i.pdf"
        )

    def test_foreign_endpoint_still_resolves(self) -> None:
        """Host mismatch does not prevent key extraction (endpoint-change safe)."""
        assert (
            key_from_url(
                url="http://old-endpoint:9000/media-bucket/obj.txt",
                bucket_name="media-bucket",
            )
            == "obj.txt"
        )

    def test_virtual_host_style(self) -> None:
        """Virtual-host style URLs resolve when the bucket is the host prefix."""
        assert (
            key_from_url(
                url="http://media-bucket.s3.example.com/path/to/obj",
                bucket_name="media-bucket",
            )
            == "path/to/obj"
        )

    def test_foreign_bucket_returns_none(self) -> None:
        """URLs for a different bucket return None."""
        assert key_from_url(url="http://host/other/obj", bucket_name="media-bucket") is None


class TestInjectPublicPathPrefix:
    """Tests for ``inject_public_path_prefix``."""

    def test_injects_once(self) -> None:
        """Path prefix is prepended when absent."""
        signed: str = "https://storage.example.com/bucket/key?sig=1"
        assert inject_public_path_prefix(signed, "/storage") == "https://storage.example.com/storage/bucket/key?sig=1"

    def test_idempotent(self) -> None:
        """Already-prefixed paths are left alone."""
        signed: str = "https://storage.example.com/storage/bucket/key?sig=1"
        assert inject_public_path_prefix(signed, "/storage") == signed

    def test_none_prefix(self) -> None:
        """None / empty prefix is a no-op."""
        signed: str = "https://storage.example.com/bucket/key"
        assert inject_public_path_prefix(signed, None) == signed
