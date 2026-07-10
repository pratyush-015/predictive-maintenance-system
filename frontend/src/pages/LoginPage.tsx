import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Activity, ArrowRight, Loader2 } from "lucide-react";
import { useAuthStore } from "../store/auth";
import { PulseStrip } from "../components/dashboard/PulseStrip";

const DEMO_WAVE = [22, 24, 21, 26, 30, 28, 24, 22, 20, 23, 27, 65, 78, 88, 92, 85, 70, 45, 30, 24, 22, 25, 23, 21];

export function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login, register } = useAuthStore();
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, email, password);
      }
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-sm"
      >
        <div className="mb-8 text-center">
          <div className="relative mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-signal/10">
            <Activity size={24} className="text-signal" />
            <span className="absolute inset-0 rounded-xl border border-signal/30 animate-pulse-slow" />
          </div>
          <h1 className="font-display text-2xl font-semibold">Pulse</h1>
          <p className="mt-1 text-sm text-mute">Predictive maintenance for your machines</p>
        </div>

        <div className="mb-6 rounded-xl border border-hairline bg-elevated/60 px-5 py-4">
          <PulseStrip values={DEMO_WAVE} height={48} />
          <p className="mt-2 text-center text-[11px] font-mono text-dim">
            live anomaly detected — cpu overload flagged in 340ms
          </p>
        </div>

        <div className="mb-5 flex rounded-lg border border-hairline bg-elevated p-1">
          <button
            onClick={() => setMode("login")}
            className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-colors ${
              mode === "login" ? "bg-signal text-void" : "text-mute hover:text-ink"
            }`}
          >
            Sign in
          </button>
          <button
            onClick={() => setMode("register")}
            className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-colors ${
              mode === "register" ? "bg-signal text-void" : "text-mute hover:text-ink"
            }`}
          >
            Create account
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-mute">Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              className="w-full rounded-lg border border-hairline bg-elevated px-3.5 py-2.5 text-sm text-ink outline-none focus:border-signal"
              placeholder="admin"
              autoComplete="username"
            />
          </div>

          {mode === "register" && (
            <div>
              <label className="mb-1.5 block text-xs font-medium text-mute">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full rounded-lg border border-hairline bg-elevated px-3.5 py-2.5 text-sm text-ink outline-none focus:border-signal"
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-xs font-medium text-mute">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full rounded-lg border border-hairline bg-elevated px-3.5 py-2.5 text-sm text-ink outline-none focus:border-signal"
              placeholder="••••••••"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </div>

          {error && (
            <div className="rounded-lg border border-crit/30 bg-crit/10 px-3 py-2 text-xs text-crit">{error}</div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-signal py-2.5 text-sm font-medium text-void transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <>
                {mode === "login" ? "Sign in" : "Create account"}
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </form>

        {mode === "register" && (
          <p className="mt-4 text-center text-[11px] text-dim">
            First account created becomes an admin automatically.
          </p>
        )}
      </motion.div>
    </div>
  );
}
