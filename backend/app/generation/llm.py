import os
import re
import time
from abc import ABC, abstractmethod
from typing import Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger

class BaseLLMClient(ABC):
    """
    Abstract interface for LLM providers.
    """
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        """
        Generate completion from system and user prompt.
        """
        pass


class GroqLLMClient(BaseLLMClient):
    """
    Cloud LLM Client using Groq API Key.
    Supports models hosted on Groq (openai/gpt-oss-20b, llama-3.1-8b-instant, qwen-2.5-32b, etc.)
    """
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or getattr(settings, "LLM_API_KEY", None)
        self.model_name = model_name or getattr(settings, "LLM_MODEL", "openai/gpt-oss-20b")
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key or "gsk_dummy_key")
        except ImportError:
            raise ImportError("The 'groq' package is required. Install via `pip install groq`.")

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        logger.info(f"Invoking Groq Cloud LLM API [{self.model_name}]...")
        start_t = time.perf_counter()
        try:
            current_key = self.api_key or os.environ.get("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or getattr(settings, "LLM_API_KEY", None)
            if not current_key or current_key in ["your_groq_api_key_here", "your_hf_token_here", "your_api_key_here", "dummy", "mock", "none"]:
                logger.warning("No valid GROQ_API_KEY / LLM_API_KEY found. Utilizing MockOfflineLLMClient fallback.")
                mock_client = MockOfflineLLMClient()
                return mock_client.generate(system_prompt, user_prompt, temperature)

            if current_key != self.api_key:
                self.api_key = current_key
                from groq import Groq
                self.client = Groq(api_key=current_key)

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature if temperature > 0.0 else getattr(settings, "LLM_TEMPERATURE", 0.0)
            )
            raw_text = response.choices[0].message.content or ""
            cleaned_text = re.sub(r"<thought>.*?</thought>", "", raw_text, flags=re.DOTALL).strip()
            
            latency = round((time.perf_counter() - start_t) * 1000, 2)
            logger.info(f"Groq API generation completed in {latency}ms.")
            return cleaned_text
        except Exception as e:
            logger.warning(f"Groq LLM API invocation failed ({e}). Falling back to MockOfflineLLMClient.")
            mock_client = MockOfflineLLMClient()
            return mock_client.generate(system_prompt, user_prompt, temperature)


class GPTOSSClient(GroqLLMClient):
    """
    Convenience alias for Groq-hosted openai/gpt-oss-20b model using Groq API key.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(api_key=api_key, model_name=model_name or getattr(settings, "LLM_MODEL", "openai/gpt-oss-20b"))


class OpenAILLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini", base_url: Optional[str] = None):
        try:
            from openai import OpenAI
            client_kwargs = {"api_key": api_key}
            url = base_url or getattr(settings, "LLM_BASE_URL", None)
            if url:
                client_kwargs["base_url"] = url
            self.client = OpenAI(**client_kwargs)
            self.model_name = model_name
        except ImportError:
            raise ImportError("The 'openai' package is required. Install via `pip install openai`.")

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        logger.info(f"Invoking Cloud LLM API model [{self.model_name}]...")
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content


class GeminiLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.model_name = model_name
        except ImportError:
            raise ImportError("The 'google-genai' package is required. Install via `pip install google-genai`.")

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        logger.info(f"Invoking Google Gemini LLM model [{self.model_name}]...")
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config={"temperature": temperature}
            )
            return response.text
        except Exception as e:
            logger.warning(f"Gemini API call failed ({e}). Falling back to MockOfflineLLMClient.")
            mock_client = MockOfflineLLMClient()
            return mock_client.generate(system_prompt, user_prompt, temperature)


class MockOfflineLLMClient(BaseLLMClient):
    """
    Offline fallback LLM client used during automated pytest or keyless development.
    Extracts facts directly from context chunks in prompt and constructs a grounded response with [Source X].
    """
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        logger.info("Invoking Offline Mock LLM Client (Keyless / Pytest mode)...")
        
        # Check if context is present
        if "<UNTRUSTED_CONTEXT_CHUNKS>" not in user_prompt or "</UNTRUSTED_CONTEXT_CHUNKS>" not in user_prompt:
            return (
                "Hello! I am the Knowvia AI Technical Documentation & Policy Intelligence Assistant. "
                "I am designed to help you search, analyze, and understand technical documentation, security policies, "
                "disaster recovery targets (RPO/RTO), API specifications, and cloud infrastructure guidelines."
            )

        context_part = user_prompt.split("<UNTRUSTED_CONTEXT_CHUNKS>")[1].split("</UNTRUSTED_CONTEXT_CHUNKS>")[0].strip()
        if not context_part:
            return "I am unable to answer based on the provided context."

        # Extract available source blocks [Source 1], [Source 2]...
        sources = re.findall(r"\[Source (\d+)\]", context_part)
        if not sources:
            return "I am unable to answer based on the provided context."

        # Return synthesized response referencing available sources
        cited_sources = " ".join([f"[Source {s}]" for s in sorted(set(sources))])
        return f"Based on the provided documentation, here is the relevant policy/technical information: {context_part[:250]}... {cited_sources}"


# Singleton instance
_llm_client_instance = None

def get_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> BaseLLMClient:
    """
    Factory function instantiating configured LLM Provider as a persistent singleton.
    Supported providers: groq, gpt_oss, openai, gemini, mock.
    """
    global _llm_client_instance
    if _llm_client_instance is not None and provider is None:
        return _llm_client_instance

    prov = (provider or settings.LLM_PROVIDER).lower()
    key = api_key or os.environ.get("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or settings.LLM_API_KEY
    model = model_name or settings.LLM_MODEL

    try:
        if prov in ["groq", "gpt_oss", "gptoss", "local"]:
            logger.info(f"Initializing GroqLLMClient for model [{model}]")
            _llm_client_instance = GroqLLMClient(api_key=key, model_name=model)
            return _llm_client_instance
        elif prov == "openai":
            if not key or key in ["your_api_key_here", "dummy", "mock", "none"]:
                _llm_client_instance = MockOfflineLLMClient()
                return _llm_client_instance
            _llm_client_instance = OpenAILLMClient(api_key=key, model_name=model)
            return _llm_client_instance
        elif prov == "gemini":
            if not key or key in ["your_api_key_here", "dummy", "mock", "none"]:
                _llm_client_instance = MockOfflineLLMClient()
                return _llm_client_instance
            _llm_client_instance = GeminiLLMClient(api_key=key, model_name=model)
            return _llm_client_instance
        else:
            logger.warning(f"Unknown LLM provider '{prov}'. Falling back to MockOfflineLLMClient.")
            _llm_client_instance = MockOfflineLLMClient()
            return _llm_client_instance
    except Exception as e:
        logger.warning(f"Failed to initialize '{prov}' LLM client ({e}). Falling back to MockOfflineLLMClient.")
        _llm_client_instance = MockOfflineLLMClient()
        return _llm_client_instance
