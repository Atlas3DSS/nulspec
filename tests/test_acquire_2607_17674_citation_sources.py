from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "acquire_2607_17674_citation_sources.py"
SPEC = importlib.util.spec_from_file_location("citation_acquisition", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ACQUISITION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ACQUISITION)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("https://arxiv.org/abs/1312.6114", "https://arxiv.org/pdf/1312.6114"),
        ("https://aclanthology.org/P19-1602/", "https://aclanthology.org/P19-1602.pdf"),
        (
            "https://openreview.net/forum?id=nZeVKeeFYf9",
            "https://openreview.net/pdf?id=nZeVKeeFYf9",
        ),
        (
            "https://proceedings.mlr.press/v119/koh20a.html",
            "https://proceedings.mlr.press/v119/koh20a/koh20a.pdf",
        ),
    ],
)
def test_direct_pdf_candidates(source: str, expected: str) -> None:
    assert expected in ACQUISITION.direct_pdf_candidates(source)


def test_pdf_discovery_resolves_relative_and_meta_links() -> None:
    html = b"""
    <html><head>
      <meta name="citation_pdf_url" content="/paper/source.pdf">
    </head><body><a href="https://example.org/second.pdf">PDF</a></body></html>
    """
    assert ACQUISITION.discover_pdf_candidates(
        html, "https://example.org/paper/index.html"
    ) == [
        "https://example.org/paper/source.pdf",
        "https://example.org/second.pdf",
    ]


def test_relative_https_redirect_is_resolved_before_validation() -> None:
    assert ACQUISITION.validated_redirect_url(
        "https://doi.org/10.1214/example", "/journals/example.pdf"
    ) == "https://doi.org/journals/example.pdf"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/paper.pdf",
        "https://localhost/paper.pdf",
        "https://127.0.0.1/paper.pdf",
        "file:///tmp/paper.pdf",
    ],
)
def test_nonpublic_or_non_https_sources_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        ACQUISITION.safe_https_url(url)
