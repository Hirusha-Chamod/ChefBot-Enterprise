import React, { Component } from "react";
import ReactMarkdown from "react-markdown";
import RecipeOptionCards from "./RecipeOptionCards";
import { User, ChefHat } from "lucide-react";

class SafeMarkdown extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(err) { console.error("Markdown error:", err); }
  render() {
    const text = String(this.props.content || "");
    if (this.state.hasError) return <div style={{ whiteSpace: "pre-wrap" }}>{text}</div>;
    return <div className="markdown-content"><ReactMarkdown>{text}</ReactMarkdown></div>;
  }
}

export default function MessageBubble({ role, content, onStartCooking, isStreaming = false }) {
  const isUser = role === "user";
  const safeText = String(content || "");

  return (
    <div className={`message-row ${isUser ? "user" : "bot"}`}>
      <div className={`message-avatar ${isUser ? "user-avatar" : "bot-avatar"}`}>
        {isUser ? <User size={15} /> : <ChefHat size={15} />}
      </div>
      <div className="message-content">
        <span className="message-sender">{isUser ? "You" : "ChefBot"}</span>
        <div className={`bubble ${isUser ? "user" : "bot"}`}>
          {isUser ? (
            <span style={{ whiteSpace: "pre-wrap" }}>{safeText}</span>
          ) : (
            <>
              <SafeMarkdown content={safeText} />
              {isStreaming && <span className="streaming-cursor">▌</span>}
              {!isStreaming && onStartCooking && (
                <RecipeOptionCards content={safeText} onStartCooking={onStartCooking} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
