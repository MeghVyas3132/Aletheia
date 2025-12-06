"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Swords,
  Clock,
  Users,
  ChevronRight,
  Trophy,
  Shield,
  User,
  AlertCircle,
  Filter,
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

interface ActiveChallengesListProps {
  apiBaseUrl: string;
  onSelectChallenge: (challenge: Challenge) => void;
}

export default function ActiveChallengesList({
  apiBaseUrl,
  onSelectChallenge,
}: ActiveChallengesListProps) {
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "voting" | "resolved">("all");

  useEffect(() => {
    const fetchChallenges = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`${apiBaseUrl}/challenges/active`);
        if (response.ok) {
          const data = await response.json();
          setChallenges(data.challenges || []);
        } else {
          setError("Failed to load challenges");
        }
      } catch (err: any) {
        setError(err.message || "Failed to load challenges");
      } finally {
        setIsLoading(false);
      }
    };

    fetchChallenges();
    // Refresh every 30 seconds
    const interval = setInterval(fetchChallenges, 30000);
    return () => clearInterval(interval);
  }, [apiBaseUrl]);

  const filteredChallenges = challenges.filter((c) => {
    if (filter === "all") return true;
    if (filter === "voting") return c.status === "voting";
    if (filter === "resolved") return c.status.startsWith("resolved");
    return true;
  });

  const getTimeRemaining = (deadline: string) => {
    const diff = new Date(deadline).getTime() - new Date().getTime();
    if (diff <= 0) return "Ended";
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}m`;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "voting":
        return (
          <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded-full text-xs font-medium flex items-center gap-1">
            <Users className="w-3 h-3" />
            Voting
          </span>
        );
      case "pending":
        return (
          <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded-full text-xs font-medium flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Pending
          </span>
        );
      case "resolved_ai_win":
        return (
          <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium flex items-center gap-1">
            <Shield className="w-3 h-3" />
            AI Won
          </span>
        );
      case "resolved_user_win":
        return (
          <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded-full text-xs font-medium flex items-center gap-1">
            <User className="w-3 h-3" />
            Challenger Won
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 bg-gray-500/20 text-gray-400 rounded-full text-xs font-medium">
            {status}
          </span>
        );
    }
  };

  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-red-950/20 to-orange-950/20 border border-red-500/30 rounded-2xl p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-red-500 border-t-transparent" />
          <span className="ml-3 text-red-400">Loading challenges...</span>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-red-950/20 to-orange-950/20 border border-red-500/30 rounded-2xl overflow-hidden"
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-red-600/20 to-orange-600/20 p-6 border-b border-red-500/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <Swords className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-red-400">Active Challenges</h2>
              <p className="text-sm text-gray-400">
                {challenges.length} challenge{challenges.length !== 1 ? "s" : ""} in progress
              </p>
            </div>
          </div>
          
          {/* Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as typeof filter)}
              className="bg-black/40 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-white"
            >
              <option value="all">All</option>
              <option value="voting">Voting</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>
      </div>

      {/* Challenges List */}
      <div className="p-4">
        {error && (
          <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm flex items-center gap-2 mb-4">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {filteredChallenges.length === 0 ? (
          <div className="text-center py-12">
            <Swords className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No active challenges</p>
            <p className="text-sm text-gray-600">
              {filter !== "all"
                ? "Try a different filter"
                : "Be the first to challenge a verdict!"}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {filteredChallenges.map((challenge, index) => {
                const totalVotes = challenge.votes_for_ai + challenge.votes_for_challenger;
                const aiPercentage = totalVotes > 0
                  ? (challenge.votes_for_ai / totalVotes) * 100
                  : 50;

                return (
                  <motion.div
                    key={challenge.challenge_id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => onSelectChallenge(challenge)}
                    className="bg-black/30 rounded-xl p-4 cursor-pointer hover:bg-black/40 transition-colors group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          {getStatusBadge(challenge.status)}
                          <span className="text-xs text-gray-500">
                            ID: {challenge.challenge_id.slice(0, 8)}...
                          </span>
                        </div>
                        <p className="text-white line-clamp-2">{challenge.explanation}</p>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-500 group-hover:text-red-400 transition-colors ml-2 flex-shrink-0" />
                    </div>

                    {/* Vote Progress Mini */}
                    <div className="mb-3">
                      <div className="h-2 bg-gray-800 rounded-full overflow-hidden flex">
                        <div
                          className="bg-green-500 h-full transition-all"
                          style={{ width: `${aiPercentage}%` }}
                        />
                        <div
                          className="bg-red-500 h-full transition-all"
                          style={{ width: `${100 - aiPercentage}%` }}
                        />
                      </div>
                    </div>

                    {/* Footer Stats */}
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1">
                          <Trophy className="w-3 h-3 text-yellow-400" />
                          <span>{challenge.stake_amount} SOL</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          <span>{totalVotes} votes</span>
                        </div>
                      </div>
                      {challenge.status === "voting" && (
                        <div className="flex items-center gap-1 text-purple-400">
                          <Clock className="w-3 h-3" />
                          <span>{getTimeRemaining(challenge.voting_deadline)}</span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </motion.div>
  );
}
