"""cohub CLI entrypoint."""
from __future__ import annotations

import io
import sys

# Windows may default stdio to GBK/cp936. Force UTF-8 for stable text IO.
def _force_utf8_stdio() -> None:
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # py3.7+
        except Exception:
            # Fallback: wrap with TextIOWrapper.
            try:
                buffer = getattr(stream, "buffer", None)
                if buffer is not None:
                    setattr(sys, stream_name, io.TextIOWrapper(buffer, encoding="utf-8", errors="replace"))
            except Exception:
                pass


_force_utf8_stdio()

import click  # noqa: E402

from .commands import (
    init as cmd_init,
    start as cmd_start,
    status as cmd_status,
    handoff as cmd_handoff,
    review as cmd_review,
    snap as cmd_snap,
    rewind as cmd_rewind,
    skill as cmd_skill,
)


@click.group(help="cohub - local workflow coordination for multiple CLI agents.")
@click.version_option(package_name="cohub")
def cli() -> None:
    """Root command group."""


cli.add_command(cmd_init.init)
cli.add_command(cmd_start.start)
cli.add_command(cmd_status.status)
cli.add_command(cmd_handoff.handoff)
cli.add_command(cmd_review.review)
cli.add_command(cmd_snap.snap)
cli.add_command(cmd_rewind.rewind)
cli.add_command(cmd_skill.skill)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
