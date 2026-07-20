import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

AGENT_API_BASE_URL = os.environ.get("AGENT_API_BASE_URL", "").rstrip("/")
AGENT_API_KEY = os.environ.get("AGENT_API_KEY", "")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "gpt-4o-mini")

NEWS_WRITER_COUNT = int(os.environ.get("NEWS_WRITER_COUNT", "1"))

DB_PATH = BASE_DIR / "db" / "bharatao_agents.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
DRAFTS_DIR = BASE_DIR / "data" / "drafts"
PROMPTS_DIR = BASE_DIR / "prompts"

# Phase 0 site (Astro, replaces the old WordPress plan -- see BHARATAO_MASTER_PLAN.md
# section 4 update). A9 Publisher writes approved drafts directly into the
# site's content collection; no REST API hop needed.
SITE_DIR = BASE_DIR.parent / "site"
SITE_CONTENT_DIR = SITE_DIR / "src" / "content" / "articles"
SITE_IMAGES_DIR = SITE_DIR / "public" / "images"


def require_agent_api() -> None:
    if not AGENT_API_BASE_URL or not AGENT_API_KEY:
        raise RuntimeError(
            "AGENT_API_BASE_URL / AGENT_API_KEY missing. Copy .env.example to .env "
            "and fill them in before running writer agents."
        )
