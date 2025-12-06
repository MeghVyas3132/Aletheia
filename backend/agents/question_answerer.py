"""
Question Answerer Agent

For inputs detected as QUESTIONS (not claims), this agent:
1. Researches the topic
2. Provides a direct, factual answer
3. Cites sources
4. Handles contentious topics with nuance

Example:
- Input: "Who owns the Kaveri river?"
- Output: Detailed answer with legal/historical context, not TRUE/FALSE
"""

import os
import logging
from dataclasses import dataclass
from typing import List, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


@dataclass
class AnswerResult:
    """Result of answering a question."""
    question: str
    answer: str
    summary: str  # Short 1-2 sentence summary
    nuance: Optional[str]  # For contentious topics
    sources: List[dict]
    confidence: float
    is_contentious: bool  # Flag for disputed topics


# Topics that require nuanced handling
CONTENTIOUS_KEYWORDS = [
    'river dispute', 'kaveri', 'cauvery', 'border dispute', 'kashmir',
    'palestine', 'israel', 'taiwan', 'china', 'ukraine', 'russia',
    'abortion', 'religion', 'caste', 'reservation', 'controversy',
    'tamilians', 'kannadigas', 'karnataka', 'tamil nadu',
]


class QuestionAnswerer:
    """
    Agent that answers questions directly instead of TRUE/FALSE verification.
    """
    
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.3,  # Lower temp for factual answers
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        # Answer prompt for general questions
        self.answer_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research assistant. Your job is to provide accurate, well-researched answers to questions.

GUIDELINES:
1. Give a DIRECT ANSWER first (don't hedge or be vague)
2. Provide context and explanation
3. Cite your sources if relevant
4. For disputed topics, present multiple perspectives fairly
5. Be factual, not opinionated
6. If the question involves regional/political disputes, explain ALL sides

FORMAT YOUR RESPONSE AS:
**ANSWER:** [Direct answer in 1-2 sentences]

**EXPLANATION:** [Detailed context, 2-3 paragraphs]

**SOURCES:** [List key sources or authorities]

**NUANCE:** [If applicable, additional perspectives or caveats]"""),
            ("human", """Question: {question}

Research context (if any):
{context}

Provide a comprehensive, balanced answer.""")
        ])
        
        # Prompt for contentious topics
        self.contentious_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a neutral expert mediator. The question involves a CONTENTIOUS or DISPUTED topic.

Your job is to:
1. Acknowledge the dispute/controversy
2. Present BOTH/ALL sides fairly
3. Cite legal, historical, or authoritative sources
4. Do NOT take sides
5. Explain why the topic is disputed

FORMAT:
**THE DISPUTE:** [Explain what's being disputed and why]

**PERSPECTIVE 1:** [First viewpoint with supporting evidence]

**PERSPECTIVE 2:** [Second viewpoint with supporting evidence]

**AUTHORITATIVE VIEW:** [What courts, laws, or international bodies say]

**CURRENT STATUS:** [Current legal/political situation]"""),
            ("human", """Contentious Question: {question}

Research context:
{context}

Provide a balanced, multi-perspective answer.""")
        ])
    
    def _is_contentious(self, question: str) -> bool:
        """Check if question involves a contentious topic."""
        q_lower = question.lower()
        return any(kw in q_lower for kw in CONTENTIOUS_KEYWORDS)
    
    async def answer(
        self, 
        question: str, 
        search_results: List[dict] = None
    ) -> AnswerResult:
        """
        Answer a question with research-backed response.
        """
        search_results = search_results or []
        is_contentious = self._is_contentious(question)
        
        # Build context from search results
        context = ""
        if search_results:
            for i, result in enumerate(search_results[:5], 1):
                title = result.get("title", "")
                snippet = result.get("snippet", result.get("content", ""))[:300]
                context += f"{i}. {title}: {snippet}\n"
        else:
            context = "No specific research context provided. Use your knowledge."
        
        # Choose appropriate prompt
        prompt = self.contentious_prompt if is_contentious else self.answer_prompt
        
        # Generate answer
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            response = await chain.ainvoke({
                "question": question,
                "context": context
            })
            
            # Parse response
            answer, summary, nuance = self._parse_response(response, is_contentious)
            
            return AnswerResult(
                question=question,
                answer=answer,
                summary=summary,
                nuance=nuance,
                sources=[{"title": r.get("title", ""), "url": r.get("link", "")} 
                        for r in search_results[:5]],
                confidence=0.7 if is_contentious else 0.85,
                is_contentious=is_contentious
            )
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return AnswerResult(
                question=question,
                answer=f"I encountered an error while researching this question: {str(e)}",
                summary="Error occurred",
                nuance=None,
                sources=[],
                confidence=0.0,
                is_contentious=is_contentious
            )
    
    def _parse_response(self, response: str, is_contentious: bool) -> tuple:
        """Parse the LLM response into structured parts."""
        answer = response
        summary = ""
        nuance = None
        
        # Extract answer section
        if "**ANSWER:**" in response:
            parts = response.split("**ANSWER:**")
            if len(parts) > 1:
                answer_part = parts[1].split("**")[0].strip()
                summary = answer_part[:200]
        elif "**THE DISPUTE:**" in response:
            parts = response.split("**THE DISPUTE:**")
            if len(parts) > 1:
                dispute_part = parts[1].split("**")[0].strip()
                summary = f"This is a disputed topic: {dispute_part[:150]}"
        
        # Extract nuance
        if "**NUANCE:**" in response:
            parts = response.split("**NUANCE:**")
            if len(parts) > 1:
                nuance = parts[1].split("**")[0].strip()
        
        if not summary:
            # Fallback: first 200 chars
            summary = response[:200].replace("\n", " ").strip()
        
        return answer, summary, nuance


# Singleton instance
_question_answerer = None

def get_question_answerer() -> QuestionAnswerer:
    """Get singleton QuestionAnswerer instance."""
    global _question_answerer
    if _question_answerer is None:
        _question_answerer = QuestionAnswerer()
    return _question_answerer
