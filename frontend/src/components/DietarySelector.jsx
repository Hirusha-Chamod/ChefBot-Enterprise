import React from "react";

const PROFILES = ["Standard", "Vegan", "Keto", "Gluten-Free", "Nut-Free"];

export default function DietarySelector({ selected, onSelect }) {
  return (
    <div className="dietary-bar">
      <span className="dietary-label">Dietary Profile:</span>
      <div className="dietary-options">
        {PROFILES.map((profile) => (
          <button
            key={profile}
            className={`dietary-pill ${selected === profile ? "active" : ""}`}
            onClick={() => onSelect(profile)}
          >
            {profile}
          </button>
        ))}
      </div>
    </div>
  );
}
