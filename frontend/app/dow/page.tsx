"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Swords, Vault, Scale, ArrowLeft } from "lucide-react";
import Link from "next/link";
import ActiveChallengesList from "@/components/ActiveChallengesList";
import TreasuryDashboard from "@/components/TreasuryDashboard";
import VotingPanel from "@/components/VotingPanel";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Challenge {
  challenge_id: string;
  verdict_id: string;
  challenger_wallet: string;
  stake_amount: number;
  evidence_links: string[];
  explanation: string;
  status: string;
  votes_for_ai: number;
  votes_for_challenger: number;
  voting_deadline: string;
  created_at: string;
}

export default function DOWPage() {
  const [selectedChallenge, setSelectedChallenge] = useState<Challenge | null>(null);
  const [userWallet, setUserWallet] = useState("");
  const [walletConnected, setWalletConnected] = useState(false);

  const handleVote = async (
    challengeId: string,
    position: "ai" | "challenger",
    reasoning: string
  ) => {
    const response = await fetch(`${API_BASE_URL}/challenge/${challengeId}/vote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        voter_wallet: userWallet,
        position,
        reasoning,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to submit vote");
    }

    // Refresh the challenge data
    const updatedResponse = await fetch(`${API_BASE_URL}/challenge/${challengeId}`);
    if (updatedResponse.ok) {
      const updated = await updatedResponse.json();
      setSelectedChallenge(updated);
    }
  };

  const connectWallet = () => {
    // Placeholder for Solana wallet connection
    // In production, integrate with Phantom, Solflare, etc.
    const mockWallet = "7xKXt...mock...wallet";
    setUserWallet(mockWallet);
    setWalletConnected(true);
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-red-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-yellow-500/10 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="border-b border-gray-800 bg-black/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                Back to Aletheia
              </Link>
            </div>
            <div className="flex items-center gap-3">
              <Scale className="w-7 h-7 text-yellow-400" />
              <h1 className="text-xl font-bold bg-gradient-to-r from-yellow-400 to-amber-300 bg-clip-text text-transparent">
                Decentralized Oracle of Wisdom
              </h1>
            </div>
            <div>
              {walletConnected ? (
                <div className="flex items-center gap-2 bg-green-500/20 text-green-400 px-4 py-2 rounded-lg">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  <span className="text-sm">{userWallet.slice(0, 8)}...</span>
                </div>
              ) : (
                <button
                  onClick={connectWallet}
                  className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 px-4 py-2 rounded-lg font-medium transition-all"
                >
                  Connect Wallet
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-bold mb-4">
            Challenge the Oracle
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Think Aletheia got it wrong? Stake your SOL, provide evidence, and let the community decide.
            Win and double your stake. Lose and contribute to the wisdom treasury.
          </p>
          <div className="flex items-center justify-center gap-6 mt-8">
            <div className="flex items-center gap-2 bg-green-500/10 text-green-400 px-4 py-2 rounded-full">
              <Swords className="w-4 h-4" />
              <span>Challenge verdicts</span>
            </div>
            <div className="flex items-center gap-2 bg-purple-500/10 text-purple-400 px-4 py-2 rounded-full">
              <Scale className="w-4 h-4" />
              <span>Vote on disputes</span>
            </div>
            <div className="flex items-center gap-2 bg-yellow-500/10 text-yellow-400 px-4 py-2 rounded-full">
              <Vault className="w-4 h-4" />
              <span>Earn rewards</span>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Main Content */}
      <section className="container mx-auto px-6 pb-16">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left Column: Challenges */}
          <div className="space-y-8">
            {/* Selected Challenge Voting Panel */}
            {selectedChallenge && selectedChallenge.status === "voting" && (
              <div>
                <button
                  onClick={() => setSelectedChallenge(null)}
                  className="flex items-center gap-2 text-gray-400 hover:text-white mb-4 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back to all challenges
                </button>
                <VotingPanel
                  challenge={selectedChallenge}
                  onVote={handleVote}
                  userWallet={userWallet}
                />
              </div>
            )}

            {/* Active Challenges List */}
            {!selectedChallenge && (
              <ActiveChallengesList
                apiBaseUrl={API_BASE_URL}
                onSelectChallenge={setSelectedChallenge}
              />
            )}
          </div>

          {/* Right Column: Treasury */}
          <div>
            <TreasuryDashboard apiBaseUrl={API_BASE_URL} />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-t border-gray-800 py-16">
        <div className="container mx-auto px-6">
          <h3 className="text-2xl font-bold text-center mb-12">How DOW Works</h3>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              {
                step: "1",
                title: "Challenge",
                description: "Stake 1-100 SOL with evidence that the AI verdict is wrong",
                color: "red",
              },
              {
                step: "2",
                title: "Community Vote",
                description: "50+ voters review evidence and vote over 48 hours",
                color: "purple",
              },
              {
                step: "3",
                title: "Resolution",
                description: "Weighted votes determine the winner based on majority",
                color: "blue",
              },
              {
                step: "4",
                title: "Payout",
                description: "Winner gets 2x stake. Losers fund the treasury",
                color: "yellow",
              },
            ].map((item, index) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`bg-${item.color}-500/10 border border-${item.color}-500/30 rounded-xl p-6 text-center`}
              >
                <div className={`w-12 h-12 rounded-full bg-${item.color}-500/20 text-${item.color}-400 flex items-center justify-center text-xl font-bold mx-auto mb-4`}>
                  {item.step}
                </div>
                <h4 className={`font-bold text-${item.color}-400 mb-2`}>{item.title}</h4>
                <p className="text-gray-400 text-sm">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
