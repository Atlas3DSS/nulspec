from __future__ import annotations

from scripts.check_repository_hygiene import (
    PROHIBITED,
    is_pinned_dependency_version,
)


def test_pip_compile_continuation_is_a_pinned_version() -> None:
    ip_shaped_version = "10" + ".3.9.90"
    text = f"nvidia-curand-cu12=={ip_shaped_version} \\\n    --hash=sha256:abc\n"
    match = PROHIBITED["RFC1918 IPv4 address"].search(text)
    assert match is not None
    assert is_pinned_dependency_version(text, match.start(), match.end())


def test_actual_private_address_is_not_a_pinned_version() -> None:
    ip_shaped_address = "10" + ".3.9.90"
    text = f"endpoint={ip_shaped_address}\n"
    match = PROHIBITED["RFC1918 IPv4 address"].search(text)
    assert match is not None
    assert not is_pinned_dependency_version(text, match.start(), match.end())
