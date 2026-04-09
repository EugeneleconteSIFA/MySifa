(function(){
  function iconSvg(){
    const common = `fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`;
    // Headset plus explicite (arceau + oreillettes + micro)
    return `<svg viewBox="0 0 24 24" aria-hidden="true">
      <path ${common} d="M4 12a8 8 0 0 1 16 0"/>
      <path ${common} d="M6 12v5a2 2 0 0 0 2 2h1v-7H8a2 2 0 0 0-2 2z"/>
      <path ${common} d="M18 12v5a2 2 0 0 1-2 2h-1v-7h1a2 2 0 0 1 2 2z"/>
      <path ${common} d="M14.5 20.5h-2.5"/>
      <path ${common} d="M14.5 20.5a3.5 3.5 0 0 0 3.5-3.5"/>
      <path ${common} d="M18 17.5l2 1.5"/>
    </svg>`;
  }

  function open(opts){
    const o = opts || {};
    const user = o.user || {};
    const page = o.page || "";
    const notify = typeof o.notify === "function" ? o.notify : (m)=>alert(String(m||""));
    const api = typeof o.api === "function"
      ? o.api
      : async (p, req) => {
          const r = await fetch(p, { credentials: "include", ...(req||{}) });
          if (!r.ok) {
            let e = {};
            try { e = await r.json(); } catch {}
            throw new Error(e.detail || ("Erreur " + r.status));
          }
          return await r.json();
        };

    const wrap = document.createElement("div");
    wrap.className = "support-modal";
    wrap.addEventListener("mousedown", (e)=>{ if (e.target === wrap) wrap.remove(); });

    const card = document.createElement("div");
    card.className = "support-card";

    const closeBtn = document.createElement("button");
    closeBtn.className = "support-close";
    closeBtn.type = "button";
    closeBtn.title = "Fermer";
    closeBtn.textContent = "✕";
    closeBtn.onclick = ()=>wrap.remove();

    const head = document.createElement("div");
    head.className = "support-head";
    const headLeft = document.createElement("div");
    const title = document.createElement("div");
    title.className = "support-title";
    title.textContent = "Contacter le support";
    const sub = document.createElement("div");
    sub.className = "support-sub";
    sub.innerHTML = `Envoi optimisé vers <span style="color:var(--accent);font-weight:800">eleconte@sifa.pro</span>`;
    headLeft.appendChild(title);
    headLeft.appendChild(sub);
    head.appendChild(headLeft);
    head.appendChild(closeBtn);

    function field(label, inputEl){
      const w = document.createElement("div");
      const l = document.createElement("label");
      l.className = "field-label";
      l.textContent = label;
      w.appendChild(l);
      w.appendChild(inputEl);
      return w;
    }

    const nameI = document.createElement("input");
    nameI.className = "field-input";
    nameI.type = "text";
    nameI.required = true;
    nameI.placeholder = "Nom / prénom";
    nameI.value = String(o.name || user.nom || "");

    const emailI = document.createElement("input");
    emailI.className = "field-input";
    emailI.type = "email";
    emailI.required = true;
    emailI.placeholder = "Email";
    emailI.value = String(o.email || user.email || "");

    const subjI = document.createElement("input");
    subjI.className = "field-input";
    subjI.type = "text";
    subjI.required = true;
    subjI.placeholder = "Objet";
    subjI.value = String(o.subject || "");

    const msgT = document.createElement("textarea");
    msgT.className = "support-textarea";
    msgT.required = true;
    msgT.placeholder = "Décrivez votre besoin (contexte, écran, message d’erreur, etc.)";
    msgT.value = String(o.message || "");

    const grid = document.createElement("div");
    grid.className = "support-grid";
    grid.appendChild(field("Nom", nameI));
    grid.appendChild(field("Email", emailI));
    const subjWrap = field("Objet", subjI); subjWrap.style.gridColumn = "1 / -1";
    const msgWrap = field("Message", msgT); msgWrap.style.gridColumn = "1 / -1";
    grid.appendChild(subjWrap);
    grid.appendChild(msgWrap);

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn-ghost";
    cancelBtn.type = "button";
    cancelBtn.textContent = "Annuler";
    cancelBtn.onclick = ()=>wrap.remove();

    const sendBtn = document.createElement("button");
    sendBtn.className = "btn";
    sendBtn.type = "button";
    sendBtn.textContent = "Envoyer";

    sendBtn.onclick = async () => {
      const payload = {
        name: String(nameI.value || "").trim(),
        email: String(emailI.value || "").trim(),
        subject: String(subjI.value || "").trim(),
        message: String(msgT.value || "").trim(),
        page: page || "",
      };
      if(!payload.name){ notify("Nom requis","warn"); return; }
      if(!payload.email){ notify("Email requis","warn"); return; }
      if(!payload.subject){ notify("Objet requis","warn"); return; }
      if(!payload.message || payload.message.length < 5){ notify("Message trop court","warn"); return; }

      sendBtn.disabled = true;
      try{
        await api("/api/support/contact", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        notify("Message envoyé au support","success");
        wrap.remove();
      }catch(e){
        notify((e && e.message) ? e.message : "Erreur envoi support","error");
      }finally{
        sendBtn.disabled = false;
      }
    };

    const actions = document.createElement("div");
    actions.className = "support-actions";
    actions.appendChild(cancelBtn);
    actions.appendChild(sendBtn);

    const hint = document.createElement("div");
    hint.className = "support-hint";
    hint.textContent = "Astuce : copie/colle le message exact d’erreur, et indique l’écran concerné.";

    card.appendChild(head);
    card.appendChild(grid);
    card.appendChild(actions);
    card.appendChild(hint);
    wrap.appendChild(card);
    document.body.appendChild(wrap);
    setTimeout(()=>{ try{ msgT.focus(); }catch(e){} }, 0);
  }

  window.MySifaSupport = { open, iconSvg };
})();

