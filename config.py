import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
CHANNEL_NAME = os.getenv("CHANNEL_NAME")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Proxy settings
USE_PROXY = os.getenv("USE_PROXY", "true").lower() == "true"
PROXY_AUTO_UPDATE = os.getenv("PROXY_AUTO_UPDATE", "true").lower() == "true"
PROXY_TEST = os.getenv("PROXY_TEST", "false").lower() == "true"  # Test proxies before using

# Manual proxy (format: host:port:secret)
MANUAL_PROXY = os.getenv("MANUAL_PROXY", "")

if not API_ID:
    raise ValueError("API_ID not found in environment variables")
if not API_HASH:
    raise ValueError("API_HASH not found in environment variables")
if not CHANNEL_NAME:
    raise ValueError("CHANNEL_NAME not found in environment variables")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")
