"use client";

import { motion } from "framer-motion";
import { Loader2, Search, Shield, Brain, CheckCircle2 } from "lucide-react";

export interface Log {
    type: string;
    agent: string;
    message: string;
}

interface VerificationProgressProps {
    logs: Log[];
    sources?: any[];
}

export default function VerificationProgress({ logs, sources = [] }: VerificationProgressProps) {
    return (
        <div className="w-full max-w-4xl mx-auto mt-12 px-4 font-mono">
            <div className="flex items-center justify-between border-b border-border pb-4 mb-8">
                <h3 className="text-sm font-bold uppercase tracking-widest text-foreground">
                    System Status: <span className="text-green-500 animate-pulse">ACTIVE</span>
                </h3>
                <div className="text-xs text-muted-foreground">
                    PROTOCOL_V2.0
                </div>
            </div>

            <div className="border-l border-border pl-6 space-y-6 relative">
                {/* Timeline line */}
                <div className="absolute left-0 top-0 bottom-0 w-px bg-border" />

                {logs.map((log, i) => (
                    <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="relative"
                    >
                        <div className="absolute -left-[29px] top-1.5 w-1.5 h-1.5 bg-muted-foreground rounded-full" />
                        <div className="flex flex-col sm:flex-row sm:items-baseline gap-2">
                            <span className="text-xs text-muted-foreground uppercase min-w-[120px]">
                                [{log.agent || "SYSTEM"}]
                            </span>
                            <span className="text-sm text-foreground/80 break-all">
                                {log.message}
                            </span>
                        </div>
                    </motion.div>
                ))}

                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="flex items-center gap-2 text-muted-foreground pt-4"
                >
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-xs uppercase tracking-wider">Processing...</span>
                </motion.div>
            </div>
        </div>
    );
}
