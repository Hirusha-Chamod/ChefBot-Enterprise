import React, { useState } from "react";

export default function VisionUploader({ onIngredientsDetected }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError("");
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/api/vision/analyze", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Vision analysis failed.");
      }

      if (data.prompt_summary) {
        onIngredientsDetected(data.prompt_summary);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <label className="btn-auth" style={{ cursor: "pointer", background: "rgba(59, 130, 246, 0.15)", borderColor: "#3b82f6", color: "#60a5fa" }}>
        {loading ? "📸 Analyzing..." : "📸 Upload Fridge Photo"}
        <input
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={handleFileChange}
          disabled={loading}
        />
      </label>
      {error && <span style={{ color: "#ef4444", fontSize: "0.75rem" }}>{error}</span>}
    </div>
  );
}
