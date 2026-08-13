import React, { useState, useEffect, useRef } from "react";
import { ChefHat, Clock, Play, Pause, RotateCcw, X, ChevronLeft, ChevronRight } from "lucide-react";

export default function CookingModeModal({ isOpen, onClose, recipeText, recipeTitle }) {
  const [steps, setSteps] = useState([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [initialSeconds, setInitialSeconds] = useState(0);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!recipeText) return;
    const lines = recipeText.split("\n");
    const parsedSteps = [];
    let currentStep = "";
    lines.forEach((line) => {
      const isHeader = /^(Step\s+\d+|^\d+\.|\*\*Step\s+\d+)/i.test(line.trim());
      if (isHeader) {
        if (currentStep.trim()) parsedSteps.push(currentStep.trim());
        currentStep = line;
      } else if (parsedSteps.length > 0 || currentStep) {
        currentStep += "\n" + line;
      }
    });
    if (currentStep.trim()) parsedSteps.push(currentStep.trim());
    if (parsedSteps.length === 0) {
      const paragraphs = recipeText.split(/\n\s*\n/).filter((p) => p.trim().length > 10);
      setSteps(paragraphs.length > 0 ? paragraphs : [recipeText]);
    } else {
      setSteps(parsedSteps);
    }
    setCurrentStepIndex(0);
  }, [recipeText, isOpen]);

  useEffect(() => {
    if (steps.length === 0) return;
    const text = steps[currentStepIndex] || "";
    const match = text.match(/(\d+)(?:\s*-\s*\d+)?\s*(minute|min|second|sec)s?/i);
    if (match) {
      const secs = match[2].toLowerCase().startsWith("min") ? parseInt(match[1]) * 60 : parseInt(match[1]);
      setTimerSeconds(secs);
      setInitialSeconds(secs);
    } else {
      setTimerSeconds(0);
      setInitialSeconds(0);
    }
    setIsTimerRunning(false);
  }, [currentStepIndex, steps]);

  useEffect(() => {
    if (isTimerRunning && timerSeconds > 0) {
      timerRef.current = setInterval(() => {
        setTimerSeconds((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            setIsTimerRunning(false);
            playBeep();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isTimerRunning, timerSeconds]);

  const playBeep = () => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.7);
    } catch (e) {}
  };

  const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  if (!isOpen) return null;
  const currentText = steps[currentStepIndex] || "No instructions available.";

  return (
    <div className="modal-backdrop">
      <div className="cooking-modal">
        {/* Header */}
        <div className="cooking-modal-header">
          <div className="modal-header-left">
            <ChefHat size={16} color="var(--accent-primary)" />
            <span className="modal-title">Cooking Mode</span>
            <span className="modal-subtitle">— {recipeTitle || "Recipe"}</span>
          </div>
          <div className="modal-header-right">
            <span className="step-indicator">Step {currentStepIndex + 1} of {steps.length}</span>
            <button className="btn-close" onClick={onClose}>
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Step Pills */}
        {steps.length > 1 && (
          <div className="step-pills-track">
            {steps.map((_, i) => (
              <button
                key={i}
                className={`step-pill ${i === currentStepIndex ? "active" : i < currentStepIndex ? "done" : ""}`}
                onClick={() => setCurrentStepIndex(i)}
              >
                Step {i + 1}
              </button>
            ))}
          </div>
        )}

        {/* Body */}
        <div className="cooking-modal-body">
          <div className="step-card">
            <div className="step-tag">Step {currentStepIndex + 1} of {steps.length}</div>
            <div className="step-text">{currentText}</div>
          </div>

          {initialSeconds > 0 && (
            <div className="timer-card">
              <div className="timer-label">
                <Clock size={12} />
                Detected Timer
              </div>
              <div className={`timer-display ${timerSeconds === 0 ? "done" : ""}`}>
                {fmt(timerSeconds)}
              </div>
              <div className="timer-actions">
                {!isTimerRunning ? (
                  <button className="btn-timer start" onClick={() => setIsTimerRunning(true)} disabled={timerSeconds === 0}>
                    <Play size={12} /> Start
                  </button>
                ) : (
                  <button className="btn-timer pause" onClick={() => setIsTimerRunning(false)}>
                    <Pause size={12} /> Pause
                  </button>
                )}
                <button className="btn-timer reset" onClick={() => { setIsTimerRunning(false); setTimerSeconds(initialSeconds); }}>
                  <RotateCcw size={12} /> Reset
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="cooking-modal-footer">
          <button
            className="btn-step-nav"
            disabled={currentStepIndex === 0}
            onClick={() => setCurrentStepIndex((p) => p - 1)}
          >
            <ChevronLeft size={14} /> Previous
          </button>
          <span className="footer-counter">{currentStepIndex + 1} / {steps.length}</span>
          <button
            className="btn-step-nav next"
            disabled={currentStepIndex === steps.length - 1}
            onClick={() => setCurrentStepIndex((p) => p + 1)}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
