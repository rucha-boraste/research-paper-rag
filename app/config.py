from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    UNSTRUCTURED_API_KEY: str
    HUGGINGFACEHUB_API_TOKEN: str
    PGVECTOR_CONNECTION: str
    GROQ_API_KEY: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    
    model_config = SettingsConfigDict(
        env_file = ".env",
        extra="ignore"
    )

Config = Settings()
# print(f"{Config.DATABASE_URL}")