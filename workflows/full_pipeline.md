# 🛡️ MoveH - Full Pipeline

Complete system architecture showing how all three agents work together.

## High-Level Architecture

```mermaid
flowchart TB
    subgraph INPUT["📥 USER INPUT"]
        claim["🎯 Claim/News to Verify"]
    end

    subgraph PARALLEL["⚡ PARALLEL EXECUTION"]
        direction LR
        subgraph AGENT1["🔍 Agent 1: Fact Checker"]
            A1S["Strategist"]
            A1E["Executor"]
            A1A["Analyst"]
            A1S --> A1E --> A1A
        end
        
        subgraph AGENT2["🕵️ Agent 2: Forensic Expert"]
            A2P["Profiler"]
            A2D["Detector"]
            A2U["Auditor"]
            A2P --> A2D --> A2U
        end
    end

    subgraph JUDGE["⚖️ Agent 3: The Judge"]
        J1["Synthesizer"]
        J2["Adjudicator"]
        J3["Reporter"]
        J1 --> J2 --> J3
    end

    subgraph OUTPUTS["📤 OUTPUTS"]
        direction TB
        PDF["📄 PDF Report"]
        SHELBY["☁️ Shelby Storage"]
        APTOS["⛓️ Aptos Blockchain"]
    end

    INPUT --> PARALLEL
    AGENT1 --> JUDGE
    AGENT2 --> JUDGE
    JUDGE --> OUTPUTS

    style INPUT fill:#1e3a5f,stroke:#38bdf8,color:#fff
    style PARALLEL fill:#0f172a,stroke:#22d3ee,color:#fff
    style AGENT1 fill:#1e293b,stroke:#22d3ee,color:#fff
    style AGENT2 fill:#1e293b,stroke:#f472b6,color:#fff
    style JUDGE fill:#1e293b,stroke:#fbbf24,color:#fff
    style OUTPUTS fill:#065f46,stroke:#10b981,color:#fff
```

## Detailed Data Flow

```mermaid
flowchart TB
    subgraph ENTRY["📥 Entry Point"]
        CLI["main.py CLI"]
        API["Future: REST API"]
    end

    subgraph CLAIM_PROCESSING["🎯 Claim Processing"]
        CP1["Extract claim text"]
        CP2["Initialize ThreadPoolExecutor"]
    end

    subgraph AGENT1_DETAIL["🔍 Fact Checker (Thread 1)"]
        direction TB
        A1_START["Start"] --> A1_STRAT["Strategist<br/>Generate 3 queries"]
        A1_STRAT --> A1_EXEC["Executor<br/>Async parallel Tavily"]
        A1_EXEC --> A1_ANAL["Analyst<br/>Evaluate evidence"]
        A1_ANAL --> A1_CHECK{"Sufficient?"}
        A1_CHECK -->|No, iter < 2| A1_STRAT
        A1_CHECK -->|Yes or iter ≥ 2| A1_OUT["Evidence Dossier"]
    end

    subgraph AGENT2_DETAIL["🕵️ Forensic Expert (Thread 2)"]
        direction TB
        A2_START["Start"] --> A2_PROF["Profiler<br/>Linguistic analysis"]
        A2_PROF --> A2_DET["Detector<br/>AI/manipulation scan"]
        A2_DET --> A2_AUD["Auditor<br/>Penalty calculation"]
        A2_AUD --> A2_OUT["Forensic Log"]
    end

    subgraph MERGE["🔀 Results Merge"]
        WAIT["ThreadPoolExecutor.wait()"]
    end

    subgraph JUDGE_DETAIL["⚖️ The Judge"]
        direction TB
        J_START["Start"] --> J_SYN["Synthesizer<br/>Normalize scores"]
        J_SYN --> J_ADJ["Adjudicator<br/>Trust-weighted consensus"]
        J_ADJ --> J_REP["Reporter<br/>Generate AEP"]
        J_REP --> J_OUT["Final Verdict + AEP"]
    end

    subgraph OUTPUT_DETAIL["📤 Output Generation"]
        direction TB
        OUT_PDF["ReportLab PDF<br/>Professional report"]
        OUT_SHELBY["Shelby Upload<br/>Decentralized storage"]
        OUT_APTOS["Aptos Smart Contract<br/>On-chain verdict"]
        OUT_CLI["Rich Terminal<br/>User display"]
    end

    ENTRY --> CLAIM_PROCESSING
    CLAIM_PROCESSING --> AGENT1_DETAIL
    CLAIM_PROCESSING --> AGENT2_DETAIL
    AGENT1_DETAIL --> MERGE
    AGENT2_DETAIL --> MERGE
    MERGE --> JUDGE_DETAIL
    JUDGE_DETAIL --> OUTPUT_DETAIL
```

## State Transitions

```mermaid
stateDiagram-v2
    [*] --> ClaimReceived: User submits claim
    
    ClaimReceived --> ParallelExecution: Initialize threads
    
    state ParallelExecution {
        [*] --> FactChecker
        [*] --> ForensicExpert
        
        state FactChecker {
            [*] --> Strategist
            Strategist --> Executor
            Executor --> Analyst
            Analyst --> Strategist: Refine (max 2)
            Analyst --> [*]: Done
        }
        
        state ForensicExpert {
            [*] --> Profiler
            Profiler --> Detector
            Detector --> Auditor
            Auditor --> [*]: Done
        }
    }
    
    ParallelExecution --> Judge: Both complete
    
    state Judge {
        [*] --> Synthesizer
        Synthesizer --> Adjudicator
        Adjudicator --> Reporter
        Reporter --> [*]
    }
    
    Judge --> OutputGeneration
    
    state OutputGeneration {
        [*] --> GeneratePDF
        GeneratePDF --> UploadShelby
        UploadShelby --> DisplayResult
        DisplayResult --> [*]
    }
    
    OutputGeneration --> [*]
```

## Parallel Execution Architecture

```mermaid
flowchart TB
    subgraph MAIN["Main Thread"]
        M1["Submit Claim"]
        M2["Create ThreadPoolExecutor"]
        M3["Submit Agent 1 Task"]
        M4["Submit Agent 2 Task"]
        M5["Wait for Both"]
        M6["Pass to Judge"]
        M1 --> M2 --> M3 --> M4 --> M5 --> M6
    end

    subgraph THREAD1["Thread 1: Fact Checker"]
        T1A["Run LangGraph"]
        T1B["Async Tavily Search"]
        T1C["Return Dossier"]
        T1A --> T1B --> T1C
    end

    subgraph THREAD2["Thread 2: Forensic Expert"]
        T2A["Run LangGraph"]
        T2B["LLM Analysis"]
        T2C["Return Log"]
        T2A --> T2B --> T2C
    end

    M3 -.->|"executor.submit()"| THREAD1
    M4 -.->|"executor.submit()"| THREAD2
    T1C -.->|"future.result()"| M5
    T2C -.->|"future.result()"| M5
```

## Technology Stack Map

```mermaid
flowchart TB
    subgraph FRONTEND["🖥️ User Interface"]
        RICH["Rich Terminal UI"]
        PDF["ReportLab PDF"]
    end

    subgraph AI_LAYER["🤖 AI Layer"]
        LANGGRAPH["LangGraph Orchestration"]
        GEMINI["Gemini 2.5 Flash"]
        TAVILY["Tavily Search API"]
    end

    subgraph STORAGE_LAYER["💾 Storage Layer"]
        SHELBY["Shelby Protocol<br/>(Decentralized)"]
        LOCAL["Local Reports/"]
    end

    subgraph BLOCKCHAIN_LAYER["⛓️ Blockchain Layer"]
        APTOS["Aptos Network"]
        MOVE["Move Smart Contract"]
    end

    FRONTEND --> AI_LAYER
    AI_LAYER --> STORAGE_LAYER
    AI_LAYER --> BLOCKCHAIN_LAYER
```

## Performance Timeline

```mermaid
gantt
    title MoveH Execution Timeline (Optimized)
    dateFormat ss
    axisFormat %S

    section Agent 1
    Strategist (LLM)     :a1s, 00, 2s
    Executor (Tavily)    :a1e, after a1s, 3s
    Analyst (LLM)        :a1a, after a1e, 2s

    section Agent 2
    Profiler (LLM)       :a2p, 00, 2s
    Detector (LLM)       :a2d, after a2p, 2s
    Auditor (calc)       :a2u, after a2d, 1s

    section Judge
    Synthesizer          :js, after a1a a2u, 1s
    Adjudicator         :ja, after js, 1s
    Reporter (LLM)      :jr, after ja, 2s

    section Output
    PDF Generation      :op, after jr, 1s
    Shelby Upload       :os, after op, 2s
```

## Use Case Flow Examples

### Financial News Verification
```mermaid
sequenceDiagram
    participant User
    participant MoveH
    participant Agent1 as 🔍 Fact Checker
    participant Agent2 as 🕵️ Forensic
    participant Judge as ⚖️ Judge
    participant Chain as ⛓️ Blockchain

    User->>MoveH: "Tesla announces $100B acquisition"
    
    par Parallel Execution
        MoveH->>Agent1: Verify claim
        Agent1->>Agent1: Search Reuters, Bloomberg, SEC
        Agent1-->>MoveH: DEBUNKED (no official source)
    and
        MoveH->>Agent2: Analyze text
        Agent2->>Agent2: Detect urgency, scam patterns
        Agent2-->>MoveH: Score: 0.35 (Suspicious)
    end
    
    MoveH->>Judge: Synthesize evidence
    Judge->>Judge: Weight: 70% facts, 30% forensics
    Judge-->>MoveH: 82% likely FALSE
    
    MoveH->>Chain: Store AEP on Aptos
    Chain-->>MoveH: Transaction hash
    
    MoveH-->>User: ❌ 82% FALSE + PDF Report
```

### Healthcare Claim Verification
```mermaid
sequenceDiagram
    participant User
    participant MoveH
    participant Agent1 as 🔍 Fact Checker
    participant Agent2 as 🕵️ Forensic
    participant Judge as ⚖️ Judge

    User->>MoveH: "New miracle cure for diabetes"
    
    par Parallel Execution
        MoveH->>Agent1: Verify claim
        Agent1->>Agent1: Search FDA, NIH, medical journals
        Agent1-->>MoveH: UNVERIFIED (no clinical trials)
    and
        MoveH->>Agent2: Analyze text
        Agent2->>Agent2: Detect "miracle", "cure" scam patterns
        Agent2-->>MoveH: Score: 0.25 (Likely Fraudulent)
    end
    
    MoveH->>Judge: Synthesize evidence
    Judge->>Judge: Weight: 25% facts, 75% forensics (no evidence)
    Judge-->>MoveH: 75% likely FALSE
    
    MoveH-->>User: ❌ 75% FALSE + Warning: Scam indicators
```

## Error Handling Flow

```mermaid
flowchart TB
    subgraph ERROR_HANDLING["Error Handling"]
        START["Start Pipeline"]
        
        subgraph AGENT1_ERR["Agent 1 Errors"]
            A1E1["Tavily API Failure"]
            A1E2["Rate Limit"]
            A1E3["Timeout"]
            A1F["Fallback: LLM Simulation"]
        end
        
        subgraph AGENT2_ERR["Agent 2 Errors"]
            A2E1["LLM API Failure"]
            A2E2["JSON Parse Error"]
            A2F["Fallback: Default Values"]
        end
        
        subgraph JUDGE_ERR["Judge Errors"]
            JE1["Missing Agent Data"]
            JF["Fallback: UNCERTAIN verdict"]
        end
        
        START --> A1E1 & A1E2 & A1E3
        A1E1 & A1E2 & A1E3 --> A1F
        
        START --> A2E1 & A2E2
        A2E1 & A2E2 --> A2F
        
        A1F & A2F --> JE1
        JE1 --> JF
        JF --> OUTPUT["Return Best Effort Result"]
    end
```

## Summary Stats

| Metric | Value |
|--------|-------|
| **Total Agents** | 3 |
| **Total Nodes** | 9 (3 per agent) |
| **Parallel Speedup** | ~3x |
| **Average Latency** | 8-12 seconds |
| **Max Iterations** | 2 (Fact Checker) |
| **Verdict Types** | 5 (TRUE, FALSE, PROBABLY_TRUE, PROBABLY_FALSE, UNCERTAIN) |
| **Storage** | Shelby (decentralized) + Local PDF |
| **Blockchain** | Aptos (Move smart contract) |
