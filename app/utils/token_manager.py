from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core import settings


class JWTTokenManager:
    def __init__(self):
        self._config = settings.auth

    def create_access_token(self, data: dict) -> str:
        return self._create_token(data, self._config.ACCESS_TOKEN_EXPIRE_HOURS)

    def create_refresh_token(self, data: dict) -> str:
        return self._create_token(data, self._config.REFRESH_TOKEN_EXPIRE_DAYS * 24)

    def create_infinite_access_token(self, data: dict) -> str:
        return self._create_token(data)

    def _create_token(self, data: dict, expire_hours: int | None = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(hours=expire_hours)
        if expire_hours:
            to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self._config.SECRET_KEY, algorithm=self._config.ALGORITHM)

    def decode_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(
                token, self._config.SECRET_KEY, algorithms=[self._config.ALGORITHM], options={"require": ["sub"]}
            )
        except JWTError:
            return None


jwt_token_manager = JWTTokenManager()
