"use client";

import { FC, useState } from "react";
import { useWallet } from "./SolanaWalletProvider";
import { Wallet, LogOut, Copy, Check, Loader2 } from "lucide-react";

interface WalletConnectButtonProps {
  className?: string;
}

export const WalletConnectButton: FC<WalletConnectButtonProps> = ({
  className = "",
}) => {
  const { publicKey, connected, connecting, connect, disconnect } = useWallet();
  const [copied, setCopied] = useState(false);

  const copyAddress = async () => {
    if (publicKey) {
      await navigator.clipboard.writeText(publicKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const shortAddress = publicKey
    ? `${publicKey.slice(0, 4)}...${publicKey.slice(-4)}`
    : "";

  if (!connected) {
    return (
      <div className={className}>
        <button
          onClick={connect}
          disabled={connecting}
          className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white rounded-xl px-4 py-2 text-sm font-semibold transition-all disabled:opacity-50"
        >
          {connecting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Connecting...
            </>
          ) : (
            <>
              <Wallet className="w-4 h-4" />
              Connect Wallet
            </>
          )}
        </button>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Wallet address with copy */}
      <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-2">
        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
        <span className="text-sm text-green-400 font-mono">{shortAddress}</span>
        <button
          onClick={copyAddress}
          className="text-gray-400 hover:text-white transition-colors p-1"
          title="Copy address"
        >
          {copied ? (
            <Check className="w-3 h-3 text-green-400" />
          ) : (
            <Copy className="w-3 h-3" />
          )}
        </button>
      </div>

      {/* Disconnect button */}
      <button
        onClick={disconnect}
        className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
        title="Disconnect wallet"
      >
        <LogOut className="w-4 h-4" />
      </button>
    </div>
  );
};

// Hook to get wallet info
export function useWalletInfo() {
  const { publicKey, connected, connecting } = useWallet();

  return {
    address: publicKey || null,
    shortAddress: publicKey
      ? `${publicKey.slice(0, 4)}...${publicKey.slice(-4)}`
      : null,
    connected,
    connecting,
  };
}

export default WalletConnectButton;
