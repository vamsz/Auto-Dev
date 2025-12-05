"""
Configuration management for the Self-Healing Agent System.
Load API keys and system parameters from environment variables.

Uses Groq API for fast, free LLM access with LLaMA 3 models.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class."""
    
    # Groq Configuration (Free LLM API)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Available Groq Models (as of 2024):
    # - llama-3.3-70b-versatile (best for coding, 128k context)
    # - llama-3.1-8b-instant (faster, good for simple tasks)
    # - mixtral-8x7b-32768 (good balance)
    # - gemma2-9b-it (Google's model)
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # GitHub Configuration
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    
    # Docker Configuration
    DOCKER_IMAGE: str = os.getenv("DOCKER_IMAGE", "python:3.10-slim")
    DOCKER_TIMEOUT: int = int(os.getenv("DOCKER_TIMEOUT", "60"))
    
    # Agent Configuration
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    WORK_DIR: str = os.getenv("WORK_DIR", "./workspace")
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration. Returns list of missing keys."""
        missing = []
        if not cls.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        if not cls.GITHUB_TOKEN:
            missing.append("GITHUB_TOKEN")
        return missing
    
    @classmethod
    def print_status(cls):
        """Print configuration status (without revealing secrets)."""
        print("=== Configuration Status ===")
        print(f"Groq API Key: {'✓ Set' if cls.GROQ_API_KEY else '✗ Missing'}")
        print(f"Groq Model: {cls.GROQ_MODEL}")
        print(f"GitHub Token: {'✓ Set' if cls.GITHUB_TOKEN else '✗ Missing'}")
        print(f"Docker Image: {cls.DOCKER_IMAGE}")
        print(f"Docker Timeout: {cls.DOCKER_TIMEOUT}s")
        print(f"Max Retry Attempts: {cls.MAX_RETRY_ATTEMPTS}")
        print(f"Work Directory: {cls.WORK_DIR}")
        print("============================")


# Create a singleton instance
config = Config()
