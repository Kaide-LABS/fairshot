"""
LLM provider configuration for Virtual FDE.
Initializes OpenAI (primary) and Gemini (cross-validation).
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

load_dotenv()


def get_openai_client() -> OpenAI:
    """Returns a configured OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def get_gemini_client() -> genai.Client:
    """Returns a configured Gemini client."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)


def get_openai_model() -> str:
    """Returns the configured OpenAI model name."""
    return os.getenv("OPENAI_MODEL", "gpt-4o")


def get_gemini_model() -> str:
    """Returns the Gemini model string."""
    return os.getenv("GEMINI_MODEL", "gemini-2.5-pro")


def validate_api_keys() -> dict[str, bool]:
    """Check which API keys are configured. Returns a dict of provider -> is_configured."""
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
    }
