import React, { useState } from "react";
import { Lightbulb, Play } from "lucide-react";

export default function RecipeOptionCards({ content, onStartCooking }) {
  const [selectedOption, setSelectedOption] = useState("Option A");

  const optionsRegex = /(\d+)\.\s*\*\*(Option\s+[A-C]):\s*([^*]+)\*\*\s*\(([^)]+)\)\s*-\s*([^\n]+)/gi;
  const matches = [...content.matchAll(optionsRegex)];

  if (matches.length === 0) {
    const hasInstructions = /step|min|cook|prep|heat|pan|skillet/i.test(content);
    if (!hasInstructions) return null;
    return (
      <div className="options-actions" style={{ marginTop: "0.75rem" }}>
        <button className="btn-cook-simple" onClick={() => onStartCooking(content, "Recipe")}>
          <Play size={12} />
          Start Cooking Mode
        </button>
      </div>
    );
  }

  const options = matches.map((m) => ({
    key: m[2].trim(),
    title: m[3].trim(),
    meta: m[4].trim(),
    description: m[5].trim(),
  }));

  // Function to extract specific option steps from markdown text
  const extractOptionSteps = (fullText, optionKey) => {
    // Escape for regex (e.g. "Option A", "Option B", "Option C")
    const keyLetter = optionKey.replace("Option ", "").trim(); // "A", "B", "C"
    
    // Pattern to match "### Option A" or "### Option A Steps" until next "### Option" or header
    const pattern = new RegExp(
      `###\\s*(?:Option\\s*${keyLetter}|${optionKey})[\\s\\S]*?\\n([\\s\\S]*?)(?=(?:###\\s*Option|[#]{2,}|\\n{3,}|$))`,
      "i"
    );
    const match = fullText.match(pattern);

    if (match && match[1] && match[1].trim().length > 15) {
      return match[1].trim();
    }
    
    // Fallback: return full text if option-specific header is not found
    return fullText;
  };

  return (
    <div className="recipe-options-wrapper">
      <div className="recipe-options-label">
        <Lightbulb size={11} />
        Recipe Candidates
      </div>
      <div className="options-grid">
        {options.map((opt) => (
          <div
            key={opt.key}
            className={`option-card ${selectedOption === opt.key ? "selected" : ""}`}
            onClick={() => setSelectedOption(opt.key)}
          >
            <div className="option-card-header">
              <span className="option-tag">{opt.key}</span>
              <span className="option-meta">{opt.meta}</span>
            </div>
            <div className="option-title">{opt.title}</div>
            <div className="option-desc">{opt.description}</div>
          </div>
        ))}
      </div>
      <div className="options-actions">
        <button
          className="btn-cook"
          onClick={() => {
            const chosen = options.find((o) => o.key === selectedOption) || options[0];
            const specificSteps = extractOptionSteps(content, chosen.key);
            onStartCooking(specificSteps, `${chosen.key}: ${chosen.title}`);
          }}
        >
          <Play size={13} />
          Start Cooking — {selectedOption}
        </button>
      </div>
    </div>
  );
}
