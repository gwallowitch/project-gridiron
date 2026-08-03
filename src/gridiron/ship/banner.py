"""Mission Control banner."""

from __future__ import annotations

import platform

from gridiron.version import (
    __python__,
    __status__,
    __title__,
    __version__,
)


def print_banner() -> None:
    print()

    print("=" * 60)
    print(f"{__title__:^60}")
    print("Professional Football Analytics Platform".center(60))
    print("=" * 60)

    print(f"Version : {__version__}")
    print(f"Status  : {__status__}")
    print(f"Python  : {platform.python_version()}")
    print(f"Target  : {__python__}")

    print("=" * 60)
    print()