Karva documentation pilot
=========================

Run ``uv run --group=dev python -m karva_docs`` from the repository root to check the existing Sybil examples with Karva.
The command generates temporary native test modules and removes them after the run.
It shares the parser configuration exported by ``conftest.py``.

The existing pytest suite remains required, including its coverage and runtime type checks.
The Karva command currently validates documentation examples only.
Each example has a separate result, and examples within a document run in source order with a shared namespace.

The adapter is tracked in `sybil-extras issue 1294 <https://github.com/adamtheturtle/sybil-extras/issues/1294>`__.
Replace the temporary Git dependency with a released version when available.
Native source-location reporting and a Sybil runner entry point are tracked in `Karva issue 1513 <https://github.com/MatthewMckee4/karva/issues/1513>`__ and `Sybil issue 173 <https://github.com/simplistix/sybil/issues/173>`__.
