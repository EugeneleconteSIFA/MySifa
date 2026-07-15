"""Login — assets CSS/JS (injectés dans app/web/html.py).

Ces constantes contiennent des placeholders `__APP_NAME_PREFIX__`,
`__APP_NAME_SUFFIX__`, `__APP_TAGLINE__`, `__APP_LOGIN_HINT__`,
`__APP_ORG_NAME__`, `__APP_NAME__`, `__V_LABEL__` qui sont substitués
par `render_frontend_html()` dans `html.py` à partir des variables
d'environnement `APP_NAME`, `APP_SPLIT`, `APP_ORG_NAME`, `APP_TAGLINE`,
`APP_LOGIN_HINT`. Défaut = valeurs SIFA (MySifa / SIFA).
"""

LOGIN_MAIN_CSS = r"""
.login-page{position:relative;z-index:1;min-height:100vh;display:flex;align-items:center;justify-content:center}
.login-theme-btn{position:fixed;top:18px;right:18px;z-index:10;
  display:inline-flex;align-items:center;gap:8px;
  padding:9px 14px;border-radius:10px;border:1px solid var(--border);
  background:var(--card);color:var(--text2);cursor:pointer;
  font-size:12px;font-family:inherit;font-weight:600;
  transition:background .15s,color .15s,border-color .15s,box-shadow .2s}
.login-theme-btn:hover{color:var(--accent);border-color:var(--accent);
  box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 18px rgba(34,211,238,.14)}
body.light .login-theme-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.login-theme-btn .theme-ico{display:inline-flex;align-items:center;line-height:1}
@media (max-width:480px){.login-theme-btn .theme-label{display:none}}
.pwd-wrap{position:relative}
.pwd-wrap input{padding-right:44px}
.pwd-toggle{position:absolute;top:50%;right:8px;transform:translateY(-50%);
  display:inline-flex;align-items:center;justify-content:center;
  width:32px;height:32px;border:none;background:transparent;cursor:pointer;
  color:var(--muted);border-radius:8px;padding:0;font-family:inherit;
  transition:color .15s,background .15s}
.pwd-toggle:hover{color:var(--accent);background:var(--accent-bg)}
.pwd-toggle:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.login-box{width:100%;max-width:420px;padding:24px}
.login-logo{text-align:center;margin-bottom:40px}
.brand{font-size:32px;font-weight:800;letter-spacing:-1px}.brand span{color:var(--accent)}
.tagline{font-size:13px;color:var(--muted);margin-top:6px}
.login-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px}
.login-card h2{font-size:18px;font-weight:700;margin-bottom:6px}
.login-card p{font-size:13px;color:var(--muted);margin-bottom:28px}
.field{margin-bottom:16px}
.field label{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}
.field input{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;color:var(--text);font-size:14px;font-family:inherit;outline:none;transition:border-color .15s}
.field input:focus{border-color:var(--accent)}
.login-btn{width:100%;background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:14px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;margin-top:8px;transition:opacity .15s}
.login-btn:disabled{opacity:.65;cursor:not-allowed}
.login-error{background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.3);border-radius:8px;padding:10px 14px;font-size:13px;color:var(--danger);margin-bottom:16px;display:none}
.login-error.show{display:block}
.login-footer{text-align:center;margin-top:20px;font-size:11px;color:var(--muted)}
/* ── Animation train d'icônes sur la page de login ────────────────────────────
   Un train composé des icônes des tuiles du portail traverse l'écran en suivant
   une trajectoire courbe aléatoire. Passe derrière la carte de connexion
   (z-index 0 vs .login-page z-index 1). Cyan accent, ne gêne pas les clics. */
.login-train-layer{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:visible}
.login-box{position:relative;z-index:2} /* passe devant le layer d'animation */
.login-wagon{
  position:absolute;top:0;left:0;
  width:0;height:0; /* point de trajet — les enfants sont positionnés autour */
  pointer-events:none;
  offset-rotate:0deg;
  opacity:0;
  will-change:opacity,offset-distance;
  animation-name:login-wagon-travel;
  animation-timing-function:linear; /* écart constant entre wagons */
  animation-fill-mode:forwards;
  animation-iteration-count:1;
}
.login-wagon-tile{
  position:absolute;top:0;left:0;
  width:42px;height:42px;
  margin:-21px 0 0 -21px;
  display:flex;align-items:center;justify-content:center;
  background:var(--card);
  border:1px solid var(--border);
  border-radius:11px;
  color:var(--accent);
  box-shadow:0 6px 16px rgba(0,0,0,.28), 0 0 0 1px rgba(34,211,238,.18);
  transform:scale(1);
  transform-origin:center;
  transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
  pointer-events:auto;
  cursor:pointer;
}
.login-wagon-tile svg{width:22px;height:22px;display:block}
body.light .login-wagon-tile{box-shadow:0 6px 16px rgba(15,23,42,.10), 0 0 0 1px rgba(8,145,178,.20)}
.login-wagon-tile:hover{
  transform:scale(1.22);
  border-color:var(--accent);
  box-shadow:0 10px 26px rgba(0,0,0,.42), 0 0 0 2px rgba(34,211,238,.45);
}
body.light .login-wagon-tile:hover{
  box-shadow:0 10px 26px rgba(15,23,42,.18), 0 0 0 2px rgba(8,145,178,.35);
}
.login-wagon-tip{
  position:absolute;
  top:34px;left:0;
  transform:translateX(-50%);
  min-width:170px;max-width:240px;
  background:var(--card);
  border:1px solid var(--border);
  border-radius:10px;
  padding:9px 13px;
  text-align:center;
  box-shadow:0 10px 26px rgba(0,0,0,.42);
  opacity:0;
  visibility:hidden;
  pointer-events:none;
  transition:opacity .18s ease, visibility .18s ease, transform .18s ease;
  z-index:10;
}
.login-wagon-tile:hover ~ .login-wagon-tip{
  opacity:1;
  visibility:visible;
  transform:translateX(-50%) translateY(4px);
}
.login-wagon-tip .tip-desc{font-size:13px;font-weight:700;color:var(--text);letter-spacing:.2px;line-height:1.35}
/* Quand un wagon est survolé → tout le train se fige */
.login-train-layer.paused .login-wagon{animation-play-state:paused}
/* Wagon survolé passe au-dessus des autres (tile + tip visibles au-dessus) */
.login-wagon.is-hovered{z-index:1000}
@keyframes login-wagon-travel{
  0%   {offset-distance:0%;   opacity:0}
  6%   {offset-distance:6%;   opacity:.95}
  94%  {offset-distance:94%;  opacity:.95}
  100% {offset-distance:100%; opacity:0}
}
@media (prefers-reduced-motion: reduce){
  .login-train-layer{display:none}
}
/* Toggle animations sur la page de login : cache le train et le fond animé.
   Réutilise la classe body.bg-anim-off gérée par MySifaTheme (préférence bgAnim). */
body.bg-anim-off .login-train-layer{display:none}
/* Barre haut-droite qui regroupe le bouton d'animations et le bouton de thème.
   .login-theme-btn conserve son style ; on lève juste son position:fixed pour
   qu'il coule dans le flex container. */
.login-topbar{position:fixed;top:18px;right:18px;z-index:10;
  display:inline-flex;align-items:center;gap:10px}
.login-topbar .login-theme-btn,
.login-topbar .login-anim-btn{position:static}
.login-anim-btn{
  display:inline-flex;align-items:center;gap:8px;
  padding:9px 14px;border-radius:10px;border:1px solid var(--border);
  background:var(--card);color:var(--text2);cursor:pointer;
  font-size:12px;font-family:inherit;font-weight:600;
  transition:background .15s,color .15s,border-color .15s,box-shadow .2s}
.login-anim-btn:hover{color:var(--accent);border-color:var(--accent);
  box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 18px rgba(34,211,238,.14)}
body.light .login-anim-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.login-anim-btn .anim-ico{display:inline-flex;align-items:center;line-height:1}
@media (max-width:480px){.login-anim-btn .anim-label{display:none}}
"""

LOGIN_MAIN_JS = r"""
// ── Login ───────────────────────────────────────────────────────
function renderLogin(){
  const isLight=document.body.classList.contains('light');
  const errEl=h('div',{className:'login-error'+(S.loginError?' show':''),id:'login-error'},S.loginError||'');
  const emailI=h('input',{type:'text',id:'login-email',name:'email',autocomplete:'username',placeholder:'identifiant ou email'});
  const pwdI=h('input',{type:'password',id:'login-password',name:'password',autocomplete:'current-password',placeholder:'••••••••'});
  const pwdToggle=h('button',{type:'button',className:'pwd-toggle','aria-label':'Afficher le mot de passe','aria-pressed':'false',
    onClick:()=>{
      const shown=pwdI.type==='text';
      pwdI.type=shown?'password':'text';
      pwdToggle.setAttribute('aria-pressed',shown?'false':'true');
      pwdToggle.setAttribute('aria-label',shown?'Afficher le mot de passe':'Masquer le mot de passe');
      pwdToggle.innerHTML='';
      pwdToggle.appendChild(iconEl(shown?'eye':'eye-off',18));
      try{pwdI.focus();const v=pwdI.value;pwdI.value='';pwdI.value=v;}catch(e){}
    }
  });
  pwdToggle.appendChild(iconEl('eye',18));
  const pwdWrap=h('div',{className:'pwd-wrap'},pwdI,pwdToggle);
  const submit=e=>{
    e.preventDefault();
    if(S.loginSubmitting)return;
    doLogin(emailI.value,pwdI.value);
  };
  const themeBtn=h('button',{type:'button',className:'login-theme-btn','aria-label':'Basculer thème clair/sombre',
    onClick:()=>{
      try{
        const _p=MySifaTheme.loadPrefs();
        const _nm=_p.mode==='light'?'dark':'light';
        // Sauver UNIQUEMENT le mode (la palette/style restent ceux du user pour le post-login),
        // puis ré-appliquer le rendu neutre pétrole sur la page de login.
        MySifaTheme.setPrefs({mode:_nm});
        MySifaTheme.applyPrefs({mode:_nm,palette:'mysifa',style:'defaut',bgAnim:_p.bgAnim});
      }catch(e){}
      render();
    }},
    h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
    h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
  );
  // Bouton toggle animations (train + fond animé) sur la page de connexion.
  // Utilise la même préférence bgAnim que Mon profil → l'état est partagé.
  let _animOn=true;
  try{ _animOn=MySifaTheme.loadPrefs().bgAnim!==false; }catch(e){}
  const animBtn=h('button',{type:'button',className:'login-anim-btn',
    'aria-label':'Activer / désactiver les animations','aria-pressed':(_animOn?'true':'false'),
    onClick:()=>{
      try{
        const _p=MySifaTheme.loadPrefs();
        const _next=_p.bgAnim===false;   // si off → on rallume, sinon on éteint
        MySifaTheme.setPrefs({bgAnim:_next});
        MySifaTheme.applyPrefs({mode:_p.mode,palette:'mysifa',style:'defaut',bgAnim:_next});
      }catch(e){}
      render();
    }},
    h('span',{className:'anim-ico'},iconEl(_animOn?'activity':'eye-off',16)),
    h('span',{className:'anim-label'},_animOn?'Animations':'Animations off')
  );
  const topbar=h('div',{className:'login-topbar'},animBtn,themeBtn);
  const trainLayer=h('div',{className:'login-train-layer',id:'login-train-layer'});
  // Démarre l'animation train juste après le mount (attend que le layer soit dans le DOM).
  setTimeout(startLoginTrainAnimation,60);
  return h('div',{className:'login-page'},
    trainLayer,
    topbar,
    h('div',{className:'login-box'},
      h('div',{className:'login-logo'},
        h('div',{className:'brand'},'__APP_NAME_PREFIX__',h('span',null,'__APP_NAME_SUFFIX__')),
        h('div',{className:'tagline'},'__APP_TAGLINE__')
      ),
      h('div',{className:'login-card'},
        h('h2',null,'Connexion'),
        h('p',null,'__APP_LOGIN_HINT__'),
        errEl,
        h('form',{onSubmit:submit},
          h('div',{className:'field'},h('label',{'for':'login-email'},'Identifiant ou email'),emailI),
          h('div',{className:'field'},h('label',{'for':'login-password'},'Mot de passe'),pwdWrap),
          h('button',{type:'submit',className:'login-btn',disabled:!!S.loginSubmitting},S.loginSubmitting?'Connexion…':'Se connecter')
        )
      ),
      h('div',{className:'login-footer'},'© __APP_ORG_NAME__ — __APP_NAME__ __V_LABEL__')
    )
  );
}

// ── Animation train d'icônes sur la page de login ─────────────────
// Fait défiler périodiquement une file d'icônes des tuiles du portail
// (edit, wrench, package, printer, calculator, truck, users, file-text,
// clipboard, palette, shield-check, tool) le long d'une trajectoire
// courbe (arc quadratique) aléatoire. Chaque wagon suit le précédent
// avec un léger décalage — effet train. Ne se relance pas tant qu'une
// instance tourne déjà (résiste aux re-renders).
function startLoginTrainAnimation(){
  const layer=document.getElementById('login-train-layer');
  if(!layer) return;
  if(layer.dataset.trainOn==='1') return;
  layer.dataset.trainOn='1';
  layer._paused=false;
  // Métadonnées de chaque icône : nom d'appli + description (miroir du portail).
  const APPS={
    'edit':          {name:'Saisie Prod',    desc:'Saisie opérateur — machine'},
    'wrench':        {name:'MyProd',         desc:'Suivi de production & Planning'},
    'package':       {name:'MyStock',        desc:'Gestion des stocks produits'},
    'printer':       {name:'MyPrint',        desc:'Étiquettes de traçabilité'},
    'calculator':    {name:'MyCompta',       desc:'Comptabilité — accès réservé'},
    'truck':         {name:'MyExpé',         desc:'Expédition & Suivi'},
    'users':         {name:'Planning RH',    desc:'Planning personnel & Congés'},
    'file-text':     {name:'Coûts matières', desc:'Matières, produits et calcul €/m²'},
    'clipboard':     {name:'MyAO',           desc:"Appels d'offre fournisseurs"},
    'palette':       {name:'MyBAT',          desc:'Bons À Tirer — suivi client'},
    'shield-check':  {name:'MyQualité',      desc:'Non-conformités & audits client'},
    'toolbox':       {name:'Maintenance',    desc:'Suivi et planification'}
  };
  const ICONS=Object.keys(APPS);
  const SPACING_PX=72;
  const WAGON_SIZE=42;

  function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
  function pickSide(){return ['top','right','bottom','left'][Math.floor(Math.random()*4)];}
  function pointOnSide(side,W,H){
    const off=WAGON_SIZE*2;
    const inset=80;
    if(side==='top')    return [inset+Math.random()*(W-inset*2), -off];
    if(side==='bottom') return [inset+Math.random()*(W-inset*2),  H+off];
    if(side==='left')   return [-off, inset+Math.random()*(H-inset*2)];
    return [W+off, inset+Math.random()*(H-inset*2)];
  }
  function measurePath(d){
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('width','0');svg.setAttribute('height','0');
    svg.style.cssText='position:absolute;width:0;height:0;visibility:hidden;pointer-events:none';
    const p=document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d',d);
    svg.appendChild(p);document.body.appendChild(svg);
    let L=0;try{L=p.getTotalLength();}catch(e){L=1000;}
    document.body.removeChild(svg);
    return L||1000;
  }
  function escHtmlLocal(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

  function makeWagon(name){
    const w=document.createElement('span');
    w.className='login-wagon';
    const tile=document.createElement('span');
    tile.className='login-wagon-tile';
    tile.setAttribute('aria-label',APPS[name].name);
    tile.innerHTML=icon(name,22);
    const tip=document.createElement('span');
    tip.className='login-wagon-tip';
    tip.innerHTML='<span class="tip-desc">'+escHtmlLocal(APPS[name].desc)+'</span>';

    // Pause / reprise du train + agrandissement + apparition tip via CSS
    tile.addEventListener('mouseenter',()=>{
      layer.classList.add('paused');layer._paused=true;
      w.classList.add('is-hovered'); // wagon passe au-dessus des autres
    });
    tile.addEventListener('mouseleave',()=>{
      layer.classList.remove('paused');layer._paused=false;
      w.classList.remove('is-hovered');
    });
    w.appendChild(tile);
    w.appendChild(tip);
    return w;
  }

  function spawnTrain(){
    const stillHere=document.getElementById('login-train-layer');
    if(!stillHere || stillHere!==layer){ return; }
    if(layer._paused){ setTimeout(spawnTrain,400); return; } // ne pas empiler pendant le hover
    const W=window.innerWidth, H=window.innerHeight;
    const entry=pickSide();
    let exit=pickSide();
    if(exit===entry) exit=({top:'bottom',bottom:'top',left:'right',right:'left'})[entry];
    const [x1,y1]=pointOnSide(entry,W,H);
    const [x2,y2]=pointOnSide(exit,W,H);
    const cx=W*0.5 + (Math.random()-0.5)*W*0.5;
    const cy=H*0.5 + (Math.random()-0.5)*H*0.5;
    const pathStr='M '+x1.toFixed(0)+' '+y1.toFixed(0)+' Q '+cx.toFixed(0)+' '+cy.toFixed(0)+' '+x2.toFixed(0)+' '+y2.toFixed(0);
    const pathLen=measurePath(pathStr);
    const speed=90+Math.random()*40; // 90-130 px/s
    const duration=Math.round(pathLen/speed*1000);
    const wagonGap=Math.round(SPACING_PX/pathLen*duration);
    const wagons=shuffle(ICONS.slice());
    wagons.forEach((name,i)=>{
      const w=makeWagon(name);
      w.style.offsetPath='path("'+pathStr+'")';
      w.style.motionPath=w.style.offsetPath;
      w.style.animationDuration=duration+'ms';
      w.style.animationDelay=(i*wagonGap)+'ms';
      layer.appendChild(w);
      // Removal via animationend (respecte le pause). Fallback timeout large au cas où.
      w.addEventListener('animationend',()=>{if(w.parentNode)w.parentNode.removeChild(w);},{once:true});
      const safety=duration+i*wagonGap+120000; // 2 min de marge en cas de pause longue
      setTimeout(()=>{if(w.parentNode)w.parentNode.removeChild(w);},safety);
    });
    const totalTrainTime=duration + wagons.length*wagonGap;
    const nextWait=Math.max(1200, totalTrainTime - 1500 + Math.random()*3500);
    setTimeout(spawnTrain,nextWait);
  }
  setTimeout(spawnTrain, 900);
}
"""
