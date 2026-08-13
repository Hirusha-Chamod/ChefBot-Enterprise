import React from "react";

const PROFILES = ["Standard", "Vegan", "Keto", "Gluten-Free", "Nut-Free"];

export default function DietarySelector({ selected, onSelect }) {
  return (
    <div className="strip-group">
      <span className="strip-label">Diet</span>
      <div className="pill-group">
        {PROFILES.map((p) => (
          <button
            key={p}
            className={`pill ${selected === p ? "active" : ""}`}
            onClick={() => onSelect(p)}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
