

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL:          str
    REDIS_URL:             str
    SENTINEL_CLIENT_ID:    str
    SENTINEL_CLIENT_SECRET:str
    FIRMS_API_KEY:         str = ""
    OWM_API_KEY:           str = ""
    HF_API_TOKEN:          str = ""

    class Config:
        env_file = ".env"

settings = Settings()