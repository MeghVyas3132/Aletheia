"""
LLM Provider Wrapper for Aletheia Agents

Provides a unified interface for LLM access with:
1. Multi-provider fallback (Groq → OpenAI → Anthropic)
2. Rate limit handling with automatic retry
3. Model consensus for critical decisions
4. Configurable behavior per agent

Usage:
    from agents.llm_provider import get_llm, invoke_with_fallback
    
    # Simple usage (uses fast model with fallback)
    llm = get_llm("fast")
    response = llm.invoke(messages)
    
    # With explicit fallback handling
    response = await invoke_with_fallback(messages)
    
    # For critical decisions (consensus across models)
    response = await get_consensus_response(messages)
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tiers for different use cases."""
    FAST = "fast"           # Quick responses, lower cost
    BALANCED = "balanced"   # Good quality, reasonable speed
    ACCURATE = "accurate"   # Best quality, slower


# Model configurations by tier and provider
MODEL_CONFIG = {
    ModelTier.FAST: {
        "groq": {"model": "llama-3.1-8b-instant", "temperature": 0.3},
        "openai": {"model": "gpt-4o-mini", "temperature": 0.3},
        "anthropic": {"model": "claude-3-haiku-20240307", "temperature": 0.3},
    },
    ModelTier.BALANCED: {
        "groq": {"model": "llama-3.3-70b-versatile", "temperature": 0.3},
        "openai": {"model": "gpt-4o-mini", "temperature": 0.3},
        "anthropic": {"model": "claude-3-5-sonnet-20241022", "temperature": 0.3},
    },
    ModelTier.ACCURATE: {
        "groq": {"model": "llama-3.3-70b-versatile", "temperature": 0.1},
        "openai": {"model": "gpt-4o", "temperature": 0.1},
        "anthropic": {"model": "claude-3-5-sonnet-20241022", "temperature": 0.1},
    },
}

# Provider priority order
PROVIDER_ORDER = ["groq", "openai", "anthropic"]


def _get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider."""
    key_map = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    return os.getenv(key_map.get(provider, ""))


def _create_llm(provider: str, config: Dict[str, Any]):
    """Create an LLM instance for a provider."""
    api_key = _get_api_key(provider)
    if not api_key:
        return None
    
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=config["model"],
            api_key=api_key,
            temperature=config.get("temperature", 0.3),
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config["model"],
            api_key=api_key,
            temperature=config.get("temperature", 0.3),
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config["model"],
            api_key=api_key,
            temperature=config.get("temperature", 0.3),
        )
    
    return None


def get_llm(tier: Union[str, ModelTier] = "balanced", provider: Optional[str] = None):
    """
    Get an LLM instance for the specified tier.
    
    Args:
        tier: Model tier ("fast", "balanced", "accurate") or ModelTier enum
        provider: Optional specific provider to use
    
    Returns:
        LLM instance (defaults to Groq)
    """
    if isinstance(tier, str):
        tier = ModelTier(tier.lower())
    
    tier_config = MODEL_CONFIG.get(tier, MODEL_CONFIG[ModelTier.BALANCED])
    
    # If specific provider requested
    if provider:
        config = tier_config.get(provider)
        if config:
            llm = _create_llm(provider, config)
            if llm:
                return llm
    
    # Try providers in order
    for prov in PROVIDER_ORDER:
        if prov in tier_config:
            llm = _create_llm(prov, tier_config[prov])
            if llm:
                return llm
    
    # Fallback: return Groq with default settings
    logger.warning("No LLM providers available, using Groq default")
    from langchain_groq import ChatGroq
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY", ""),
        temperature=0.3,
    )


async def invoke_with_fallback(
    messages: List[BaseMessage],
    tier: Union[str, ModelTier] = "balanced",
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> str:
    """
    Invoke LLM with automatic fallback to other providers on failure.
    
    Args:
        messages: List of LangChain messages
        tier: Model tier to use
        max_retries: Max retries per provider
        retry_delay: Delay between retries (seconds)
    
    Returns:
        Response content string
    """
    if isinstance(tier, str):
        tier = ModelTier(tier.lower())
    
    tier_config = MODEL_CONFIG.get(tier, MODEL_CONFIG[ModelTier.BALANCED])
    errors = []
    
    for provider in PROVIDER_ORDER:
        if provider not in tier_config:
            continue
        
        config = tier_config[provider]
        llm = _create_llm(provider, config)
        
        if not llm:
            continue
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(llm.invoke, messages)
                return response.content
                
            except Exception as e:
                error_msg = str(e)
                errors.append(f"{provider}:{error_msg[:50]}")
                
                # Check for rate limit
                if "429" in error_msg or "rate" in error_msg.lower():
                    logger.warning(f"{provider} rate limited, waiting...")
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.warning(f"{provider} failed: {error_msg[:100]}")
                    break  # Don't retry for non-rate-limit errors
    
    raise Exception(f"All LLM providers failed: {'; '.join(errors)}")


async def get_consensus_response(
    messages: List[BaseMessage],
    tier: Union[str, ModelTier] = "accurate",
    min_providers: int = 2
) -> Dict[str, Any]:
    """
    Get responses from multiple providers and return consensus.
    
    For critical decisions where 99.99% accuracy is needed.
    
    Args:
        messages: List of LangChain messages
        tier: Model tier to use
        min_providers: Minimum providers needed for consensus
    
    Returns:
        Dict with consensus response and individual responses
    """
    if isinstance(tier, str):
        tier = ModelTier(tier.lower())
    
    tier_config = MODEL_CONFIG.get(tier, MODEL_CONFIG[ModelTier.ACCURATE])
    
    async def get_response(provider: str) -> Optional[Dict[str, str]]:
        config = tier_config.get(provider)
        if not config:
            return None
        
        llm = _create_llm(provider, config)
        if not llm:
            return None
        
        try:
            response = await asyncio.to_thread(llm.invoke, messages)
            return {"provider": provider, "response": response.content}
        except Exception as e:
            logger.warning(f"Consensus: {provider} failed: {e}")
            return None
    
    # Get responses in parallel
    tasks = [get_response(p) for p in PROVIDER_ORDER if p in tier_config]
    results = await asyncio.gather(*tasks)
    
    # Filter successful responses
    responses = [r for r in results if r is not None]
    
    if len(responses) < min_providers:
        raise Exception(f"Not enough providers responded ({len(responses)} < {min_providers})")
    
    # Simple consensus: return first response (in production, would analyze for agreement)
    # For true consensus, we'd parse structured responses and check agreement
    return {
        "consensus": responses[0]["response"],
        "provider_count": len(responses),
        "responses": responses,
        "unanimous": len(set(r["response"][:100] for r in responses)) == 1
    }


# Convenience: Create default LLM instances for backward compatibility
def get_fast_llm():
    """Get a fast LLM for quick operations."""
    return get_llm(ModelTier.FAST)


def get_balanced_llm():
    """Get a balanced LLM for typical operations."""
    return get_llm(ModelTier.BALANCED)


def get_accurate_llm():
    """Get the most accurate LLM for critical decisions."""
    return get_llm(ModelTier.ACCURATE)


# Module-level default LLM (for backward compatibility)
default_llm = get_llm(ModelTier.BALANCED)
