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
                
                # Check if API key exists and is not empty
                has_api_key = False
                try:
                    api_key = SettingsService.decrypt_api_key(settings.api_key)
                    has_api_key = bool(api_key and api_key.strip())
                except Exception:
                    has_api_key = False
                
                # Check if model config is complete
                has_model_config = bool(
                    settings.model_provider and 
                    settings.model_provider.strip() and
                    settings.model_name and 
                    settings.model_name.strip()
                )
                
                # Status is "provisioned" if both API key and model config exist
                status = "provisioned" if (has_api_key and has_model_config) else "not_provisioned"
                
                return {
                    "provider": settings.model_provider,
                    "model_name": settings.model_name,
                    "max_tokens": settings.max_tokens,
                    "temperature": settings.temperature,
                    "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
                    "updated_by": settings.updated_by,
                    "status": status,
                    "has_api_key": has_api_key,
                    "has_model_config": has_model_config,
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
    def _clean_api_key(api_key: str) -> str:
        """
        Clean API key by removing whitespace and hidden characters.
        
        Args:
            api_key: Raw API key string
            
        Returns:
            Cleaned API key
        """
        if not api_key:
            return ""
        
        # Remove all types of whitespace (including non-breaking spaces, zero-width spaces, etc.)
        import re
        # First, remove leading/trailing whitespace
        cleaned = api_key.strip()
        # Remove any zero-width characters
        cleaned = re.sub(r'[\u200b-\u200d\ufeff]', '', cleaned)
        # Remove any non-breaking spaces and other unusual spaces
        cleaned = cleaned.replace('\u00a0', ' ').replace('\u2000', ' ').replace('\u2001', ' ')
        cleaned = cleaned.replace('\u2002', ' ').replace('\u2003', ' ').replace('\u2004', ' ')
        cleaned = cleaned.replace('\u2005', ' ').replace('\u2006', ' ').replace('\u2007', ' ')
        cleaned = cleaned.replace('\u2008', ' ').replace('\u2009', ' ').replace('\u200a', ' ')
        # Final strip
        cleaned = cleaned.strip()
        
        return cleaned
    
    @staticmethod
    def validate_api_key(provider: str, model_name: str, api_key: str) -> Dict[str, Any]:
        """
        Validate API key by making a test call to the model API.
        
        Returns:
            Dict with 'valid' (bool) and 'message' (str)
        """
        # Normalize provider to lowercase
        provider = provider.lower().strip() if provider else ""
        
        if not provider:
            return {
                "valid": False,
                "message": "Provider is required"
            }
        
        if not api_key:
            return {
                "valid": False,
                "message": "API key is required"
            }
        
        # Clean the API key to remove any hidden characters or extra whitespace
        api_key = SettingsService._clean_api_key(api_key)
        
        if not api_key:
            return {
                "valid": False,
                "message": "API key is required (key appears to be empty after cleaning)"
            }
        
        # Log first few and last few characters for debugging (without exposing full key)
        key_preview = f"{api_key[:7]}...{api_key[-4:]}" if len(api_key) > 11 else "***"
        logger.info(f"Validating API key for provider '{provider}': {key_preview} (length: {len(api_key)})")
        
        try:
            import httpx
            
            if provider == "openai":
                # Validate OpenAI API key format first
                if not api_key.startswith(("sk-", "sk-proj-")):
                    logger.warning(f"OpenAI API key format may be invalid (doesn't start with 'sk-' or 'sk-proj-'): {key_preview}")
                    # Continue anyway, as format might have changed
                
                # Validate OpenAI API key by calling the models endpoint
                headers = {"Authorization": f"Bearer {api_key}"}
                try:
                    response = httpx.get("https://api.openai.com/v1/models", headers=headers, timeout=10.0)
                    response.raise_for_status()
                    
                    # If we get here, the API key is valid
                    logger.info(f"OpenAI API key validation successful for {key_preview}")
                    return {
                        "valid": True,
                        "message": "API key validation successful"
                    }
                except httpx.HTTPStatusError as e:
                    error_msg = f"OpenAI API returned {e.response.status_code}"
                    error_detail = None
                    try:
                        error_data = e.response.json()
                        if "error" in error_data:
                            error_detail = error_data["error"].get("message", "")
                            error_msg = error_detail
                            # Log the full error for debugging
                            logger.error(f"OpenAI API key validation failed: Status {e.response.status_code}, Error: {error_detail}")
                    except:
                        error_text = e.response.text[:200] if e.response.text else ""
                        error_msg = f"{error_msg}: {error_text}"
                        logger.error(f"OpenAI API key validation failed: {error_msg}")
                    
                    # Provide more helpful error messages
                    if e.response.status_code == 401:
                        if error_detail and "incorrect" in error_detail.lower():
                            return {
                                "valid": False,
                                "message": f"Invalid API key. Please verify your API key is correct and has not been revoked. You can find your API key at https://platform.openai.com/account/api-keys."
                            }
                        else:
                            return {
                                "valid": False,
                                "message": f"Authentication failed. Please check your API key. Status: {e.response.status_code}"
                            }
                    elif e.response.status_code == 429:
                        return {
                            "valid": False,
                            "message": "Rate limit exceeded. Please try again later."
                        }
                    else:
                        return {
                            "valid": False,
                            "message": f"API key validation failed: {error_msg}"
                        }
                except httpx.RequestError as e:
                    logger.error(f"OpenAI API request error: {e}")
                    return {
                        "valid": False,
                        "message": f"Network error connecting to OpenAI API: {str(e)}"
                    }
            
            elif provider == "gemini":
                # Validate Gemini API key by trying to list models
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    # Try to list models (this will fail if key is invalid)
                    list(genai.list_models())
                    return {
                        "valid": True,
                        "message": "API key validation successful"
                    }
                except ImportError:
                    return {
                        "valid": False,
                        "message": "Google Generative AI library not available"
                    }
                except Exception as e:
                    logger.error(f"Gemini API key validation failed: {e}")
                    return {
                        "valid": False,
                        "message": f"API key validation failed: {str(e)}"
                    }
            
            elif provider == "anthropic":
                # Validate Anthropic API key format and make a minimal test call
                if not api_key.startswith("sk-ant-"):
                    return {
                        "valid": False,
                        "message": "Invalid Anthropic API key format (must start with 'sk-ant-')"
                    }
                
                # For Anthropic, we can't easily test without making a completion call
                # So we'll just validate the format for now
                # In production, you might want to make a minimal completion call
                return {
                    "valid": True,
                    "message": "API key format validated (format check only)"
                }
            
            else:
                # For other providers, try using LiteLLM if available
                if not LiteLlm:
                    return {
                        "valid": False,
                        "message": f"Provider '{provider}' not supported for validation"
                    }
                
                try:
                    # Build model string
                    if "/" in model_name:
                        model = model_name
                    else:
                        model = f"{provider}/{model_name}"
                    
                    # Create LiteLLM instance and make a minimal test call
                    lite_llm_kwargs = {
                        "model": model,
                        "api_key": api_key,
                    }
                    
                    test_model = LiteLlm(**lite_llm_kwargs)
                    
                    # Try to make a minimal completion call
                    # This will actually validate the key
                    try:
                        # Make a very small test call
                        response = test_model.complete(
                            prompt="test",
                            max_tokens=1,
                            temperature=0
                        )
                        return {
                            "valid": True,
                            "message": "API key validation successful"
                        }
                    except Exception as e:
                        logger.error(f"LiteLLM test call failed: {e}")
                        return {
                            "valid": False,
                            "message": f"API key validation failed: {str(e)}"
                        }
                except Exception as e:
                    logger.error(f"LiteLLM validation failed: {e}")
                    return {
                        "valid": False,
                        "message": f"API key validation failed: {str(e)}"
                    }
            
        except ImportError:
            logger.error("httpx not available for API key validation")
            return {
                "valid": False,
                "message": "Validation not available (httpx not installed)"
            }
        except Exception as e:
            logger.error(f"Error validating API key: {e}", exc_info=True)
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
            
            # Normalize provider to lowercase for case-insensitive comparison
            provider = provider.lower().strip() if provider else ""
            
            if not provider:
                return {
                    "success": False,
                    "models": [],
                    "message": "Provider is required"
                }
            
            if not api_key:
                return {
                    "success": False,
                    "models": [],
                    "message": "API key is required"
                }
            
            # Clean the API key to remove any hidden characters or extra whitespace
            api_key = SettingsService._clean_api_key(api_key)
            
            if not api_key:
                return {
                    "success": False,
                    "models": [],
                    "message": "API key is required (key appears to be empty after cleaning)"
                }
            
            models = []
            
            if provider == "openai":
                # Use OpenAI API to list models
                headers = {"Authorization": f"Bearer {api_key}"}
                try:
                    response = httpx.get("https://api.openai.com/v1/models", headers=headers, timeout=10.0)
                    response.raise_for_status()  # Raise exception for non-200 status codes
                    
                    data = response.json()
                    # Filter for chat models (gpt-*)
                    models = [
                        model["id"] 
                        for model in data.get("data", [])
                        if model["id"].startswith("gpt-") and "inference" not in model.get("id", "")
                    ]
                    # Remove duplicates and sort
                    models = sorted(list(set(models)))
                    
                    if not models:
                        return {
                            "success": False,
                            "models": [],
                            "message": "No GPT models found in API response"
                        }
                except httpx.HTTPStatusError as e:
                    error_msg = f"OpenAI API returned {e.response.status_code}"
                    try:
                        error_data = e.response.json()
                        if "error" in error_data:
                            error_msg = error_data["error"].get("message", error_msg)
                    except:
                        error_msg = f"{error_msg}: {e.response.text[:200]}"
                    logger.error(f"OpenAI API error: {error_msg}")
                    return {
                        "success": False,
                        "models": [],
                        "message": f"Failed to fetch models from OpenAI: {error_msg}"
                    }
                except httpx.RequestError as e:
                    logger.error(f"OpenAI API request error: {e}")
                    return {
                        "success": False,
                        "models": [],
                        "message": f"Network error connecting to OpenAI API: {str(e)}"
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
                    logger.warning("google.generativeai not available, skipping key validation")
                    pass
                except Exception as e:
                    logger.error(f"Gemini API key validation failed: {e}")
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
                        "message": "Invalid Anthropic API key format (must start with 'sk-ant-')"
                    }
                # Key format is valid, return models
            
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
    def test_saved_configuration() -> Dict[str, Any]:
        """
        Test the saved model configuration using the stored API key.
        
        Returns:
            Dict with 'valid' (bool) and 'message' (str)
        """
        try:
            # Get saved settings
            settings = SettingsService.get_model_settings()
            if not settings:
                return {
                    "valid": False,
                    "message": "No model configuration found. Please configure and save settings first."
                }
            
            # Get saved API key
            api_key = SettingsService.get_api_key()
            if not api_key:
                return {
                    "valid": False,
                    "message": "No API key found in saved configuration. Please update settings with a valid API key."
                }
            
            # Validate using saved configuration
            provider = settings.get("provider")
            model_name = settings.get("model_name")
            
            if not provider or not model_name:
                return {
                    "valid": False,
                    "message": "Incomplete configuration. Please ensure provider and model name are set."
                }
            
            # Test the saved configuration
            result = SettingsService.validate_api_key(
                provider=provider,
                model_name=model_name,
                api_key=api_key
            )
            
            # Enhance message to indicate it's using saved config
            if result["valid"]:
                result["message"] = f"Saved configuration test successful! {provider}/{model_name} is ready to use."
            
            return result
            
        except Exception as e:
            logger.error(f"Error testing saved configuration: {e}", exc_info=True)
            return {
                "valid": False,
                "message": f"Failed to test saved configuration: {str(e)}"
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
                # Clean the API key before encrypting
                cleaned_api_key = SettingsService._clean_api_key(api_key) if api_key else ""
                
                # Encrypt API key
                encrypted_key = SettingsService.encrypt_api_key(cleaned_api_key)
                
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

