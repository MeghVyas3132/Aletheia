"use client";

import { useState } from "react";
import SearchHero from "../components/SearchHero";
import VerificationResult from "../components/VerificationResult";
import VerificationProgress, { Log } from "../components/VerificationProgress";
import { motion, AnimatePresence } from "framer-motion";
import Navbar from "@/components/Navbar";

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<Log[]>([]);
  const [sources, setSources] = useState<any[]>([]);

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    setLogs([]);
    setSources([]);

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
      const res = await fetch(`${apiBaseUrl}/verify_stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim: query }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to verify claim");
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No reader available");

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            if (dataStr === "[DONE]") break;

            try {
              const data = JSON.parse(dataStr);

              if (data.type === "log") {
                setLogs(prev => [...prev, data]);
              } else if (data.type === "sources") {
                setSources(prev => [...prev, ...data.data]);
              } else if (data.type === "result") {
                setResult(data.data);
              } else if (data.type === "answer") {
                // NEW: Handle question answers (not TRUE/FALSE verification)
                setResult({
                  ...data,
                  is_answer: true,  // Flag for VerificationResult
                  verdict: null,    // No verdict for questions
                  truth_probability: null
                });
              } else if (data.type === "error") {
                setError(data.message);
              } else if (data.type === "status") {
                // V2: Handle phase status updates
                setLogs(prev => [...prev, { type: "log", agent: data.phase || "System", message: data.message }]);
              } else if (data.type === "triage") {
                // V2: Claim triage complete
                setLogs(prev => [...prev, { type: "log", agent: "Triage", message: `Domains: ${data.data.domains.join(", ")} | Complexity: ${data.data.complexity}` }]);
              } else if (data.type === "domain_agent") {
                // V2: Domain agent result
                setLogs(prev => [...prev, { type: "log", agent: data.domain, message: `Analyzed with ${(data.confidence * 100).toFixed(0)}% confidence` }]);
              } else if (data.type === "agent") {
                // V2: Core agent result
                setLogs(prev => [...prev, { type: "log", agent: data.agent, message: `Verdict: ${data.verdict || "Complete"}` }]);
              } else if (data.type === "devils_advocate") {
                // V2: Devil's Advocate challenge
                setLogs(prev => [...prev, { type: "log", agent: "Devil's Advocate", message: `Attack strength: ${data.attack_strength}` }]);
              } else if (data.type === "debate_round") {
                // V2: Council debate round
                setLogs(prev => [...prev, { type: "log", agent: "Council", message: `Round ${data.round}: ${data.type}` }]);
              } else if (data.type === "jury_vote") {
                // V2: Jury vote
                setLogs(prev => [...prev, { type: "log", agent: `Juror (${data.juror})`, message: `Vote: ${data.vote}` }]);
              }
            } catch (e) {
              console.error("Error parsing stream", e);
            }
          }
        }
      }

    } catch (err: any) {
      console.error(err);
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    setLogs([]);
    setSources([]);
  };

  return (
    <main className="min-h-screen bg-background text-foreground selection:bg-primary/30 overflow-x-hidden font-mono grid-bg transition-colors duration-300">
      {/* Grid Overlay */}
      <div className="fixed inset-0 z-0 pointer-events-none border-x border-border max-w-7xl mx-auto" />

      <div className="relative z-10 flex flex-col min-h-screen max-w-7xl mx-auto border-x border-border">
        <Navbar onReset={handleReset} />

        <div className="flex-1 flex flex-col">
          <AnimatePresence mode="wait">
            {!result && !isLoading && logs.length === 0 ? (
              <motion.div
                key="search"
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="flex flex-col items-center justify-center flex-1 w-full px-4"
              >
                <SearchHero onSearch={handleSearch} isLoading={isLoading} />
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center text-destructive mt-8 border border-destructive/20 bg-destructive/5 py-2 px-6 text-xs font-mono uppercase tracking-wide"
                  >
                    Error: {error}
                  </motion.div>
                )}
              </motion.div>
            ) : !result && (isLoading || logs.length > 0) ? (
              <motion.div
                key="progress"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, y: -20 }}
                className="w-full flex-1"
              >
                <VerificationProgress logs={logs} sources={sources} />
              </motion.div>
            ) : (
              <motion.div
                key="result"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="w-full flex-1"
              >
                <VerificationResult data={result} onReset={handleReset} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <footer className="border-t border-border py-6 px-6 text-center text-xs text-muted-foreground font-mono uppercase tracking-widest">
          Powered by Groq, Tavily & AI Council
        </footer>
      </div>
    </main>
  );
}
