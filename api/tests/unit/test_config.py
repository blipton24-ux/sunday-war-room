import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.config import DEV_CREDENTIALS_KEY, DEV_JWT_SECRET, Settings


def test_production_refuses_the_dev_secret() -> None:
    with pytest.raises(ValidationError, match="API_JWT_SECRET"):
        Settings(environment="production", api_jwt_secret=DEV_JWT_SECRET)


def test_short_secret_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(api_jwt_secret="too-short")


REAL_SECRET = "a-real-production-secret-0123456789abcdef"


def test_production_refuses_the_dev_credentials_key() -> None:
    with pytest.raises(ValidationError, match="development key"):
        Settings(environment="production", api_jwt_secret=REAL_SECRET)  # dev key is the default


def test_production_accepts_a_real_credentials_key_even_with_the_old_one_after_it() -> None:
    new = Fernet.generate_key().decode()
    ok = Settings(
        environment="production",
        api_jwt_secret=REAL_SECRET,
        credentials_keys=new,
    )
    assert ok.credentials_key_list == [new]
    with pytest.raises(ValidationError, match="development key"):  # rotation must drop the dev key
        Settings(
            environment="production",
            api_jwt_secret=REAL_SECRET,
            credentials_keys=f"{new},{DEV_CREDENTIALS_KEY}",
        )


def test_an_invalid_credentials_key_is_rejected_at_startup() -> None:
    with pytest.raises(ValidationError, match="invalid Fernet key"):
        Settings(credentials_keys="not-a-key")
    with pytest.raises(ValidationError, match="at least one"):
        Settings(credentials_keys=" , ")


def test_credentials_keys_are_split_on_commas() -> None:
    a, b = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    assert Settings(credentials_keys=f" {a} , {b} ").credentials_key_list == [a, b]
