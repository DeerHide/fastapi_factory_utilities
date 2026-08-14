"""Tests for optional extra guards."""

import pytest

from fastapi_factory_utilities.core.exceptions import MissingExtraError
from fastapi_factory_utilities.core.plugins.extras import PLUGIN_BACKENDS, require_extra

_MISSING_MODULE = "fastapi_factory_utilities_missing_extra_zz"


@pytest.mark.parametrize("extra", [item[0] for item in PLUGIN_BACKENDS])
def test_missing_extra_error_names_the_extra(extra: str) -> None:
    """Each plugin extra produces a named error, not a bare import failure."""
    with pytest.raises(MissingExtraError, match=extra) as exc_info:
        require_extra(extra, _MISSING_MODULE)
    assert extra in str(exc_info.value)
    assert "fastapi_factory_utilities[" in str(exc_info.value)
    assert not isinstance(exc_info.value, ModuleNotFoundError)
