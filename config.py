"""
Configuration management for Autonomous Research Agent.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load local.settings.json if it exists
settings_path = Path("local.settings.json")
if settings_path.exists():
    with open(settings_path) as f:
        local_settings = json.load(f)
        if "env" in local_settings:
            for key, value in local_settings["env"].items():
                os.environ[key] = value

# Load environment variables from .env
load_dotenv()

# Kimi API (support both KIMI_ and ANTHROPIC_ prefixes)
KIMI_API_KEY = (
    os.getenv("KIMI_API_KEY")
    or os.getenv("MOONSHOT_API_KEY")
    or os.getenv("ANTHROPIC_AUTH_TOKEN", "")
)
KIMI_API_URL = os.getenv("KIMI_API_URL") or os.getenv("ANTHROPIC_BASE_URL", "https://openrouter.ai/api/v1")
KIMI_MODEL = os.getenv("KIMI_MODEL") or os.getenv("ANTHROPIC_MODEL", "deepseek/deepseek-v4-pro")

# Firecrawl API
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")

# Server
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Research Defaults
DEFAULT_DEPTH = int(os.getenv("DEFAULT_DEPTH", "3"))
DEFAULT_VERIFY = os.getenv("DEFAULT_VERIFY", "True").lower() == "true"
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "15"))
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "200000"))

# Paths
DATABASE_PATH = os.getenv("DATABASE_PATH", "logs/research.db")
LOG_PATH = os.getenv("LOG_PATH", "logs/research.jsonl")
REPORT_PATH = os.getenv("REPORT_PATH", "reports/")

# Create directories
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
Path(REPORT_PATH).mkdir(parents=True, exist_ok=True)


class Config:
    """Configuration object for dependency injection."""

    kimi_api_key = KIMI_API_KEY
    kimi_api_url = KIMI_API_URL
    kimi_model = KIMI_MODEL
    firecrawl_api_key = FIRECRAWL_API_KEY
    server_host = SERVER_HOST
    server_port = SERVER_PORT
    debug = DEBUG
    default_depth = DEFAULT_DEPTH
    default_verify = DEFAULT_VERIFY
    max_iterations = MAX_ITERATIONS
    token_budget = TOKEN_BUDGET
    database_path = DATABASE_PATH
    log_path = LOG_PATH
    report_path = REPORT_PATH

    @classmethod
    def validate(cls):
        """Validate configuration."""
        if not cls.kimi_api_key:
            print("Warning: KIMI_API_KEY or MOONSHOT_API_KEY not set. LLM calls will use fallback behavior.")
        return True


# Validate on import
Config.validate()
