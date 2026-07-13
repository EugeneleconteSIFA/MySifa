"""Login DA Kernse — variante utilisée quand `KERNSE_THEME=1`.

Chargée conditionnellement par `app/web/html.py` à la place de
`app/web/login_assets.py` (le login MySifa historique). Le rendu suit la
maquette Kernse : logo icône K + wordmark, gros titre `Bienvenue.` /
`Portail interne <Name>.`, tagline riche multi-ligne, formulaire login
avec « Se souvenir de moi » et « Mot de passe oublié ? », bouton primary
navy, alternatives SSO Azure AD + Badge NFC (visuelles pour l'instant,
à connecter aux endpoints existants plus tard), footer statut opérationnel.

Placeholders substitués par `html.render_frontend_html()` (défauts
paramétrables via env vars — cf. `config.py`) :
    __APP_NAME_PREFIX__ / __APP_NAME_SUFFIX__ (wordmark bicolore)
    __APP_WELCOME_TITLE__ / __APP_WELCOME_SUB__ (gros titre 2 lignes)
    __APP_TAGLINE_RICH__ (tagline riche)
    __APP_LOGIN_HINT__ (accès réservé au personnel Kernse)
    __APP_STATUS_TEXT__ (Service opérationnel)
    __APP_ORG_NAME__ / __APP_NAME__ (footer)
    __V_LABEL__ (version dans le footer)
"""

# ─── CSS ─────────────────────────────────────────────────────────────────
LOGIN_MAIN_CSS = r"""
/* Kernse — Login DA (navy/orange/crème) */
.login-page{
  position:relative;z-index:1;min-height:100vh;
  display:flex;flex-direction:column;align-items:center;justify-content:flex-start;
  padding:48px 24px 24px;
  background:var(--bg);
}

/* Bouton thème (garde le pattern MySifa mais couleurs Kernse) */
.login-theme-btn{
  position:fixed;top:18px;right:18px;z-index:10;
  display:inline-flex;align-items:center;gap:8px;
  padding:9px 14px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);
  cursor:pointer;font-size:12px;font-weight:600;font-family:var(--font-sans);
  transition:border-color .15s,color .15s,box-shadow .2s;
}
.login-theme-btn:hover{color:var(--orange);border-color:var(--orange)}
.login-theme-btn .theme-ico{display:inline-flex;align-items:center;line-height:1}
@media (max-width:480px){.login-theme-btn .theme-label{display:none}

/* En-tête : logo icône K + wordmark côte à côte */
.k-header{
  display:flex;align-items:center;gap:14px;
  max-width:640px;width:100%;margin:32px 0 24px;
}
.k-logo-icon{
  width:44px;height:44px;border-radius:11px;
  background:var(--navy);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-family:var(--font-brand);font-weight:900;
  box-shadow:0 4px 12px rgba(24,36,68,.15);
  flex-shrink:0;
}
.k-logo-icon svg{width:24px;height:24px}
.k-wordmark{
  font-family:var(--font-brand);font-weight:900;
  font-size:36px;letter-spacing:-1.5px;color:var(--navy);line-height:1;
}
.k-wordmark span{color:var(--orange);margin-left:-3px}

/* Gros titre "Bienvenue. Portail interne <Nom>." */
.k-welcome{
  max-width:640px;width:100%;
  font-family:var(--font-brand);font-weight:900;
  font-size:56px;letter-spacing:-2.5px;line-height:1.02;
  color:var(--navy);margin-bottom:18px;
}
.k-welcome-sub{color:var(--navy)}
.k-welcome-sub em{color:var(--orange);font-style:normal}

/* Tagline riche */
.k-tagline{
  max-width:640px;width:100%;
  font-size:15px;line-height:1.55;color:var(--text2);
  margin-bottom:36px;
}

/* Card login */
.k-login-card{
  max-width:640px;width:100%;
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:32px;
  box-shadow:0 1px 2px rgba(24,36,68,.05),0 12px 32px rgba(24,36,68,.08);
}
.k-login-card h2{
  font-family:var(--font-brand);font-weight:900;
  font-size:22px;letter-spacing:-.5px;color:var(--navy);margin-bottom:6px;
}
.k-login-hint{
  font-size:13px;color:var(--text2);margin-bottom:24px;
}

.k-field{margin-bottom:16px}
.k-field label{
  display:block;font-size:11px;font-weight:800;text-transform:uppercase;
  letter-spacing:.6px;color:var(--text2);margin-bottom:8px;
}
.k-field input{
  width:100%;padding:12px 16px;
  border:1px solid var(--border);border-radius:10px;
  background:var(--card);color:var(--text);
  font-size:14px;font-family:var(--font-sans);
  transition:border-color .15s,box-shadow .15s;
}
.k-field input:focus{
  outline:none;border-color:var(--orange);
  box-shadow:0 0 0 3px rgba(242,101,43,.15);
}
.pwd-wrap{position:relative}
.pwd-wrap input{padding-right:44px}
.pwd-toggle{
  position:absolute;top:50%;right:8px;transform:translateY(-50%);
  display:inline-flex;align-items:center;justify-content:center;
  width:32px;height:32px;border:none;background:transparent;cursor:pointer;
  color:var(--muted);border-radius:8px;padding:0;font-family:inherit;
}
.pwd-toggle:hover{color:var(--orange);background:var(--orange-bg)}

/* Ligne "Se souvenir de moi" + "Mot de passe oublié ?" */
.k-row-options{
  display:flex;align-items:center;justify-content:space-between;
  margin:10px 0 20px;font-size:13px;
}
.k-remember{display:flex;align-items:center;gap:8px;color:var(--text2);cursor:pointer}
.k-remember input[type=checkbox]{
  width:16px;height:16px;accent-color:var(--orange);cursor:pointer;
}
.k-forgot{color:var(--orange);text-decoration:none;font-weight:600}
.k-forgot:hover{text-decoration:underline}

/* Bouton primary NAVY (pas orange !) */
.k-btn-primary{
  width:100%;padding:14px 18px;
  background:var(--navy);color:#fff;border:none;border-radius:10px;
  font-weight:800;font-size:14px;font-family:var(--font-sans);
  cursor:pointer;letter-spacing:.2px;
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  transition:background .15s,transform .1s;
}
.k-btn-primary:hover{background:var(--navy-2)}
.k-btn-primary:active{transform:translateY(1px)}
.k-btn-primary:disabled{opacity:.55;cursor:not-allowed}

/* Divider "OU" */
.k-divider{
  display:flex;align-items:center;gap:12px;
  margin:22px 0 16px;color:var(--muted);font-size:11px;
  text-transform:uppercase;letter-spacing:.6px;font-weight:700;
}
.k-divider::before,.k-divider::after{
  content:'';flex:1;height:1px;background:var(--border);
}

/* Boutons secondaires (SSO + Badge NFC) */
.k-btn-secondary{
  width:100%;padding:13px 18px;margin-bottom:10px;
  background:var(--card);color:var(--navy);
  border:1px solid var(--border);border-radius:10px;
  font-weight:700;font-size:14px;font-family:var(--font-sans);
  cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;gap:10px;
  transition:border-color .15s,box-shadow .15s;
}
.k-btn-secondary:hover{
  border-color:var(--navy);
  box-shadow:0 0 0 3px rgba(24,36,68,.06);
}
.k-btn-secondary svg{width:18px;height:18px;flex-shrink:0}
.k-btn-secondary[data-coming-soon]::after{
  content:'bientôt';margin-left:auto;
  font-size:10px;text-transform:uppercase;letter-spacing:.5px;
  color:var(--muted);font-weight:800;
}

/* Footer */
.k-footer{
  max-width:640px;width:100%;margin-top:32px;
  display:flex;align-items:center;justify-content:space-between;
  font-size:12px;color:var(--muted);
}
.k-status{display:inline-flex;align-items:center;gap:8px}
.k-status .dot{
  width:8px;height:8px;border-radius:50%;background:var(--success);
  box-shadow:0 0 0 3px rgba(31,157,87,.15);
}
.k-version{font-family:var(--font-mono);font-weight:600}

/* Message d'erreur */
.k-err{
  padding:10px 14px;background:var(--danger-bg);color:var(--danger);
  border-radius:8px;font-size:13px;font-weight:600;margin-bottom:14px;
}

/* Responsive */
@media (max-width:640px){
  .k-welcome{font-size:38px;letter-spacing:-1.5px}
  .k-header{margin:16px 0 20px}
  .k-login-card{padding:24px}
}
"""

# ─── JS (rendu React-in-string) ──────────────────────────────────────────
LOGIN_MAIN_JS = r"""
function LoginView({S, set}){
  const submit=async(ev)=>{
    ev.preventDefault();
    if(S.loginSubmitting) return;
    set({loginErr:null,loginSubmitting:true});
    const fd=new FormData(ev.target);
    try{
      const r=await fetch('/api/auth/login',{
        method:'POST',credentials:'include',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          email:fd.get('email'),
          password:fd.get('password'),
          remember:fd.get('remember')==='on',
        }),
      });
      if(!r.ok){
        const d=await r.json().catch(()=>({}));
        set({loginErr:d.detail||'Identifiants invalides.',loginSubmitting:false});
        return;
      }
      const u=await api('/api/auth/me');
      S.user=u;
      try{ MySifaTheme.mergeFromUser(u); }catch(e){}
      S.app='portal';
      set({loginSubmitting:false,loginErr:null});
    }catch(e){
      set({loginErr:e.message||'Erreur réseau.',loginSubmitting:false});
    }
  };

  const emailI=h('input',{
    id:'login-email',type:'email',name:'email',
    required:true,autoComplete:'username',autoFocus:true,
    placeholder:'julie.perez@__APP_ORG_NAME__.fr',
  });
  const pwdI=h('input',{
    id:'login-password',type:'password',name:'password',
    required:true,autoComplete:'current-password',
    placeholder:'••••••••',
  });
  const pwdWrap=h('div',{className:'pwd-wrap'},pwdI,
    h('button',{type:'button',className:'pwd-toggle',
      onClick:()=>{const i=document.getElementById('login-password');
        if(!i)return;i.type=i.type==='password'?'text':'password';},
      'aria-label':'Afficher le mot de passe'},
      iconEl('eye',18)
    )
  );

  const errEl=S.loginErr
    ? h('div',{className:'k-err'},S.loginErr)
    : null;

  const isLight=document.body.classList.contains('light');
  const themeBtn=h('button',{className:'login-theme-btn',type:'button',
    onClick:()=>{try{MySifaTheme.toggleMode();render();}catch(e){} },
    'aria-label':'Basculer thème'},
    h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
    h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
  );

  return h('div',{className:'login-page'},
    themeBtn,
    // En-tête : icône K + wordmark
    h('div',{className:'k-header'},
      h('div',{className:'k-logo-icon'},
        // SVG stylisé "K" — bâton vertical + branches orange
        h('svg',{viewBox:'0 0 32 32',fill:'none','aria-hidden':'true'},
          h('rect',{x:'6',y:'5',width:'4',height:'22',rx:'1.5',fill:'#ffffff'}),
          h('path',{d:'M11 15 L20 5 L26 5 L15 15.5 L26 27 L20 27 L11 17 Z',fill:'#F2652B'})
        )
      ),
      h('div',{className:'k-wordmark'},'__APP_NAME_PREFIX__',h('span',null,'__APP_NAME_SUFFIX__'))
    ),
    // Gros titre "Bienvenue. Portail interne <Name>."
    h('h1',{className:'k-welcome'},
      '__APP_WELCOME_TITLE__',
      h('br'),
      h('span',{className:'k-welcome-sub'},
        // On split le APP_WELCOME_SUB pour colorer le nom : détection heuristique
        // via className CSS ; par défaut tout en navy sauf le mot APP_NAME souligné orange.
        '__APP_WELCOME_SUB__'
      )
    ),
    // Tagline riche
    h('p',{className:'k-tagline'},'__APP_TAGLINE_RICH__'),
    // Card login
    h('div',{className:'k-login-card'},
      h('h2',null,'Connexion'),
      h('p',{className:'k-login-hint'},'__APP_LOGIN_HINT__'),
      errEl,
      h('form',{onSubmit:submit},
        h('div',{className:'k-field'},
          h('label',{'for':'login-email'},'Identifiant ou email'),
          emailI
        ),
        h('div',{className:'k-field'},
          h('label',{'for':'login-password'},'Mot de passe'),
          pwdWrap
        ),
        h('div',{className:'k-row-options'},
          h('label',{className:'k-remember'},
            h('input',{type:'checkbox',name:'remember',defaultChecked:false}),
            'Se souvenir de moi'
          ),
          h('a',{className:'k-forgot',href:'#',
            onClick:(e)=>{e.preventDefault();alert('Fonction à venir : contactez votre administrateur.');}
          },'Mot de passe oublié ?')
        ),
        h('button',{type:'submit',className:'k-btn-primary',
          disabled:!!S.loginSubmitting},
          S.loginSubmitting ? 'Connexion…' : [
            h('span',null,'→'),
            ' Se connecter'
          ]
        )
      ),
      h('div',{className:'k-divider'},'OU'),
      // SSO Azure AD (visuel — à connecter à un endpoint OIDC plus tard)
      h('button',{type:'button',className:'k-btn-secondary','data-coming-soon':'1',
        onClick:()=>alert('SSO Microsoft Azure AD à venir. Contactez votre administrateur.'),
      },
        h('svg',{viewBox:'0 0 24 24',fill:'currentColor','aria-hidden':'true'},
          h('path',{d:'M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z'})
        ),
        'SSO — Microsoft Azure AD'
      ),
      // Badge NFC (visuel — à connecter à l'endpoint /api/auth/nfc plus tard)
      h('button',{type:'button',className:'k-btn-secondary','data-coming-soon':'1',
        onClick:()=>alert('Badge NFC atelier à venir. Contactez votre administrateur.'),
      },
        h('svg',{viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'2','aria-hidden':'true'},
          h('circle',{cx:'12',cy:'12',r:'10'}),
          h('path',{d:'M9 12l2 2 4-4'})
        ),
        'Badge NFC / Poste atelier'
      )
    ),
    // Footer
    h('div',{className:'k-footer'},
      h('span',{className:'k-status'},
        h('span',{className:'dot'}),
        '__APP_STATUS_TEXT__'
      ),
      h('span',{className:'k-version'},'__V_LABEL__ · __ENV_NAME_VALUE__')
    )
  );
}
"""
