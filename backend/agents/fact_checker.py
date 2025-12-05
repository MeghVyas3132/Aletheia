"""
Agent 1: The Fact Checker - MoveH (OPTIMIZED)

Verifies claims by searching authoritative sources and analyzing evidence.
- Strategist: Generates search queries
- Executor: Fetches search results (ASYNC PARALLEL)
- Analyst: Evaluates evidence sufficiency

Optimizations:
- Async parallel Tavily searches
- Redis-like in-memory caching
- Optimized search parameters
- Concurrent query execution
"""

import os
import asyncio
import hashlib
from typing import TypedDict, Literal
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.3,
)

# In-memory cache for search results
_search_cache: dict[str, dict] = {}


def _cache_key(query: str) -> str:
    """Generate cache key for a query."""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()


class FactCheckerState(TypedDict):
    """State for the Fact Checker agent."""
    claim: str
    search_queries: list[str]
    search_results: list[dict]
    analysis: str
    is_sufficient: bool
    iteration_count: int
    evidence_dossier: dict


def strategist_node(state: FactCheckerState) -> FactCheckerState:
    """Generate targeted search queries to verify the claim."""
    claim = state["claim"]
    iteration = state.get("iteration_count", 0)
    previous_results = state.get("search_results", [])
    
    if iteration == 0:
        prompt = f"""You are a fact-checking strategist for news verification.
        
Given this claim to verify:
"{claim}"

Generate exactly 3 specific search queries to find authoritative sources that can verify or debunk this claim.
Focus on:
1. Official sources (government sites, company press releases, regulatory bodies)
2. Major news outlets (Bloomberg, Reuters, AP, BBC)
3. Cross-referencing with historical data or related news

Return ONLY the 3 queries, one per line, no numbering or bullets."""
    else:
        results_summary = "\n".join([
            f"- Query: {r.get('query', 'N/A')}, Found: {len(r.get('results', []))} results"
            for r in previous_results
        ])
        
        prompt = f"""You are a fact-checking strategist. Previous search attempts were insufficient.

Original claim: "{claim}"

Previous search results summary:
{results_summary}

The evidence was vague or insufficient. Generate 3 NEW, more specific search queries.
Return ONLY the 3 queries, one per line, no numbering or bullets."""

    response = llm.invoke([
        SystemMessage(content="You are an expert fact-checking strategist."),
        HumanMessage(content=prompt)
    ])
    
    queries = [q.strip() for q in response.content.strip().split("\n") if q.strip()][:3]
    
    return {
        **state,
        "search_queries": queries,
        "iteration_count": iteration + 1
    }


def executor_node(state: FactCheckerState) -> FactCheckerState:
    """Fetch search results for each query using ASYNC PARALLEL execution."""
    queries = state["search_queries"]
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    if tavily_api_key:
        try:
            results = asyncio.run(_parallel_tavily_search(queries, tavily_api_key))
        except Exception:
            results = _simulate_search(queries)
    else:
        results = _simulate_search(queries)
    
    return {**state, "search_results": results}


async def _parallel_tavily_search(queries: list[str], api_key: str) -> list[dict]:
    """Execute multiple Tavily searches in parallel for maximum speed."""
    from tavily import AsyncTavilyClient
    
    client = AsyncTavilyClient(api_key=api_key)
    
    # Check cache first, identify queries that need fetching
    cached_results = {}
    queries_to_fetch = []
    
    for query in queries:
        cache_key = _cache_key(query)
        if cache_key in _search_cache:
            cached_results[query] = _search_cache[cache_key]
        else:
            queries_to_fetch.append(query)
    
    # Parallel fetch for uncached queries
    if queries_to_fetch:
        async def search_single(query: str) -> dict:
            try:
                search_response = await client.search(
                    query=query,
                    search_depth="basic",  # Faster than "advanced"
                    max_results=4,  # Optimized: fewer results, faster response
                    include_raw_content=False,  # Faster without raw content
                    topic="general"
                )
                
                formatted_results = []
                for r in search_response.get("results", []):
                    formatted_results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", "")[:1000],
                        "score": r.get("score", 0),
                        "published_date": r.get("published_date", "")
                    })
                
                result = {
                    "query": query,
                    "results": formatted_results,
                    "status": "success",
                    "answer": search_response.get("answer", "")
                }
                
                # Cache the result
                _search_cache[_cache_key(query)] = result
                return result
                
            except Exception as e:
                return {"query": query, "results": [], "status": f"error: {str(e)}"}
        
        # Execute all searches in parallel
        fetched = await asyncio.gather(
            *(search_single(q) for q in queries_to_fetch),
            return_exceptions=True
        )
        
        # Process fetched results
        for i, result in enumerate(fetched):
            if isinstance(result, Exception):
                cached_results[queries_to_fetch[i]] = {
                    "query": queries_to_fetch[i],
                    "results": [],
                    "status": f"error: {str(result)}"
                }
            else:
                cached_results[queries_to_fetch[i]] = result
    
    # Return results in original query order
    return [cached_results[q] for q in queries]


def _simulate_search(queries: list[str]) -> list[dict]:
    """Simulate search results using LLM when Tavily is not available."""
    results = []
    for query in queries:
        prompt = f"""Simulate a web search for: "{query}"

Provide 3 simulated search results with:
1. A realistic headline/title
2. A plausible URL
3. A content snippet (2-3 sentences)

Format each result clearly."""

        response = llm.invoke([
            SystemMessage(content="You are simulating realistic web search results."),
            HumanMessage(content=prompt)
        ])
        
        results.append({
            "query": query,
            "results": [{
                "title": f"Simulated: {query[:50]}",
                "url": "https://simulated-search.example.com",
                "content": response.content,
                "score": 0.85,
                "simulated": True
            }],
            "status": "simulated",
            "answer": response.content[:500]
        })
    return results


def analyst_node(state: FactCheckerState) -> FactCheckerState:
    """Evaluate search results and determine if evidence is sufficient."""
    claim = state["claim"]
    search_results = state["search_results"]
    
    results_text = ""
    for r in search_results:
        results_text += f"\n\nQuery: {r['query']}\n"
        for result in r.get("results", []):
            if isinstance(result, dict):
                results_text += f"- {result.get('title', 'N/A')}: {result.get('content', '')[:500]}\n"
            else:
                results_text += f"- {str(result)[:500]}\n"
    
    prompt = f"""You are a fact-checking analyst.

CLAIM TO VERIFY:
"{claim}"

SEARCH RESULTS:
{results_text}

Analyze and provide:
1. EVIDENCE QUALITY: SUFFICIENT or INSUFFICIENT
2. ANALYSIS: Brief analysis
3. PRELIMINARY VERDICT: VERIFIED, DEBUNKED, or UNVERIFIED

Format:
EVIDENCE_QUALITY: [SUFFICIENT/INSUFFICIENT]
ANALYSIS: [Your analysis]
VERDICT: [VERIFIED/DEBUNKED/UNVERIFIED]"""

    response = llm.invoke([
        SystemMessage(content="You are an expert fact-checking analyst."),
        HumanMessage(content=prompt)
    ])
    
    analysis_text = response.content
    is_sufficient = "EVIDENCE_QUALITY: SUFFICIENT" in analysis_text.upper()
    
    verdict = "UNVERIFIED"
    if "VERDICT: VERIFIED" in analysis_text.upper():
        verdict = "VERIFIED"
    elif "VERDICT: DEBUNKED" in analysis_text.upper():
        verdict = "DEBUNKED"
    
    evidence_dossier = {
        "original_claim": claim,
        "search_queries_used": state["search_queries"],
        "search_results": search_results,
        "analysis": analysis_text,
        "preliminary_verdict": verdict,
        "iterations": state["iteration_count"],
        "evidence_sufficient": is_sufficient
    }
    
    return {
        **state,
        "analysis": analysis_text,
        "is_sufficient": is_sufficient,
        "evidence_dossier": evidence_dossier
    }


def should_continue(state: FactCheckerState) -> Literal["refine", "output"]:
    """Determine if we should refine queries or output."""
    if state["iteration_count"] >= 2:  # Max 2 iterations for speed
        return "output"
    if state["is_sufficient"]:
        return "output"
    return "refine"


def build_fact_checker_graph():
    """Build and compile the Fact Checker LangGraph."""
    workflow = StateGraph(FactCheckerState)
    
    workflow.add_node("strategist", strategist_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("analyst", analyst_node)
    
    workflow.set_entry_point("strategist")
    workflow.add_edge("strategist", "executor")
    workflow.add_edge("executor", "analyst")
    workflow.add_conditional_edges("analyst", should_continue, {"refine": "strategist", "output": END})
    
    return workflow.compile()


class FactChecker:
    """Agent 1: The Fact Checker - Verifies claims via web search (OPTIMIZED)."""
    
    def __init__(self):
        self.graph = build_fact_checker_graph()
    
    async def astream_verify(self, claim: str):
        """Verify a claim asynchronously and yield state updates."""
        initial_state: FactCheckerState = {
            "claim": claim,
            "search_queries": [],
            "search_results": [],
            "analysis": "",
            "is_sufficient": False,
            "iteration_count": 0,
            "evidence_dossier": {}
        }
        async for event in self.graph.astream(initial_state):
            yield event
    
    @staticmethod
    def clear_cache():
        """Clear the search results cache."""
        global _search_cache
        _search_cache = {}
