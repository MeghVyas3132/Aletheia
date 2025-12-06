"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, FC } from "react";

/**
 * Mock Wallet Provider for Demo Mode
 * 
 * This is a simplified wallet implementation for MVP/demo purposes.
 * In production, replace with full Solana wallet adapter:
 * - @solana/wallet-adapter-react
 * - @solana/wallet-adapter-wallets
 * - @solana/web3.js
 */

interface WalletContextType {
  connected: boolean;
  publicKey: string | null;
  connecting: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  signMessage: (message: string) => Promise<string>;
}

const WalletContext = createContext<WalletContextType | null>(null);

export function useWallet() {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error("useWallet must be used within a WalletProvider");
  }
  return context;
}

// Demo wallet addresses (for testing)
const DEMO_WALLETS = [
  "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
  "Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr",
  "3KEQxQS2Z7WPsjL5SYdJjHEXqeJEDPMGa2wKqzK4PWLD",
  "DRpbCBMxVnDK7maPM5tGv6MvB3v1sRMC86PZ8okm21hy",
];

interface SolanaWalletProviderProps {
  children: ReactNode;
}

export const SolanaWalletProvider: FC<SolanaWalletProviderProps> = ({
  children,
}) => {
  const [connected, setConnected] = useState(false);
  const [publicKey, setPublicKey] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  // Check for saved wallet on mount
  useEffect(() => {
    const savedWallet = localStorage.getItem("aletheia_demo_wallet");
    if (savedWallet) {
      setPublicKey(savedWallet);
      setConnected(true);
    }
  }, []);

  const connect = async () => {
    setConnecting(true);
    
    // Simulate connection delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Generate a random demo wallet
    const wallet = DEMO_WALLETS[Math.floor(Math.random() * DEMO_WALLETS.length)];
    
    setPublicKey(wallet);
    setConnected(true);
    localStorage.setItem("aletheia_demo_wallet", wallet);
    
    setConnecting(false);
  };

  const disconnect = () => {
    setPublicKey(null);
    setConnected(false);
    localStorage.removeItem("aletheia_demo_wallet");
  };

  const signMessage = async (message: string): Promise<string> => {
    // Mock signature for demo
    return `demo_signature_${message.substring(0, 10)}_${Date.now()}`;
  };

  return (
    <WalletContext.Provider
      value={{
        connected,
        publicKey,
        connecting,
        connect,
        disconnect,
        signMessage,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
};

export default SolanaWalletProvider;
