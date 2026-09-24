"""Guardrail: GitHub Actions must be pinned to full commit SHAs."""

from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"
_DEPENDABOT_PATH = _REPO_ROOT / ".github" / "dependabot.yml"
_SHA_LENGTH = 40


def _workflow_files() -> list[Path]:
    return sorted(_WORKFLOWS_DIR.glob("*.yml")) + sorted(_WORKFLOWS_DIR.glob("*.yaml"))


def _collect_uses(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        uses = node.get("uses")
        if isinstance(uses, str):
            found.append(uses)
        for value in node.values():
            found.extend(_collect_uses(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_collect_uses(item))
    return found


def test_at_least_one_workflow_file_exists() -> None:
    """Empty/missing workflows dir must fail loudly, not skip the pin checks."""
    assert _workflow_files(), f"expected workflow files under {_WORKFLOWS_DIR}"


@pytest.mark.parametrize("workflow_path", _workflow_files(), ids=lambda p: p.name)
def test_actions_are_pinned_to_full_commit_shas(workflow_path: Path) -> None:
    """Every third-party ``uses:`` entry must be owner/repo@<40-char sha>."""
    document = yaml.safe_load(workflow_path.read_text())
    uses_entries = _collect_uses(document)
    assert uses_entries, f"expected at least one action in {workflow_path.name}"

    for uses in uses_entries:
        # Local reusable workflows: ./path — skip SHA rule
        if uses.startswith("./"):
            continue
        assert "@" in uses, f"missing pin in {workflow_path.name}: {uses}"
        ref = uses.rsplit("@", maxsplit=1)[1].split()[0]  # strip trailing comments
        assert len(ref) == _SHA_LENGTH and all(c in "0123456789abcdef" for c in ref.lower()), (
            f"Action not SHA-pinned in {workflow_path.name}: {uses}"
        )


def test_dependabot_tracks_github_actions_ecosystem() -> None:
    """Dependabot must refresh Action pins, not only pip."""
    dependabot = yaml.safe_load(_DEPENDABOT_PATH.read_text())
    ecosystems = {entry["package-ecosystem"] for entry in dependabot["updates"]}
    assert "github-actions" in ecosystems
