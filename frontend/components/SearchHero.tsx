"use client";

import { useState } from "react";
import { ArrowRight, Search, ShieldCheck } from "lucide-react";
import { motion } from "framer-motion";

interface SearchHeroProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export default function SearchHero({ onSearch, isLoading }: SearchHeroProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  const suggestions = [
    "Tesla announced they are acquiring Twitter",
    "Nvidia invested in Nokia",
    "Bitcoin crashed to $10,000 today"
  ];

  return (
    <div className="flex flex-col items-start justify-center w-full max-w-4xl mx-auto px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full mb-12"
      >
        <div className="flex flex-col items-start mb-8">
          <div className="flex items-baseline gap-4 mb-2">
            <h1 className="text-7xl md:text-9xl font-bold tracking-tighter text-foreground font-display leading-none">
              VERIFY
            </h1>
            <span className="text-4xl md:text-6xl text-muted-foreground font-display">+</span>
          </div>
          <h1 className="text-7xl md:text-9xl font-bold tracking-tighter text-foreground font-display leading-none ml-12 md:ml-24">
            CLAIM
          </h1>
        </div>

        <p className="text-sm md:text-base text-muted-foreground max-w-xl font-mono uppercase tracking-widest border-l border-border pl-6 py-2">
          AI-powered fact-checking on the blockchain. <br />
          Multi-agent intelligence // Aptos Network
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="w-full"
      >
        <form onSubmit={handleSubmit} className="relative group mb-12">
          <div className="relative flex items-center">
            <span className="absolute left-0 text-muted-foreground font-mono text-xl">{">"}</span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="ENTER CLAIM TO VERIFY..."
              className="w-full pl-8 pr-32 py-4 bg-transparent border-b border-border text-xl md:text-3xl text-foreground placeholder-muted-foreground font-display uppercase tracking-wide focus:outline-none focus:border-primary transition-colors rounded-none"
              disabled={isLoading}
              autoFocus
            />
            <button
              type="submit"
              disabled={!query.trim() || isLoading}
              className="absolute right-0 bottom-4 px-6 py-2 bg-primary text-primary-foreground font-bold uppercase tracking-wider hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-display text-lg"
            >
              {isLoading ? "PROCESSING..." : "EXECUTE"}
            </button>
          </div>
        </form>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 border-t border-border pt-8">
          <div className="text-xs text-muted-foreground font-mono uppercase mb-2 md:mb-0">Suggested Queries_</div>
          <div className="col-span-2 flex flex-wrap gap-2">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuery(s);
                  onSearch(s);
                }}
                className="px-3 py-1 text-xs text-muted-foreground border border-border hover:border-primary hover:text-foreground transition-colors font-mono uppercase text-left"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
