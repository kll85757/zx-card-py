from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MySQL
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "rootpwd"
    mysql_db: str = "zxcard"

    # Optional SQLite fallback for local dev
    use_sqlite: bool = True
    sqlite_path: str = "./zxcard.db"

    # Meilisearch
    meili_host: str = "http://127.0.0.1:7700"
    meili_api_key: str = "masterKey"
    meili_index: str = "cards"
    meili_disabled: bool = True  # disable by default for local MVP

    # Celery/Redis
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_disabled: bool = True  # disable by default for local MVP

    # Mini-program (placeholder)
    wechat_appid: str = "wx_your_appid"
    wechat_secret: str = "your_secret"

    class Config:
        env_file = ".env"


settings = Settings()


