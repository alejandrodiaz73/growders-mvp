/**
 * Growders MVP — app.js
 * Chat simulator logic.
 *
 * Design constraints:
 *  - No build step in Tier 0 (plain ES modules, no bundler)
 *  - API base URL auto-detected from window.location.origin
 *  - Session token in sessionStorage (cleared on tab close)
 *  - History capped at 20 messages to control token usage
 *  - Input sanitised before sending
 */

// ── Config ────────────────────────────────────────────────────────
const API_BASE = `${window.location.origin}/api/v1`;

// Demo tenant ID — in production this comes from the auth session
// Replace with your actual tenant UUID once DB is seeded
const DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001";

const MAX_HISTORY = 20;
const SESSION_KEY = "growders_session_token";
const HISTORY_KEY = "growders_chat_history";

// ── Session ───────────────────────────────────────────────────────
function getOrCreateSessionToken() {
  let token = sessionStorage.getItem(SESSION_KEY);
  if (!token) {
    token = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, token);
  }
  return token;
}

function getHistory() {
  try {
    return JSON.parse(sessionStorage.getItem(HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function appendHistory(role, content) {
  const history = getHistory();
  history.push({ role, content });
  // Keep only last MAX_HISTORY messages
  const trimmed = history.slice(-MAX_HISTORY);
  sessionStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed));
}

function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(HISTORY_KEY);
}

// ── DOM helpers ───────────────────────────────────────────────────
const messagesEl = document.getElementById("messages");
const inputEl    = document.getElementById("userInput");
const sendBtn    = document.getElementById("sendBtn");
const clearBtn   = document.getElementById("clearBtn");
const waStatus   = document.getElementById("waStatus");

function formatTime() {
  return new Date().toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

function appendBubble(role, text) {
  const div = document.createElement("div");
  div.className = `bubble bubble--${role === "user" ? "out" : "in"}`;
  div.innerHTML = `
    <div class="bubble__text">${escapeHtml(text)}</div>
    <div class="bubble__time">${formatTime()}</div>
  `;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function showTyping() {
  const div = document.createElement("div");
  div.className = "bubble bubble--in bubble--typing";
  div.id = "typingIndicator";
  div.textContent = "MarIA está escribiendo…";
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function removeTyping() {
  document.getElementById("typingIndicator")?.remove();
}

function escapeHtml(text) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return text.replace(/[&<>"']/g, m => map[m]);
}

function setLoading(loading) {
  sendBtn.disabled = loading;
  inputEl.disabled = loading;
  waStatus.textContent = loading ? "escribiendo…" : "en línea";
  waStatus.style.color = loading ? "var(--color-text-muted)" : "var(--color-success)";
}

// ── Welcome message ───────────────────────────────────────────────
function showWelcome() {
  appendBubble(
    "assistant",
    "¡Hola! Soy MarIA 👋 El asistente virtual de este negocio. ¿En qué te puedo ayudar hoy?"
  );
}

// ── API call ──────────────────────────────────────────────────────
async function sendMessage(message) {
  const trimmed = message.trim();
  if (!trimmed) return;

  const sessionToken = getOrCreateSessionToken();
  const history = getHistory();

  // Show user bubble
  appendBubble("user", trimmed);
  appendHistory("user", trimmed);
  inputEl.value = "";
  autoResize();

  setLoading(true);
  showTyping();

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-ID": DEMO_TENANT_ID,
      },
      body: JSON.stringify({
        message: trimmed,
        session_token: sessionToken,
        history: history.slice(0, -1), // exclude the message we just added
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    const data = await response.json();
    removeTyping();
    appendBubble("assistant", data.response);
    appendHistory("assistant", data.response);

  } catch (err) {
    removeTyping();
    appendBubble(
      "assistant",
      "Lo siento, tuve un problema al responder. Por favor intenta de nuevo en un momento."
    );
    console.error("Chat error:", err);
  } finally {
    setLoading(false);
    inputEl.focus();
  }
}

// ── Auto-resize textarea ──────────────────────────────────────────
function autoResize() {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + "px";
}

// ── Event listeners ───────────────────────────────────────────────
sendBtn.addEventListener("click", () => sendMessage(inputEl.value));

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage(inputEl.value);
  }
});

inputEl.addEventListener("input", autoResize);

clearBtn.addEventListener("click", () => {
  clearSession();
  messagesEl.innerHTML = "";
  showWelcome();
  inputEl.focus();
});

// Scenario buttons
document.querySelectorAll(".scenario-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const msg = btn.dataset.msg;
    if (msg) sendMessage(msg);
  });
});

// ── Init ──────────────────────────────────────────────────────────
showWelcome();
inputEl.focus();
