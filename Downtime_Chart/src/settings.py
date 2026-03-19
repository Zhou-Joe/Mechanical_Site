import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables"""
    
    # Splunk Configuration
    SPLUNK_HOST = os.getenv("SPLUNK_HOST")
    SPLUNK_TOKEN = os.getenv("SPLUNK_TOKEN")
    SPLUNK_USERNAME = os.getenv("SPLUNK_USERNAME")
    SPLUNK_PASSWORD = os.getenv("SPLUNK_PASSWORD")
    SPLUNK_VERIFY_TLS = os.getenv("SPLUNK_VERIFY_TLS", "False").lower() == "true"
    
    # Security settings for Splunk queries
    INDEX_WHITELIST = os.getenv("INDEX_WHITELIST", "main,summary").split(",")
    ALLOWED_CMDS = os.getenv("ALLOWED_CMDS", "").split(",") if os.getenv("ALLOWED_CMDS") else []
    FORBIDDEN_CMDS = os.getenv("FORBIDDEN_CMDS", "delete,eval,inputlookup,outputlookup,tail").split(",")

# Create a singleton instance
settings = Settings()