# ⚖️ Agent 3: The Judge

The final arbiter that synthesizes evidence from both agents and renders a probability-based verdict.

## Workflow Diagram

```mermaid
flowchart TB
    subgraph INPUTS["📥 INPUTS"]
        direction LR
        a1["🔍 Agent 1 Output<br/>(Evidence Dossier)"]
        a2["🕵️ Agent 2 Output<br/>(Forensic Log)"]
    end

    subgraph SYNTHESIZER["🔄 SYNTHESIZER NODE"]
        direction TB
        syn1["Normalize Agent 1 Score"]
        syn2["Normalize Agent 2 Score"]
        syn3["Calculate Confidence Levels"]
        syn1 --> syn2 --> syn3
    end

    subgraph ADJUDICATOR["⚖️ ADJUDICATOR NODE"]
        direction TB
        adj1["Determine Dynamic Weights"]
        adj2["Calculate Final Score"]
        adj3["Check Agent Agreement"]
        adj4["Generate Probability Verdict"]
        adj1 --> adj2 --> adj3 --> adj4
    end

    subgraph REPORTER["📝 REPORTER NODE"]
        direction TB
        rep1["Generate Judicial Reasoning"]
        rep2["Create Claim Hash"]
        rep3["Build AEP Package"]
        rep1 --> rep2 --> rep3
    end

    subgraph OUTPUT["📤 OUTPUT"]
        out["📋 Audit Evidence Package (AEP)"]
        out_details["• verdict (TRUE/FALSE/UNCERTAIN)<br/>• truth_probability (%)<br/>• confidence_level<br/>• reasoning<br/>• methodology<br/>• blockchain_ready"]
        out --> out_details
    end

    INPUTS --> SYNTHESIZER
    SYNTHESIZER --> ADJUDICATOR
    ADJUDICATOR --> REPORTER
    REPORTER --> OUTPUT

    style INPUTS fill:#1e3a5f,stroke:#38bdf8,color:#fff
    style SYNTHESIZER fill:#1e293b,stroke:#22d3ee,color:#fff
    style ADJUDICATOR fill:#1e293b,stroke:#fbbf24,color:#fff
    style REPORTER fill:#1e293b,stroke:#f472b6,color:#fff
    style OUTPUT fill:#065f46,stroke:#10b981,color:#fff
```

## State Schema

```mermaid
classDiagram
    class JudgeState {
        +dict agent1_data
        +dict agent2_data
        +dict normalized_scores
        +dict weights
        +float final_score
        +str verdict
        +str confidence_level
        +str reasoning
        +dict aep_package
    }
```

## Node Details

### 1️⃣ Synthesizer Node (Score Normalization)

```mermaid
flowchart TB
    subgraph SYNTHESIZER["🔄 Score Normalization"]
        subgraph AGENT1_NORM["Agent 1 Normalization"]
            A1V["Verdict: VERIFIED"] --> A1S1["Score: 1.0"]
            A1D["Verdict: DEBUNKED"] --> A1S2["Score: 0.0"]
            A1U["Verdict: UNVERIFIED"] --> A1S3["Score: 0.5"]
        end
        
        subgraph AGENT2_NORM["Agent 2 Normalization"]
            A2I["Integrity Score"] --> A2S["Score: 0.0 - 1.0<br/>(Already normalized)"]
        end
        
        subgraph CONFIDENCE_CALC["Confidence Calculation"]
            C1["Score ≥0.85 or ≤0.15 → HIGH"]
            C2["Score ≥0.70 or ≤0.30 → MEDIUM"]
            C3["Otherwise → LOW"]
        end
        
        AGENT1_NORM --> CONFIDENCE_CALC
        AGENT2_NORM --> CONFIDENCE_CALC
    end
```

### 2️⃣ Adjudicator Node (Trust-Weighted Consensus)

```mermaid
flowchart TB
    subgraph ADJUDICATOR["⚖️ Dynamic Weighting"]
        subgraph WEIGHT_LOGIC["Weight Determination"]
            W1["Definitive Evidence<br/>(s1 ≤0.1 or ≥0.9)<br/>→ Facts: 85%, Forensics: 15%"]
            W2["Strong Evidence<br/>(s1 ≤0.2 or ≥0.8)<br/>→ Facts: 70%, Forensics: 30%"]
            W3["No Evidence<br/>(s1 = 0.5)<br/>→ Facts: 25%, Forensics: 75%"]
            W4["Mixed Signals<br/>(otherwise)<br/>→ Facts: 50%, Forensics: 50%"]
        end
        
        subgraph FORMULA["Score Formula"]
            F["final_score = (s1 × w1) + (s2 × w2)"]
        end
        
        WEIGHT_LOGIC --> FORMULA
    end
```

### 3️⃣ Verdict Determination

```mermaid
flowchart TB
    subgraph VERDICTS["Verdict Logic"]
        SCORE["Final Score"] --> CHECK
        
        subgraph CHECK["Score Thresholds"]
            V1["≥ 0.75 → TRUE<br/>'X% likely to be true'"]
            V2["≤ 0.25 → FALSE<br/>'X% likely to be false'"]
            V3["≥ 0.60 → PROBABLY_TRUE"]
            V4["≤ 0.40 → PROBABLY_FALSE"]
            V5["0.40 - 0.60 → UNCERTAIN"]
        end
        
        subgraph AGREEMENT["Agreement Check"]
            AG1["Agents Agree → Keep Verdict"]
            AG2["Agents Disagree → UNCERTAIN"]
        end
        
        CHECK --> AGREEMENT
    end
```

### 4️⃣ Reporter Node (AEP Generation)

```mermaid
flowchart TB
    subgraph REPORTER["📝 AEP Package"]
        subgraph REASONING["LLM Reasoning"]
            R1["Summarize Evidence"]
            R2["State Probability"]
            R3["Provide Action Item"]
        end
        
        subgraph AEP["Audit Evidence Package"]
            A1["aep_version: 1.0"]
            A2["claim_id: SHA256 hash"]
            A3["timestamp: ISO format"]
            A4["verdict: decision + probability"]
            A5["methodology: weights + rationale"]
            A6["evidence: both agent summaries"]
            A7["blockchain_ready: true"]
        end
        
        REASONING --> AEP
    end
```

## Dynamic Weight System

```mermaid
flowchart LR
    subgraph WEIGHTS["Dynamic Weight Selection"]
        direction TB
        
        subgraph SCENARIO1["Strong Fact Evidence"]
            S1A["Agent 1: VERIFIED/DEBUNKED"]
            S1B["Weight: 85% Facts, 15% Forensics"]
            S1A --> S1B
        end
        
        subgraph SCENARIO2["Moderate Evidence"]
            S2A["Agent 1: Leaning one way"]
            S2B["Weight: 70% Facts, 30% Forensics"]
            S2A --> S2B
        end
        
        subgraph SCENARIO3["No Fact Evidence"]
            S3A["Agent 1: UNVERIFIED"]
            S3B["Weight: 25% Facts, 75% Forensics"]
            S3A --> S3B
        end
        
        subgraph SCENARIO4["Mixed Signals"]
            S4A["Conflicting indicators"]
            S4B["Weight: 50% Facts, 50% Forensics"]
            S4A --> S4B
        end
    end
```

## Confidence Level Matrix

```mermaid
flowchart TB
    subgraph CONFIDENCE["Confidence Calculation"]
        subgraph AGREE["Agents Agree"]
            AG1["Score ≥0.85 or ≤0.15 → VERY HIGH"]
            AG2["Score ≥0.70 or ≤0.30 → HIGH"]
            AG3["Otherwise → MEDIUM"]
        end
        
        subgraph DISAGREE["Agents Disagree"]
            DG1["Score ≥0.60 or ≤0.40 → LOW"]
            DG2["Otherwise → VERY LOW"]
        end
    end
```

## AEP (Audit Evidence Package) Structure

```mermaid
classDiagram
    class AEP {
        +str aep_version
        +str claim_id
        +str timestamp
        +VerdictInfo verdict
        +str reasoning
        +Methodology methodology
        +Evidence evidence
        +bool blockchain_ready
        +str shelby_storage_ref
    }
    
    class VerdictInfo {
        +str decision
        +str verdict_text
        +float truth_probability
        +float confidence_score
        +str confidence_level
    }
    
    class Methodology {
        +dict weights_used
        +str weight_rationale
        +bool agents_in_agreement
    }
    
    class Evidence {
        +Agent1Evidence agent_1_fact_checker
        +Agent2Evidence agent_2_forensic_expert
    }
    
    AEP --> VerdictInfo
    AEP --> Methodology
    AEP --> Evidence
```

## Sample Verdict Output

```
┌─────────────────────────────────────────────────────┐
│  ⚖️ THE JUDGE - Final Verdict                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Verdict: 78% likely FALSE                          │
│  Confidence: HIGH                                   │
│                                                     │
│  Reasoning:                                         │
│  "This claim is 78% likely to be false based on    │
│   contradicting evidence from Reuters and AP.       │
│   Verify with official company statements before    │
│   taking any action."                               │
│                                                     │
│  📋 AEP Generated: claim_abc123...                 │
│  ⛓️ Blockchain Ready: Yes                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```
