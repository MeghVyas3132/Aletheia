"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Info, 
  X,
  Loader2
} from "lucide-react";

// Toast types
type ToastType = "success" | "error" | "warning" | "info" | "loading";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextType {
  toasts: Toast[];
  showToast: (toast: Omit<Toast, "id">) => string;
  hideToast: (id: string) => void;
  showSuccess: (title: string, message?: string) => string;
  showError: (title: string, message?: string) => string;
  showWarning: (title: string, message?: string) => string;
  showInfo: (title: string, message?: string) => string;
  showLoading: (title: string, message?: string) => string;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

// Toast provider component
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((toast: Omit<Toast, "id">) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newToast: Toast = { ...toast, id };
    
    setToasts((prev) => [...prev, newToast]);
    
    // Auto-hide after duration (default 5s, loading never auto-hides)
    if (toast.type !== "loading") {
      const duration = toast.duration || 5000;
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
    
    return id;
  }, []);

  const hideToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showSuccess = useCallback((title: string, message?: string) => {
    return showToast({ type: "success", title, message });
  }, [showToast]);

  const showError = useCallback((title: string, message?: string) => {
    return showToast({ type: "error", title, message, duration: 8000 });
  }, [showToast]);

  const showWarning = useCallback((title: string, message?: string) => {
    return showToast({ type: "warning", title, message });
  }, [showToast]);

  const showInfo = useCallback((title: string, message?: string) => {
    return showToast({ type: "info", title, message });
  }, [showToast]);

  const showLoading = useCallback((title: string, message?: string) => {
    return showToast({ type: "loading", title, message });
  }, [showToast]);

  return (
    <ToastContext.Provider
      value={{
        toasts,
        showToast,
        hideToast,
        showSuccess,
        showError,
        showWarning,
        showInfo,
        showLoading,
      }}
    >
      {children}
      <ToastContainer toasts={toasts} onClose={hideToast} />
    </ToastContext.Provider>
  );
}

// Toast container
function ToastContainer({
  toasts,
  onClose,
}: {
  toasts: Toast[];
  onClose: (id: string) => void;
}) {
  return (
    <div className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 max-w-md">
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onClose={() => onClose(toast.id)} />
        ))}
      </AnimatePresence>
    </div>
  );
}

// Individual toast item
function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-400" />,
    error: <XCircle className="w-5 h-5 text-red-400" />,
    warning: <AlertTriangle className="w-5 h-5 text-yellow-400" />,
    info: <Info className="w-5 h-5 text-blue-400" />,
    loading: <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />,
  };

  const backgrounds = {
    success: "bg-green-500/10 border-green-500/30",
    error: "bg-red-500/10 border-red-500/30",
    warning: "bg-yellow-500/10 border-yellow-500/30",
    info: "bg-blue-500/10 border-blue-500/30",
    loading: "bg-purple-500/10 border-purple-500/30",
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 100, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.9 }}
      className={`flex items-start gap-3 p-4 rounded-lg border backdrop-blur-sm ${backgrounds[toast.type]}`}
    >
      <div className="flex-shrink-0 mt-0.5">{icons[toast.type]}</div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-white text-sm">{toast.title}</p>
        {toast.message && (
          <p className="text-xs text-gray-400 mt-1">{toast.message}</p>
        )}
      </div>
      {toast.type !== "loading" && (
        <button
          onClick={onClose}
          className="flex-shrink-0 text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </motion.div>
  );
}

// Utility function to handle API errors
export function handleApiError(error: any, showError: (title: string, message?: string) => void) {
  console.error("API Error:", error);
  
  // Rate limit error
  if (error.status === 429 || error.message?.includes("429") || error.message?.includes("rate")) {
    showError(
      "Rate Limited",
      "Too many requests. Please wait a moment and try again."
    );
    return;
  }
  
  // Network error
  if (error.name === "TypeError" && error.message === "Failed to fetch") {
    showError(
      "Connection Error",
      "Cannot connect to server. Please check your internet connection."
    );
    return;
  }
  
  // Server error
  if (error.status >= 500) {
    showError(
      "Server Error",
      "Something went wrong on our end. Please try again later."
    );
    return;
  }
  
  // Validation error
  if (error.status === 400 || error.status === 422) {
    showError(
      "Validation Error",
      error.detail || error.message || "Please check your input and try again."
    );
    return;
  }
  
  // Auth error
  if (error.status === 401 || error.status === 403) {
    showError(
      "Access Denied",
      "You don't have permission to perform this action."
    );
    return;
  }
  
  // Generic error
  showError(
    "Error",
    error.detail || error.message || "An unexpected error occurred."
  );
}

// API fetch wrapper with error handling
export async function apiFetch<T>(
  url: string,
  options: RequestInit = {},
  showError?: (title: string, message?: string) => void
): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      error.status = response.status;
      throw error;
    }
    
    return await response.json();
  } catch (error: any) {
    if (showError) {
      handleApiError(error, showError);
    }
    throw error;
  }
}

export default ToastProvider;
