import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "ChefBot-Enterprise API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # JWT Settings
    SECRET_KEY: str = os.environ.get("JWT_SECRET", "chefbot_enterprise_super_secret_jwt_key_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # API Keys
    OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
    TAVILY_API_KEY: str = os.environ.get("TAVILY_API_KEY", "")
    USDA_API_KEY: str = os.environ.get("USDA_API_KEY", "DEMO_KEY")
    OPENROUTER_MODEL: str = os.environ.get("OPENROUTER_MODEL", "openrouter/auto")
    
    # DB & Monitoring Settings
    DB_PATH: str = os.path.join(os.path.dirname(__file__), "..", "..", "chefbot_enterprise.db")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    LANGSMITH_API_KEY: str = os.environ.get("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.environ.get("LANGSMITH_PROJECT", "ChefBot-Enterprise")

settings = Settings()
