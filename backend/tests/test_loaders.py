"""Unit tests for parsing helpers in ocorrencias.loaders."""

from __future__ import annotations

import datetime as dt

import pytest

from ocorrencias.loaders import reconcile_ocorrencia_date


@pytest.mark.parametrize(
    "ano,mes,raw_data,expected",
    [
        # Year/month/day all agree → use the date as-is.
        (2023, 3, "10/03/2023", dt.date(2023, 3, 10)),
        # CSV `data` has a typo year (1924 → meant 2024) but month matches
        # mes → trust ano+mes for year, pull day from the typo'd date.
        (2024, 3, "26/03/1924", dt.date(2024, 3, 26)),
        # CSV `data` month conflicts with mes → fall back to day=1.
        (2021, 6, "20/05/1978", dt.date(2021, 6, 1)),
        # CSV `data` empty → day=1.
        (2022, 11, "", dt.date(2022, 11, 1)),
        (2022, 11, None, dt.date(2022, 11, 1)),
        # Unparseable junk in `data` → day=1.
        (2022, 11, "not-a-date", dt.date(2022, 11, 1)),
        # CSV `data` day=31 in a 30-day month → fall back to day=1.
        (2023, 4, "31/04/2023", dt.date(2023, 4, 1)),
    ],
)
def test_reconcile_happy_paths(ano, mes, raw_data, expected):
    assert reconcile_ocorrencia_date(ano, mes, raw_data) == expected


@pytest.mark.parametrize(
    "ano,mes",
    [
        (None, 5),       # missing ano
        (2023, None),    # missing mes
        (1999, 5),       # before YEAR_MIN (2000)
        (2023, 0),       # month out of range
        (2023, 13),      # month out of range
    ],
)
def test_reconcile_returns_none_for_bad_anomes(ano, mes):
    assert reconcile_ocorrencia_date(ano, mes, "10/05/2023") is None
