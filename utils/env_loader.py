# /home/vincent/ixome/utils/env_loader.py
# Secure .env loader for IXome.ai, fits existing code (e.g., import in app.py, agents, scrapers for keys like OPENAI_API_KEY, SNAPONE_PASSWORD).
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

def load_env():
    """Load .env file and log loaded keys (without values for security)."""
    load_dotenv(dotenv_path='/home/vincent/ixome/.env')
    required_keys = [
        'OPENAI_API_KEY',
        'XAI_API_KEY',
        'PINECONE_API_KEY',
        'GOOGLE_API_KEY',
        'YOUTUBE_API_KEY',
        'LANGCHAIN_API_KEY',
        'STRIPE_API_KEY',
        'WEB3_PROVIDER',
        'COMPANY_SOLANA_WALLET',
        'LUTRON_USERNAME',
        'LUTRON_PASSWORD',
        'SNAPONE_USERNAME',
        'SNAPONE_PASSWORD',
        'EMAIL_USER',
        'EMAIL_PASS'
    ]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        logger.error(f"Missing .env keys: {missing_keys}")
        raise ValueError(f"Missing .env keys: {missing_keys}")
    logger.info("Loaded .env keys: " + ', '.join(required_keys))
    return True

if __name__ == "__main__":
    load_env()  # Test load