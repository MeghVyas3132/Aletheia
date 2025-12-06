"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Swords, 
  AlertTriangle, 
  Link2, 
  Plus, 
  Trash2, 
  Loader2,
  Shield,
  Coins
} from "lucide-react";

interface ChallengeFormProps {
  verdictId: string;
  claim: string;
  verdict: string;
  confidence: number;
  onSubmit: (challenge: ChallengeData) => Promise<void>;
  onCancel: () => void;
}

interface ChallengeData {
  verdict_id: string;
  challenger_wallet: string;
  stake_amount: number;
  evidence_links: string[];
  explanation: string;
}

export default function ChallengeForm({
  verdictId,
  claim,
  verdict,
  confidence,
  onSubmit,
  onCancel,
}: ChallengeFormProps) {
  const [walletAddress, setWalletAddress] = useState("");
  const [stakeAmount, setStakeAmount] = useState(10);
  const [evidenceLinks, setEvidenceLinks] = useState<string[]>(["", ""]);
  const [explanation, setExplanation] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addEvidenceLink = () => {
    setEvidenceLinks([...evidenceLinks, ""]);
  };

  const removeEvidenceLink = (index: number) => {
    if (evidenceLinks.length > 2) {
      setEvidenceLinks(evidenceLinks.filter((_, i) => i !== index));
    }
  };

  const updateEvidenceLink = (index: number, value: string) => {
    const updated = [...evidenceLinks];
    updated[index] = value;
    setEvidenceLinks(updated);
  };

  const validateForm = (): boolean => {
    if (!walletAddress.trim()) {
      setError("Please enter your wallet address");
      return false;
    }
    if (stakeAmount < 1 || stakeAmount > 100) {
      setError("Stake must be between 1 and 100 SOL");
      return false;
    }
    const validLinks = evidenceLinks.filter((l) => l.trim().length > 0);
    if (validLinks.length < 2) {
      setError("Please provide at least 2 evidence links");
      return false;
    }
    if (explanation.length < 100) {
      setError(`Explanation must be at least 100 characters (${explanation.length}/100)`);
      return false;
    }
    setError(null);
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit({
        verdict_id: verdictId,
        challenger_wallet: walletAddress,
        stake_amount: stakeAmount,
        evidence_links: evidenceLinks.filter((l) => l.trim().length > 0),
        explanation,
      });
    } catch (err: any) {
      setError(err.message || "Failed to submit challenge");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="bg-gradient-to-br from-red-950/30 to-orange-950/30 border border-red-500/30 rounded-2xl p-6 mt-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-red-500/20 rounded-lg">
          <Swords className="w-6 h-6 text-red-400" />
        </div>
        <div>
          <h3 className="text-xl font-bold text-red-400">Challenge This Verdict</h3>
          <p className="text-sm text-gray-400">Stake SOL to dispute the AI's decision</p>
        </div>
      </div>

      {/* Original Verdict Summary */}
      <div className="bg-black/30 rounded-xl p-4 mb-6">
        <div className="text-sm text-gray-400 mb-1">Challenging verdict:</div>
        <div className="text-white font-medium mb-2">{claim}</div>
        <div className="flex items-center gap-4">
          <span className={`px-3 py-1 rounded-full text-sm font-bold ${
            verdict === "TRUE" ? "bg-green-500/20 text-green-400" :
            verdict === "FALSE" ? "bg-red-500/20 text-red-400" :
            "bg-yellow-500/20 text-yellow-400"
          }`}>
            AI says: {verdict}
          </span>
          <span className="text-sm text-gray-400">
            Confidence: {(confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Form Fields */}
      <div className="space-y-5">
        {/* Wallet Address */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Your Wallet Address
          </label>
          <input
            type="text"
            value={walletAddress}
            onChange={(e) => setWalletAddress(e.target.value)}
            placeholder="Enter your Solana wallet address"
            className="w-full bg-black/40 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-colors"
          />
        </div>

        {/* Stake Amount */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <div className="flex items-center gap-2">
              <Coins className="w-4 h-4" />
              Stake Amount (SOL)
            </div>
          </label>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="1"
              max="100"
              value={stakeAmount}
              onChange={(e) => setStakeAmount(Number(e.target.value))}
              className="flex-1 accent-red-500"
            />
            <div className="bg-black/40 border border-gray-600 rounded-lg px-4 py-2 min-w-[100px] text-center">
              <span className="text-2xl font-bold text-white">{stakeAmount}</span>
              <span className="text-gray-400 ml-1">SOL</span>
            </div>
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Min: 1 SOL</span>
            <span>Max: 100 SOL</span>
          </div>
        </div>

        {/* Evidence Links */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <div className="flex items-center gap-2">
              <Link2 className="w-4 h-4" />
              Evidence Links (min 2 required)
            </div>
          </label>
          <div className="space-y-2">
            {evidenceLinks.map((link, index) => (
              <div key={index} className="flex items-center gap-2">
                <input
                  type="url"
                  value={link}
                  onChange={(e) => updateEvidenceLink(index, e.target.value)}
                  placeholder={`https://source${index + 1}.com/evidence`}
                  className="flex-1 bg-black/40 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-colors"
                />
                {evidenceLinks.length > 2 && (
                  <button
                    onClick={() => removeEvidenceLink(index)}
                    className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
          <button
            onClick={addEvidenceLink}
            className="mt-2 flex items-center gap-1 text-sm text-red-400 hover:text-red-300 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add another link
          </button>
        </div>

        {/* Explanation */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Explain why the verdict is wrong
          </label>
          <textarea
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Provide a detailed explanation of why you believe the AI's verdict is incorrect. Include specific facts, data, or reasoning that contradicts the verdict..."
            rows={5}
            className="w-full bg-black/40 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-colors resize-none"
          />
          <div className="flex justify-between text-xs mt-1">
            <span className={explanation.length >= 100 ? "text-green-400" : "text-gray-500"}>
              {explanation.length}/100 characters minimum
            </span>
          </div>
        </div>

        {/* Warning */}
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 flex gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="text-yellow-400 font-medium mb-1">Important Notice</p>
            <p className="text-gray-300">
              If you lose, your <strong>{stakeAmount} SOL</strong> stake will be forfeited. 
              If you win, you'll receive <strong>{stakeAmount * 2} SOL</strong> (2x your stake).
              The community will vote to determine the outcome.
            </p>
          </div>
        </div>

        {/* Error Message */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={onCancel}
            className="flex-1 px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="flex-1 px-6 py-3 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Swords className="w-5 h-5" />
                Submit Challenge ({stakeAmount} SOL)
              </>
            )}
          </button>
        </div>
      </div>
    </motion.div>
  );
}
