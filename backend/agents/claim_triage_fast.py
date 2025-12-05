"""
Fast Claim Triage - Rule-based (NO LLM calls)

Uses regex patterns and keyword matching instead of LLM.
Reduces triage from 1 LLM call to 0 LLM calls.
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Set


class Domain(Enum):
    """Domain categories for claims."""
    TECH = "tech"
    FINANCE = "finance"
    POLITICS = "politics"
    HEALTH = "health"
    SCIENCE = "science"
    CRYPTO = "crypto"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    GEOPOLITICS = "geopolitics"
    CLIMATE = "climate"
    LEGAL = "legal"
    GENERAL = "general"


class Complexity(Enum):
    """Claim complexity levels."""
    SIMPLE = "simple"      # Single fact, easy to verify
    MEDIUM = "medium"      # Multiple aspects, needs cross-referencing
    COMPLEX = "complex"    # Multi-domain, requires expert analysis


@dataclass
class TriageResult:
    """Result of claim triage."""
    original_claim: str
    normalized_claim: str
    domains: List[Domain]
    complexity: Complexity
    entities: List[str]
    claim_type: str  # factual, opinion, prediction, comparison


# Domain keyword patterns
DOMAIN_PATTERNS = {
    Domain.TECH: [
        r'\b(ai|artificial intelligence|machine learning|ml|deep learning)\b',
        r'\b(google|apple|microsoft|meta|amazon|openai|nvidia|tesla)\b',
        r'\b(iphone|android|software|hardware|chip|gpu|cpu)\b',
        r'\b(startup|tech company|silicon valley|app|platform)\b',
        r'\b(data|algorithm|robot|automation|cloud|saas)\b',
    ],
    Domain.FINANCE: [
        r'\b(stock|market|nasdaq|dow|s&p|nyse|ipo)\b',
        r'\b(billion|million|trillion|revenue|profit|earnings)\b',
        r'\b(bank|goldman|jpmorgan|citi|wells fargo|fed|reserve)\b',
        r'\b(investment|investor|hedge fund|venture capital|vc)\b',
        r'\b(acquisition|merger|buyout|valuation|market cap)\b',
    ],
    Domain.POLITICS: [
        r'\b(president|congress|senate|house|democrat|republican)\b',
        r'\b(biden|trump|obama|election|vote|ballot|poll)\b',
        r'\b(government|legislation|bill|law|policy|regulation)\b',
        r'\b(liberal|conservative|left|right|party)\b',
        r'\b(campaign|candidate|politician|governor|senator)\b',
    ],
    Domain.HEALTH: [
        r'\b(covid|vaccine|virus|pandemic|disease|infection)\b',
        r'\b(doctor|hospital|patient|treatment|medicine|drug)\b',
        r'\b(fda|cdc|who|health|medical|clinical|trial)\b',
        r'\b(cancer|heart|diabetes|mental health|therapy)\b',
        r'\b(pfizer|moderna|johnson|pharmaceutical|pharma)\b',
    ],
    Domain.SCIENCE: [
        r'\b(nasa|space|mars|moon|rocket|satellite|orbit)\b',
        r'\b(research|study|scientist|experiment|discovery)\b',
        r'\b(physics|chemistry|biology|genetics|dna|quantum)\b',
        r'\b(university|professor|journal|peer.?review|paper)\b',
        r'\b(climate|environment|carbon|emissions|renewable)\b',
    ],
    Domain.CRYPTO: [
        r'\b(bitcoin|btc|ethereum|eth|crypto|blockchain)\b',
        r'\b(token|nft|defi|web3|wallet|mining)\b',
        r'\b(binance|coinbase|ftx|kraken|exchange)\b',
        r'\b(altcoin|stablecoin|usdt|usdc|solana|cardano)\b',
    ],
    Domain.SPORTS: [
        r'\b(nba|nfl|mlb|nhl|fifa|olympics|world cup)\b',
        r'\b(player|team|coach|game|match|score|win|lose)\b',
        r'\b(championship|finals|playoffs|season|league)\b',
        r'\b(football|basketball|soccer|baseball|tennis|golf)\b',
    ],
    Domain.ENTERTAINMENT: [
        r'\b(movie|film|actor|actress|hollywood|netflix|disney)\b',
        r'\b(music|album|song|artist|concert|grammy|oscar)\b',
        r'\b(celebrity|star|famous|viral|trending|tiktok)\b',
        r'\b(tv|show|series|streaming|youtube|spotify)\b',
    ],
    Domain.GEOPOLITICS: [
        r'\b(war|military|army|troops|invasion|conflict)\b',
        r'\b(russia|ukraine|china|nato|un|eu|sanctions)\b',
        r'\b(nuclear|missile|defense|security|intelligence)\b',
        r'\b(diplomacy|treaty|alliance|summit|ambassador)\b',
    ],
    Domain.CLIMATE: [
        r'\b(climate change|global warming|greenhouse|carbon)\b',
        r'\b(renewable|solar|wind|electric|ev|battery)\b',
        r'\b(environment|pollution|emissions|fossil fuel)\b',
        r'\b(wildfire|hurricane|flood|drought|extreme weather)\b',
    ],
    Domain.LEGAL: [
        r'\b(court|judge|lawsuit|trial|verdict|sentence)\b',
        r'\b(supreme court|attorney|lawyer|prosecutor|defendant)\b',
        r'\b(sue|appeal|settlement|damages|liability)\b',
        r'\b(criminal|civil|constitutional|rights|justice)\b',
    ],
}

# Entity extraction patterns
ENTITY_PATTERNS = [
    # Organizations/Companies (capitalized words)
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Corp|LLC|Ltd|Co)\.?)?)\b',
    # People names (two+ capitalized words)
    r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
    # Money amounts
    r'\$[\d,]+(?:\.\d+)?(?:\s*(?:billion|million|trillion|B|M|K))?',
    # Percentages
    r'\d+(?:\.\d+)?%',
    # Dates
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    r'\b20\d{2}\b',
]

# Complexity indicators
COMPLEXITY_INDICATORS = {
    'simple': [
        r'^is\s+\w+\s+\w+\??$',  # Simple "Is X Y?" questions
        r'^\w+\s+is\s+',  # Simple "X is" statements
        r'\b(true|false|yes|no)\b',
    ],
    'complex': [
        r'\b(because|therefore|however|although|despite)\b',
        r'\b(compared to|versus|vs\.?|better than|worse than)\b',
        r'\b(caused|resulted|led to|influenced|affected)\b',
        r'\b(multiple|several|various|many|all|every)\b',
        r'\band\b.*\band\b',  # Multiple "and"s indicate complexity
    ]
}

# Claim type patterns
CLAIM_TYPE_PATTERNS = {
    'prediction': [
        r'\b(will|going to|expected to|predicted|forecast)\b',
        r'\b(by 20\d{2}|in the future|soon|next year)\b',
    ],
    'opinion': [
        r'\b(best|worst|greatest|terrible|amazing|horrible)\b',
        r'\b(should|must|need to|ought to)\b',
        r'\b(believe|think|feel|opinion)\b',
    ],
    'comparison': [
        r'\b(more than|less than|bigger|smaller|faster|slower)\b',
        r'\b(compared to|versus|vs\.?|than)\b',
    ],
    'factual': []  # Default
}


class FastClaimTriage:
    """Fast rule-based claim triage (no LLM calls)."""
    
    def triage(self, claim: str) -> TriageResult:
        """
        Analyze claim using regex patterns.
        Zero LLM calls - instant results.
        """
        normalized = claim.lower().strip()
        
        # Detect domains
        domains = self._detect_domains(normalized)
        
        # Extract entities
        entities = self._extract_entities(claim)
        
        # Assess complexity
        complexity = self._assess_complexity(normalized, domains, entities)
        
        # Determine claim type
        claim_type = self._determine_claim_type(normalized)
        
        return TriageResult(
            original_claim=claim,
            normalized_claim=normalized,
            domains=domains if domains else [Domain.GENERAL],
            complexity=complexity,
            entities=entities,
            claim_type=claim_type
        )
    
    def _detect_domains(self, claim: str) -> List[Domain]:
        """Detect domains using keyword patterns."""
        detected: Set[Domain] = set()
        
        for domain, patterns in DOMAIN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, claim, re.IGNORECASE):
                    detected.add(domain)
                    break  # One match per domain is enough
        
        # Sort by relevance (count matches)
        domain_scores = {}
        for domain in detected:
            score = sum(
                1 for p in DOMAIN_PATTERNS[domain] 
                if re.search(p, claim, re.IGNORECASE)
            )
            domain_scores[domain] = score
        
        # Return top 2 domains
        sorted_domains = sorted(domain_scores.keys(), key=lambda d: domain_scores[d], reverse=True)
        return sorted_domains[:2] if sorted_domains else [Domain.GENERAL]
    
    def _extract_entities(self, claim: str) -> List[str]:
        """Extract named entities using regex."""
        entities = set()
        
        for pattern in ENTITY_PATTERNS:
            matches = re.findall(pattern, claim)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if len(match) > 2 and match.lower() not in {'the', 'and', 'for', 'that', 'this'}:
                    entities.add(match.strip())
        
        # Limit to 10 entities
        return list(entities)[:10]
    
    def _assess_complexity(self, claim: str, domains: List[Domain], entities: List[str]) -> Complexity:
        """Assess claim complexity based on patterns."""
        # Check for complex indicators
        complex_score = 0
        for pattern in COMPLEXITY_INDICATORS['complex']:
            if re.search(pattern, claim, re.IGNORECASE):
                complex_score += 1
        
        # Check for simple indicators
        simple_score = 0
        for pattern in COMPLEXITY_INDICATORS['simple']:
            if re.search(pattern, claim, re.IGNORECASE):
                simple_score += 1
        
        # Factor in domains and entities
        if len(domains) > 1:
            complex_score += 1
        if len(entities) > 5:
            complex_score += 1
        if len(claim.split()) > 30:
            complex_score += 1
        if len(claim.split()) < 10:
            simple_score += 1
        
        # Determine complexity
        if complex_score >= 3:
            return Complexity.COMPLEX
        elif simple_score >= 2 and complex_score == 0:
            return Complexity.SIMPLE
        else:
            return Complexity.MEDIUM
    
    def _determine_claim_type(self, claim: str) -> str:
        """Determine the type of claim."""
        for claim_type, patterns in CLAIM_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, claim, re.IGNORECASE):
                    return claim_type
        return 'factual'


# Singleton instance
_triage_instance = None

def get_fast_triage() -> FastClaimTriage:
    """Get singleton triage instance."""
    global _triage_instance
    if _triage_instance is None:
        _triage_instance = FastClaimTriage()
    return _triage_instance
