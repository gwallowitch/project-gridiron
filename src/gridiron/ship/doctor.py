"""Repository health checks."""

from __future__ import annotations

from pathlib import Path


def check_repository(root: Path = Path(".")) -> bool:
    required = [
        root / "data",
        root / "database",
        root / "docs",
        root / "src",
        root / "tests",
    ]

    healthy = True

    print()
    print("Repository Health")
    print("-----------------")

    for path in required:
        exists = path.exists()

        print(
            f"{'✓' if exists else '✗'} {path.name}"
        )

        healthy &= exists

    print()

    return healthy