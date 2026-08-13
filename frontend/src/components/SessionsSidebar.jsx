import React from "react";
import { MessageSquare, Plus, Trash2, PanelLeftClose, PanelLeft, Loader2 } from "lucide-react";

export default function SessionsSidebar({
  isOpen,
  onToggle,
  sessions,
  activeThreadId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  loading = false,
}) {
  if (!isOpen) {
    return (
      <button className="sidebar-toggle-btn collapsed" onClick={onToggle} title="Open Sessions Sidebar">
        <PanelLeft size={16} />
      </button>
    );
  }

  return (
    <aside className="sessions-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title-group">
          {loading ? (
            <Loader2 size={16} className="spin" color="var(--accent-primary)" />
          ) : (
            <MessageSquare size={16} color="var(--accent-primary)" />
          )}
          <span>Saved Sessions</span>
        </div>
        <button className="sidebar-toggle-btn" onClick={onToggle} title="Collapse Sidebar">
          <PanelLeftClose size={16} />
        </button>
      </div>

      <div className="sidebar-actions">
        <button className="btn-new-chat" onClick={onNewChat}>
          <Plus size={14} />
          <span>New Recipe Chat</span>
        </button>
      </div>

      <div className="sessions-list">
        {loading && sessions.length === 0 ? (
          <div className="sessions-empty" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.4rem" }}>
            <Loader2 size={14} className="spin" color="var(--accent-primary)" />
            <span>Loading...</span>
          </div>
        ) : sessions.length === 0 ? (
          <div className="sessions-empty">No previous sessions</div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.thread_id}
              className={`session-item ${s.thread_id === activeThreadId ? "active" : ""}`}
              onClick={() => onSelectSession(s.thread_id)}
            >
              <div className="session-item-content">
                <span className="session-title">{s.title}</span>
                <span className="session-date">
                  {new Date(s.updated_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              <button
                className="btn-delete-session"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(s.thread_id);
                }}
                title="Delete Session"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
