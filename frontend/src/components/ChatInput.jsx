import React, { useState } from "react";

export default function ChatInput({ onSend, allowWebSearch, onToggleWebSearch, disabled }) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim() || disabled) return;
    onSend(prompt);
    setPrompt("");
  };

  return (
    <form className="input-form" onSubmit={handleSubmit}>
      <button
        type="button"
        className={`btn-toggle-web ${allowWebSearch ? "active" : ""}`}
        onClick={onToggleWebSearch}
        title={allowWebSearch ? "Web Search Enabled (Tavily)" : "Web Search Disabled (Offline API)"}
      >
        🌐 Web Search: {allowWebSearch ? "ON" : "OFF"}
      </button>

      <input
        type="text"
        className="chat-input"
        placeholder="Type fridge ingredients (e.g., 3 eggs, onion, soy sauce, no butter)..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        disabled={disabled}
      />

      <button type="submit" className="btn-send" disabled={disabled || !prompt.trim()}>
        Send
      </button>
    </form>
  );
}
