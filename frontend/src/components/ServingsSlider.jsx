import React from "react";
import { Users } from "lucide-react";

export default function ServingsSlider({ servings, onChange }) {
  return (
    <div className="servings-control">
      <span className="strip-label">Servings</span>
      <input
        type="range"
        min="1"
        max="10"
        value={servings}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="servings-range"
      />
      <span className="servings-value">
        <Users size={11} />
        {servings} {servings === 1 ? "Person" : "People"}
      </span>
    </div>
  );
}
