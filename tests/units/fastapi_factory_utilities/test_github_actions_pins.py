"""Guardrail: GitHub Actions must be pinned to full commit SHAs."""

from pathlib import Path

import pytest
import yaml

_WORKFLOWS_DIR = Path(__file__).resolve().parents[3] / ".github" / "workflows"
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
    dependabot = yaml.safe_load(Path(".github/dependabot.yml").read_text())
    ecosystems = {entry["package-ecosystem"] for entry in dependabot["updates"]}
    assert "github-actions" in ecosystems
