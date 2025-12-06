"use client";

import { useState } from "react";
import { AlertTriangle, X, TestTube } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface DemoModeBannerProps {
  network?: string;
}

export function DemoModeBanner({ network = "devnet" }: DemoModeBannerProps) {
  const [isVisible, setIsVisible] = useState(true);

  if (!isVisible) return null;

  const isTestnet = network === "devnet" || network === "testnet";

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -50 }}
        className={`fixed top-0 left-0 right-0 z-[100] ${
          isTestnet
            ? "bg-gradient-to-r from-yellow-600 to-orange-600"
            : "bg-gradient-to-r from-green-600 to-emerald-600"
        }`}
      >
        <div className="container mx-auto px-4 py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isTestnet ? (
                <TestTube className="w-4 h-4 text-white" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-white" />
              )}
              <span className="text-white text-sm font-medium">
                {isTestnet ? (
                  <>
                    <span className="font-bold uppercase">Demo Mode</span>
                    {" • "}
                    Connected to Solana {network}. No real funds at risk.
                  </>
                ) : (
                  <>
                    <span className="font-bold uppercase">Mainnet</span>
                    {" • "}
                    Real funds. Please verify before staking.
                  </>
                )}
              </span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-xs text-white/80 hidden sm:inline">
                {isTestnet && "Get devnet SOL: "}
                {isTestnet && (
                  <a
                    href="https://faucet.solana.com/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-white"
                  >
                    faucet.solana.com
                  </a>
                )}
              </span>
              <button
                onClick={() => setIsVisible(false)}
                className="text-white/80 hover:text-white transition-colors p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export default DemoModeBanner;
