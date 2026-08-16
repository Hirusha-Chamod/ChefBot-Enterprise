import React, { useState, useEffect } from "react";
import { Brain, Trash2, X, Sparkles, Loader2, AlertCircle } from "lucide-react";

export default function MemoriesModal({ isOpen, onClose }) {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deletingKey, setDeletingKey] = useState(null);

  const fetchMemories = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("chefbot_token") || localStorage.getItem("token");
      const headers = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("http://localhost:8000/api/chat/memories", { headers });
      if (res.ok) {
        const data = await res.json();
        setMemories(data);
      }
    } catch (err) {
      console.error("Failed to fetch memories:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchMemories();
    }
  }, [isOpen]);

  const handleDelete = async (key) => {
    setDeletingKey(key);
    try {
      const token = localStorage.getItem("chefbot_token") || localStorage.getItem("token");
      const headers = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`http://localhost:8000/api/chat/memories/${key}`, {
        method: "DELETE",
        headers,
      });
      if (res.ok) {
        setMemories((prev) => prev.filter((m) => m.key !== key));
      }
    } catch (err) {
      console.error("Failed to delete memory:", err);
    } finally {
      setDeletingKey(null);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("Are you sure you want to clear all learned memories?")) return;
    setLoading(true);
    try {
      for (const m of memories) {
        await handleDelete(m.key);
      }
    } finally {
      setLoading(false);
    }
  };

  const getMemoryEmoji = (text) => {
    if (!text || typeof text !== "string") return "💡";
    const lower = text.toLowerCase();
    if (lower.includes("allerg") || lower.includes("peanut") || lower.includes("nut") || lower.includes("dairy")) return "⚠️";
    if (lower.includes("mexican") || lower.includes("italian") || lower.includes("asian") || lower.includes("thai")) return "🌮";
    if (lower.includes("cook") || lower.includes("people") || lower.includes("family")) return "👥";
    if (lower.includes("fryer") || lower.includes("skillet") || lower.includes("oven") || lower.includes("pot")) return "🍳";
    if (lower.includes("spicy") || lower.includes("sweet") || lower.includes("healthy") || lower.includes("keto")) return "✨";
    return "💡";
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop">
      <div className="memories-modal">
        {/* Header */}
        <div className="memories-modal-header">
          <div className="memories-header-left">
            <div className="memories-icon-badge">
              <Brain size={18} />
            </div>
            <div>
              <h3 className="memories-title">ChefBot Memory</h3>
              <p className="memories-subtitle">Learned preferences & dietary constraints</p>
            </div>
          </div>
          <button className="btn-close" onClick={onClose} title="Close">
            <X size={16} />
          </button>
        </div>

        {/* Content Body */}
        <div className="memories-modal-body">
          {loading ? (
            <div className="memories-loading">
              <Loader2 size={24} className="spin" />
              <span>Accessing long-term memory...</span>
            </div>
          ) : !Array.isArray(memories) || memories.length === 0 ? (
            <div className="memories-empty">
              <Sparkles size={32} className="empty-sparkle" />
              <h4>No memories learned yet</h4>
              <p>
                As you chat, ChefBot automatically remembers your allergies, dietary preferences, and kitchen equipment across all your sessions!
              </p>
            </div>
          ) : (
            <div className="memories-list">
              {memories.map((m) => {
                const factText = m?.text || m?.content || (typeof m?.value === "string" ? m.value : "") || "Learned culinary preference";
                return (
                  <div key={m.key} className="memory-card">
                    <div className="memory-card-icon">
                      <span>{getMemoryEmoji(factText)}</span>
                    </div>
                    <div className="memory-card-text">
                      <span className="memory-fact">{factText}</span>
                    </div>
                    <button
                      className="btn-delete-memory"
                      onClick={() => handleDelete(m.key)}
                      disabled={deletingKey === m.key}
                      title="Forget this memory"
                    >
                      {deletingKey === m.key ? (
                        <Loader2 size={14} className="spin" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        {memories.length > 0 && (
          <div className="memories-modal-footer">
            <span className="memories-count">{memories.length} learned fact{memories.length > 1 ? "s" : ""}</span>
            <button className="btn-clear-memories" onClick={handleClearAll} disabled={loading}>
              Clear All
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
