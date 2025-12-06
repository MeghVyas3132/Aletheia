"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Vault,
  TrendingUp,
  TrendingDown,
  Trophy,
  Users,
  Shield,
  ArrowUpRight,
  ArrowDownRight,
  History,
  Award,
  Coins,
  BarChart3,
} from "lucide-react";

interface TreasuryStats {
  total_balance: number;
  reserved_for_payouts: number;
  available_balance: number;
  total_challenges: number;
  ai_wins: number;
  challenger_wins: number;
  total_staked_all_time: number;
  total_paid_out: number;
}

interface ChallengerStats {
  wallet: string;
  challenges: number;
  wins: number;
  total_won: number;
}

interface VoterStats {
  wallet: string;
  votes: number;
  accuracy: number;
  reputation: number;
}

interface TreasuryDashboardProps {
  apiBaseUrl: string;
}

export default function TreasuryDashboard({ apiBaseUrl }: TreasuryDashboardProps) {
  const [stats, setStats] = useState<TreasuryStats | null>(null);
  const [topChallengers, setTopChallengers] = useState<ChallengerStats[]>([]);
  const [topVoters, setTopVoters] = useState<VoterStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "challengers" | "voters">("overview");

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        
        // Fetch treasury stats
        const treasuryRes = await fetch(`${apiBaseUrl}/treasury`);
        if (treasuryRes.ok) {
          const treasuryData = await treasuryRes.json();
          setStats(treasuryData);
        }

        // Fetch leaderboards
        const challengersRes = await fetch(`${apiBaseUrl}/leaderboard/challengers`);
        if (challengersRes.ok) {
          const challengersData = await challengersRes.json();
          setTopChallengers(challengersData.challengers || []);
        }

        const votersRes = await fetch(`${apiBaseUrl}/leaderboard/voters`);
        if (votersRes.ok) {
          const votersData = await votersRes.json();
          setTopVoters(votersData.voters || []);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load treasury data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [apiBaseUrl]);

  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-yellow-950/20 to-amber-950/20 border border-yellow-500/30 rounded-2xl p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-yellow-500 border-t-transparent" />
          <span className="ml-3 text-yellow-400">Loading treasury data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-8 text-center">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  const aiWinRate = stats && stats.total_challenges > 0
    ? ((stats.ai_wins / stats.total_challenges) * 100).toFixed(1)
    : "99.99";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-yellow-950/20 to-amber-950/20 border border-yellow-500/30 rounded-2xl overflow-hidden"
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-yellow-600/20 to-amber-600/20 p-6 border-b border-yellow-500/30">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-yellow-500/20 rounded-lg">
            <Vault className="w-7 h-7 text-yellow-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-yellow-400">DOW Treasury</h2>
            <p className="text-sm text-gray-400">Decentralized Oracle of Wisdom Reserve</p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-800">
        {[
          { id: "overview", label: "Overview", icon: BarChart3 },
          { id: "challengers", label: "Top Challengers", icon: Trophy },
          { id: "voters", label: "Top Voters", icon: Users },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex-1 flex items-center justify-center gap-2 py-3 transition-colors ${
              activeTab === tab.id
                ? "bg-yellow-500/10 text-yellow-400 border-b-2 border-yellow-500"
                : "text-gray-400 hover:text-gray-300 hover:bg-gray-800/50"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-6">
        {/* Overview Tab */}
        {activeTab === "overview" && stats && (
          <div className="space-y-6">
            {/* Main Balance */}
            <div className="text-center py-6">
              <div className="text-sm text-gray-400 mb-2">Total Treasury Balance</div>
              <div className="text-5xl font-bold bg-gradient-to-r from-yellow-400 to-amber-300 bg-clip-text text-transparent">
                {stats.total_balance.toLocaleString()} SOL
              </div>
              <div className="text-sm text-gray-500 mt-2">
                Available: {stats.available_balance.toLocaleString()} SOL 
                <span className="mx-2">•</span>
                Reserved: {stats.reserved_for_payouts.toLocaleString()} SOL
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-black/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-gray-400 mb-2">
                  <History className="w-4 h-4" />
                  <span className="text-sm">Total Challenges</span>
                </div>
                <div className="text-2xl font-bold text-white">{stats.total_challenges}</div>
              </div>
              <div className="bg-black/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-gray-400 mb-2">
                  <Shield className="w-4 h-4 text-green-400" />
                  <span className="text-sm">AI Wins</span>
                </div>
                <div className="text-2xl font-bold text-green-400">{stats.ai_wins}</div>
              </div>
              <div className="bg-black/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-gray-400 mb-2">
                  <Users className="w-4 h-4 text-red-400" />
                  <span className="text-sm">Challenger Wins</span>
                </div>
                <div className="text-2xl font-bold text-red-400">{stats.challenger_wins}</div>
              </div>
              <div className="bg-black/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-gray-400 mb-2">
                  <TrendingUp className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm">AI Win Rate</span>
                </div>
                <div className="text-2xl font-bold text-yellow-400">{aiWinRate}%</div>
              </div>
            </div>

            {/* Financial Flow */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <ArrowUpRight className="w-5 h-5 text-green-400" />
                  <span className="text-green-400 font-medium">Total Staked</span>
                </div>
                <div className="text-3xl font-bold text-green-400">
                  {stats.total_staked_all_time.toLocaleString()} SOL
                </div>
                <div className="text-sm text-gray-500 mt-1">All-time stakes from challenges</div>
              </div>
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <ArrowDownRight className="w-5 h-5 text-red-400" />
                  <span className="text-red-400 font-medium">Total Paid Out</span>
                </div>
                <div className="text-3xl font-bold text-red-400">
                  {stats.total_paid_out.toLocaleString()} SOL
                </div>
                <div className="text-sm text-gray-500 mt-1">Rewards to successful challengers</div>
              </div>
            </div>
          </div>
        )}

        {/* Challengers Tab */}
        {activeTab === "challengers" && (
          <div className="space-y-4">
            <div className="text-sm text-gray-400 mb-4">
              Top challengers who have successfully disputed AI verdicts
            </div>
            {topChallengers.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No challengers yet. Be the first to challenge!
              </div>
            ) : (
              topChallengers.map((challenger, index) => (
                <motion.div
                  key={challenger.wallet}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="bg-black/30 rounded-xl p-4 flex items-center gap-4"
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                    index === 0 ? "bg-yellow-500/20 text-yellow-400" :
                    index === 1 ? "bg-gray-400/20 text-gray-300" :
                    index === 2 ? "bg-amber-600/20 text-amber-500" :
                    "bg-gray-700/20 text-gray-400"
                  }`}>
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-white">
                      {challenger.wallet.slice(0, 8)}...{challenger.wallet.slice(-6)}
                    </div>
                    <div className="text-sm text-gray-500">
                      {challenger.challenges} challenges • {challenger.wins} wins
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1 text-yellow-400 font-bold">
                      <Coins className="w-4 h-4" />
                      {challenger.total_won} SOL
                    </div>
                    <div className="text-xs text-gray-500">won</div>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}

        {/* Voters Tab */}
        {activeTab === "voters" && (
          <div className="space-y-4">
            <div className="text-sm text-gray-400 mb-4">
              Most accurate voters who help maintain truth in the system
            </div>
            {topVoters.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No voters yet. Start voting on challenges!
              </div>
            ) : (
              topVoters.map((voter, index) => (
                <motion.div
                  key={voter.wallet}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="bg-black/30 rounded-xl p-4 flex items-center gap-4"
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                    index === 0 ? "bg-purple-500/20 text-purple-400" :
                    index === 1 ? "bg-gray-400/20 text-gray-300" :
                    index === 2 ? "bg-amber-600/20 text-amber-500" :
                    "bg-gray-700/20 text-gray-400"
                  }`}>
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-white">
                      {voter.wallet.slice(0, 8)}...{voter.wallet.slice(-6)}
                    </div>
                    <div className="text-sm text-gray-500">
                      {voter.votes} votes
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1 text-purple-400 font-bold">
                      <Award className="w-4 h-4" />
                      {(voter.accuracy * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500">accuracy</div>
                  </div>
                  <div className="text-right">
                    <div className="text-yellow-400 font-bold">
                      {voter.reputation.toFixed(0)}
                    </div>
                    <div className="text-xs text-gray-500">reputation</div>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
