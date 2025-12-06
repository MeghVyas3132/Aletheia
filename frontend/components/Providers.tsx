"use client";

import { ReactNode } from "react";
import { ThemeProvider } from "@/components/theme-provider";
import { SolanaWalletProvider } from "@/components/SolanaWalletProvider";
import { ToastProvider } from "@/components/Toast";
import { DemoModeBanner } from "@/components/DemoModeBanner";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const network = process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet";
  
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem
      disableTransitionOnChange
    >
      <SolanaWalletProvider>
        <ToastProvider>
          <DemoModeBanner network={network} />
          <div className="pt-10">{children}</div>
        </ToastProvider>
      </SolanaWalletProvider>
    </ThemeProvider>
  );
}

export default Providers;
