import React, { useState } from "react";
import { Camera, Loader2 } from "lucide-react";

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
      if (!response.ok) throw new Error(data.detail || "Vision analysis failed.");
      if (data.prompt_summary) onIngredientsDetected(data.prompt_summary);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="vision-uploader-inline">
      <label className="btn-vision-inline" title="Scan Fridge Photo">
        {loading ? <Loader2 size={15} className="spin" /> : <Camera size={15} />}
        <span>{loading ? "Scanning..." : "Scan Fridge"}</span>
        <input
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={handleFileChange}
          disabled={loading}
        />
      </label>
      {error && <span className="vision-error-inline">{error}</span>}
    </div>
  );
}
