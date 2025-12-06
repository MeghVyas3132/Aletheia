"""
Multi-Model LLM Provider - Aletheia

Provides access to multiple LLM providers for:
1. Fallback when primary model is rate-limited
2. Multi-model consensus for critical decisions
3. Cost optimization by routing to cheaper models

Supported providers:
- Groq (llama-3.1-8b-instant) - Primary, fast, free tier
- OpenAI (gpt-4o-mini) - Fallback, paid
- Anthropic (claude-3-haiku) - Fallback, paid
- Together AI (mixtral-8x7b) - Alternative free tier
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    TOGETHER = "together"


@dataclass
class LLMConfig:
    """Configuration for an LLM provider."""
    provider: LLMProvider
    model: str
    api_key: Optional[str]
    temperature: float = 0.3
    max_tokens: int = 2000
    enabled: bool = True
    priority: int = 0  # Lower = higher priority


# Default configurations
DEFAULT_CONFIGS = [
    LLMConfig(
        provider=LLMProvider.GROQ,
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        priority=0,
        enabled=bool(os.getenv("GROQ_API_KEY"))
    ),
    LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        priority=1,
        enabled=bool(os.getenv("OPENAI_API_KEY"))
    ),
    LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-haiku-20240307",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        priority=2,
        enabled=bool(os.getenv("ANTHROPIC_API_KEY"))
    ),
    LLMConfig(
        provider=LLMProvider.TOGETHER,
        model="mistralai/Mixtral-8x7B-Instruct-v0.1",
        api_key=os.getenv("TOGETHER_API_KEY"),
        priority=3,
        enabled=bool(os.getenv("TOGETHER_API_KEY"))
    ),
]


def get_llm(config: LLMConfig):
    """Get an LLM instance for a given config."""
    if config.provider == LLMProvider.GROQ:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    
    elif config.provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    
    elif config.provider == LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    
    elif config.provider == LLMProvider.TOGETHER:
        from langchain_together import ChatTogether
        return ChatTogether(
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    
    raise ValueError(f"Unknown provider: {config.provider}")


class MultiModelProvider:
    """
    Provides access to multiple LLM models with fallback and consensus.
    """
    
    def __init__(self, configs: List[LLMConfig] = None):
        self.configs = configs or [c for c in DEFAULT_CONFIGS if c.enabled]
        self.configs.sort(key=lambda x: x.priority)
        
        if not self.configs:
            raise ValueError("No LLM providers configured. Set at least GROQ_API_KEY.")
        
        # Track rate limits
        self._rate_limited: Dict[LLMProvider, float] = {}
        
        logger.info(f"MultiModelProvider initialized with {len(self.configs)} providers")
    
    def _is_rate_limited(self, provider: LLMProvider) -> bool:
        """Check if a provider is currently rate-limited."""
        import time
        if provider in self._rate_limited:
            if time.time() < self._rate_limited[provider]:
                return True
            del self._rate_limited[provider]
        return False
    
    def _mark_rate_limited(self, provider: LLMProvider, seconds: int = 60):
        """Mark a provider as rate-limited for a duration."""
        import time
        self._rate_limited[provider] = time.time() + seconds
        logger.warning(f"{provider.value} rate-limited for {seconds}s")
    
    async def invoke(self, prompt: str, system_prompt: str = None) -> Tuple[str, LLMProvider]:
        """
        Invoke an LLM with automatic fallback on rate limits.
        
        Returns: (response_text, provider_used)
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        errors = []
        
        for config in self.configs:
            if self._is_rate_limited(config.provider):
                continue
            
            try:
                llm = get_llm(config)
                response = await asyncio.to_thread(llm.invoke, messages)
                return response.content, config.provider
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Rate limit detection
                if "429" in error_str or "rate" in error_str or "quota" in error_str:
                    self._mark_rate_limited(config.provider, 60)
                    logger.warning(f"{config.provider.value} rate limited, trying next...")
                    errors.append(f"{config.provider.value}: Rate limited")
                else:
                    logger.error(f"{config.provider.value} error: {e}")
                    errors.append(f"{config.provider.value}: {str(e)[:100]}")
                
                continue
        
        raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}")
    
    async def invoke_with_consensus(
        self,
        prompt: str,
        system_prompt: str = None,
        min_models: int = 2,
        require_majority: bool = True
    ) -> Tuple[str, float, List[Dict]]:
        """
        Invoke multiple models and return consensus result.
        
        Used for critical decisions where we need 99.99% accuracy.
        
        Returns: (consensus_result, agreement_score, individual_responses)
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        # Get available (non-rate-limited) providers
        available = [c for c in self.configs if not self._is_rate_limited(c.provider)]
        
        if len(available) < min_models:
            # Fall back to single model if not enough available
            result, provider = await self.invoke(prompt, system_prompt)
            return result, 1.0, [{"provider": provider.value, "response": result}]
        
        # Query all available models in parallel
        async def query_model(config: LLMConfig):
            try:
                llm = get_llm(config)
                response = await asyncio.to_thread(llm.invoke, messages)
                return {
                    "provider": config.provider.value,
                    "response": response.content,
                    "success": True
                }
            except Exception as e:
                if "429" in str(e).lower() or "rate" in str(e).lower():
                    self._mark_rate_limited(config.provider, 60)
                return {
                    "provider": config.provider.value,
                    "error": str(e),
                    "success": False
                }
        
        # Run queries in parallel
        tasks = [query_model(c) for c in available[:min_models + 1]]
        results = await asyncio.gather(*tasks)
        
        # Filter successful results
        successful = [r for r in results if r["success"]]
        
        if len(successful) < 1:
            raise RuntimeError("No LLM providers returned successful responses")
        
        if len(successful) == 1:
            return successful[0]["response"], 1.0, results
        
        # Calculate consensus
        responses = [r["response"] for r in successful]
        consensus, agreement = self._calculate_consensus(responses)
        
        return consensus, agreement, results
    
    def _calculate_consensus(self, responses: List[str]) -> Tuple[str, float]:
        """
        Calculate consensus from multiple responses.
        
        For verdict-style responses, looks for TRUE/FALSE/UNCERTAIN.
        Returns the majority verdict and agreement score.
        """
        verdicts = []
        
        for response in responses:
            upper = response.upper()
            if "TRUE" in upper and "FALSE" not in upper:
                verdicts.append("TRUE")
            elif "FALSE" in upper and "TRUE" not in upper:
                verdicts.append("FALSE")
            else:
                verdicts.append("UNCERTAIN")
        
        # Count votes
        from collections import Counter
        counts = Counter(verdicts)
        majority_verdict, majority_count = counts.most_common(1)[0]
        
        agreement = majority_count / len(verdicts)
        
        # Return the full response from the majority position
        for response, verdict in zip(responses, verdicts):
            if verdict == majority_verdict:
                return response, agreement
        
        return responses[0], agreement
    
    def get_available_providers(self) -> List[str]:
        """Get list of available (configured) providers."""
        return [c.provider.value for c in self.configs]
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        import time
        return {
            c.provider.value: {
                "enabled": c.enabled,
                "model": c.model,
                "rate_limited": self._is_rate_limited(c.provider),
                "rate_limit_expires": self._rate_limited.get(c.provider, 0) - time.time()
                    if c.provider in self._rate_limited else None
            }
            for c in self.configs
        }


# Singleton instance
_multi_model_provider: Optional[MultiModelProvider] = None


def get_multi_model_provider() -> MultiModelProvider:
    """Get the singleton multi-model provider."""
    global _multi_model_provider
    if _multi_model_provider is None:
        _multi_model_provider = MultiModelProvider()
    return _multi_model_provider


# Convenience function for simple invocation with fallback
async def invoke_llm(prompt: str, system_prompt: str = None) -> str:
    """Simple LLM invocation with automatic fallback."""
    provider = get_multi_model_provider()
    result, _ = await provider.invoke(prompt, system_prompt)
    return result


# Convenience function for consensus-based invocation
async def invoke_llm_consensus(
    prompt: str,
    system_prompt: str = None,
    min_models: int = 2
) -> Tuple[str, float]:
    """Invoke multiple models for consensus (high accuracy mode)."""
    provider = get_multi_model_provider()
    result, agreement, _ = await provider.invoke_with_consensus(prompt, system_prompt, min_models)
    return result, agreement
