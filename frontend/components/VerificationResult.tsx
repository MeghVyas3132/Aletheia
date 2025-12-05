"use client";

import { motion } from "framer-motion";
import { CheckCircle, XCircle, AlertTriangle, Shield, Brain, FileText, Activity, Clock, Link as LinkIcon } from "lucide-react";
import clsx from "clsx";

interface VerificationResultProps {
    data: any;
    onReset: () => void;
}

export default function VerificationResult({ data, onReset }: VerificationResultProps) {
    const { 
        claim,
        verdict, 
        confidence_score, 
        truth_probability, 
        verdict_text,
        confidence_level,
        summary, 
        sources, 
        forensic_analysis, 
        chain_metadata,
        processing_time,
        aptos_tx,
        aptos_status,
        aptos_explorer_url,
        on_chain_verdict,
        download_url
    } = data;

    const isTrue = truth_probability >= 60;
    const isFalse = truth_probability <= 40;

    const statusColor = isTrue ? "text-emerald-500" : isFalse ? "text-rose-500" : "text-amber-500";
    const borderColor = isTrue ? "border-emerald-500/50" : isFalse ? "border-rose-500/50" : "border-amber-500/50";

    return (
        <div className="w-full max-w-6xl mx-auto pb-20 px-4 pt-8 font-mono">
            {/* Header / Verdict */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-12"
            >
                <div className="flex justify-between items-center mb-8">
                    <button
                        onClick={onReset}
                        className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2 uppercase tracking-widest"
                    >
                        ← Verify another claim
                    </button>
                    {processing_time && (
                        <div className="text-xs text-muted-foreground flex items-center gap-2 uppercase tracking-widest">
                            <Clock className="w-3 h-3" />
                            Processed in {processing_time}
                        </div>
                    )}
                </div>

                <div className={clsx("border-l-4 p-8 bg-card/30 backdrop-blur-sm", borderColor)}>
                    {/* Original Query */}
                    {claim && (
                        <div className="mb-6 pb-6 border-b border-border/50">
                            <div className="text-xs text-muted-foreground uppercase tracking-widest mb-2">Original Query_</div>
                            <p className="text-foreground/90 text-sm md:text-base leading-relaxed italic">&ldquo;{claim}&rdquo;</p>
                        </div>
                    )}
                    
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                        <div>
                            <div className="text-xs text-muted-foreground uppercase tracking-widest mb-2">Final Verdict_</div>
                            <h2 className={clsx("text-6xl md:text-8xl font-bold font-display uppercase leading-none", statusColor)}>
                                {verdict_text || (isTrue ? "VERIFIED" : isFalse ? "DEBUNKED" : "UNCERTAIN")}
                            </h2>
                            <p className="text-muted-foreground mt-2 font-mono text-sm uppercase flex items-center gap-4">
                                <span>Confidence: <span className="text-foreground">{(confidence_score * 100).toFixed(0)}%</span></span>
                                {confidence_level && (
                                    <>
                                        <span className="text-border">|</span>
                                        <span>Level: <span className="text-foreground">{confidence_level}</span></span>
                                    </>
                                )}
                            </p>
                        </div>

                        <div className="flex items-center gap-8">
                            <div className="text-right">
                                <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Truth Probability</div>
                                <div className={clsx("text-4xl font-bold font-display", statusColor)}>{truth_probability.toFixed(0)}%</div>
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-border border border-border">
                {/* Main Content */}
                <div className="lg:col-span-2 bg-card p-8 space-y-12">

                    {/* Summary */}
                    <motion.section
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                    >
                        <h3 className="text-xl font-bold text-foreground mb-6 font-display uppercase flex items-center gap-2">
                            <span className="w-2 h-2 bg-blue-500"></span>
                            AI Analysis
                        </h3>
                        <div className="text-foreground/80 leading-relaxed text-sm md:text-base border-l border-border pl-6">
                            <p>{summary}</p>
                        </div>
                    </motion.section>

                    {/* Sources */}
                    <motion.section
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                        <h3 className="text-xl font-bold text-foreground mb-6 font-display uppercase flex items-center gap-2">
                            <span className="w-2 h-2 bg-blue-500"></span>
                            Evidence Sources
                        </h3>
                        <div className="grid gap-px bg-border border border-border">
                            {sources && sources.length > 0 ? (
                                sources.map((source: any, i: number) => (
                                    <div key={i}>
                                        {source.results && source.results.map((res: any, j: number) => (
                                            <a key={`${i}-${j}`} href={res.url} target="_blank" rel="noopener noreferrer" className="block group bg-card p-4 hover:bg-muted transition-colors">
                                                <h4 className="font-bold text-foreground text-sm group-hover:text-blue-500 truncate uppercase mb-1">{res.title}</h4>
                                                <p className="text-xs text-muted-foreground truncate font-mono">{res.url}</p>
                                            </a>
                                        ))}
                                    </div>
                                ))
                            ) : (
                                <div className="bg-card p-4 text-muted-foreground text-sm italic">No sources found.</div>
                            )}
                        </div>
                    </motion.section>
                </div>

                {/* Sidebar */}
                <div className="bg-card p-8 space-y-12 border-l border-border">

                    {/* Forensic Analysis */}
                    <motion.section
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                        <h3 className="text-xl font-bold text-foreground mb-6 font-display uppercase flex items-center gap-2">
                            <span className="w-2 h-2 bg-purple-500"></span>
                            Forensics
                        </h3>

                        <div className="space-y-6">
                            <div className="flex justify-between items-center border-b border-border pb-4">
                                <span className="text-xs uppercase text-muted-foreground">Forensic Verdict</span>
                                <span className="text-sm font-bold uppercase text-foreground">{forensic_analysis.verdict || "UNKNOWN"}</span>
                            </div>

                            <div>
                                <div className="flex justify-between text-xs uppercase mb-2">
                                    <span className="text-muted-foreground">Integrity Score</span>
                                    <span className="text-foreground">{(forensic_analysis.integrity_score * 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1 bg-muted w-full">
                                    <div
                                        className="h-full bg-purple-500"
                                        style={{ width: `${forensic_analysis.integrity_score * 100}%` }}
                                    />
                                </div>
                            </div>

                            <div>
                                <div className="flex justify-between text-xs uppercase mb-2">
                                    <span className="text-muted-foreground">AI Probability</span>
                                    <span className="text-foreground">{(forensic_analysis.ai_probability * 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1 bg-muted w-full">
                                    <div
                                        className="h-full bg-foreground"
                                        style={{ width: `${forensic_analysis.ai_probability * 100}%` }}
                                    />
                                </div>
                            </div>

                            {/* AI Indicators */}
                            {forensic_analysis.ai_indicators && forensic_analysis.ai_indicators.length > 0 && (
                                <div className="pt-4">
                                    <p className="text-xs font-bold text-muted-foreground uppercase mb-2">AI Indicators</p>
                                    <ul className="space-y-2">
                                        {forensic_analysis.ai_indicators.slice(0, 3).map((indicator: string, i: number) => (
                                            <li key={i} className="text-[10px] text-muted-foreground flex items-start gap-2">
                                                <span className="text-purple-500 mt-0.5">●</span>
                                                {indicator}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {forensic_analysis.penalties.length > 0 && (
                                <div className="pt-6 border-t border-border">
                                    <p className="text-xs font-bold text-muted-foreground uppercase mb-4">Red Flags Detected</p>
                                    <ul className="space-y-3">
                                        {forensic_analysis.penalties.map(([flag, score]: any, i: number) => (
                                            <li key={i} className="text-xs text-destructive flex justify-between items-center uppercase">
                                                <span>{flag}</span>
                                                <span className="bg-destructive/10 px-1.5 py-0.5 text-[10px]">-{score.toFixed(2)}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </motion.section>

                    {/* Blockchain Metadata */}
                    <motion.section
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                    >
                        <h3 className="text-xl font-bold text-foreground mb-6 font-display uppercase flex items-center gap-2">
                            <span className="w-2 h-2 bg-green-500 animate-pulse"></span>
                            On-Chain Data
                        </h3>

                        <div className="space-y-4 text-xs font-mono">
                            <div className="flex justify-between border-b border-border pb-2">
                                <span className="text-muted-foreground uppercase">Network</span>
                                <span className="text-foreground">APTOS TESTNET</span>
                            </div>
                            <div className="flex justify-between border-b border-border pb-2">
                                <span className="text-muted-foreground uppercase">Type</span>
                                <span className="text-foreground">{chain_metadata.claim_type_name || "GENERAL"}</span>
                            </div>
                            
                            {/* Status Badge */}
                            <div className="flex justify-between border-b border-border pb-2">
                                <span className="text-muted-foreground uppercase">Status</span>
                                <span className={clsx(
                                    "uppercase font-bold",
                                    aptos_status === "already_on_chain" ? "text-emerald-500" : 
                                    aptos_status === "submitted" ? "text-blue-500" : "text-amber-500"
                                )}>
                                    {aptos_status === "already_on_chain" ? "✓ ON-CHAIN" : 
                                     aptos_status === "submitted" ? "✓ SUBMITTED" : "PENDING"}
                                </span>
                            </div>
                            
                            <div>
                                <span className="text-muted-foreground block mb-2 uppercase">Claim Hash</span>
                                <code className="block bg-muted p-3 text-muted-foreground break-all text-[10px]">
                                    {chain_metadata.claim_hash || "0x..."}
                                </code>
                            </div>

                            {/* Show existing on-chain verdict info */}
                            {on_chain_verdict && (
                                <div className="border border-emerald-500/30 bg-emerald-500/5 p-3 space-y-2">
                                    <div className="text-[10px] text-emerald-500 uppercase font-bold">Existing On-Chain Verdict</div>
                                    <div className="flex justify-between text-[10px]">
                                        <span className="text-muted-foreground">Verdict:</span>
                                        <span className="text-foreground font-bold">{on_chain_verdict.verdict}</span>
                                    </div>
                                    <div className="flex justify-between text-[10px]">
                                        <span className="text-muted-foreground">Confidence:</span>
                                        <span className="text-foreground">{on_chain_verdict.confidence}%</span>
                                    </div>
                                    {on_chain_verdict.shelby_download_url && (
                                        <a 
                                            href={on_chain_verdict.shelby_download_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="block text-[10px] text-blue-500 hover:text-blue-400 truncate"
                                        >
                                            View Original Report →
                                        </a>
                                    )}
                                </div>
                            )}

                            {aptos_tx && (
                                <div>
                                    <span className="text-muted-foreground block mb-2 uppercase">Transaction Hash</span>
                                    <a 
                                        href={`https://explorer.aptoslabs.com/txn/${aptos_tx}?network=testnet`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block bg-muted p-3 text-blue-500 hover:text-blue-400 break-all text-[10px] transition-colors"
                                    >
                                        {aptos_tx}
                                    </a>
                                </div>
                            )}
                            
                            {/* Explorer URL for existing verdicts */}
                            {aptos_explorer_url && !aptos_tx && (
                                <div>
                                    <span className="text-muted-foreground block mb-2 uppercase">View on Explorer</span>
                                    <a 
                                        href={aptos_explorer_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block bg-muted p-3 text-blue-500 hover:text-blue-400 break-all text-[10px] transition-colors"
                                    >
                                        Open Aptos Explorer →
                                    </a>
                                </div>
                            )}

                            {download_url && (
                                <div className="pt-4 border-t border-border">
                                    <a
                                        href={download_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center justify-center gap-2 w-full bg-primary text-primary-foreground font-bold uppercase py-3 hover:bg-primary/90 transition-colors"
                                    >
                                        <FileText className="w-4 h-4" />
                                        Download AEP Report
                                    </a>
                                </div>
                            )}
                        </div>
                    </motion.section>

                </div>
            </div>
        </div>
    );
}
