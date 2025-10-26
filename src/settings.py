from typing import Optional
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Environment(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class Redis(Environment):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 7777
    REDIS_PASSWORD: Optional[SecretStr] = None


class Bot(Environment):
    TOKEN: SecretStr = SecretStr("8080170871:AAFE0406OtITKrUDElNzfVLJcn_Nasmh0nY")

class Settings(Bot, Redis):
    USER_ID: int = 1247834167


settings = Settings()