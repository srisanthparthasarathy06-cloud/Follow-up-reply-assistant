import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("demo@relay.ai");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
      navigate("/");
    } catch (err: any) {
      setError(
        `${err.message}. Is the backend running at ${api.base}? ${
          mode === "login" ? "If you haven't yet, run python seed.py in backend/ first." : ""
        }`
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-bg">
      <div className="card w-[380px] p-9">
        <div className="flex items-center gap-2.5 mb-6">
          <div className="w-8 h-8 rounded-[9px] bg-gradient-to-br from-accent to-[#8b8ef7] flex items-center justify-center font-display font-bold text-white">
            R
          </div>
          <div>
            <div className="font-display font-semibold text-[16.5px]">Relay</div>
            <div className="text-[11px] text-textFaint">AI email assistant</div>
          </div>
        </div>

        <div className="flex gap-1 mb-6 bg-surface2 rounded-lg p-1">
          <button
            className={`flex-1 py-1.5 rounded-md text-[13px] font-medium ${
              mode === "login" ? "bg-accent text-white" : "text-textDim"
            }`}
            onClick={() => setMode("login")}
            type="button"
          >
            Sign in
          </button>
          <button
            className={`flex-1 py-1.5 rounded-md text-[13px] font-medium ${
              mode === "register" ? "bg-accent text-white" : "text-textDim"
            }`}
            onClick={() => setMode("register")}
            type="button"
          >
            Create account
          </button>
        </div>

        {error && (
          <div className="bg-danger/10 text-danger text-[12.5px] px-3 py-2.5 rounded-lg mb-3.5">{error}</div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-3.5">
            <label className="block text-[11.5px] text-textFaint uppercase tracking-wide mb-1.5">Email</label>
            <input
              className="w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-[13.5px] text-text outline-none focus:border-accent"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-[11.5px] text-textFaint uppercase tracking-wide mb-1.5">Password</label>
            <input
              className="w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-[13.5px] text-text outline-none focus:border-accent"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
              minLength={4}
            />
          </div>
          <button className="btn btn-primary w-full justify-center" disabled={loading} type="submit">
            {loading ? <span className="spinner" /> : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <div className="text-[11px] text-textFaint text-center mt-4 leading-relaxed">
          Demo login is pre-filled. First time? Run <span className="font-mono">python seed.py</span> in your{" "}
          <span className="font-mono">backend/</span> folder, or use "Create account" to register your own.
        </div>
      </div>
    </div>
  );
}
