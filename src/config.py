from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    # JWT / auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS — which browser origins may call the API (["*"] = any, dev only)
    CORS_ORIGINS: list[str] = ["*"]

    model_config = {"env_file": ".env"}


Config = Settings()
