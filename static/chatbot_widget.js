/**
 * mysifa.com — Chatbot Widget
 * Vanilla JS, zéro dépendance externe
 * Bulle flottante bas-gauche → panel de chat
 * Appelle POST /api/chat (FastAPI)
 */
(function () {
  "use strict";

  const css = `
    :root {
      --chat-accent:    #f59e0b;
      --chat-accent2:   #d97706;
      --chat-bg:        #111827;
      --chat-surface:   #1f2937;
      --chat-surface2:  #374151;
      --chat-border:    #374151;
      --chat-text:      #f3f4f6;
      --chat-muted:     #9ca3af;
      --chat-user-bg:   #f59e0b;
      --chat-user-text: #111827;
      --chat-bot-bg:    #1f2937;
      --chat-bot-text:  #f3f4f6;
      --chat-radius:    14px;
      --chat-w:         370px;
      --chat-h:         520px;
      --chat-font:      'Courier New', 'Lucida Console', monospace;
    }

    #sifa-chat-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      left: auto;
      z-index: 9998;
      width: 54px;
      height: 54px;
      border-radius: 50%;
      background: var(--chat-accent);
      border: 2px solid var(--chat-accent2);
      box-shadow: 0 4px 18px rgba(245,158,11,0.45), 0 1px 4px rgba(0,0,0,0.5);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.18s ease, box-shadow 0.18s ease;
      outline: none;
    }
    #sifa-chat-btn:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 24px rgba(245,158,11,0.6), 0 2px 6px rgba(0,0,0,0.5);
    }
    #sifa-chat-btn svg { display: block; }

    #sifa-chat-badge {
      position: absolute;
      top: -4px;
      right: -4px;
      width: 16px;
      height: 16px;
      background: #ef4444;
      border-radius: 50%;
      border: 2px solid #111827;
      display: none;
    }

    #sifa-chat-panel {
      position: fixed;
      bottom: 90px;
      right: 24px;
      left: auto;
      z-index: 9999;
      width: var(--chat-w);
      height: var(--chat-h);
      background: var(--chat-bg);
      border: 1px solid var(--chat-border);
      border-radius: var(--chat-radius);
      box-shadow: 0 12px 48px rgba(0,0,0,0.65), 0 2px 12px rgba(0,0,0,0.4);
      display: flex;
      flex-direction: column;
      font-family: var(--chat-font);
      font-size: 13px;
      transform-origin: bottom right;
      transform: scale(0.88) translateY(12px);
      opacity: 0;
      pointer-events: none;
      transition: transform 0.22s cubic-bezier(.34,1.56,.64,1), opacity 0.18s ease;
      overflow: hidden;
    }
    #sifa-chat-panel.open {
      transform: scale(1) translateY(0);
      opacity: 1;
      pointer-events: all;
    }

    #sifa-chat-header {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 16px;
      background: var(--chat-surface);
      border-bottom: 1px solid var(--chat-border);
      flex-shrink: 0;
    }
    .sifa-header-dot {
      width: 9px; height: 9px;
      border-radius: 50%;
      background: var(--chat-accent);
      box-shadow: 0 0 7px var(--chat-accent);
      flex-shrink: 0;
      animation: sifa-pulse 2s infinite;
    }
    @keyframes sifa-pulse {
      0%,100% { opacity: 1; }
      50%      { opacity: 0.35; }
    }
    .sifa-header-title {
      flex: 1;
      color: var(--chat-text);
      font-weight: 700;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .sifa-header-sub {
      font-size: 10px;
      color: var(--chat-muted);
      letter-spacing: 0.05em;
      text-transform: none;
      font-weight: 400;
      display: block;
    }
    #sifa-chat-close {
      background: none;
      border: none;
      cursor: pointer;
      color: var(--chat-muted);
      padding: 4px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      transition: color 0.15s, background 0.15s;
    }
    #sifa-chat-close:hover { color: var(--chat-text); background: var(--chat-surface2); }

    #sifa-quick-actions {
      display: flex;
      gap: 6px;
      padding: 10px 14px;
      background: var(--chat-surface);
      border-bottom: 1px solid var(--chat-border);
      flex-wrap: wrap;
      flex-shrink: 0;
    }
    .sifa-quick-btn {
      font-family: var(--chat-font);
      font-size: 10px;
      padding: 4px 9px;
      border-radius: 20px;
      background: transparent;
      border: 1px solid var(--chat-border);
      color: var(--chat-muted);
      cursor: pointer;
      transition: border-color 0.15s, color 0.15s, background 0.15s;
      white-space: nowrap;
    }
    .sifa-quick-btn:hover {
      border-color: var(--chat-accent);
      color: var(--chat-accent);
      background: rgba(245,158,11,0.08);
    }

    #sifa-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      scrollbar-width: thin;
      scrollbar-color: var(--chat-surface2) transparent;
    }
    #sifa-messages::-webkit-scrollbar { width: 5px; }
    #sifa-messages::-webkit-scrollbar-thumb { background: var(--chat-surface2); border-radius: 3px; }

    .sifa-msg {
      display: flex;
      flex-direction: column;
      max-width: 88%;
      animation: sifa-msg-in 0.18s ease;
    }
    @keyframes sifa-msg-in {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .sifa-msg.bot  { align-self: flex-start; }
    .sifa-msg.user { align-self: flex-end; }

    .sifa-bubble {
      padding: 9px 13px;
      border-radius: 10px;
      line-height: 1.5;
      word-break: break-word;
    }
    .sifa-msg.bot  .sifa-bubble {
      background: var(--chat-bot-bg);
      color: var(--chat-bot-text);
      border: 1px solid var(--chat-border);
      border-bottom-left-radius: 3px;
    }
    .sifa-msg.user .sifa-bubble {
      background: var(--chat-user-bg);
      color: var(--chat-user-text);
      font-weight: 600;
      border-bottom-right-radius: 3px;
    }

    .sifa-msg-label {
      font-size: 10px;
      color: var(--chat-muted);
      margin-bottom: 4px;
      letter-spacing: 0.04em;
    }
    .sifa-msg.user .sifa-msg-label { text-align: right; }

    .sifa-status {
      display: inline-block;
      font-size: 10px;
      padding: 2px 7px;
      border-radius: 20px;
      margin-top: 5px;
      font-weight: 600;
    }
    .sifa-status.ok  { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid #10b981; }
    .sifa-status.err { background: rgba(239,68,68,0.15);  color: #ef4444; border: 1px solid #ef4444; }
    .sifa-status.info { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid #f59e0b; }

    #sifa-typing {
      display: none;
      align-self: flex-start;
      padding: 10px 14px;
      background: var(--chat-bot-bg);
      border: 1px solid var(--chat-border);
      border-radius: 10px;
      border-bottom-left-radius: 3px;
      gap: 5px;
      align-items: center;
    }
    #sifa-typing.visible { display: flex; }
    .sifa-dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: var(--chat-muted);
      animation: sifa-bounce 1.2s infinite;
    }
    .sifa-dot:nth-child(2) { animation-delay: 0.2s; }
    .sifa-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes sifa-bounce {
      0%,60%,100% { transform: translateY(0); }
      30%          { transform: translateY(-5px); }
    }

    #sifa-input-area {
      display: flex;
      align-items: flex-end;
      gap: 8px;
      padding: 12px 14px;
      background: var(--chat-surface);
      border-top: 1px solid var(--chat-border);
      flex-shrink: 0;
    }
    #sifa-input {
      flex: 1;
      background: var(--chat-surface2);
      border: 1px solid var(--chat-border);
      border-radius: 8px;
      color: var(--chat-text);
      font-family: var(--chat-font);
      font-size: 12.5px;
      padding: 9px 12px;
      resize: none;
      max-height: 90px;
      min-height: 38px;
      outline: none;
      transition: border-color 0.15s;
      line-height: 1.4;
    }
    #sifa-input:focus { border-color: var(--chat-accent); }
    #sifa-input::placeholder { color: var(--chat-muted); }

    #sifa-send {
      width: 38px; height: 38px;
      border-radius: 8px;
      background: var(--chat-accent);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: background 0.15s, transform 0.1s;
    }
    #sifa-send:hover  { background: var(--chat-accent2); }
    #sifa-send:active { transform: scale(0.94); }
    #sifa-send:disabled { background: var(--chat-surface2); cursor: not-allowed; }

    @media (max-width: 430px) {
      #sifa-chat-panel { width: calc(100vw - 32px); }
    }
  `;

  const quickActions = [
    { label: "📋 Voir planning", text: "Montre-moi le planning de la machine 1" },
    { label: "📦 Voir stock",    text: "Consulte l'état du stock" },
    { label: "➕ Planning",      text: "Ajoute au planning machine 1 la référence " },
    { label: "🏷️ Stock",        text: "Ajoute en stock la référence " },
  ];

  function buildHTML() {
    const qaBtns = quickActions
      .map(q => `<button class="sifa-quick-btn" data-text="${q.text}">${q.label}</button>`)
      .join("");

    return `
      <button id="sifa-chat-btn" aria-label="Ouvrir l'assistant SIFA">
        <span id="sifa-chat-badge"></span>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" fill="#111827"/>
          <circle cx="8" cy="11" r="1.2" fill="#f59e0b"/>
          <circle cx="12" cy="11" r="1.2" fill="#f59e0b"/>
          <circle cx="16" cy="11" r="1.2" fill="#f59e0b"/>
        </svg>
      </button>

      <div id="sifa-chat-panel" role="dialog" aria-label="Assistant SIFA">
        <div id="sifa-chat-header">
          <span class="sifa-header-dot"></span>
          <div class="sifa-header-title">
            Assistant SIFA
            <span class="sifa-header-sub">myprod · mystock</span>
          </div>
          <button id="sifa-chat-close" aria-label="Fermer">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <div id="sifa-quick-actions">${qaBtns}</div>

        <div id="sifa-messages"></div>

        <div id="sifa-typing">
          <span class="sifa-dot"></span>
          <span class="sifa-dot"></span>
          <span class="sifa-dot"></span>
        </div>

        <div id="sifa-input-area">
          <textarea id="sifa-input" placeholder="Ex: Ajoute la référence X au planning machine 1…" rows="1" aria-label="Message"></textarea>
          <button id="sifa-send" aria-label="Envoyer">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M14 8L2 2l3 6-3 6 12-6z" fill="#111827"/>
            </svg>
          </button>
        </div>
      </div>
    `;
  }

  function init() {
    const style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);

    const wrapper = document.createElement("div");
    wrapper.id = "sifa-chat-root";
    wrapper.innerHTML = buildHTML();
    document.body.appendChild(wrapper);

    const btn = document.getElementById("sifa-chat-btn");
    const panel = document.getElementById("sifa-chat-panel");
    const close = document.getElementById("sifa-chat-close");
    const msgs = document.getElementById("sifa-messages");
    const input = document.getElementById("sifa-input");
    const send = document.getElementById("sifa-send");
    const typing = document.getElementById("sifa-typing");
    const badge = document.getElementById("sifa-chat-badge");
    const qaBtns = document.querySelectorAll(".sifa-quick-btn");

    let isOpen = false;
    let isLoading = false;
    let history = [];
    let msgCount = 0;

    addBotMessage("Bonjour. Je suis l'assistant **SIFA**.\nJe peux aider sur **planning** et **stock**.\nQue veux-tu faire ?");

    function togglePanel() {
      isOpen = !isOpen;
      panel.classList.toggle("open", isOpen);
      badge.style.display = "none";
      if (isOpen) setTimeout(() => input.focus(), 220);
    }

    btn.addEventListener("click", togglePanel);
    close.addEventListener("click", togglePanel);

    document.addEventListener("click", (e) => {
      if (isOpen && !panel.contains(e.target) && e.target !== btn) {
        isOpen = false;
        panel.classList.remove("open");
      }
    });

    qaBtns.forEach(b => {
      b.addEventListener("click", () => {
        const text = b.getAttribute("data-text") || "";
        input.value = text;
        input.focus();
        input.setSelectionRange(text.length, text.length);
      });
    });

    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 90) + "px";
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });
    send.addEventListener("click", handleSend);

    function formatText(t) {
      return String(t || "")
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");
    }
    function scrollBottom() {
      setTimeout(() => { msgs.scrollTop = msgs.scrollHeight; }, 30);
    }
    function addBotMessage(text, statusType = null) {
      const div = document.createElement("div");
      div.className = "sifa-msg bot";
      const label = document.createElement("div");
      label.className = "sifa-msg-label";
      label.textContent = "SIFA";
      const bubble = document.createElement("div");
      bubble.className = "sifa-bubble";
      bubble.innerHTML = formatText(text);
      div.appendChild(label);
      div.appendChild(bubble);
      if (statusType) {
        const badge2 = document.createElement("span");
        badge2.className = `sifa-status ${statusType}`;
        badge2.textContent = statusType === "ok" ? "✓ Action effectuée" : statusType === "err" ? "✗ Erreur" : "ℹ Info";
        div.appendChild(badge2);
      }
      msgs.appendChild(div);
      scrollBottom();
      if (!isOpen) {
        badge.style.display = "block";
        msgCount++;
      }
    }
    function addUserMessage(text) {
      const div = document.createElement("div");
      div.className = "sifa-msg user";
      const label = document.createElement("div");
      label.className = "sifa-msg-label";
      label.textContent = "Vous";
      const bubble = document.createElement("div");
      bubble.className = "sifa-bubble";
      bubble.textContent = text;
      div.appendChild(label);
      div.appendChild(bubble);
      msgs.appendChild(div);
      scrollBottom();
    }
    function setLoading(val) {
      isLoading = val;
      send.disabled = val;
      input.disabled = val;
      typing.classList.toggle("visible", val);
      if (val) scrollBottom();
    }

    async function handleSend() {
      const text = input.value.trim();
      if (!text || isLoading) return;
      addUserMessage(text);
      history.push({ role: "user", content: text });
      input.value = "";
      input.style.height = "auto";
      setLoading(true);
      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: history }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.detail || `HTTP ${res.status}`);
        }
        const reply = data.reply || "Aucune réponse.";
        const status = data.status || null;
        addBotMessage(reply, status);
        history.push({ role: "assistant", content: reply });
      } catch (err) {
        addBotMessage("Erreur de connexion au serveur.", "err");
        console.error("[SIFA Chat]", err);
      } finally {
        setLoading(false);
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

