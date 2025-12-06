"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Vote,
  ThumbsUp,
  ThumbsDown,
  Clock,
  Users,
  Trophy,
  AlertCircle,
  Loader2,
  Shield,
  User,
  ExternalLink,
  Ban,
  CheckCircle2,
} from "lucide-react";

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

interface EligibilityResult {
  eligible: boolean;
  reason: string;
  warning?: string;
  requirements?: {
    min_wallet_age_days: number;
    min_sol_balance: number;
    min_transaction_count: number;
    max_votes_per_hour: number;
  };
}

interface VotingPanelProps {
  challenge: Challenge;
  onVote: (challengeId: string, position: "ai" | "challenger", reasoning: string) => Promise<void>;
  userWallet: string;
  hasVoted?: boolean;
  userVote?: "ai" | "challenger";
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function VotingPanel({
  challenge,
  onVote,
  userWallet,
  hasVoted = false,
  userVote,
}: VotingPanelProps) {
  const [selectedPosition, setSelectedPosition] = useState<"ai" | "challenger" | null>(null);
  const [reasoning, setReasoning] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState("");
  
  // Eligibility state
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [isCheckingEligibility, setIsCheckingEligibility] = useState(false);

  // Check eligibility when wallet is provided
  useEffect(() => {
    const checkEligibility = async () => {
      if (!userWallet || hasVoted) {
        return;
      }
      
      setIsCheckingEligibility(true);
      
      try {
        const response = await fetch(
          `${API_URL}/voter/${userWallet}/eligibility?challenge_id=${challenge.challenge_id}`
        );
        
        if (response.ok) {
          const data = await response.json();
          setEligibility(data);
        } else {
          // Graceful degradation - allow voting if check fails
          setEligibility({ eligible: true, reason: "Unable to verify eligibility" });
        }
      } catch (err) {
        console.error("Eligibility check failed:", err);
        // Graceful degradation
        setEligibility({ eligible: true, reason: "Unable to verify eligibility" });
      } finally {
        setIsCheckingEligibility(false);
      }
    };
    
    checkEligibility();
  }, [userWallet, challenge.challenge_id, hasVoted]);

  // Calculate time remaining
  useEffect(() => {
    const calculateTimeLeft = () => {
      const deadline = new Date(challenge.voting_deadline);
      const now = new Date();
      const diff = deadline.getTime() - now.getTime();

      if (diff <= 0) {
        setTimeLeft("Voting ended");
        return;
      }

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      setTimeLeft(`${hours}h ${minutes}m remaining`);
    };

    calculateTimeLeft();
    const interval = setInterval(calculateTimeLeft, 60000);
    return () => clearInterval(interval);
  }, [challenge.voting_deadline]);

  const totalVotes = challenge.votes_for_ai + challenge.votes_for_challenger;
  const aiPercentage = totalVotes > 0 ? (challenge.votes_for_ai / totalVotes) * 100 : 50;
  const challengerPercentage = totalVotes > 0 ? (challenge.votes_for_challenger / totalVotes) * 100 : 50;

  const handleSubmitVote = async () => {
    if (!selectedPosition) {
      setError("Please select a position");
      return;
    }
    if (reasoning.length < 50) {
      setError(`Please provide reasoning (${reasoning.length}/50 characters minimum)`);
      return;
    }
    
    // Check eligibility before submitting
    if (eligibility && !eligibility.eligible) {
      setError(`Cannot vote: ${eligibility.reason}`);
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onVote(challenge.challenge_id, selectedPosition, reasoning);
    } catch (err: any) {
      setError(err.message || "Failed to submit vote");
    } finally {
      setIsSubmitting(false);
    }
  };

  const isVotingActive = challenge.status === "voting";
  const canVote = eligibility?.eligible !== false;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-purple-950/30 to-blue-950/30 border border-purple-500/30 rounded-2xl p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <Vote className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-purple-400">Community Vote</h3>
            <p className="text-sm text-gray-400">Who is right about this claim?</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-gray-400">
          <Clock className="w-4 h-4" />
          <span className="text-sm">{timeLeft}</span>
        </div>
      </div>

      {/* Challenge Summary */}
      <div className="bg-black/30 rounded-xl p-4 mb-6">
        <div className="flex items-center gap-2 mb-2">
          <User className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-400">
            Challenger: {challenge.challenger_wallet.slice(0, 8)}...{challenge.challenger_wallet.slice(-6)}
          </span>
        </div>
        <p className="text-white mb-3">{challenge.explanation}</p>
        <div className="flex flex-wrap gap-2">
          {challenge.evidence_links.map((link, index) => (
            <a
              key={index}
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300 bg-purple-500/10 px-2 py-1 rounded"
            >
              <ExternalLink className="w-3 h-3" />
              Source {index + 1}
            </a>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <Trophy className="w-4 h-4 text-yellow-400" />
          <span className="text-yellow-400 font-medium">
            Stake: {challenge.stake_amount} SOL (Winner gets {challenge.stake_amount * 2} SOL)
          </span>
        </div>
      </div>

      {/* Vote Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between mb-2">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-green-400" />
            <span className="text-sm text-green-400">AI Correct</span>
            <span className="text-xs text-gray-500">({challenge.votes_for_ai} votes)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">({challenge.votes_for_challenger} votes)</span>
            <span className="text-sm text-red-400">Challenger Correct</span>
            <User className="w-4 h-4 text-red-400" />
          </div>
        </div>
        <div className="h-4 bg-gray-800 rounded-full overflow-hidden flex">
          <motion.div
            initial={{ width: "50%" }}
            animate={{ width: `${aiPercentage}%` }}
            className="bg-gradient-to-r from-green-600 to-green-400 h-full"
          />
          <motion.div
            initial={{ width: "50%" }}
            animate={{ width: `${challengerPercentage}%` }}
            className="bg-gradient-to-r from-red-400 to-red-600 h-full"
          />
        </div>
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>{aiPercentage.toFixed(1)}%</span>
          <span>{challengerPercentage.toFixed(1)}%</span>
        </div>
      </div>

      {/* Vote Status */}
      <div className="flex items-center justify-center gap-4 mb-6 py-3 bg-black/20 rounded-lg">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-400">{totalVotes} total votes</span>
        </div>
        <div className="w-px h-4 bg-gray-700" />
        <span className="text-sm text-gray-400">
          {Math.max(0, 50 - totalVotes)} more needed for resolution
        </span>
      </div>

      {/* Already Voted */}
      {hasVoted && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 flex items-center gap-3">
          <div className="p-2 bg-green-500/20 rounded-full">
            {userVote === "ai" ? (
              <ThumbsUp className="w-5 h-5 text-green-400" />
            ) : (
              <ThumbsDown className="w-5 h-5 text-red-400" />
            )}
          </div>
          <div>
            <p className="text-green-400 font-medium">You've already voted!</p>
            <p className="text-sm text-gray-400">
              You voted that {userVote === "ai" ? "the AI is correct" : "the challenger is correct"}
            </p>
          </div>
        </div>
      )}

      {/* Voting Form */}
      {!hasVoted && isVotingActive && (
        <div className="space-y-4">
          {/* Eligibility Check */}
          {isCheckingEligibility && (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
              <span className="text-sm text-blue-400">Checking voting eligibility...</span>
            </div>
          )}
          
          {/* Eligibility Warning */}
          {eligibility && !eligibility.eligible && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Ban className="w-5 h-5 text-red-400" />
                <span className="font-medium text-red-400">Cannot Vote</span>
              </div>
              <p className="text-sm text-gray-300 mb-2">{eligibility.reason}</p>
              {eligibility.requirements && (
                <div className="text-xs text-gray-500 space-y-1">
                  <p>Requirements:</p>
                  <ul className="list-disc list-inside">
                    <li>Wallet age: at least {eligibility.requirements.min_wallet_age_days} days</li>
                    <li>SOL balance: at least {eligibility.requirements.min_sol_balance} SOL</li>
                    <li>Transactions: at least {eligibility.requirements.min_transaction_count}</li>
                  </ul>
                </div>
              )}
            </div>
          )}
          
          {/* Eligibility Confirmed */}
          {eligibility?.eligible && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <span className="text-sm text-green-400">You are eligible to vote</span>
            </div>
          )}
          
          {/* Position Selection */}
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setSelectedPosition("ai")}
              disabled={!canVote}
              className={`p-4 rounded-xl border-2 transition-all ${
                selectedPosition === "ai"
                  ? "border-green-500 bg-green-500/20"
                  : "border-gray-600 bg-black/30 hover:border-gray-500"
              } ${!canVote ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <div className="flex flex-col items-center gap-2">
                <Shield className={`w-8 h-8 ${selectedPosition === "ai" ? "text-green-400" : "text-gray-400"}`} />
                <span className={`font-medium ${selectedPosition === "ai" ? "text-green-400" : "text-gray-300"}`}>
                  AI is Correct
                </span>
                <span className="text-xs text-gray-500">
                  The original verdict stands
                </span>
              </div>
            </button>
            <button
              onClick={() => setSelectedPosition("challenger")}
              disabled={!canVote}
              className={`p-4 rounded-xl border-2 transition-all ${
                selectedPosition === "challenger"
                  ? "border-red-500 bg-red-500/20"
                  : "border-gray-600 bg-black/30 hover:border-gray-500"
              } ${!canVote ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <div className="flex flex-col items-center gap-2">
                <User className={`w-8 h-8 ${selectedPosition === "challenger" ? "text-red-400" : "text-gray-400"}`} />
                <span className={`font-medium ${selectedPosition === "challenger" ? "text-red-400" : "text-gray-300"}`}>
                  Challenger is Correct
                </span>
                <span className="text-xs text-gray-500">
                  The verdict should change
                </span>
              </div>
            </button>
          </div>

          {/* Reasoning */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Explain your reasoning
            </label>
            <textarea
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
              placeholder="Why do you believe this position is correct? Your vote weight increases with quality reasoning..."
              rows={3}
              className="w-full bg-black/40 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-colors resize-none"
            />
            <div className="text-xs text-gray-500 mt-1">
              {reasoning.length}/50 characters minimum
            </div>
          </div>

          {/* Error Message */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm flex items-center gap-2"
              >
                <AlertCircle className="w-4 h-4" />
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submit Button */}
          <button
            onClick={handleSubmitVote}
            disabled={isSubmitting || !selectedPosition || !canVote}
            className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Submitting Vote...
              </>
            ) : !canVote ? (
              <>
                <Ban className="w-5 h-5" />
                Voting Not Available
              </>
            ) : (
              <>
                <Vote className="w-5 h-5" />
                Cast Your Vote
              </>
            )}
          </button>
        </div>
      )}

      {/* Voting Ended */}
      {!isVotingActive && challenge.status !== "voting" && (
        <div className={`rounded-xl p-4 flex items-center gap-3 ${
          challenge.status === "resolved_ai_win"
            ? "bg-green-500/10 border border-green-500/30"
            : "bg-red-500/10 border border-red-500/30"
        }`}>
          <Trophy className={`w-6 h-6 ${
            challenge.status === "resolved_ai_win" ? "text-green-400" : "text-red-400"
          }`} />
          <div>
            <p className={`font-medium ${
              challenge.status === "resolved_ai_win" ? "text-green-400" : "text-red-400"
            }`}>
              {challenge.status === "resolved_ai_win"
                ? "AI Verdict Upheld!"
                : "Challenger Won!"}
            </p>
            <p className="text-sm text-gray-400">
              {challenge.status === "resolved_ai_win"
                ? `The community agreed with Aletheia. ${challenge.stake_amount} SOL added to treasury.`
                : `The challenger was right and received ${challenge.stake_amount * 2} SOL.`}
            </p>
          </div>
        </div>
      )}
    </motion.div>
  );
}
