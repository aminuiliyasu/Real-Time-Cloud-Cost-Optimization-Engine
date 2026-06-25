from collections.abc import Iterable

from fastapi import Depends, Header, HTTPException

from app.core.config import settings


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid or missing api key")


def require_roles(allowed_roles: Iterable[str]):
    allowed = {role.lower() for role in allowed_roles}

    def dependency(
        _auth: None = Depends(require_api_key),
        x_role: str | None = Header(default=None, alias="X-Role"),
    ) -> None:
        if not x_role or x_role.lower() not in allowed:
            raise HTTPException(status_code=403, detail="insufficient role")

    return dependency
