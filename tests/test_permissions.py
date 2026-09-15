"""Tests for the security module."""

import pathlib

import pytest

from security import PermissionManager, RiskLevel, SecurityConfig, SecurityError


@pytest.fixture
def pm(tmp_path: pathlib.Path) -> PermissionManager:
    """Create a PermissionManager with a temporary project root and some sensitive paths."""
    return PermissionManager(
        SecurityConfig(
            project_root=tmp_path,
            sensitive_paths=[str(tmp_path / "secrets")],
            blocked_shell_tokens=["rm"],
            blocked_write_extensions=[".exe"],
            outside_root_write_policy=RiskLevel.PROMPT,
            outside_root_read_policy=RiskLevel.SAFE,
        ),
    )


def test_safe_shell_command(pm: PermissionManager) -> None:
    """Test that a safe shell command is allowed."""
    decision = pm.check_shell("ls -la")
    assert decision.risk == RiskLevel.SAFE


def test_blocked_shell_token(pm: PermissionManager) -> None:
    """Test that a shell command with a blocked token is blocked."""
    decision = pm.check_shell("rm -rf build")
    assert decision.risk == RiskLevel.BLOCKED


def test_blocked_shell_pattern(pm: PermissionManager) -> None:
    """Test that a shell command with a blocked pattern is blocked."""
    decision = pm.check_shell("Invoke-Expression $payload")
    assert decision.risk == RiskLevel.BLOCKED


def test_read_inside_project_is_safe(
    pm: PermissionManager,
    tmp_path: pathlib.Path,
) -> None:
    """Test that reading a file inside the project root is safe."""
    decision = pm.check_path(str(tmp_path / "file.txt"), "read")
    assert decision.risk == RiskLevel.SAFE


def test_write_outside_project_prompts(pm: PermissionManager) -> None:
    """Test that writing to a file outside the project root prompts for approval."""
    decision = pm.check_path("C:/outside/file.txt", "write")
    assert decision.risk == RiskLevel.PROMPT


def test_write_to_sensitive_path_is_blocked(
    pm: PermissionManager,
    tmp_path: pathlib.Path,
) -> None:
    """Test that writing to a sensitive path is blocked."""
    decision = pm.check_path(str(tmp_path / "secrets" / "key.txt"), "write")
    assert decision.risk == RiskLevel.BLOCKED


def test_write_executable_extension_prompts(
    pm: PermissionManager,
    tmp_path: pathlib.Path,
) -> None:
    """Test that writing to a file with a blocked extension prompts for approval."""
    decision = pm.check_path(str(tmp_path / "app.exe"), "write")
    assert decision.risk == RiskLevel.PROMPT


def test_confirm_auto_allows_safe(pm: PermissionManager) -> None:
    """Test that confirm returns True for safe actions."""
    decision = pm.check_shell("git status")
    assert pm.confirm(decision) is True


def test_confirm_blocked_is_false(pm: PermissionManager) -> None:
    """Test that confirm returns False for blocked actions."""
    decision = pm.check_shell("rm file")
    assert pm.confirm(decision) is False


def test_require_approval_raises_on_blocked(pm: PermissionManager) -> None:
    """Test that require_approval raises SecurityError for blocked actions."""
    decision = pm.check_shell("rm file")
    with pytest.raises(SecurityError):
        pm.require_approval(decision)
