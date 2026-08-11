import React, { useState } from "react";
import MessageBubble from "./components/MessageBubble";
import ChatInput from "./components/ChatInput";
import DietarySelector from "./components/DietarySelector";
import AuthModal from "./components/AuthModal";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [allowWebSearch, setAllowWebSearch] = useState(true);
  const [dietaryProfile, setDietaryProfile] = useState("Standard");
  const [threadId] = useState(() => "session_" + Math.random().toString(36).substr(2, 9));
  
  // Auth State
  const [user, setUser] = useState(null);
  const [token, setToken] = useState("");
  const [isAuthOpen, setIsAuthOpen] = useState(false);

  const handleAuthSuccess = (userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
    if (userData.dietary_profile) {
      setDietaryProfile(userData.dietary_profile);
    }
  };

  const handleSend = async (promptText) => {
    const userMsg = { role: "user", content: promptText };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const headers = { "Content-Type": "application/json" };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers,
        body: JSON.stringify({
          prompt: promptText,
          allow_web_search: allowWebSearch,
          dietary_profile: dietaryProfile,
          thread_id: threadId,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Error connecting to ChefBot engine.");
      }

      const botMsg = { role: "assistant", content: data.recipe };
      setMessages((prev) => [...prev, botMsg]);
    } catch (error) {
      const errorMsg = {
        role: "assistant",
        content: `⚠️ ChefBot Error: ${error.message}`,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-brand">
          <span>👨‍🍳</span>
          <h1>ChefBot Enterprise</h1>
          <span className="badge-langgraph">LangGraph Engine</span>
          <span className="badge-security">7-Pillar Security</span>
        </div>

        <div className="header-actions">
          {user ? (
            <span style={{ fontSize: "0.85rem", color: "#34d399", fontWeight: "600" }}>
              👤 {user.username}
            </span>
          ) : (
            <button className="btn-auth" onClick={() => setIsAuthOpen(true)}>
              Sign In / Register
            </button>
          )}
        </div>
      </header>

      {/* Dietary Profile Selector */}
      <DietarySelector selected={dietaryProfile} onSelect={setDietaryProfile} />

      {/* Chat Messages */}
      <main className="chat-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <span>🥗</span>
            <h2>Welcome to ChefBot Enterprise</h2>
            <p>
              Powered by <strong>LangGraph</strong>, persistent session memory, and <strong>7-Pillar Enterprise Security</strong>.
            </p>
            <p style={{ fontSize: "0.85rem", opacity: 0.7 }}>
              Type your fridge ingredients below to generate a custom step-by-step recipe!
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <MessageBubble key={index} role={msg.role} content={msg.content} />
          ))
        )}

        {loading && (
          <div className="message-row bot">
            <div className="bubble bot" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span className="spinner">🍳</span> ChefBot is thinking via LangGraph...
            </div>
          </div>
        )}
      </main>

      {/* Chat Input */}
      <ChatInput
        onSend={handleSend}
        allowWebSearch={allowWebSearch}
        onToggleWebSearch={() => setAllowWebSearch(!allowWebSearch)}
        disabled={loading}
      />

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />
    </div>
  );
}
