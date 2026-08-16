import React, { useState, useEffect, useRef } from "react";
import MessageBubble from "./components/MessageBubble";
import ChatInput from "./components/ChatInput";
import DietarySelector from "./components/DietarySelector";
import ServingsSlider from "./components/ServingsSlider";
import AuthModal from "./components/AuthModal";
import CookingModeModal from "./components/CookingModeModal";
import MemoriesModal from "./components/MemoriesModal";
import SessionsSidebar from "./components/SessionsSidebar";
import { ChatSkeletonLoader } from "./components/SkeletonLoader";
import { ChefHat, Flame, PanelLeft, Brain } from "lucide-react";
import "./styles/index.css";

function generateThreadId() {
  return "session_" + Math.random().toString(36).substr(2, 9);
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [allowWebSearch, setAllowWebSearch] = useState(true);
  const [dietaryProfile, setDietaryProfile] = useState("Standard");
  const [servings, setServings] = useState(2);
  
  // Modals
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isCookingOpen, setIsCookingOpen] = useState(false);
  const [isMemoriesOpen, setIsMemoriesOpen] = useState(false);
  const [activeRecipeText, setActiveRecipeText] = useState("");
  const [activeRecipeTitle, setActiveRecipeTitle] = useState("");
  
  // Persistent Thread ID State
  const [threadId, setThreadId] = useState(() => {
    return localStorage.getItem("chefbot_thread_id") || generateThreadId();
  });
  
  // Sessions Sidebar State
  const [sessions, setSessions] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Auth State — hydrated from localStorage so it survives page refresh
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("chefbot_user")) || null; }
    catch { return null; }
  });
  const [token, setToken] = useState(() => localStorage.getItem("chefbot_token") || "");

  useEffect(() => {
    localStorage.setItem("chefbot_thread_id", threadId);
    fetchHistory(threadId);
  }, [threadId]);

  useEffect(() => {
    fetchSessions();
  }, [token]);

  const fetchSessions = async () => {
    setLoadingSessions(true);
    try {
      const headers = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch("http://localhost:8000/api/chat/sessions", { headers });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (err) {
      console.log("Error loading chat sessions:", err);
    } finally {
      setLoadingSessions(false);
    }
  };

  const fetchHistory = async (targetThreadId) => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`http://localhost:8000/api/chat/history/${targetThreadId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages);
        } else {
          setMessages([]);
        }
      }
    } catch (err) {
      console.log("Error loading session history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleAuthSuccess = (userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
    // Persist so auth survives page refresh
    localStorage.setItem("chefbot_token", accessToken);
    localStorage.setItem("chefbot_user", JSON.stringify(userData));
    if (userData.dietary_profile) setDietaryProfile(userData.dietary_profile);
  };

  const handleLogout = () => {
    setUser(null);
    setToken("");
    localStorage.removeItem("chefbot_token");
    localStorage.removeItem("chefbot_user");
  };

  const handleNewChat = () => {
    const newId = generateThreadId();
    setThreadId(newId);
    setMessages([]);
  };

  const handleSelectSession = (targetThreadId) => {
    setThreadId(targetThreadId);
  };

  const handleDeleteSession = async (targetThreadId) => {
    try {
      await fetch(`http://localhost:8000/api/chat/sessions/${targetThreadId}`, { method: "DELETE" });
      setSessions((prev) => prev.filter((s) => s.thread_id !== targetThreadId));
      if (targetThreadId === threadId) {
        handleNewChat();
      }
    } catch (err) {
      console.log("Error deleting session:", err);
    }
  };

  const handleStartCooking = (recipeContent, title) => {
    setActiveRecipeText(recipeContent);
    setActiveRecipeTitle(title || "Recipe");
    setIsCookingOpen(true);
  };

  const handleSend = async (promptText) => {
    const activeThread = threadId;
    setMessages((prev) => [
      ...prev,
      { role: "user", content: promptText },
      { role: "assistant", content: "" }
    ]);
    setLoading(true);

    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch("http://localhost:8000/api/chat/stream", {
        method: "POST",
        headers,
        body: JSON.stringify({
          prompt: promptText,
          allow_web_search: allowWebSearch,
          dietary_profile: dietaryProfile,
          thread_id: activeThread,
          servings,
        }),
      });

      if (!response.ok) {
        throw new Error("Error connecting to ChefBot engine.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: streamDone } = await reader.read();
        done = streamDone;
        if (value) {
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split(/\r?\n\r?\n/);
          buffer = events.pop() || "";

          for (const event of events) {
            const lines = event.split(/\r?\n/);
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                try {
                  const jsonStr = line.slice(6).trim();
                  if (!jsonStr) continue;
                  const parsed = JSON.parse(jsonStr);

                  if (parsed.error) {
                    throw new Error(parsed.error);
                  }

                  if (parsed.token) {
                    setMessages((prev) => {
                      const newArr = [...prev];
                      const lastIdx = newArr.length - 1;
                      if (lastIdx >= 0 && newArr[lastIdx].role === "assistant") {
                        newArr[lastIdx] = {
                          ...newArr[lastIdx],
                          content: newArr[lastIdx].content + parsed.token,
                        };
                      }
                      return newArr;
                    });
                  }
                } catch (e) {
                  console.log("Stream line parse warning:", e);
                }
              }
            }
          }
        }
      }

      // Refresh sidebar list in background without reloading chat messages
      fetchSessions();
    } catch (error) {
      console.log("Stream error:", error);
    } finally {
      setLoading(false);
    }
  };

  const EXAMPLE_PROMPTS = [
    "3 eggs, onion, soy sauce",
    "chicken breast, garlic, lemon",
    "pasta, tomato, basil",
    "tofu, ginger, sesame oil",
  ];

  return (
    <div className="app-shell-with-sidebar">
      {/* Sessions History Sidebar */}
      <SessionsSidebar
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        sessions={sessions}
        activeThreadId={threadId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        loading={loadingSessions}
      />

      <div className="app-shell">
        {/* Top Navigation */}
        <header className="top-nav">
          <div className="nav-brand">
            {!isSidebarOpen && (
              <button
                className="sidebar-toggle-btn in-nav"
                onClick={() => setIsSidebarOpen(true)}
                title="Open Saved Chats"
              >
                <PanelLeft size={16} />
              </button>
            )}
            <div className="nav-brand-icon">
              <ChefHat size={18} />
            </div>
            <span className="nav-brand-name">ChefBot <span>Enterprise</span></span>
          </div>

          <div className="nav-actions">
            <button
              className="btn-memory-nav"
              onClick={() => setIsMemoriesOpen(true)}
              title="View & manage learned memories"
            >
              <Brain size={14} />
              <span>Memories</span>
            </button>

            {user ? (
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="btn-nav-action user-btn">{user.username}</span>
                <button
                  className="btn-signin"
                  style={{ background: "transparent", border: "1px solid var(--border-subtle)", color: "var(--text-secondary)", fontSize: "0.72rem", padding: "0.3rem 0.7rem" }}
                  onClick={handleLogout}
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <button className="btn-signin" onClick={() => setIsAuthOpen(true)}>
                Sign In
              </button>
            )}
          </div>
        </header>

        {/* Control Strip */}
        <div className="control-strip">
          <DietarySelector selected={dietaryProfile} onSelect={setDietaryProfile} />
          <ServingsSlider servings={servings} onChange={setServings} />
        </div>

        {/* Chat Area */}
        <main className="chat-area">
          {loadingHistory ? (
            <ChatSkeletonLoader />
          ) : messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon-wrap">
                <ChefHat size={34} />
              </div>
              <h2>ChefBot Enterprise Assistant</h2>
              <p>
                Your AI-powered culinary companion for custom recipes, ingredient detection, and step-by-step cooking mode.
              </p>
              <p style={{ fontSize: "0.78rem", color: "var(--text-tertiary)" }}>
                Recipes scaled for <span className="empty-highlight">{servings} {servings === 1 ? "person" : "people"}</span>
                {dietaryProfile !== "Standard" && <> · <span className="empty-highlight">{dietaryProfile}</span> profile active</>}
              </p>
              <div className="empty-chips">
                {EXAMPLE_PROMPTS.map((p) => (
                  <button key={p} className="empty-chip" onClick={() => handleSend(p)}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="chat-messages">
              {messages.map((msg, i) => (
                <MessageBubble
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  onStartCooking={msg.role === "assistant" ? handleStartCooking : undefined}
                  isStreaming={loading && i === messages.length - 1 && msg.role === "assistant"}
                />
              ))}
              {loading && !messages[messages.length - 1]?.content && (
                <div className="thinking-row">
                  <div className="message-avatar bot-avatar">
                    <ChefHat size={14} />
                  </div>
                  <div className="thinking-bubble">
                    <Flame size={14} className="spin" color="var(--accent-primary)" />
                    <span>Preparing ingredients & recipes...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </main>

        {/* Input Bar with inline Scan Fridge */}
        <ChatInput
          onSend={handleSend}
          allowWebSearch={allowWebSearch}
          onToggleWebSearch={() => setAllowWebSearch(!allowWebSearch)}
          disabled={loading}
        />

        {/* Modals */}
        <AuthModal
          isOpen={isAuthOpen}
          onClose={() => setIsAuthOpen(false)}
          onAuthSuccess={handleAuthSuccess}
        />
        <CookingModeModal
          isOpen={isCookingOpen}
          onClose={() => setIsCookingOpen(false)}
          recipeText={activeRecipeText}
          recipeTitle={activeRecipeTitle}
        />
        <MemoriesModal
          isOpen={isMemoriesOpen}
          onClose={() => setIsMemoriesOpen(false)}
        />
      </div>
    </div>
  );
}
