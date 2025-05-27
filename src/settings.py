from typing import Optional
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Environment(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class Redis(Environment):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[SecretStr] = None


class Bot(Environment):
    TOKEN: SecretStr = SecretStr("7952648091:AAHek5j-EREIfUiin6hHAZS59chG92jPED8")

class Settings(Bot, Redis):
    USER_ID: int = 1247834167


settings = Settings()