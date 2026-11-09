import pytest
from pydantic import ValidationError

from app.config import DEV_JWT_SECRET, Settings


def test_production_refuses_the_dev_secret() -> None:
    with pytest.raises(ValidationError, match="API_JWT_SECRET"):
        Settings(environment="production", api_jwt_secret=DEV_JWT_SECRET)


def test_short_secret_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(api_jwt_secret="too-short")
