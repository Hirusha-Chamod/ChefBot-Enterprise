import React, { useState } from "react";
import { ChefHat, Loader2 } from "lucide-react";

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const endpoint = isLogin
      ? "http://localhost:8000/api/auth/login"
      : "http://localhost:8000/api/auth/register";
    const payload = isLogin ? { username, password } : { username, email, password };
    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Authentication failed.");
      onAuthSuccess(data.user, data.access_token);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <ChefHat size={20} color="var(--accent-primary)" />
          <h2>{isLogin ? "Welcome back" : <span>Create account</span>}</h2>
        </div>

        {error && (
          <div style={{ color: "var(--accent-red)", fontSize: "0.78rem", padding: "0.4rem 0.6rem", background: "rgba(239, 68, 68, 0.08)", borderRadius: "4px", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <div className="form-group">
            <label>Username</label>
            <input type="text" required value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. chef_master" />
          </div>
          {!isLogin && (
            <div className="form-group">
              <label>Email</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="chef@enterprise.com" />
            </div>
          )}
          <div className="form-group">
            <label>Password</label>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </div>
          <button type="submit" className="btn-auth-submit" disabled={loading}>
            {loading ? (
              <span style={{ display: "flex", alignItems: "center", gap: "0.4rem", justifyContent: "center" }}>
                <Loader2 size={14} className="spin" /> Processing...
              </span>
            ) : isLogin ? "Sign In" : "Create Account"}
          </button>
        </form>

        <div className="auth-switch">
          {isLogin ? "No account?" : "Already registered?"}{" "}
          <button type="button" onClick={() => { setIsLogin(!isLogin); setError(""); }}>
            {isLogin ? "Sign Up" : "Sign In"}
          </button>
        </div>
      </div>
    </div>
  );
}
