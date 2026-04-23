"""Unit test auxiliary functions."""

from datetime import datetime

from battinfoconverter_backend.auxiliary import coerce_date_to_iso


def test_date_coercion() -> None:
    """Check that date coercion works as expected."""
    assert coerce_date_to_iso("2026/01/31") == "2026-01-31"
    assert coerce_date_to_iso("2026-01-31") == "2026-01-31"
    assert coerce_date_to_iso("2026.01.31") == "2026-01-31"
    assert coerce_date_to_iso("31/01/2026") == "2026-01-31"
    assert coerce_date_to_iso("31-01-2026") == "2026-01-31"
    assert coerce_date_to_iso("31.01.2026") == "2026-01-31"

    assert coerce_date_to_iso("   2026/01/31    ") == "2026-01-31"

    assert coerce_date_to_iso(datetime.fromisoformat("2026-01-31")) == "2026-01-31"
