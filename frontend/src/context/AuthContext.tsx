import { createContext, useContext, useState, ReactNode } from "react";
import { api } from "../lib/api";

interface AuthState {
  token: string | null;
  email: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("relay_token"));
  const [email, setEmail] = useState<string | null>(localStorage.getItem("relay_email"));

  async function login(emailInput: string, password: string) {
    const data = await api.login(emailInput, password);
    setToken(data.access_token);
    setEmail(emailInput);
    localStorage.setItem("relay_token", data.access_token);
    localStorage.setItem("relay_email", emailInput);
  }

  async function register(emailInput: string, password: string) {
    const data = await api.register(emailInput, password);
    setToken(data.access_token);
    setEmail(emailInput);
    localStorage.setItem("relay_token", data.access_token);
    localStorage.setItem("relay_email", emailInput);
  }

  function logout() {
    setToken(null);
    setEmail(null);
    localStorage.removeItem("relay_token");
    localStorage.removeItem("relay_email");
  }

  return <AuthContext.Provider value={{ token, email, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
