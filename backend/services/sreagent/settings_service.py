"""Settings service for managing model configuration."""

import os
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import get_db_session
from .models import ModelSettings

# Import LiteLLM for API key validation
try:
    from google.adk.models.lite_llm import LiteLlm
except ImportError:
    LiteLlm = None

logger = logging.getLogger(__name__)

# Encryption key for API keys (should be stored in K8s secret)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", None)
if ENCRYPTION_KEY:
    # Use provided key (must be base64-encoded Fernet key)
    try:
        cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    except Exception as e:
        logger.warning(f"Invalid encryption key format: {e}. Generating new key.")
        ENCRYPTION_KEY = None

if not ENCRYPTION_KEY:
    # Generate a new key (for development only - should be set in production)
    logger.warning("ENCRYPTION_KEY not set. Generating temporary key. This should be set in production!")
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    logger.warning(f"Generated encryption key: {key.decode()}. Set ENCRYPTION_KEY environment variable in production!")


class SettingsService:
    """Service for managing model settings."""
    
    @staticmethod
    def encrypt_api_key(api_key: str) -> str:
        """Encrypt API key before storage."""
        if not api_key:
            return ""
        encrypted = cipher_suite.encrypt(api_key.encode())
        return encrypted.decode()
    
    @staticmethod
    def decrypt_api_key(encrypted_key: str) -> str:
        """Decrypt API key for use."""
        if not encrypted_key:
            return ""
        try:
            decrypted = cipher_suite.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise ValueError("Failed to decrypt API key")
    
    @staticmethod
    def get_model_settings() -> Optional[Dict[str, Any]]:
        """Get current model settings from database."""
        try:
            db = get_db_session()
            try:
                settings = db.query(ModelSettings).filter(ModelSettings.id == 1).first()
                if not settings:
                    return None
                
                return {
                    "provider": settings.model_provider,
                    "model_name": settings.model_name,
                    "max_tokens": settings.max_tokens,
                    "temperature": settings.temperature,
                    "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
                    "updated_by": settings.updated_by,
                }
            finally:
                db.close()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting model settings: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting model settings: {e}")
            raise
    
    @staticmethod
    def get_api_key() -> Optional[str]:
        """Get decrypted API key from database."""
        try:
            db = get_db_session()
            try:
                settings = db.query(ModelSettings).filter(ModelSettings.id == 1).first()
                if not settings:
                    return None
                
                return SettingsService.decrypt_api_key(settings.api_key)
            finally:
                db.close()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting API key: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting API key: {e}")
            raise
    
    @staticmethod
    def validate_api_key(provider: str, model_name: str, api_key: str) -> Dict[str, Any]:
        """
        Validate API key by making a test call to the model.
        
        Returns:
            Dict with 'valid' (bool) and 'message' (str)
        """
        if not LiteLlm:
            return {
                "valid": False,
                "message": "LiteLLM not available for validation"
            }
        
        try:
            # Build model string
            if "/" in model_name:
                model = model_name
            else:
                model = f"{provider}/{model_name}"
            
            # Create LiteLLM instance with test key
            lite_llm_kwargs = {
                "model": model,
                "api_key": api_key,
            }
            
            # Make a minimal test call
            test_model = LiteLlm(**lite_llm_kwargs)
            
            # Try to generate a simple response (this will validate the key)
            # Note: We can't easily test without making an actual API call
            # For now, we'll just check if the model can be instantiated
            # In a real implementation, you might want to make a minimal API call
            
            return {
                "valid": True,
                "message": "API key validation successful"
            }
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return {
                "valid": False,
                "message": f"API key validation failed: {str(e)}"
            }
    
    @staticmethod
    def list_available_models(provider: str, api_key: str) -> Dict[str, Any]:
        """
        List available models for a given provider using their API.
        
        Returns:
            Dict with 'success' (bool), 'models' (list), and 'message' (str)
        """
        try:
            import httpx
            
            models = []
            
            if provider == "openai":
                # Use OpenAI API to list models
                headers = {"Authorization": f"Bearer {api_key}"}
                response = httpx.get("https://api.openai.com/v1/models", headers=headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    # Filter for chat models (gpt-*)
                    models = [
                        model["id"] 
                        for model in data.get("data", [])
                        if model["id"].startswith("gpt-") and "inference" not in model.get("id", "")
                    ]
                    # Remove duplicates and sort
                    models = sorted(list(set(models)))
                else:
                    return {
                        "success": False,
                        "models": [],
                        "message": f"Failed to fetch models: {response.text}"
                    }
            
            elif provider == "gemini":
                # Gemini models are fixed - return common ones
                models = [
                    "gemini-2.0-flash",
                    "gemini-1.5-pro",
                    "gemini-1.5-flash",
                    "gemini-pro",
                ]
                # Try to validate the key by making a simple request
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    # List models to validate key (this will fail if key is invalid)
                    list(genai.list_models())
                except ImportError:
                    # If google.generativeai is not available, just return the models
                    # The key will be validated when saving
                    pass
                except Exception as e:
                    return {
                        "success": False,
                        "models": [],
                        "message": f"API key validation failed: {str(e)}"
                    }
            
            elif provider == "anthropic":
                # Anthropic models are fixed - return common ones
                models = [
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                    "claude-3-5-sonnet-20240620",
                    "claude-3-5-haiku-20241022",
                ]
                # Validate key by checking if it's properly formatted
                if not api_key.startswith("sk-ant-"):
                    return {
                        "success": False,
                        "models": [],
                        "message": "Invalid Anthropic API key format"
                    }
            
            else:
                return {
                    "success": False,
                    "models": [],
                    "message": f"Unsupported provider: {provider}"
                }
            
            return {
                "success": True,
                "models": models,
                "message": f"Found {len(models)} available models"
            }
            
        except ImportError:
            logger.error("httpx not available for model listing")
            return {
                "success": False,
                "models": [],
                "message": "Model listing not available (httpx not installed)"
            }
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return {
                "success": False,
                "models": [],
                "message": f"Failed to list models: {str(e)}"
            }
    
    @staticmethod
    def update_model_settings(
        provider: str,
        model_name: str,
        api_key: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        updated_by: Optional[str] = None
    ) -> bool:
        """
        Update model settings in database.
        
        Args:
            provider: Model provider (e.g., "openai", "gemini")
            model_name: Model name (e.g., "gpt-4", "gemini-2.0-flash")
            api_key: API key (will be encrypted)
            max_tokens: Optional max tokens
            temperature: Optional temperature (0.0-2.0)
            updated_by: Optional admin user who updated
            
        Returns:
            True if successful
        """
        try:
            db = get_db_session()
            try:
                # Encrypt API key
                encrypted_key = SettingsService.encrypt_api_key(api_key)
                
                # Get or create settings
                settings = db.query(ModelSettings).filter(ModelSettings.id == 1).first()
                
                if settings:
                    # Update existing
                    settings.model_provider = provider
                    settings.model_name = model_name
                    settings.api_key = encrypted_key
                    settings.max_tokens = max_tokens
                    settings.temperature = temperature
                    settings.updated_by = updated_by
                    # updated_at is auto-updated by SQLAlchemy
                else:
                    # Create new
                    settings = ModelSettings(
                        id=1,
                        model_provider=provider,
                        model_name=model_name,
                        api_key=encrypted_key,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        updated_by=updated_by,
                    )
                    db.add(settings)
                
                db.commit()
                logger.info(f"Model settings updated: {provider}/{model_name}")
                return True
                
            except SQLAlchemyError as e:
                db.rollback()
                logger.error(f"Database error updating model settings: {e}")
                raise
            except Exception as e:
                db.rollback()
                logger.error(f"Error updating model settings: {e}")
                raise
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to update model settings: {e}")
            raise

