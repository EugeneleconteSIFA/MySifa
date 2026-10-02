(function(){
  var root=document.documentElement;
  root.classList.add('js');
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Titre du hero : la fin de phrase change toutes les 2,8 s et descend.
     La hauteur suit la variante la plus longue pour que la page ne saute pas. */
  (function(){
    var rot=document.querySelector('.rot');
    if(!rot)return;
    var items=rot.querySelectorAll('.rot-i');
    function fit(){
      var h=0;
      for(var i=0;i<items.length;i++){
        /* Un mot plus large que la colonne serait coupé : on réduit cette
           variante juste assez pour qu'elle tienne. */
        var it=items[i];
        it.style.fontSize='';
        var w=it.clientWidth;
        if(w&&it.scrollWidth>w){it.style.fontSize=(Math.floor(100*w/it.scrollWidth)-1)+'%';}
        h=Math.max(h,it.offsetHeight);
      }
      rot.style.height=h+'px';
    }
    fit();
    window.addEventListener('resize',fit);
    if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);
    if(reduce||items.length<2)return;
    var cur=0;
    setInterval(function(){
      if(document.hidden)return;
      var prev=items[cur];
      cur=(cur+1)%items.length;
      var next=items[cur];
      prev.classList.remove('is-on');prev.classList.add('is-out');
      next.classList.remove('is-out');next.classList.add('is-on');
      setTimeout(function(){prev.classList.remove('is-out');},750);
    },2800);
  })();

  /* Thème */
  var btn=document.getElementById('themeBtn');
  function applyTheme(t){
    root.setAttribute('data-theme',t);
    if(btn)btn.setAttribute('aria-label',t==='dark'?'Passer en thème clair':'Passer en thème sombre');
  }
  try{var saved=localStorage.getItem('sifa-theme');if(saved==='light'||saved==='dark')applyTheme(saved);}catch(e){}
  if(btn)btn.addEventListener('click',function(){
    var t=root.getAttribute('data-theme')==='dark'?'light':'dark';
    applyTheme(t);
    try{localStorage.setItem('sifa-theme',t);}catch(e){}
  });


  /* Mot détouré « ENDUCTEUR » : toujours affiché en entier, sur toute la largeur */
  (function(){
    var f=document.querySelector('.bigfit');
    if(!f)return;
    function fit(){
      f.style.fontSize='100px';
      var w=f.parentNode.clientWidth;
      if(w&&f.scrollWidth)f.style.fontSize=(100*w/f.scrollWidth*0.995)+'px';
    }
    fit();
    window.addEventListener('resize',fit);
    if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);
  })();

  /* Délais d'apparition décalés entre éléments frères */
  document.querySelectorAll('.reveal').forEach(function(el){
    var i=0,s=el.previousElementSibling;
    while(s){if(s.classList&&s.classList.contains('reveal'))i++;s=s.previousElementSibling;}
    el.style.setProperty('--d',Math.min(i*70,420)+'ms');
  });

  /* Compteurs */
  function count(el){
    var end=parseFloat(el.getAttribute('data-count')),suf=el.getAttribute('data-suffix')||'';
    if(reduce){return;}
    var t0=null,d=1300;
    function step(ts){
      if(!t0)t0=ts;
      var p=Math.min((ts-t0)/d,1),v=Math.round(end*(1-Math.pow(1-p,3)));
      el.textContent=v.toLocaleString('fr-FR')+suf;
      if(p<1)requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  var items=document.querySelectorAll('.reveal');
  if(!('IntersectionObserver' in window)||reduce){
    items.forEach(function(el){el.classList.add('in');});
  }else{
    var io=new IntersectionObserver(function(entries){
      entries.forEach(function(en){
        if(!en.isIntersecting)return;
        en.target.classList.add('in');
        en.target.querySelectorAll('[data-count]').forEach(count);
        io.unobserve(en.target);
      });
    },{threshold:.12,rootMargin:'0px 0px -40px 0px'});
    items.forEach(function(el){io.observe(el);});

    /* Section active dans la nav */
    var links=document.querySelectorAll('.nav a[href*="#"]');
    var so=new IntersectionObserver(function(entries){
      entries.forEach(function(en){
        if(!en.isIntersecting)return;
        links.forEach(function(a){var h=a.getAttribute('href')||'';if(h.indexOf('#')<0)return;a.setAttribute('aria-current',h.slice(h.indexOf('#'))==='#'+en.target.id?'true':'false');});
      });
    },{rootMargin:'-45% 0px -50% 0px'});
    document.querySelectorAll('main section[id]').forEach(function(s){so.observe(s);});
  }

  /* Parallaxe légère et écartement de la vue éclatée */
  if(!reduce&&window.matchMedia('(min-width: 901px)').matches){
    var px=[].slice.call(document.querySelectorAll('[data-px]'));
    var lb=document.getElementById('layersBox'),ly=[].slice.call(document.querySelectorAll('.layers .ly'));
    var ticking=false;
    function frame(){
      ticking=false;
      var vh=window.innerHeight;
      px.forEach(function(el){
        var r=el.getBoundingClientRect();
        if(r.bottom<-200||r.top>vh+200)return;
        var c=(r.top+r.height/2-vh/2);
        el.style.transform='translate3d(0,'+(c*parseFloat(el.getAttribute('data-px'))).toFixed(1)+'px,0)'+(el.classList.contains('hero-photo')?' rotate(1.4deg)':el.classList.contains('side')?' rotate(-2.5deg)':'');
      });
      if(lb){
        var r=lb.getBoundingClientRect();
        var p=1-Math.max(0,Math.min(1,(r.top+r.height*.5-vh*.35)/(vh*.6)));
        ly.forEach(function(g){g.style.transform='translateY('+((1-p)*parseFloat(g.getAttribute('data-off'))).toFixed(1)+'px)';});
      }
    }
    function onScroll(){if(!ticking){ticking=true;requestAnimationFrame(frame);}}
    window.addEventListener('scroll',onScroll,{passive:true});
    window.addEventListener('resize',onScroll);
    frame();
  }
})();

/* Formulaire de devis.
   Aperçu MySifa (page en noindex) : aucun envoi, message de maquette.
   Site publié : en attendant un traitement côté serveur, la demande est
   préparée dans la messagerie du visiteur (mailto vers contact@sifa.pro). */
(function(){
  var form=document.getElementById('devis');
  if(!form)return;
  var sel=document.getElementById('f-prod');
  try{
    var p=new URLSearchParams(location.search).get('produit');
    if(p&&sel){for(var i=0;i<sel.options.length;i++){if(sel.options[i].value===p){sel.selectedIndex=i;break;}}}
  }catch(e){}
  var preview=!!document.querySelector('meta[name="robots"][content*="noindex"]');
  form.addEventListener('submit',function(e){
    e.preventDefault();
    var msg=document.getElementById('formMsg');
    if(preview){msg.textContent='Maquette : ce formulaire n\'est pas connecté, aucune donnée n\'a été envoyée.';return;}
    if(!form.checkValidity()){msg.textContent='Adresse e-mail et description du besoin obligatoires.';return;}
    var f=function(n){var el=form.elements[n];return el?el.value.trim():'';};
    var prod=sel&&sel.selectedIndex>0?sel.options[sel.selectedIndex].text:'';
    var body=['Société : '+f('societe'),'Nom : '+f('nom'),'E-mail : '+f('email'),'Téléphone : '+f('tel'),'Produit : '+prod,'Quantité estimée : '+f('quantite'),'','Besoin :',f('message')].join('\n');
    location.href='mailto:contact@sifa.pro?subject='+encodeURIComponent('Demande de devis'+(prod?' : '+prod:''))+'&body='+encodeURIComponent(body);
    msg.textContent='Votre messagerie s\'ouvre avec la demande préremplie. Sinon : contact@sifa.pro.';
  });
})();
