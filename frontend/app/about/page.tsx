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
                            <h1 className="text-6xl md:text-8xl font-bold font-display uppercase tracking-tighter">
                                About Us
                            </h1>
                            <p className="text-muted-foreground text-lg md:text-xl font-mono uppercase tracking-widest">
                                Team IcySpicy
                            </p>
                        </div>

                        {/* Group Photo */}
                        <div className="w-full h-[500px] bg-muted border border-border relative overflow-hidden group flex items-center justify-center">
                            {/* Blurred Background */}
                            <div
                                className="absolute inset-0 bg-cover bg-center blur-xl opacity-50 scale-110"
                                style={{ backgroundImage: "url('/group-photo.jpeg')" }}
                            />
                            {/* Main Image */}
                            <img src="/group-photo.jpeg" alt="Team IcySpicy" className="relative z-10 h-full w-full object-contain shadow-2xl" />
                        </div>

                        {/* Team Members */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                            {/* Mohit */}
                            <div className="space-y-6 p-8 border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                                <div>
                                    <h2 className="text-3xl font-bold font-display uppercase mb-2">Mohit Paddhariya</h2>
                                    <p className="text-sm text-muted-foreground font-mono uppercase tracking-widest">Full-Stack & Gen-AI Developer</p>
                                </div>
                                <p className="text-foreground/80 leading-relaxed">
                                    Building innovative digital solutions across web, mobile, and AI platforms. Specializing in modern frameworks, cloud technologies, and open source contributions.
                                </p>
                                <a
                                    href="https://www.mohitp.me/"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-block text-xs font-bold uppercase tracking-widest border-b border-primary text-primary hover:text-primary/80 transition-colors pb-1"
                                >
                                    Visit Portfolio →
                                </a>
                            </div>

                            {/* Darshith */}
                            <div className="space-y-6 p-8 border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                                <div>
                                    <h2 className="text-3xl font-bold font-display uppercase mb-2">Darshith M S</h2>
                                    <p className="text-sm text-muted-foreground font-mono uppercase tracking-widest">Developer & Partner</p>
                                </div>
                                <p className="text-foreground/80 leading-relaxed">
                                    Partner in crime at Team IcySpicy. Contributing to the vision and execution of MoveH.
                                </p>
                                <a
                                    href="https://www.linkedin.com/in/darshith-m-s-241356304/?originalSubdomain=in"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-block text-xs font-bold uppercase tracking-widest border-b border-primary text-primary hover:text-primary/80 transition-colors pb-1"
                                >
                                    View LinkedIn →
                                </a>
                            </div>
                        </div>

                        {/* Footer Note */}
                        <div className="text-center pt-12 border-t border-border">
                            <p className="text-xs text-muted-foreground font-mono uppercase tracking-widest">
                                Built with ❤️ by Team IcySpicy • PES University, Bangalore
                            </p>
                        </div>

                    </motion.div>
                </div>

                <footer className="border-t border-border py-6 px-6 text-center text-xs text-muted-foreground font-mono uppercase tracking-widest">
                    Powered by Aptos & Gemini 2.5
                </footer>
            </div>
        </main>
    );
}
