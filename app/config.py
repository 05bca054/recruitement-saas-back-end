"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "recruitment_saas"
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 7
    
    # Application
    app_name: str = "Recruitment SaaS Platform"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # File Upload
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10
    
    # AI & Integrations
    openai_api_key: str = ""
    telegram_bot_token: str = ""
    
    # Billing
    input_token_cost_per_million: float = 1.00
    output_token_cost_per_million: float = 2.50
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
