import React, { useState } from "react";
import { SendHorizonal, Globe } from "lucide-react";
import VisionUploader from "./VisionUploader";

export default function ChatInput({ onSend, allowWebSearch, onToggleWebSearch, disabled }) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim() || disabled) return;
    onSend(prompt);
    setPrompt("");
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className="input-bar" onSubmit={handleSubmit}>
      <VisionUploader onIngredientsDetected={(ingredients) => onSend(`Fridge photo detected: ${ingredients}`)} />

      <button
        type="button"
        className={`btn-web-toggle ${allowWebSearch ? "active" : ""}`}
        onClick={onToggleWebSearch}
        title={allowWebSearch ? "Web Search ON" : "Web Search OFF"}
      >
        <Globe size={13} />
        <span>Web {allowWebSearch ? "ON" : "OFF"}</span>
      </button>

      <input
        type="text"
        className="input-field"
        placeholder="Enter ingredients or recipe request..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKey}
        disabled={disabled}
      />

      <button type="submit" className="btn-send" disabled={disabled || !prompt.trim()}>
        <SendHorizonal size={14} />
        <span>Send</span>
      </button>
    </form>
  );
}
