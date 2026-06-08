/* MySifa — Humeur quotidienne (popup partagé entre toutes les pages) */
(function(){
  const HUMEURS=[
    {val:'😊',label:'Joyeux'},
    {val:'😩',label:'Épuisé'},
    {val:'😢',label:'Triste'},
    {val:'🤒',label:'Malade'},
    {val:'😐',label:'Normal'},
    {val:'😠',label:'Colère'},
    {val:'🥵',label:'Chaud'},
    {val:'🥶',label:'Froid'},
    {val:'🤮',label:'Nauséeux'},
    {val:'🥱',label:'Fatigué'},
  ];

  function todayIso(){
    const d=new Date();
    return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  }

  function popupKey(uid){
    return 'mysifa.humeur.popup.'+uid+'.'+todayIso();
  }

  function injectStyles(){
    if(document.getElementById('mys-humeur-css'))return;
    const s=document.createElement('style');
    s.id='mys-humeur-css';
    s.textContent=`
.mys-humeur-overlay{
  position:fixed;inset:0;z-index:20000;background:rgba(0,0,0,.6);
  display:flex;align-items:center;justify-content:center;padding:20px;
}
.mys-humeur-card{
  background:var(--card,#111827);border:1px solid var(--border,#1e293b);border-radius:18px;
  padding:28px 26px 22px;width:min(400px,100%);box-shadow:0 24px 64px rgba(0,0,0,.5);
  text-align:center;font-family:'Segoe UI',system-ui,sans-serif;
}
.mys-humeur-title{font-size:17px;font-weight:700;color:var(--text,#f1f5f9);margin-bottom:6px}
.mys-humeur-sub{font-size:13px;color:var(--muted,#94a3b8);margin-bottom:22px;line-height:1.5}
.mys-humeur-emojis{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-bottom:18px}
.mys-humeur-item{display:flex;flex-direction:column;align-items:center;gap:3px}
.mys-humeur-btn{
  font-size:26px;width:54px;height:54px;border-radius:14px;
  border:2px solid var(--border,#1e293b);background:var(--bg,#0a0e17);
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  transition:border-color .15s,background .15s,transform .1s;line-height:1;padding:0;
}
.mys-humeur-btn:hover{
  border-color:var(--accent,#22d3ee);background:var(--accent-bg,rgba(34,211,238,0.12));
  transform:scale(1.1);
}
.mys-humeur-lbl{font-size:10px;color:var(--muted,#94a3b8);font-weight:600;
  text-transform:uppercase;letter-spacing:.3px}
.mys-humeur-skip{
  background:transparent;border:none;color:var(--muted,#94a3b8);font-size:12px;
  cursor:pointer;font-family:inherit;padding:6px 12px;border-radius:8px;
}
.mys-humeur-skip:hover{color:var(--text,#f1f5f9);background:rgba(255,255,255,.05)}
    `;
    document.head.appendChild(s);
  }

  function showPopup(uid){
    injectStyles();
    const old=document.getElementById('mys-humeur-modal');
    if(old)old.remove();
    const overlay=document.createElement('div');
    overlay.id='mys-humeur-modal';
    overlay.className='mys-humeur-overlay';
    overlay.innerHTML=`
      <div class="mys-humeur-card" role="dialog" aria-labelledby="mys-humeur-ttl">
        <div class="mys-humeur-title" id="mys-humeur-ttl">De quelle humeur êtes-vous aujourd'hui ?</div>
        <div class="mys-humeur-sub">Votre humeur sera visible dans la messagerie par vos collègues.</div>
        <div class="mys-humeur-emojis">
          ${HUMEURS.map(h=>`
            <div class="mys-humeur-item">
              <button type="button" class="mys-humeur-btn" data-val="${h.val}" title="${h.label}">${h.val}</button>
              <span class="mys-humeur-lbl">${h.label}</span>
            </div>`).join('')}
        </div>
        <button type="button" class="mys-humeur-skip">Passer</button>
      </div>`;
    overlay.querySelectorAll('.mys-humeur-btn').forEach(btn=>{
      btn.addEventListener('click',()=>pickHumeur(uid,btn.dataset.val,overlay));
    });
    overlay.querySelector('.mys-humeur-skip').addEventListener('click',()=>dismiss(uid,overlay));
    document.body.appendChild(overlay);
  }

  async function pickHumeur(uid,val,overlay){
    try{
      await fetch('/api/auth/me/humeur',{
        method:'PUT',credentials:'include',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({humeur_valeur:val})
      });
    }catch(e){}
    dismiss(uid,overlay);
  }

  function dismiss(uid,overlay){
    try{localStorage.setItem(popupKey(uid),'1');}catch(e){}
    if(overlay)overlay.remove();
  }

  window.MySifaHumeur={
    maybeShow:function(me){
      if(!me||!me.id)return;
      if(!me.humeur_active)return;
      const today=todayIso();
      if(me.humeur_date===today&&me.humeur_valeur)return;
      try{if(localStorage.getItem(popupKey(me.id)))return;}catch(e){}
      showPopup(me.id);
    }
  };
})();
