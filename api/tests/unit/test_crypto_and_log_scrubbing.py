"""Credential encryption and log scrubbing (P3 step 4, ADR-052)."""

from __future__ import annotations

import json
from typing import Any

import pytest
import structlog
from cryptography.fernet import Fernet

from app.crypto import CredentialCipher, CredentialError, get_cipher
from app.logging import REDACTED, scrub_secrets

COOKIES = '{"espn_s2": "AEB%2Fsecretvalue", "swid": "{ABC-123}"}'


def key() -> str:
    return Fernet.generate_key().decode()


def test_round_trip_and_the_stored_value_is_not_the_cookie() -> None:
    cipher = CredentialCipher([key()])
    token = cipher.encrypt(COOKIES)
    assert "secretvalue" not in token and "ABC-123" not in token
    assert cipher.decrypt(token) == COOKIES


def test_the_same_value_encrypts_differently_each_time() -> None:
    cipher = CredentialCipher([key()])
    assert cipher.encrypt(COOKIES) != cipher.encrypt(COOKIES)  # random IV; no pattern leaks


def test_a_different_key_cannot_read_it() -> None:
    token = CredentialCipher([key()]).encrypt(COOKIES)
    with pytest.raises(CredentialError):
        CredentialCipher([key()]).decrypt(token)


def test_tampering_is_detected_not_decrypted_to_garbage() -> None:
    cipher = CredentialCipher([key()])
    token = cipher.encrypt(COOKIES)
    flipped = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(CredentialError):
        cipher.decrypt(flipped)


def test_rotation_moves_data_to_the_newest_key_and_old_keys_can_then_be_dropped() -> None:
    old, new = key(), key()
    token = CredentialCipher([old]).encrypt(COOKIES)
    both = CredentialCipher([new, old])  # new first: it encrypts; old still reads
    assert both.decrypt(token) == COOKIES
    rotated = both.rotate(token)
    assert rotated != token
    assert CredentialCipher([new]).decrypt(rotated) == COOKIES  # old key no longer needed
    with pytest.raises(CredentialError):
        CredentialCipher([old]).decrypt(rotated)
    with pytest.raises(CredentialError):
        both.rotate("garbage")


def test_a_cipher_needs_a_key() -> None:
    with pytest.raises(ValueError, match="at least one"):
        CredentialCipher([])


def test_the_default_cipher_uses_the_configured_keys() -> None:
    assert get_cipher().decrypt(get_cipher().encrypt("x")) == "x"


# --------------------------------------------------------------------------- log scrubbing
def run(**fields: object) -> dict[str, Any]:
    return dict(scrub_secrets(None, "info", dict(fields)))


def test_secret_fields_are_blanked_by_name() -> None:
    out = run(event="connect", espn_s2="AEBsecret", SWID="{ABC}", cookie="a=b", user_id=7)
    assert out["espn_s2"] == out["SWID"] == out["cookie"] == REDACTED
    assert out["user_id"] == 7 and out["event"] == "connect"


def test_secrets_inside_nested_values_and_text_are_blanked() -> None:
    out = run(
        event="request failed: espn_s2=AEBsecret; SWID={ABC}",
        headers={"Cookie": "espn_s2=AEBsecret", "accept": "json"},
        items=[{"authorization": "Bearer x"}, "SWID: {ABC}"],
    )
    text = json.dumps(out)
    assert "AEBsecret" not in text and "{ABC}" not in text and "Bearer x" not in text
    assert out["headers"]["accept"] == "json"


def test_the_configured_logger_scrubs_real_log_lines(capsys: pytest.CaptureFixture[str]) -> None:
    from app.logging import configure_logging, get_logger

    structlog.reset_defaults()
    configure_logging("INFO", json=True)
    get_logger("test").info("espn_connect", espn_s2="AEBsecret", note="swid={ABC}")
    printed = capsys.readouterr().out
    assert "AEBsecret" not in printed and "{ABC}" not in printed
    assert REDACTED in printed
