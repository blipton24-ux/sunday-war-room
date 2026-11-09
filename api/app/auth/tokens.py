"""The API token handed from Next.js to FastAPI (ADR-017).

After Auth.js signs a user in, the Next.js server mints a short-lived JWT:

    {"sub": "<users.id>", "iss": "swr-web", "aud": "swr-api", "iat": ..., "exp": ...}

signed with HS256 and the shared `API_JWT_SECRET`. FastAPI checks the signature, issuer,
audience and expiry, and takes the user id from `sub`. Nothing else in the token is trusted.
"""

from datetime import UTC, datetime, timedelta

import jwt

from app.config import Settings

ALGORITHM = "HS256"


class InvalidToken(Exception):
    pass


def decode_api_token(token: str, settings: Settings) -> int:
    """Return the user id from a valid token, or raise InvalidToken."""
    try:
        claims = jwt.decode(
            token,
            settings.api_jwt_secret,
            algorithms=[ALGORITHM],  # pinned: never accept "none" or another algorithm
            audience=settings.api_jwt_audience,
            issuer=settings.api_jwt_issuer,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
            leeway=10,
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc
    sub = claims["sub"]
    if not isinstance(sub, str) or not sub.isdigit():
        raise InvalidToken("sub must be a numeric user id")
    return int(sub)


def mint_api_token(user_id: int, settings: Settings, ttl: timedelta = timedelta(minutes=15)) -> str:
    """Create a token. Production tokens come from Next.js; this exists for tests and scripts."""
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iss": settings.api_jwt_issuer,
            "aud": settings.api_jwt_audience,
            "iat": now,
            "exp": now + ttl,
        },
        settings.api_jwt_secret,
        algorithm=ALGORITHM,
    )
