"""Controlled tool layer for child agents.

Tools are the only way a child agent can observe the outside world.
Every tool call is enforced against the task's ``allowed_scopes`` —
no file outside the whitelist can be read, and path traversal is blocked
at the tool layer (before the constraint layer even sees the proposal).

Built-in tools:
    - ``read_file``:            Read a file within allowed scopes.
    - ``glob``:                 List files matching a pattern within allowed scopes.
    - ``grep``:                 Search file contents within allowed scopes.
    - ``preview_text_patch``:   Preview an exact local replacement without writing.

Usage in a specialist::

    class MySpecialist(BaseSpecialist):
        def run(self, task: TaskSpec) -> list[AgentProposal]:
            ctx = ToolContext(allowed_scopes=task.allowed_scopes)
            content = ctx.read_file("app/static/play.html")
            matches = ctx.grep("settings", "app/static/")
            ...

Custom tools can be registered via :class:`ToolRegistry`.
"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .records import EvidenceProvenance

_MAX_PREVIEW_OLD_TEXT_BYTES = 8_192
_MAX_PREVIEW_NEW_TEXT_BYTES = 16_384


class ToolSecurityError(PermissionError):
    """Raised when a tool call violates scope boundaries."""


@dataclass(frozen=True)
class ToolResult:
    """Structured result from a tool call."""
    tool: str
    ok: bool
    data: Any = None
    error: str | None = None
    provenance: EvidenceProvenance | None = None


def _normalize_path(path: str) -> str:
    """Normalize a path string to forward-slash form."""
    return str(path or "").strip().replace("\\", "/")


def _has_traversal(path: str) -> bool:
    """Check for path traversal (``..``, absolute, drive prefix, ``~``)."""
    normalized = _normalize_path(path)
    first_segment = normalized.split("/", 1)[0]
    return (
        normalized.startswith(("/", "~"))
        or ":" in first_segment
        or any(part == ".." for part in normalized.split("/"))
    )


def _is_sha256_hex(value: str) -> bool:
    text = str(value or "").strip()
    return len(text) == 64 and all(char in "0123456789abcdefABCDEF" for char in text)


def _scope_allowed(path: str, allowed_scopes: tuple[str, ...]) -> bool:
    """Check if *path* falls within any of the *allowed_scopes*."""
    normalized = _normalize_path(path)
    for scope in allowed_scopes:
        scope_norm = _normalize_path(scope)
        if scope_norm.endswith("/*"):
            # Wildcard scope: check directory prefix
            prefix = scope_norm[:-2]
            if normalized.startswith(prefix + "/") or normalized == prefix:
                return True
        elif scope_norm.endswith("*"):
            prefix = scope_norm.rstrip("*")
            if normalized.startswith(prefix):
                return True
        elif normalized == scope_norm:
            return True
    return False


class ToolContext:
    """Scoped execution context for a single task's tool calls.

    Every tool method checks ``allowed_scopes`` before touching the
    filesystem.  Violations raise :class:`ToolSecurityError`.

    Args:
        allowed_scopes: Whitelist of file paths/patterns the tools may access.
        workspace_root: Root directory for resolving relative paths.
    """

    def __init__(
        self,
        allowed_scopes: tuple[str, ...] = (),
        workspace_root: str | Path = ".",
    ) -> None:
        self.allowed_scopes = allowed_scopes
        self.workspace_root = Path(workspace_root).resolve()
        self._call_log: list[dict[str, Any]] = []
        self._call_counter = 0

    # ── Security gate ──────────────────────────────────────────────

    def _enforce_scope(self, path: str) -> Path:
        """Validate *path* against allowed scopes and return resolved Path.

        Raises:
            ToolSecurityError: If the path is outside allowed scopes or
                contains traversal.
        """
        normalized = _normalize_path(path)
        if _has_traversal(normalized):
            raise ToolSecurityError(
                f"Path traversal blocked: {path}"
            )
        if not _scope_allowed(normalized, self.allowed_scopes):
            raise ToolSecurityError(
                f"Scope escape blocked: '{path}' is not in allowed scopes "
                f"({', '.join(self.allowed_scopes) or 'none'})"
            )
        return self.workspace_root / normalized

    def _next_tool_call_id(self, tool: str) -> str:
        self._call_counter += 1
        return f"{tool}:{self._call_counter:06d}"

    def _log(self, tool: str, args: dict[str, Any], result: ToolResult) -> None:
        self._call_log.append({
            "tool": tool,
            "args": args,
            "ok": result.ok,
            "error": result.error,
            "provenance": result.provenance,
        })

    @property
    def call_log(self) -> tuple[dict[str, Any], ...]:
        """Audit trail of all tool calls made through this context."""
        return tuple(self._call_log)

    # ── Built-in tools ─────────────────────────────────────────────

    def read_file(self, path: str, max_bytes: int = 512 * 1024) -> ToolResult:
        """Read a text file within allowed scopes.

        Args:
            path: Relative path within the workspace.
            max_bytes: Maximum bytes to read (default 512KB).

        Returns:
            ToolResult with ``data`` set to the file content string.
        """
        try:
            tool_call_id = self._next_tool_call_id("read_file")
            resolved = self._enforce_scope(path)
            if not resolved.exists():
                return ToolResult("read_file", False, error=f"File not found: {path}")
            if not resolved.is_file():
                return ToolResult("read_file", False, error=f"Not a file: {path}")
            raw = resolved.read_bytes()
            content = raw[:max_bytes].decode("utf-8", errors="replace")
            provenance = EvidenceProvenance(
                path=_normalize_path(path),
                sha256=hashlib.sha256(raw).hexdigest(),
                tool_call_id=tool_call_id,
                snippet_hash=hashlib.sha256(raw[:max_bytes]).hexdigest() if len(raw) > max_bytes else "",
            )
            result = ToolResult("read_file", True, data=content, provenance=provenance)
            self._log("read_file", {"path": path, "max_bytes": max_bytes}, result)
            return result
        except ToolSecurityError as e:
            result = ToolResult("read_file", False, error=str(e))
            self._log("read_file", {"path": path}, result)
            return result
        except Exception as e:
            result = ToolResult("read_file", False, error=f"read_file failed: {e}")
            self._log("read_file", {"path": path}, result)
            return result

    def preview_text_patch(
        self,
        path: str,
        old_text: str,
        new_text: str,
        *,
        expected_sha256: str = "",
    ) -> ToolResult:
        """Preview an exact text replacement without writing to disk.

        This is the deterministic half of the token-saving patch protocol:
        child agents can propose local ``old_text``/``new_text`` hunks, while the
        tool layer checks scope, optional preimage hash, exact-anchor uniqueness,
        and Python syntax for ``.py`` files before any future commit stage.
        """
        args = {"path": path, "expected_sha256": expected_sha256}
        try:
            if not isinstance(old_text, str) or not isinstance(new_text, str):
                result = ToolResult("preview_text_patch", False, error="old_text and new_text must be strings")
                self._log("preview_text_patch", args, result)
                return result
            old_text_bytes = old_text.encode("utf-8", errors="replace")
            new_text_bytes = new_text.encode("utf-8", errors="replace")
            args.update({
                "old_text_bytes": len(old_text_bytes),
                "new_text_bytes": len(new_text_bytes),
            })
            if len(old_text_bytes) > _MAX_PREVIEW_OLD_TEXT_BYTES:
                result = ToolResult("preview_text_patch", False, error="old_text is too large")
                self._log("preview_text_patch", args, result)
                return result
            if len(new_text_bytes) > _MAX_PREVIEW_NEW_TEXT_BYTES:
                result = ToolResult("preview_text_patch", False, error="new_text is too large")
                self._log("preview_text_patch", args, result)
                return result

            tool_call_id = self._next_tool_call_id("preview_text_patch")
            resolved = self._enforce_scope(path)
            if not resolved.exists():
                result = ToolResult("preview_text_patch", False, error=f"File not found: {path}")
                self._log("preview_text_patch", args, result)
                return result
            if not resolved.is_file():
                result = ToolResult("preview_text_patch", False, error=f"Not a file: {path}")
                self._log("preview_text_patch", args, result)
                return result
            if not old_text:
                result = ToolResult("preview_text_patch", False, error="old_text must not be empty")
                self._log("preview_text_patch", args, result)
                return result
            if old_text == new_text:
                result = ToolResult("preview_text_patch", False, error="no-op patch rejected")
                self._log("preview_text_patch", args, result)
                return result

            raw = resolved.read_bytes()
            sha256_before = hashlib.sha256(raw).hexdigest()
            if expected_sha256:
                if not _is_sha256_hex(expected_sha256):
                    result = ToolResult("preview_text_patch", False, error="expected_sha256 is not a sha256 hex digest")
                    self._log("preview_text_patch", args, result)
                    return result
                if expected_sha256 != sha256_before:
                    result = ToolResult("preview_text_patch", False, error="expected_sha256 does not match current file")
                    self._log("preview_text_patch", args, result)
                    return result

            original = raw.decode("utf-8", errors="replace")
            occurrence_count = original.count(old_text)
            if occurrence_count == 0:
                result = ToolResult("preview_text_patch", False, error="old_text not found")
                self._log("preview_text_patch", args, result)
                return result
            if occurrence_count > 1:
                result = ToolResult("preview_text_patch", False, error="old_text is ambiguous")
                self._log("preview_text_patch", args, result)
                return result

            patched = original.replace(old_text, new_text, 1)
            if resolved.suffix == ".py":
                try:
                    ast.parse(patched)
                except SyntaxError as exc:
                    result = ToolResult("preview_text_patch", False, error=f"python syntax error after patch: {exc.msg}")
                    self._log("preview_text_patch", args, result)
                    return result

            patched_bytes = patched.encode("utf-8")
            sha256_after = hashlib.sha256(patched_bytes).hexdigest()
            provenance = EvidenceProvenance(
                path=_normalize_path(path),
                sha256=sha256_before,
                tool_call_id=tool_call_id,
            )
            result = ToolResult(
                "preview_text_patch",
                True,
                data={
                    "path": _normalize_path(path),
                    "sha256_before": sha256_before,
                    "sha256_after": sha256_after,
                    "old_text_hash": hashlib.sha256(old_text_bytes).hexdigest(),
                    "new_text_hash": hashlib.sha256(new_text_bytes).hexdigest(),
                    "changed_bytes_delta": len(patched_bytes) - len(raw),
                    "writes_disk": False,
                },
                provenance=provenance,
            )
            self._log("preview_text_patch", args, result)
            return result
        except ToolSecurityError as e:
            result = ToolResult("preview_text_patch", False, error=str(e))
            self._log("preview_text_patch", args, result)
            return result
        except Exception as e:
            result = ToolResult("preview_text_patch", False, error=f"preview_text_patch failed: {e}")
            self._log("preview_text_patch", args, result)
            return result

    def glob(self, pattern: str, base_dir: str = ".") -> ToolResult:
        """List files matching a glob pattern within allowed scopes.

        Args:
            pattern: Glob pattern (e.g. ``**/*.py``, ``*.html``).
            base_dir: Base directory to search in (must be in allowed scopes).

        Returns:
            ToolResult with ``data`` set to a list of relative path strings.
        """
        try:
            resolved_base = self._enforce_scope(base_dir)
            if not resolved_base.exists():
                return ToolResult("glob", False, error=f"Directory not found: {base_dir}")
            if not resolved_base.is_dir():
                return ToolResult("glob", False, error=f"Not a directory: {base_dir}")
            matches = sorted(
                str(p.relative_to(self.workspace_root)).replace("\\", "/")
                for p in resolved_base.rglob(pattern)
                if p.is_file()
            )
            # Double-check each match is in scope (rglob can escape)
            safe_matches = [
                m for m in matches
                if _scope_allowed(m, self.allowed_scopes) and not _has_traversal(m)
            ]
            result = ToolResult("glob", True, data=safe_matches)
            self._log("glob", {"pattern": pattern, "base_dir": base_dir}, result)
            return result
        except ToolSecurityError as e:
            result = ToolResult("glob", False, error=str(e))
            self._log("glob", {"pattern": pattern, "base_dir": base_dir}, result)
            return result
        except Exception as e:
            result = ToolResult("glob", False, error=f"glob failed: {e}")
            self._log("glob", {"pattern": pattern, "base_dir": base_dir}, result)
            return result

    def grep(
        self,
        pattern: str,
        base_dir: str = ".",
        file_pattern: str = "*",
        max_results: int = 50,
    ) -> ToolResult:
        """Search file contents within allowed scopes.

        Args:
            pattern: Regex pattern to search for in file contents.
            base_dir: Base directory to search in.
            file_pattern: Glob pattern to filter files (e.g. ``*.py``).
            max_results: Maximum number of matches to return.

        Returns:
            ToolResult with ``data`` set to a list of dicts:
            ``{"file": str, "line": int, "text": str}``.
        """
        try:
            resolved_base = self._enforce_scope(base_dir)
            if not resolved_base.exists():
                return ToolResult("grep", False, error=f"Directory not found: {base_dir}")
            if not resolved_base.is_dir():
                return ToolResult("grep", False, error=f"Not a directory: {base_dir}")

            regex = re.compile(pattern, re.IGNORECASE)
            matches: list[dict[str, Any]] = []

            for file_path in resolved_base.rglob(file_pattern):
                if not file_path.is_file():
                    continue
                rel = str(file_path.relative_to(self.workspace_root)).replace("\\", "/")
                if not _scope_allowed(rel, self.allowed_scopes) or _has_traversal(rel):
                    continue
                try:
                    for line_num, line in enumerate(
                        file_path.read_bytes()[:256 * 1024].decode("utf-8", errors="replace").splitlines(),
                        1,
                    ):
                        if regex.search(line):
                            matches.append({"file": rel, "line": line_num, "text": line[:200]})
                            if len(matches) >= max_results:
                                break
                except Exception:
                    continue
                if len(matches) >= max_results:
                    break

            result = ToolResult("grep", True, data=matches)
            self._log("grep", {"pattern": pattern, "base_dir": base_dir, "file_pattern": file_pattern}, result)
            return result
        except ToolSecurityError as e:
            result = ToolResult("grep", False, error=str(e))
            self._log("grep", {"pattern": pattern, "base_dir": base_dir}, result)
            return result
        except Exception as e:
            result = ToolResult("grep", False, error=f"grep failed: {e}")
            self._log("grep", {"pattern": pattern, "base_dir": base_dir}, result)
            return result


# ── Tool Registry (for custom tools) ───────────────────────────────────


@dataclass(frozen=True)
class ToolDefinition:
    """Declaration of a registered tool."""
    name: str
    handler: Callable[..., ToolResult]
    description: str = ""
    requires_scope: bool = True  # If True, the tool's path arg is scope-checked


class ToolRegistry:
    """Registry for custom tools that specialists can access.

    Built-in tools (read_file, glob, grep, preview_text_patch) are always available via
    :class:`ToolContext`.  This registry is for *additional* tools
    that projects may want to add (e.g. ``run_test``, ``http_get``).
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        handler: Callable[..., ToolResult],
        description: str = "",
        requires_scope: bool = True,
    ) -> None:
        """Register a custom tool.

        Args:
            name: Tool name (must be unique).
            handler: Callable that returns a ToolResult.
            description: Human-readable description.
            requires_scope: If True, the first positional arg is scope-checked.
        """
        self._tools[name] = ToolDefinition(
            name=name,
            handler=handler,
            description=description,
            requires_scope=requires_scope,
        )

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools.keys())

    def available_tools(self, declared: tuple[str, ...]) -> tuple[str, ...]:
        """Return which of the *declared* tools are actually registered."""
        return tuple(name for name in declared if name in self._tools)
