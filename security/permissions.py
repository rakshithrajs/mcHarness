import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

import yaml


class RiskLevel(str, Enum):
    SAFE = "safe"
    PROMPT = "prompt"
    BLOCKED = "blocked"


class SecurityError(Exception):
    """Raised when a tool call is rejected by the permission manager."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class SecurityDecision:
    risk: RiskLevel
    reason: str
    path: str | None = None
    command: str | None = None


@dataclass
class SecurityConfig:
    project_root: Path = field(default_factory=lambda: Path(os.getcwd()).resolve())
    sensitive_paths: list[str] = field(default_factory=list[str])
    blocked_shell_tokens: list[str] = field(default_factory=list[str])
    blocked_write_extensions: list[str] = field(default_factory=list[str])
    outside_root_write_policy: RiskLevel = RiskLevel.PROMPT
    outside_root_read_policy: RiskLevel = RiskLevel.SAFE


def _default_config() -> SecurityConfig:
    return SecurityConfig(
        project_root=Path(os.getcwd()).resolve(),
        sensitive_paths=[
            r"C:\Windows",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            r"C:\Users\*\AppData\*",
            os.path.expanduser("~/.ssh"),
            os.path.expanduser("~/.aws"),
            os.path.expanduser("~/.gnupg"),
            os.path.expanduser("~/.docker"),
            r"HKEY_*",
            r"HKCU:*",
            r"HKLM:*",
            "/etc",
            "/bin",
            "/sbin",
            "/usr/bin",
            "/usr/sbin",
        ],
        blocked_shell_tokens=[
            "rm",
            "rmdir",
            "rd",
            "del",
            "erase",
            "format",
            "mkfs",
            "dd",
            "fdisk",
            "diskpart",
            "reg delete",
            "invoke-expression",
            "iex",
            "set-executionpolicy",
            "new-localuser",
            "net user",
            "netsh",
            "wevtutil cl",
            "clear-eventlog",
            "downloadstring",
            "downloadfile",
            "start-process",
            "-EncodedCommand",
            "-enc ",
        ],
        blocked_write_extensions=[
            ".exe",
            ".dll",
            ".bat",
            ".cmd",
            ".ps1",
            ".vbs",
            ".js",
            ".wsf",
            ".hta",
            ".reg",
            ".msi",
            ".msp",
            ".scr",
        ],
        outside_root_write_policy=RiskLevel.PROMPT,
        outside_root_read_policy=RiskLevel.SAFE,
    )


def _load_config_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _resolve_path(path: str | Path, root: Path) -> Path:
    target = Path(path)
    if target.is_absolute():
        return target.resolve()
    return (root / target).resolve()


class PermissionManager:
    """Application-layer guard for agent tool calls."""

    def __init__(self, config: SecurityConfig | None = None):
        self.config = config or _default_config()
        self._approved_families: set[str] = set()
        self._blocked_families: set[str] = set()
        self._pause_hook: Callable[[], None] | None = None
        self._resume_hook: Callable[[], None] | None = None

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "PermissionManager":
        config = _default_config()
        if project_root is not None:
            config.project_root = project_root.resolve()

        file_path = config.project_root / ".security.yml"
        overrides = _load_config_file(file_path)

        if "project_root" in overrides:
            config.project_root = Path(overrides["project_root"]).expanduser().resolve()
        if "sensitive_paths" in overrides:
            config.sensitive_paths = overrides["sensitive_paths"]
        if "blocked_shell_tokens" in overrides:
            config.blocked_shell_tokens = overrides["blocked_shell_tokens"]
        if "blocked_write_extensions" in overrides:
            config.blocked_write_extensions = overrides["blocked_write_extensions"]
        if "outside_root_write_policy" in overrides:
            config.outside_root_write_policy = RiskLevel(
                overrides["outside_root_write_policy"]
            )
        if "outside_root_read_policy" in overrides:
            config.outside_root_read_policy = RiskLevel(
                overrides["outside_root_read_policy"]
            )

        return cls(config)

    def _is_sensitive(self, path: Path) -> bool:
        path_str = str(path)
        norm_path = os.path.normcase(path_str)
        for pattern in self.config.sensitive_paths:
            expanded = os.path.expanduser(pattern)
            if _match_path(norm_path, os.path.normcase(expanded)):
                return True
        return False

    def _outside_root(self, path: Path) -> bool:
        try:
            path.relative_to(self.config.project_root)
            return False
        except ValueError:
            return True

    def _family(self, command: str) -> str:
        """Extract a simple family name for 'always' / 'never' prompts."""
        first = command.strip().split()[0].lower() if command.strip() else ""
        return first

    def check_shell(self, command: str) -> SecurityDecision:
        if not command or not command.strip():
            return SecurityDecision(RiskLevel.SAFE, "empty command")

        lower = command.lower()

        for token in self.config.blocked_shell_tokens:
            if token.lower() in lower:
                return SecurityDecision(
                    RiskLevel.BLOCKED,
                    f"blocked shell token '{token}' detected",
                    command=command,
                )

        destructive_patterns = [
            r"\brm\b",
            r"\brmdir\b",
            r"\brd\s+/[sq]",
            r"\bdel\s+/[fq]",
            r"\berase\s+/[fq]",
            r"\bremove-item\b",
            r"\bclear-eventlog\b",
            r"\bwevtutil\s+cl\b",
            r"\bformat\b",
            r"\bmkfs\b",
            r"\bdiskpart\b",
            r"\bfdisk\b",
            r"\bdd\s+if=",
            r"invoke-expression|iex\b",
            r"downloadstring|downloadfile",
            r"set-executionpolicy",
            r"new-localuser|net\s+user",
            r"\bcurl\b.*\|\s*(iex|invoke-expression|powershell|pwsh)",
            r"\bwget\b.*\|\s*(iex|invoke-expression|powershell|pwsh)",
        ]
        for pattern in destructive_patterns:
            if re.search(pattern, lower):
                return SecurityDecision(
                    RiskLevel.BLOCKED,
                    f"destructive shell pattern matched: {pattern!r}",
                    command=command,
                )

        outside_write_indicators = [
            r"\bmove-item\b",
            r"\bcopy-item\b",
            r"\bren\b",
            r"\brename\b",
            r"\bnew-item\b",
            r"\bset-content\b",
            r"\badd-content\b",
            r"\bout-file\b",
            r"\bsc\s+create\b",
            r"\bsc\s+delete\b",
        ]
        for pattern in outside_write_indicators:
            if re.search(pattern, lower):
                return SecurityDecision(
                    RiskLevel.PROMPT,
                    f"file-system mutation detected: {pattern!r}",
                    command=command,
                )

        return SecurityDecision(
            RiskLevel.SAFE, "command passed heuristic checks", command=command
        )

    def check_path(self, path: str | Path, operation: str) -> SecurityDecision:
        resolved = _resolve_path(path, self.config.project_root)

        if self._is_sensitive(resolved):
            return SecurityDecision(
                RiskLevel.BLOCKED,
                f"{operation} targets sensitive path: {resolved}",
                path=str(resolved),
            )

        outside = self._outside_root(resolved)
        if operation in ("write", "overwrite", "edit", "delete"):
            if outside:
                policy = self.config.outside_root_write_policy
                return SecurityDecision(
                    policy,
                    f"{operation} outside project root: {resolved}",
                    path=str(resolved),
                )

            ext = resolved.suffix.lower()
            if ext in [e.lower() for e in self.config.blocked_write_extensions]:
                return SecurityDecision(
                    RiskLevel.PROMPT,
                    f"writing executable/script file ({ext}) is restricted: {resolved}",
                    path=str(resolved),
                )

        if operation in ("read",) and outside:
            policy = self.config.outside_root_read_policy
            if policy != RiskLevel.SAFE:
                return SecurityDecision(
                    policy,
                    f"read outside project root: {resolved}",
                    path=str(resolved),
                )

        return SecurityDecision(
            RiskLevel.SAFE, f"{operation} allowed", path=str(resolved)
        )

    def confirm(self, decision: SecurityDecision) -> bool:
        if decision.risk == RiskLevel.BLOCKED:
            return False
        if decision.risk == RiskLevel.SAFE:
            return True

        family = self._family(decision.command or decision.path or "")
        if family in self._approved_families:
            return True
        if family in self._blocked_families:
            return False

        print("\n[SECURITY] The agent wants to perform a high-risk action:")
        if decision.command:
            print(f"  Command: {decision.command}")
        if decision.path:
            print(f"  Path:    {decision.path}")
        print(f"  Reason:  {decision.reason}")

        try:
            answer = self._run_input("Allow? [y/n/always/block]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("  -> denied (no input)")
            return False

        if answer in ("y", "yes"):
            return True
        if answer == "always":
            self._approved_families.add(family)
            return True
        if answer == "block":
            self._blocked_families.add(family)
            return False
        return False

    def set_prompt_hooks(
        self,
        pause: Callable[[], None] | None = None,
        resume: Callable[[], None] | None = None,
    ) -> None:
        """Register hooks to pause/resume live terminal rendering around ``input()`` prompts."""
        self._pause_hook = pause
        self._resume_hook = resume

    def _run_input(self, prompt: str) -> str:
        """Run ``input()`` safely when a live display may be active."""
        if self._pause_hook:
            self._pause_hook()
        try:
            return input(prompt)
        finally:
            if self._resume_hook:
                self._resume_hook()

    def require_approval(self, decision: SecurityDecision) -> None:
        if not self.confirm(decision):
            raise SecurityError(decision.reason)


def _match_path(path: str, pattern: str) -> bool:
    """Case-normalized path matching supporting wildcards and directory prefixes."""
    if pattern == path:
        return True
    if pattern.endswith("*") and path.startswith(pattern[:-1]):
        return True
    if path.startswith(pattern + os.sep) or path.startswith(pattern + "/"):
        return True
    regex = "^" + re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".") + "$"
    return bool(re.match(regex, path))
