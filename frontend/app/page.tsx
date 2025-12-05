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
              } else if (data.type === "error") {
                setError(data.message);
              } else if (data.type === "status") {
                // Optional: handle generic status updates
                setLogs(prev => [...prev, { type: "log", agent: "System", message: data.message }]);
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
          Powered by Aptos & Gemini 2.5
        </footer>
      </div>
    </main>
  );
}
