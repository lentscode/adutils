"""Persistent per-user state for ``adutils``.

State is kept in the OS-appropriate per-user data directory (via
:mod:`platformdirs`) so it survives re-creations of the virtualenv the
package is installed in.

Currently stores the SSH target the user configured with the ``init``
subcommand so later commands (e.g. ``adutils ssh``) can reuse it without
making the user type ``user@host`` again.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

_APP_NAME = "adutils"
_STATE_FILE = Path(user_data_dir(_APP_NAME, appauthor=False)) / "state.json"


def state_path() -> Path:
    """Return the absolute path of the on-disk state file."""
    return _STATE_FILE


def load_state() -> dict[str, Any]:
    """Load and return the persisted state, or an empty dict if absent."""
    if not _STATE_FILE.exists():
        return {}
    try:
        return json.loads(_STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, Any]) -> None:
    """Persist ``state`` to disk, creating parent dirs as needed."""
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def save_ssh_target(
    *,
    user: str,
    host: str,
    ssh_opts: tuple[str, ...] = (),
) -> None:
    """Persist the SSH target used by ``init`` so other commands can reuse it."""
    state = load_state()
    state["ssh"] = {"user": user, "host": host, "ssh_opts": list(ssh_opts)}
    save_state(state)


def load_ssh_target() -> dict[str, Any] | None:
    """Return the saved SSH target, or ``None`` if none was ever saved."""
    state = load_state()
    target = state.get("ssh")
    if not target or not target.get("user") or not target.get("host"):
        return None
    return target
