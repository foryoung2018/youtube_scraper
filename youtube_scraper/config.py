import os


OUTPUT_DIR = os.environ.get("YT_OUTPUT_DIR", os.path.join(os.getcwd(), "downloads"))
OUTPUT_TEMPLATE = "%(title)s.%(ext)s"
MAX_DOWNLOADS = int(os.environ.get("YT_MAX_DOWNLOADS", "5"))
TIMEOUT = int(os.environ.get("YT_TIMEOUT", "30"))

DISCOVER_MAX_RESULTS = int(os.environ.get("YT_DISCOVER_RESULTS", "10"))
LLM_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
