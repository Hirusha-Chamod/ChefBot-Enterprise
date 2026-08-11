import React, { Component } from "react";
import ReactMarkdown from "react-markdown";

class SafeMarkdown extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error("Markdown rendering fallback:", error);
  }

  render() {
    const text = String(this.props.content || "");
    if (this.state.hasError) {
      return <div style={{ whiteSpace: "pre-wrap" }}>{text}</div>;
    }
    return (
      <div className="markdown-content">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
    );
  }
}

export default function MessageBubble({ role, content }) {
  const isUser = role === "user";
  const safeText = String(content || "");

  return (
    <div className={`message-row ${isUser ? "user" : "bot"}`}>
      <div className={`bubble ${isUser ? "user" : "bot"}`}>
        {isUser ? safeText : <SafeMarkdown content={safeText} />}
      </div>
    </div>
  );
}
