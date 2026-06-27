"""Command line interface for ``adutils``.

Currently exposes the ``init`` subcommand, which connects to a remote
machine over SSH, configures the user's global git identity and turns
every first-level directory inside the user's home directory into a
non-bare git repository (without committing anything).

The tool relies on the standard ``ssh`` client being available on the
machine running the CLI – it shells out to it instead of pulling in a
Python SSH dependency.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from typing import Sequence

from adutils import state


class SshError(RuntimeError):
    """Raised when a remote command fails to execute."""


def _remote_run(
    user: str,
    host: str,
    command: str,
    *,
    ssh_opts: Sequence[str] = (),
    check: bool = True,
) -> str:
    """Run ``command`` on ``user@host`` through ssh and return its stdout.

    Parameters
    ----------
    user, host:
        SSH credentials/host to connect to.
    command:
        A single shell command (or ``&&``-chained script) executed by the
        remote login shell.
    ssh_opts:
        Extra flags forwarded to the ``ssh`` invocation (e.g.
        ``("-p", "2222")``).
    check:
        When ``True`` (default) a non-zero exit code is turned into an
        :class:`SshError` that includes the captured stderr.
    """
    target = f"{user}@{host}"
    cmd = ["ssh", *ssh_opts, target, command]
    print(f"[ssh] {target}$ {command}", file=sys.stderr)
    return _exec_ssh(cmd)


def _exec_ssh(cmd: list[str], *, interactive: bool = False) -> str:
    """Run an ``ssh`` invocation, streaming output to the terminal.

    When ``interactive`` is True the child inherits the controlling
    terminal (for an interactive login shell) and stdout is not captured.
    """
    completed = subprocess.run(
        cmd,
        capture_output=not interactive,
        text=True,
    )
    if not interactive:
        if completed.stdout:
            sys.stdout.write(completed.stdout)
        if completed.stderr:
            sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        raise SshError(
            f"ssh command failed (exit {completed.returncode}): "
            f"{shlex.join(cmd)}"
        )
    return completed.stdout if not interactive else ""


def _ssh_target_from_state_or_args(
    *, user: str | None, host: str | None
) -> tuple[str, str, tuple[str, ...]]:
    """Resolve ``(user, host, ssh_opts)`` falling back to saved state."""
    saved = state.load_ssh_target()
    if not user or not host:
        if saved is None:
            raise SshError(
                "no SSH target saved yet; run `adutils init` first or "
                "pass --user/--host explicitly"
            )
        user = user or saved["user"]
        host = host or saved["host"]
        ssh_opts = tuple(saved.get("ssh_opts", []))
    else:
        ssh_opts = ()
    return user, host, ssh_opts


def init(
    user: str,
    host: str,
    git_username: str,
    git_email: str,
    *,
    ssh_opts: Sequence[str] = (),
) -> None:
    """Connect to ``user@host`` and bootstrap git across the home directory.

    Steps performed on the remote:

    1. ``git config --global user.name`` / ``user.email``
    2. enumerate first-level directories under ``$HOME``
    3. ``git init`` inside each one (no commit is created)
    """
    if not user or not host:
        raise ValueError("both --user and --host are required")

    # 1. global git identity (optional — skipped if neither is given)
    if git_username or git_email:
        if not git_username or not git_email:
            raise ValueError(
                "--git-username and --git-email must be provided together "
                "(or both omitted to skip the git identity step)"
            )
        _remote_run(
            user,
            host,
            f"git config --global user.name {shlex.quote(git_username)} "
            f"&& git config --global user.email {shlex.quote(git_email)}",
            ssh_opts=ssh_opts,
        )
    # remember the SSH target so other commands (e.g. `adutils ssh`)
    # can reuse it without asking the user again.
    state.save_ssh_target(user=user, host=host, ssh_opts=ssh_opts)

    # List first-level directories once and `git init` inside each.
    # Run as a single remote script so the shell expands `$HOME` itself and
    # so we only need one round-trip to ssh; quoting handles names with
    # spaces via the `git init` builtin.
    script = (
        'for d in "$HOME"/*/; do '
        '[ -d "$d" ] || continue; '
        'echo "=> initialising ${d%/}"; '
        '(cd "$d" && git init) || echo "  ! git init failed in $d"; '
        'done'
    )
    _remote_run(user, host, script, ssh_opts=ssh_opts)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adutils",
        description="Attack/Defense CTF utilities.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p_init = sub.add_parser(
        "init",
        help="Configure global git identity and `git init` every first-level "
        "directory in the remote user's home.",
    )
    p_init.add_argument("-u", "--user", required=True, help="SSH user.")
    p_init.add_argument("-H", "--host", required=True, help="SSH host.")
    p_init.add_argument(
        "--git-username",
        default=None,
        help="git global user.name. If set, --git-email is required too. "
        "Omit both to skip configuring the git identity.",
    )
    p_init.add_argument(
        "--git-email",
        default=None,
        help="git global user.email. If set, --git-username is required too. "
        "Omit both to skip configuring the git identity.",
    )
    p_init.add_argument(
        "-o",
        "--ssh-opt",
        action="append",
        default=[],
        metavar="OPT",
        help="Extra option forwarded to ssh (repeatable), e.g. -o Port=2222. "
        "Note: each value is passed to ssh verbatim as a single argument.",
    )
    p_init.set_defaults(func=_cmd_init)

    p_ssh = sub.add_parser(
        "ssh",
        help="Open an interactive SSH shell to the saved target started by `init`.",
    )
    p_ssh.add_argument(
        "-u", "--user", default=None, help="Override the saved SSH user."
    )
    p_ssh.add_argument(
        "-H", "--host", default=None, help="Override the saved SSH host."
    )
    p_ssh.add_argument(
        "-o",
        "--ssh-opt",
        action="append",
        default=[],
        metavar="OPT",
        help="Extra option forwarded to ssh (repeatable), e.g. -o Port=2222.",
    )
    p_ssh.add_argument(
        "--show",
        action="store_true",
        help="Only print the resulting `ssh` invocation and exit.",
    )
    p_ssh.set_defaults(func=_cmd_ssh)

    return parser


def _cmd_init(args: argparse.Namespace) -> None:
    try:
        init(
            user=args.user,
            host=args.host,
            git_username=args.git_username,
            git_email=args.git_email,
            ssh_opts=tuple(args.ssh_opt),
        )
    except SshError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


def _cmd_ssh(args: argparse.Namespace) -> None:
    try:
        user, host, saved_opts = _ssh_target_from_state_or_args(
            user=args.user, host=args.host
        )
        ssh_opts = (*saved_opts, *args.ssh_opt)
        cmd = ["ssh", *ssh_opts, f"{user}@{host}"]
        if args.show:
            print(shlex.join(cmd))
            return
        _exec_ssh(cmd, interactive=True)
    except SshError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()