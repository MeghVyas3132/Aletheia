"use client";

import { motion } from "framer-motion";
import { CheckCircle, XCircle, AlertTriangle, Shield, Brain, FileText, Activity, Clock, Link as LinkIcon, Users, Scale, Target, Coins, MessageCircle, HelpCircle } from "lucide-react";
import clsx from "clsx";

interface VerificationResultProps {
    data: any;
    onReset: () => void;
}

export default function VerificationResult({ data, onReset }: VerificationResultProps) {
    // Check if this is an ANSWER (question) vs VERIFICATION (claim)
    const isAnswer = data.is_answer || data.type === "answer" || data.input_type === "question" || data.input_type === "comparison";
    
    if (isAnswer) {
        return <AnswerResult data={data} onReset={onReset} />;
    }
    
    // Original verification result rendering
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
        processing_time,
        download_url,
        // V2 additions
        triage,
        council_vote,
        debate_rounds,
        devils_advocate,
        market_id,
        market,
        claim_id
    } = data;

    const truthProb = truth_probability || 50;
    const isTrue = truthProb >= 60;
    const isFalse = truthProb <= 40;

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
                            <h2 className={clsx("text-3xl md:text-5xl font-bold font-display uppercase leading-none", statusColor)}>
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
                            AI Council Analysis
                        </h3>
                        <div className="text-foreground/80 leading-relaxed text-xs md:text-sm border-l border-border pl-6">
                            <p>{summary}</p>
                        </div>
                    </motion.section>

                    {/* AI Council Vote */}
                    {council_vote && (
                        <motion.section
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.15 }}
                        >
                            <h3 className="text-xl font-bold text-foreground mb-6 font-display uppercase flex items-center gap-2">
                                <span className="w-2 h-2 bg-purple-500"></span>
                                <Users className="w-4 h-4" />
                                Council Vote ({debate_rounds || 3} Rounds)
                            </h3>
                            <div className="grid grid-cols-3 gap-4">
                                <div className="bg-emerald-500/10 border border-emerald-500/30 p-4 text-center">
                                    <div className="text-3xl font-bold text-emerald-500">{council_vote.true || 0}</div>
                                    <div className="text-xs text-muted-foreground uppercase mt-1">True</div>
                                </div>
                                <div className="bg-rose-500/10 border border-rose-500/30 p-4 text-center">
                                    <div className="text-3xl font-bold text-rose-500">{council_vote.false || 0}</div>
                                    <div className="text-xs text-muted-foreground uppercase mt-1">False</div>
                                </div>
                                <div className="bg-amber-500/10 border border-amber-500/30 p-4 text-center">
                                    <div className="text-3xl font-bold text-amber-500">{council_vote.uncertain || 0}</div>
                                    <div className="text-xs text-muted-foreground uppercase mt-1">Uncertain</div>
                                </div>
                            </div>
                        </motion.section>
                    )}

                    {/* Devil's Advocate */}
                    {devils_advocate && (
                        <motion.section
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.18 }}
                        >
                            <h3 className="text-xl font-bold text-foreground mb-6 font-display uppercase flex items-center gap-2">
                                <span className="w-2 h-2 bg-rose-500"></span>
                                <Target className="w-4 h-4" />
                                Devil&apos;s Advocate
                            </h3>
                            <div className="border border-rose-500/30 bg-rose-500/5 p-4">
                                <div className="flex justify-between items-center mb-4">
                                    <span className="text-xs text-muted-foreground uppercase">Attack Strength</span>
                                    <span className={clsx(
                                        "text-sm font-bold uppercase",
                                        devils_advocate.attack_strength === "strong" ? "text-rose-500" :
                                        devils_advocate.attack_strength === "moderate" ? "text-amber-500" : "text-emerald-500"
                                    )}>
                                        {devils_advocate.attack_strength}
                                    </span>
                                </div>
                                <p className="text-xs text-foreground/70">{devils_advocate.recommendation}</p>
                            </div>
                        </motion.section>
                    )}

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
                                sources.map((source: any, i: number) => {
                                    // Handle both old format (with results array) and V2 format (direct)
                                    if (source.results) {
                                        return source.results.map((res: any, j: number) => (
                                            <a key={`${i}-${j}`} href={res.url} target="_blank" rel="noopener noreferrer" className="block group bg-card p-4 hover:bg-muted transition-colors">
                                                <h4 className="font-bold text-foreground text-sm group-hover:text-blue-500 truncate uppercase mb-1">{res.title}</h4>
                                                <p className="text-xs text-muted-foreground truncate font-mono">{res.url}</p>
                                            </a>
                                        ));
                                    }
                                    return (
                                        <a key={i} href={source.url} target="_blank" rel="noopener noreferrer" className="block group bg-card p-4 hover:bg-muted transition-colors">
                                            <h4 className="font-bold text-foreground text-sm group-hover:text-blue-500 truncate uppercase mb-1">{source.title || "Source"}</h4>
                                            <p className="text-xs text-muted-foreground truncate font-mono">{source.url}</p>
                                        </a>
                                    );
                                })
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
                                <span className="text-sm font-bold uppercase text-foreground">{forensic_analysis?.verdict || "UNKNOWN"}</span>
                            </div>

                            <div>
                                <div className="flex justify-between text-xs uppercase mb-2">
                                    <span className="text-muted-foreground">Integrity Score</span>
                                    <span className="text-foreground">{((forensic_analysis?.integrity_score || 0) * 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1 bg-muted w-full">
                                    <div
                                        className="h-full bg-purple-500"
                                        style={{ width: `${(forensic_analysis?.integrity_score || 0) * 100}%` }}
                                    />
                                </div>
                            </div>

                            <div>
                                <div className="flex justify-between text-xs uppercase mb-2">
                                    <span className="text-muted-foreground">AI Probability</span>
                                    <span className="text-foreground">{((forensic_analysis?.ai_probability || 0) * 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1 bg-muted w-full">
                                    <div
                                        className="h-full bg-foreground"
                                        style={{ width: `${(forensic_analysis?.ai_probability || 0) * 100}%` }}
                                    />
                                </div>
                            </div>

                            {/* AI Indicators */}
                            {forensic_analysis?.ai_indicators && forensic_analysis.ai_indicators.length > 0 && (
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

                            {forensic_analysis?.penalties && forensic_analysis.penalties.length > 0 && (
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

                    {/* Truth Market */}
                    {market && (
                        <motion.section
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.4 }}
                        >
                            <h3 className="text-xl font-bold text-foreground mb-6 font-display uppercase flex items-center gap-2">
                                <span className="w-2 h-2 bg-amber-500 animate-pulse"></span>
                                <Coins className="w-4 h-4" />
                                Truth Market
                            </h3>

                            <div className="space-y-4 text-xs font-mono">
                                <div className="flex justify-between border-b border-border pb-2">
                                    <span className="text-muted-foreground uppercase">Status</span>
                                    <span className="text-emerald-500 uppercase font-bold">
                                        {market.status === "open" ? "🟢 OPEN" : market.status}
                                    </span>
                                </div>
                                <div className="flex justify-between border-b border-border pb-2">
                                    <span className="text-muted-foreground uppercase">Total Pool</span>
                                    <span className="text-foreground">{(market.total_pool || 0).toFixed(2)} ALETH</span>
                                </div>
                                <div className="flex justify-between border-b border-border pb-2">
                                    <span className="text-muted-foreground uppercase">Correct Bets</span>
                                    <span className="text-emerald-500">{(market.correct_pool || 0).toFixed(2)} ALETH</span>
                                </div>
                                <div className="flex justify-between border-b border-border pb-2">
                                    <span className="text-muted-foreground uppercase">Wrong Bets</span>
                                    <span className="text-rose-500">{(market.wrong_pool || 0).toFixed(2)} ALETH</span>
                                </div>
                                
                                <div className="pt-4">
                                    <div className="text-muted-foreground uppercase mb-2">Aletheia Says</div>
                                    <div className={clsx(
                                        "text-lg font-bold uppercase",
                                        market.aletheia_verdict === "TRUE" ? "text-emerald-500" :
                                        market.aletheia_verdict === "FALSE" ? "text-rose-500" : "text-amber-500"
                                    )}>
                                        {market.aletheia_verdict}
                                    </div>
                                    <div className="text-muted-foreground">
                                        Confidence: {((market.aletheia_confidence || 0) * 100).toFixed(0)}%
                                    </div>
                                </div>

                                <div className="pt-4 border-t border-border">
                                    <div className="grid grid-cols-2 gap-2">
                                        <button className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold uppercase py-2 px-4 text-xs transition-colors">
                                            Bet Correct
                                        </button>
                                        <button className="bg-rose-500 hover:bg-rose-600 text-white font-bold uppercase py-2 px-4 text-xs transition-colors">
                                            Bet Wrong
                                        </button>
                                    </div>
                                    <p className="text-[10px] text-muted-foreground mt-2 text-center">
                                        Connect wallet to place bets
                                    </p>
                                </div>
                            </div>
                        </motion.section>
                    )}

                    {/* Claim ID & Triage */}
                    <motion.section
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.45 }}
                    >
                        <h3 className="text-xl font-bold text-foreground mb-6 font-display uppercase flex items-center gap-2">
                            <span className="w-2 h-2 bg-cyan-500"></span>
                            Claim Analysis
                        </h3>
                        
                        <div className="space-y-4 text-xs font-mono">
                            {triage && (
                                <>
                                    <div className="flex justify-between border-b border-border pb-2">
                                        <span className="text-muted-foreground uppercase">Complexity</span>
                                        <span className={clsx(
                                            "uppercase font-bold",
                                            triage.complexity === "complex" ? "text-rose-500" :
                                            triage.complexity === "medium" ? "text-amber-500" : "text-emerald-500"
                                        )}>
                                            {triage.complexity}
                                        </span>
                                    </div>
                                    
                                    {triage.domains && triage.domains.length > 0 && (
                                        <div>
                                            <span className="text-muted-foreground block mb-2 uppercase">Domains</span>
                                            <div className="flex flex-wrap gap-1">
                                                {triage.domains.map((domain: string, i: number) => (
                                                    <span key={i} className="bg-cyan-500/10 text-cyan-500 px-2 py-0.5 text-[10px] uppercase">
                                                        {domain}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {triage.entities && triage.entities.length > 0 && (
                                        <div>
                                            <span className="text-muted-foreground block mb-2 uppercase">Entities</span>
                                            <div className="flex flex-wrap gap-1">
                                                {triage.entities.slice(0, 5).map((entity: string, i: number) => (
                                                    <span key={i} className="bg-muted text-foreground px-2 py-0.5 text-[10px]">
                                                        {entity}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}
                            
                            {claim_id && (
                                <div className="pt-4 border-t border-border">
                                    <span className="text-muted-foreground block mb-2 uppercase">Claim ID</span>
                                    <code className="block bg-muted p-3 text-muted-foreground break-all text-[10px]">
                                        {claim_id}
                                    </code>
                                </div>
                            )}
                            
                            {market_id && (
                                <div>
                                    <span className="text-muted-foreground block mb-2 uppercase">Market ID</span>
                                    <code className="block bg-muted p-3 text-muted-foreground break-all text-[10px]">
                                        {market_id}
                                    </code>
                                </div>
                            )}
                        </div>
                    </motion.section>

                    {download_url && (
                        <div className="pt-4 border-t border-border">
                            <a
                                href={download_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-center gap-2 w-full bg-primary text-primary-foreground font-bold uppercase py-3 hover:bg-primary/90 transition-colors text-xs"
                            >
                                <FileText className="w-4 h-4" />
                                Download Report
                            </a>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
}

// ==================== ANSWER RESULT COMPONENT (for questions) ====================

function AnswerResult({ data, onReset }: VerificationResultProps) {
    const {
        question,
        answer,
        summary,
        nuance,
        is_contentious,
        sources,
        confidence,
        domains,
        processing_time
    } = data;

    return (
        <div className="w-full max-w-6xl mx-auto pb-20 px-4 pt-8 font-mono">
            {/* Header */}
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
                        ← Ask another question
                    </button>
                    {processing_time && (
                        <div className="text-xs text-muted-foreground flex items-center gap-2 uppercase tracking-widest">
                            <Clock className="w-3 h-3" />
                            Answered in {processing_time}s
                        </div>
                    )}
                </div>

                <div className={clsx(
                    "border-l-4 p-8 bg-card/30 backdrop-blur-sm",
                    is_contentious ? "border-amber-500/50" : "border-blue-500/50"
                )}>
                    {/* Original Question */}
                    <div className="mb-6 pb-6 border-b border-border/50">
                        <div className="text-xs text-muted-foreground uppercase tracking-widest mb-2 flex items-center gap-2">
                            <HelpCircle className="w-3 h-3" />
                            Your Question_
                        </div>
                        <p className="text-foreground/90 text-sm md:text-base leading-relaxed italic">&ldquo;{question}&rdquo;</p>
                    </div>
                    
                    {/* Contentious Warning */}
                    {is_contentious && (
                        <div className="mb-6 p-4 border border-amber-500/30 bg-amber-500/5">
                            <div className="flex items-center gap-2 text-amber-500 text-xs uppercase tracking-widest mb-2">
                                <AlertTriangle className="w-4 h-4" />
                                Contentious Topic
                            </div>
                            <p className="text-muted-foreground text-sm">
                                This topic is disputed. Multiple perspectives are presented below.
                            </p>
                        </div>
                    )}
                    
                    {/* Answer Header */}
                    <div className="flex items-center gap-3 mb-4">
                        <MessageCircle className="w-6 h-6 text-blue-500" />
                        <h2 className="text-2xl font-bold font-display uppercase">Answer</h2>
                        {confidence && (
                            <span className="text-xs text-muted-foreground uppercase">
                                ({Math.round(confidence * 100)}% confidence)
                            </span>
                        )}
                    </div>
                </div>
            </motion.div>

            {/* Main Answer Content */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-8">
                    {/* Full Answer */}
                    <motion.section
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="border border-border bg-card/30 p-6"
                    >
                        <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-4 flex items-center gap-2">
                            <Brain className="w-4 h-4" />
                            Research Answer_
                        </h3>
                        <div className="prose prose-invert prose-sm max-w-none">
                            <div className="text-foreground/90 whitespace-pre-wrap leading-relaxed text-xs md:text-sm">
                                {answer}
                            </div>
                        </div>
                    </motion.section>

                    {/* Nuance (if applicable) */}
                    {nuance && (
                        <motion.section
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 }}
                            className="border border-amber-500/30 bg-amber-500/5 p-6"
                        >
                            <h3 className="text-xs font-bold uppercase tracking-widest text-amber-500 mb-4 flex items-center gap-2">
                                <Scale className="w-4 h-4" />
                                Additional Nuance_
                            </h3>
                            <p className="text-foreground/80 text-xs leading-relaxed">
                                {nuance}
                            </p>
                        </motion.section>
                    )}
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    {/* Domains */}
                    {domains && domains.length > 0 && (
                        <motion.section
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 }}
                            className="border border-border bg-card/30 p-4"
                        >
                            <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
                                Topics_
                            </h3>
                            <div className="flex flex-wrap gap-2">
                                {domains.map((domain: string, i: number) => (
                                    <span key={i} className="px-2 py-1 bg-muted text-muted-foreground text-xs uppercase">
                                        {domain}
                                    </span>
                                ))}
                            </div>
                        </motion.section>
                    )}

                    {/* Sources */}
                    {sources && sources.length > 0 && (
                        <motion.section
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.3 }}
                            className="border border-border bg-card/30 p-4"
                        >
                            <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-2">
                                <LinkIcon className="w-3 h-3" />
                                Sources_
                            </h3>
                            <ul className="space-y-2">
                                {sources.map((source: any, i: number) => (
                                    <li key={i} className="text-xs">
                                        {source.url ? (
                                            <a
                                                href={source.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-blue-400 hover:text-blue-300 transition-colors block truncate"
                                            >
                                                {source.title || source.url}
                                            </a>
                                        ) : (
                                            <span className="text-muted-foreground">{source.title}</span>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        </motion.section>
                    )}

                    {/* Summary Box */}
                    {summary && (
                        <motion.section
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.4 }}
                            className="border border-blue-500/30 bg-blue-500/5 p-4"
                        >
                            <h3 className="text-xs font-bold uppercase tracking-widest text-blue-500 mb-3">
                                TL;DR_
                            </h3>
                            <p className="text-foreground/80 text-sm leading-relaxed">
                                {summary}
                            </p>
                        </motion.section>
                    )}
                </div>
            </div>
        </div>
    );
}
