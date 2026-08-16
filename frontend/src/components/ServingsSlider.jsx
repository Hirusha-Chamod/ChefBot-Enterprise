import React, { useState, useEffect, useRef } from "react";
import { Users, ChevronDown, Check } from "lucide-react";

const SERVING_OPTIONS = [
  { value: 1, label: "1 Person", desc: "Single portion" },
  { value: 2, label: "2 People", desc: "Couple / Pair" },
  { value: 3, label: "3 People", desc: "Small family" },
  { value: 4, label: "4 People", desc: "Standard family" },
  { value: 5, label: "5 People", desc: "Medium group" },
  { value: 6, label: "6 People", desc: "Large family" },
  { value: 8, label: "8 People", desc: "Dinner party" },
  { value: 10, label: "10 People", desc: "Gathering" },
  { value: 12, label: "12 People", desc: "Big feast" },
];

export default function ServingsSlider({ servings, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentOption = SERVING_OPTIONS.find((o) => o.value === servings) || SERVING_OPTIONS[1];

  return (
    <div className="servings-dropdown-wrap" ref={dropdownRef}>
      <span className="strip-label">Servings</span>
      <div className="custom-select-wrapper">
        <button
          type="button"
          className={`custom-select-trigger ${isOpen ? "open" : ""}`}
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
        >
          <Users size={13} className="servings-icon" />
          <span className="current-serving-label">{currentOption.label}</span>
          <ChevronDown size={12} className={`servings-arrow ${isOpen ? "rotate" : ""}`} />
        </button>

        {isOpen && (
          <div className="custom-dropdown-menu">
            <div className="custom-dropdown-header">Select Serving Size</div>
            <div className="custom-dropdown-list">
              {SERVING_OPTIONS.map((opt) => {
                const isSelected = opt.value === servings;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    className={`custom-dropdown-option ${isSelected ? "selected" : ""}`}
                    onClick={() => {
                      onChange(opt.value);
                      setIsOpen(false);
                    }}
                  >
                    <div className="opt-info">
                      <span className="opt-label">{opt.label}</span>
                      <span className="opt-desc">{opt.desc}</span>
                    </div>
                    {isSelected && <Check size={14} className="opt-check" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
