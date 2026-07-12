from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # "dev" | "prod" — gates interactive docs and can switch log verbosity.
    ENVIRONMENT: str = "dev"

    DATABASE_URL: str

    # JWT / auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS — which browser origins may call the API (["*"] = any, dev only)
    CORS_ORIGINS: list[str] = ["*"]

    # MongoDB — the NoSQL store for the activity log (polyglot persistence)
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB: str = "bookstore"

    # Kafka — event bus in front of the activity log (see src/kafka.py)
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    model_config = {"env_file": ".env"}


Config = Settings()
