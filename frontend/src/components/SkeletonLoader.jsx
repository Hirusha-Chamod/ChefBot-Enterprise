import React from "react";

export function ChatSkeletonLoader() {
  return (
    <div className="chat-skeleton-container" aria-label="Loading conversation...">
      {/* User message skeleton */}
      <div className="message-row user skeleton-row">
        <div className="message-avatar user-avatar skeleton-avatar shimmer" />
        <div className="message-content">
          <div className="skeleton-line skeleton-sender shimmer" style={{ width: "40px" }} />
          <div className="bubble user skeleton-bubble">
            <div className="skeleton-line shimmer" style={{ width: "180px", height: "16px" }} />
          </div>
        </div>
      </div>

      {/* Bot message skeleton */}
      <div className="message-row bot skeleton-row">
        <div className="message-avatar bot-avatar skeleton-avatar shimmer" />
        <div className="message-content">
          <div className="skeleton-line skeleton-sender shimmer" style={{ width: "55px" }} />
          <div className="bubble bot skeleton-bubble">
            <div className="skeleton-line shimmer" style={{ width: "65%", height: "18px", marginBottom: "12px" }} />
            <div className="skeleton-line shimmer" style={{ width: "90%", height: "14px", marginBottom: "8px" }} />
            <div className="skeleton-line shimmer" style={{ width: "80%", height: "14px", marginBottom: "16px" }} />
            
            {/* Skeleton recipe cards */}
            <div className="skeleton-cards-grid">
              <div className="skeleton-card shimmer">
                <div className="skeleton-line shimmer" style={{ width: "40%", height: "12px", marginBottom: "6px" }} />
                <div className="skeleton-line shimmer" style={{ width: "80%", height: "14px" }} />
              </div>
              <div className="skeleton-card shimmer">
                <div className="skeleton-line shimmer" style={{ width: "40%", height: "12px", marginBottom: "6px" }} />
                <div className="skeleton-line shimmer" style={{ width: "75%", height: "14px" }} />
              </div>
              <div className="skeleton-card shimmer">
                <div className="skeleton-line shimmer" style={{ width: "40%", height: "12px", marginBottom: "6px" }} />
                <div className="skeleton-line shimmer" style={{ width: "85%", height: "14px" }} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function SidebarSkeletonLoader({ count = 4 }) {
  return (
    <div className="sidebar-skeleton-list">
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="session-item-skeleton shimmer">
          <div className="skeleton-line shimmer" style={{ width: `${60 + (idx % 3) * 15}%`, height: "13px", marginBottom: "6px" }} />
          <div className="skeleton-line shimmer" style={{ width: "35%", height: "10px" }} />
        </div>
      ))}
    </div>
  );
}
