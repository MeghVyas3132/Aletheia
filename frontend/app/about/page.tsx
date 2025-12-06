"use client";

import Navbar from "@/components/Navbar";
import { motion } from "framer-motion";

export default function About() {
    return (
        <main className="min-h-screen bg-background text-foreground selection:bg-primary/30 overflow-x-hidden font-mono grid-bg transition-colors duration-300">
            {/* Grid Overlay */}
            <div className="fixed inset-0 z-0 pointer-events-none border-x border-border max-w-7xl mx-auto" />

            <div className="relative z-10 flex flex-col min-h-screen max-w-7xl mx-auto border-x border-border">
                <Navbar />

                <div className="flex-1 flex flex-col items-center justify-center p-8 md:p-16">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="w-full max-w-4xl space-y-12"
                    >
                        {/* Header */}
                        <div className="text-center space-y-4">
                            <h1 className="text-6xl md:text-5xl font-bold font-display uppercase tracking-tighter">
                                About Us
                            </h1>
                            <p className="text-muted-foreground text-lg md:text-xl font-mono uppercase tracking-widest">
                                Team Without You
                            </p>
                        </div>

                        {/* Team Members */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                            {/* Megh Vyas */}
                            <div className="space-y-4 p-6 border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                                <div>
                                    <h2 className="text-2xl font-bold font-display uppercase mb-2">Megh Vyas</h2>
                                    <p className="text-sm text-muted-foreground font-mono uppercase tracking-widest">DevOps & Gen-AI Developer</p>
                                </div>
                            </div>

                            {/* Anton Raj Singh */}
                            <div className="space-y-4 p-6 border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                                <div>
                                    <h2 className="text-2xl font-bold font-display uppercase mb-2">Anton Raj Singh</h2>
                                    <p className="text-sm text-muted-foreground font-mono uppercase tracking-widest">Full Stack Developer / AI Engineer</p>
                                </div>
                            </div>

                            {/* Mayuresh Singh */}
                            <div className="space-y-4 p-6 border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                                <div>
                                    <h2 className="text-2xl font-bold font-display uppercase mb-2">Mayuresh Singh</h2>
                                    <p className="text-sm text-muted-foreground font-mono uppercase tracking-widest">Full Stack Developer</p>
                                </div>
                            </div>

                            {/* Mohhemad Rayan */}
                            <div className="space-y-4 p-6 border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                                <div>
                                    <h2 className="text-2xl font-bold font-display uppercase mb-2">Mohammed Rayan</h2>
                                    <p className="text-sm text-muted-foreground font-mono uppercase tracking-widest">Web3 Developer</p>
                                </div>
                            </div>

                            {/* Monali Bundela */}
                            <div className="space-y-4 p-6 border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                                <div>
                                    <h2 className="text-2xl font-bold font-display uppercase mb-2">Monali Bundela</h2>
                                    <p className="text-sm text-muted-foreground font-mono uppercase tracking-widest">Full Stack Developer</p>
                                </div>
                            </div>
                        </div>

                        {/* Footer Note */}
                        <div className="text-center pt-12 border-t border-border">
                            <p className="text-xs text-muted-foreground font-mono uppercase tracking-widest">
                                Built with ❤️ by Team Without You • Aexiz Solutions, Bangalore
                            </p>
                        </div>

                    </motion.div>
                </div>

                <footer className="border-t border-border py-6 px-6 text-center text-xs text-muted-foreground font-mono uppercase tracking-widest">
                    Powered by SingularityNET & Groq
                </footer>
            </div>
        </main>
    );
}
