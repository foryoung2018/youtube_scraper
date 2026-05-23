import os


OUTPUT_DIR = os.environ.get("YT_OUTPUT_DIR", os.path.join(os.getcwd(), "downloads"))
OUTPUT_TEMPLATE = "%(title)s.%(ext)s"
MAX_DOWNLOADS = int(os.environ.get("YT_MAX_DOWNLOADS", "5"))
TIMEOUT = int(os.environ.get("YT_TIMEOUT", "30"))
