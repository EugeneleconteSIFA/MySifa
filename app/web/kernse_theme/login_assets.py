"""Login DA Kernse — variante utilisée quand `KERNSE_THEME=1`.

Chargée conditionnellement par `app/web/html.py` à la place de
`app/web/login_assets.py`. La fonction exportée par le JS s'appelle
`renderLogin()` (pas d'arguments) pour matcher l'API attendue par
`function render()` dans le monolithe MySifa. Elle utilise les mêmes
helpers globaux : `h()`, `iconEl()`, `S`, `doLogin()`, `MySifaTheme`.

Rendu suivant la maquette Kernse : logo icône K + wordmark bicolore,
gros titre `Bienvenue.` / `Portail interne <Name>.`, tagline riche,
formulaire login avec « Se souvenir de moi » + « Mot de passe oublié ? »,
bouton primary navy, alternatives SSO Azure AD + Badge NFC (visuel,
à connecter plus tard), footer statut opérationnel.

Placeholders substitués par `html.render_frontend_html()` :
    __APP_NAME_PREFIX__ / __APP_NAME_SUFFIX__ (wordmark bicolore)
    __APP_WELCOME_TITLE__ / __APP_WELCOME_SUB__ (gros titre 2 lignes)
    __APP_TAGLINE_RICH__ (tagline riche)
    __APP_LOGIN_HINT__ (accès réservé)
    __APP_STATUS_TEXT__ (Service opérationnel)
    __APP_ORG_NAME__ / __APP_NAME__ (email placeholder + footer)
    __V_LABEL__ / __ENV_NAME_VALUE__ (version + env dans le footer)
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

.login-theme-btn{
  position:fixed;top:18px;right:18px;z-index:10;
  display:inline-flex;align-items:center;gap:8px;
  padding:9px 14px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);
  cursor:pointer;font-size:12px;font-weight:600;font-family:var(--font-sans, inherit);
  transition:border-color .15s,color .15s,box-shadow .2s;
}
.login-theme-btn:hover{color:var(--orange);border-color:var(--orange)}
.login-theme-btn .theme-ico{display:inline-flex;align-items:center;line-height:1}
@media (max-width:480px){.login-theme-btn .theme-label{display:none}}

.k-header{
  display:flex;align-items:center;gap:14px;
  max-width:640px;width:100%;margin:32px 0 24px;
}
.k-logo-icon{
  width:44px;height:44px;border-radius:11px;
  background:var(--navy);color:#fff;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 4px 12px rgba(24,36,68,.15);
  flex-shrink:0;
}
.k-logo-icon svg{width:26px;height:26px}
.k-wordmark{
  font-family:var(--font-brand, 'Poppins', system-ui, sans-serif);font-weight:900;
  font-size:36px;letter-spacing:-1.5px;color:var(--navy);line-height:1;
}
.k-wordmark span{color:var(--orange);margin-left:-3px}

.k-welcome{
  max-width:640px;width:100%;
  font-family:var(--font-brand, 'Poppins', system-ui, sans-serif);font-weight:900;
  font-size:56px;letter-spacing:-2.5px;line-height:1.02;
  color:var(--navy);margin-bottom:18px;
}
.k-welcome-sub{color:var(--navy)}
.k-welcome-sub em{color:var(--orange);font-style:normal}

.k-tagline{
  max-width:640px;width:100%;
  font-size:15px;line-height:1.55;color:var(--text2);
  margin-bottom:36px;
}

.k-login-card{
  max-width:640px;width:100%;
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:32px;
  box-shadow:0 1px 2px rgba(24,36,68,.05),0 12px 32px rgba(24,36,68,.08);
}
.k-login-card h2{
  font-family:var(--font-brand, 'Poppins', system-ui, sans-serif);font-weight:900;
  font-size:22px;letter-spacing:-.5px;color:var(--navy);margin-bottom:6px;
}
.k-login-hint{font-size:13px;color:var(--text2);margin-bottom:24px}

.k-field{margin-bottom:16px}
.k-field label{
  display:block;font-size:11px;font-weight:800;text-transform:uppercase;
  letter-spacing:.6px;color:var(--text2);margin-bottom:8px;
}
.k-field input{
  width:100%;padding:12px 16px;
  border:1px solid var(--border);border-radius:10px;
  background:var(--card);color:var(--text);
  font-size:14px;font-family:var(--font-sans, inherit);
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
.pwd-toggle:hover{color:var(--orange);background:var(--accent-bg, rgba(242,101,43,.12))}

.k-row-options{
  display:flex;align-items:center;justify-content:space-between;
  margin:10px 0 20px;font-size:13px;
}
.k-remember{display:flex;align-items:center;gap:8px;color:var(--text2);cursor:pointer}
.k-remember input[type=checkbox]{width:16px;height:16px;accent-color:var(--orange);cursor:pointer}
.k-forgot{color:var(--orange);text-decoration:none;font-weight:600}
.k-forgot:hover{text-decoration:underline}

.k-btn-primary{
  width:100%;padding:14px 18px;
  background:var(--navy);color:#fff;border:none;border-radius:10px;
  font-weight:800;font-size:14px;font-family:var(--font-sans, inherit);
  cursor:pointer;letter-spacing:.2px;
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  transition:background .15s,transform .1s;
}
.k-btn-primary:hover{background:var(--navy-2, #26314f)}
.k-btn-primary:active{transform:translateY(1px)}
.k-btn-primary:disabled{opacity:.55;cursor:not-allowed}

.k-divider{
  display:flex;align-items:center;gap:12px;
  margin:22px 0 16px;color:var(--muted);font-size:11px;
  text-transform:uppercase;letter-spacing:.6px;font-weight:700;
}
.k-divider::before,.k-divider::after{content:'';flex:1;height:1px;background:var(--border)}

.k-btn-secondary{
  width:100%;padding:13px 18px;margin-bottom:10px;
  background:var(--card);color:var(--navy);
  border:1px solid var(--border);border-radius:10px;
  font-weight:700;font-size:14px;font-family:var(--font-sans, inherit);
  cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;gap:10px;
  transition:border-color .15s,box-shadow .15s;
}
.k-btn-secondary:hover{border-color:var(--navy);box-shadow:0 0 0 3px rgba(24,36,68,.06)}
.k-btn-secondary svg{width:18px;height:18px;flex-shrink:0}
.k-btn-secondary[data-coming-soon]::after{
  content:'bientôt';margin-left:auto;
  font-size:10px;text-transform:uppercase;letter-spacing:.5px;
  color:var(--muted);font-weight:800;
}

.k-footer{
  max-width:640px;width:100%;margin-top:32px;
  display:flex;align-items:center;justify-content:space-between;
  font-size:12px;color:var(--muted);
}
.k-status{display:inline-flex;align-items:center;gap:8px}
.k-status .dot{
  width:8px;height:8px;border-radius:50%;background:var(--success, #1f9d57);
  box-shadow:0 0 0 3px rgba(31,157,87,.15);
}
.k-version{font-family:var(--font-mono, 'JetBrains Mono', monospace);font-weight:600}

.k-err{
  padding:10px 14px;background:var(--danger-bg, rgba(207,59,50,.1));color:var(--danger, #cf3b32);
  border-radius:8px;font-size:13px;font-weight:600;margin-bottom:14px;
}

@media (max-width:640px){
  .k-welcome{font-size:38px;letter-spacing:-1.5px}
  .k-header{margin:16px 0 20px}
  .k-login-card{padding:24px}
}
"""

# ─── JS ──────────────────────────────────────────────────────────────────
# ⚠ IMPORTANT — la fonction s'appelle `renderLogin()` sans args pour matcher
# l'API attendue par `function render()` dans le monolithe MySifa. Elle
# utilise les helpers globaux du portail : `h()`, `iconEl()`, `S`, `render()`,
# `doLogin()`, `MySifaTheme`.
LOGIN_MAIN_JS = r"""
// ── Login DA Kernse ─────────────────────────────────────────────
function renderLogin(){
  const isLight=document.body.classList.contains('light');
  const errEl=S.loginError
    ? h('div',{className:'k-err',id:'login-error'},S.loginError)
    : null;

  const emailI=h('input',{type:'text',id:'login-email',name:'email',
    autocomplete:'username',placeholder:'identifiant ou email'});
  const pwdI=h('input',{type:'password',id:'login-password',name:'password',
    autocomplete:'current-password',placeholder:'••••••••'});
  const pwdToggle=h('button',{type:'button',className:'pwd-toggle',
    'aria-label':'Afficher le mot de passe','aria-pressed':'false',
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

  const submit=(e)=>{
    e.preventDefault();
    if(S.loginSubmitting)return;
    doLogin(emailI.value,pwdI.value);
  };

  const themeBtn=h('button',{type:'button',className:'login-theme-btn',
    'aria-label':'Basculer thème clair/sombre',
    onClick:()=>{
      try{
        const _p=MySifaTheme.loadPrefs();
        const _nm=_p.mode==='light'?'dark':'light';
        MySifaTheme.setPrefs({mode:_nm});
        MySifaTheme.applyPrefs({mode:_nm,palette:'mysifa',style:'defaut',bgAnim:_p.bgAnim});
      }catch(e){}
      render();
    }},
    h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
    h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
  );

  // SVG K stylisé pour l'icône logo
  const kIcon=h('div',{className:'k-logo-icon'});
  kIcon.innerHTML='<svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><rect x="6" y="5" width="4" height="22" rx="1.5" fill="#ffffff"/><path d="M11 15 L20 5 L26 5 L15 15.5 L26 27 L20 27 L11 17 Z" fill="#F2652B"/></svg>';

  return h('div',{className:'login-page'},
    themeBtn,
    h('div',{className:'k-header'},
      kIcon,
      h('div',{className:'k-wordmark'},'__APP_NAME_PREFIX__',h('span',null,'__APP_NAME_SUFFIX__'))
    ),
    h('h1',{className:'k-welcome'},
      '__APP_WELCOME_TITLE__',
      h('br'),
      h('span',{className:'k-welcome-sub'},'__APP_WELCOME_SUB__')
    ),
    h('p',{className:'k-tagline'},'__APP_TAGLINE_RICH__'),
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
          S.loginSubmitting?'Connexion…':'Se connecter'
        )
      ),
      h('div',{className:'k-divider'},'OU'),
      h('button',{type:'button',className:'k-btn-secondary','data-coming-soon':'1',
        onClick:()=>alert('SSO Microsoft Azure AD à venir. Contactez votre administrateur.'),
      },
        (function(){
          const b=document.createElement('span');
          b.innerHTML='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" width="18" height="18"><path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z"/></svg>';
          return b.firstChild;
        })(),
        'SSO — Microsoft Azure AD'
      ),
      h('button',{type:'button',className:'k-btn-secondary','data-coming-soon':'1',
        onClick:()=>alert('Badge NFC atelier à venir. Contactez votre administrateur.'),
      },
        (function(){
          const b=document.createElement('span');
          b.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" width="18" height="18"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/></svg>';
          return b.firstChild;
        })(),
        'Badge NFC / Poste atelier'
      )
    ),
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
