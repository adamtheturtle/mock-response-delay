"""Run this project's Sybil documentation examples through Karva."""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from sybil_extras.integrations.karva import generate_karva_tests


def main() -> int:
    """Generate temporary tests and keep pytest validation alongside
    them.
    """
    with TemporaryDirectory(
        dir=Path.cwd(), prefix="karva_sybil_"
    ) as directory:
        generated = generate_karva_tests(
            reference="conftest:sybil",
            paths=[
                Path("README.rst"),
                Path("docs/source"),
                Path("src"),
                Path("tests"),
            ],
            destination=Path(directory),
        )
        if len(generated) == 0:
            message = "No documentation examples were collected"
            raise ValueError(message)
        result = subprocess.run(  # noqa: S603
            args=[sys.executable, "-m", "karva", "test", directory],
            check=False,
        )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
