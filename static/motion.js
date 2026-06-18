/* ============================================================
   MySifa - motion.js
   Couche d'animation. Initialise les 6 patterns de motion.css :
     1. data-page-enter : cascade d'entree (pose --i sur enfants)
     2. .mo-reveal      : reveal au scroll via IntersectionObserver
     3. data-count-to   : compteurs chiffres en format fr-FR
     4. .mo-live        : pulse + statusChange() anneau au changement
     5. data-nav-indicator + .nav-ind : indicateur glissant
     6. skeleton(), fadeInChildren() : chargement par squelette
   API : window.Motion (scan, pageEnter, reveal, count, nav,
   statusChange, skeleton, fadeInChildren, reduced).
   Auto-init au DOMContentLoaded.
   ============================================================ */
(function(){
  'use strict';

  var Motion = {};

  function reduced(){
    try {
      if (document.body && document.body.classList.contains('reduce-anim')) return true;
      if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return true;
    } catch(e){}
    return false;
  }
  Motion.reduced = reduced;

  // ---------- 1. Page-enter cascade ----------
  Motion.pageEnter = function(el){
    if(!el) return;
    var kids = el.children;
    if(reduced()){
      for(var i=0;i<kids.length;i++){ kids[i].style.removeProperty('--i'); }
      return;
    }
    for(var j=0;j<kids.length;j++){
      kids[j].style.setProperty('--i', String(j));
    }
  };

  // ---------- 2. Scroll reveal ----------
  var revealObserver = null;
  var revealQueue = [];
  var revealTimer = null;

  function flushRevealQueue(){
    revealTimer = null;
    revealQueue.sort(function(a,b){
      return (a.getBoundingClientRect().top||0) - (b.getBoundingClientRect().top||0);
    });
    revealQueue.forEach(function(el, i){
      setTimeout(function(){ el.classList.add('is-in'); }, i * 55);
    });
    revealQueue = [];
  }

  function getRevealObserver(){
    if(revealObserver) return revealObserver;
    if(typeof IntersectionObserver === 'undefined') return null;
    revealObserver = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if(entry.isIntersecting){
          revealQueue.push(entry.target);
          revealObserver.unobserve(entry.target);
          if(!revealTimer) revealTimer = setTimeout(flushRevealQueue, 30);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    return revealObserver;
  }

  Motion.reveal = function(el){
    if(!el) return;
    if(reduced()){ el.classList.add('is-in'); return; }
    var obs = getRevealObserver();
    if(!obs){ el.classList.add('is-in'); return; }
    obs.observe(el);
  };

  // ---------- 3. Count-up ----------
  function frFormat(value, decimals){
    try {
      return value.toLocaleString('fr-FR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      });
    } catch(e) {
      return decimals > 0 ? value.toFixed(decimals) : String(Math.round(value));
    }
  }

  Motion.count = function(el){
    if(!el) return;
    if(el.dataset.countDone === '1') return;
    var target = parseFloat(String(el.dataset.countTo || '0').replace(',', '.'));
    if(isNaN(target)) return;
    var suffix = el.dataset.suffix || '';
    var prefix = el.dataset.prefix || '';
    var decimals = parseInt(el.dataset.decimals || '0', 10) || 0;
    var duration = parseInt(el.dataset.duration || '900', 10) || 900;
    el.dataset.countDone = '1';
    if(reduced()){ el.textContent = prefix + frFormat(target, decimals) + suffix; return; }
    var start = performance.now();
    function step(now){
      var t = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - t, 3);
      var v = target * eased;
      el.textContent = prefix + frFormat(v, decimals) + suffix;
      if(t < 1) requestAnimationFrame(step);
      else el.textContent = prefix + frFormat(target, decimals) + suffix;
    }
    requestAnimationFrame(step);
  };

  var countObserver = null;
  function getCountObserver(){
    if(countObserver) return countObserver;
    if(typeof IntersectionObserver === 'undefined') return null;
    countObserver = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if(entry.isIntersecting){
          Motion.count(entry.target);
          countObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.25 });
    return countObserver;
  }

  // ---------- 4. Status change ring ----------
  Motion.statusChange = function(dot, ringColor, keepPulsing){
    if(!dot) return;
    if(ringColor) dot.style.setProperty('--ring-c', ringColor);
    try { dot.style.animation = 'none'; void dot.offsetWidth; } catch(e){}
    dot.style.animation = 'mo-pulse-ring 0.55s var(--ease-out)';
    setTimeout(function(){
      dot.style.animation = '';
      if(keepPulsing) dot.classList.add('mo-live');
      else dot.classList.remove('mo-live');
    }, 580);
  };

  // ---------- 5. Nav indicator ----------
  Motion.nav = function(navEl){
    if(!navEl) return;
    var ind = navEl.querySelector('.nav-ind');
    if(!ind) return;
    var active = navEl.querySelector('.navitem.active');
    if(!active){
      ind.style.opacity = '0';
      return;
    }
    var navRect = navEl.getBoundingClientRect();
    var aRect = active.getBoundingClientRect();
    ind.style.transition = reduced() ? 'none' : ('transform var(--mo-base) var(--ease-out), width var(--mo-base) var(--ease-out), height var(--mo-base) var(--ease-out)');
    ind.style.opacity = '1';
    ind.style.transform = 'translate(' + (aRect.left - navRect.left) + 'px,' + (aRect.top - navRect.top) + 'px)';
    ind.style.width = aRect.width + 'px';
    ind.style.height = aRect.height + 'px';
  };

  // ---------- 6. Skeleton / fadeInChildren ----------
  Motion.skeleton = function(container, rows, cols){
    if(!container) return;
    rows = rows || 3;
    cols = cols || 3;
    var html = '';
    for(var r=0;r<rows;r++){
      html += '<div class="mo-sk-row">';
      for(var c=0;c<cols;c++){
        var w = 60 + Math.floor(Math.random() * 100);
        html += '<div class="mo-skeleton" style="height:14px;width:' + w + 'px"></div>';
      }
      html += '</div>';
    }
    container.innerHTML = html;
  };

  Motion.fadeInChildren = function(container){
    if(!container) return;
    var kids = container.children;
    if(reduced()){
      for(var i=0;i<kids.length;i++){
        kids[i].style.opacity = '';
        kids[i].style.transform = '';
      }
      return;
    }
    for(var j=0;j<kids.length;j++){
      (function(c, idx){
        c.style.opacity = '0';
        c.style.transform = 'translateY(14px)';
        c.style.transition = 'opacity 0.28s var(--ease-out), transform 0.28s var(--ease-out)';
        c.style.transitionDelay = (idx * 55) + 'ms';
        requestAnimationFrame(function(){
          requestAnimationFrame(function(){
            c.style.opacity = '1';
            c.style.transform = '';
          });
        });
      })(kids[j], j);
    }
  };

  // ---------- Scan helper ----------
  Motion.scan = function(root){
    root = root || document;
    // 1. Page-enter : (re)pose --i sur les enfants si pas deja fait
    var enters = root.querySelectorAll ? root.querySelectorAll('[data-page-enter]') : [];
    for(var i=0;i<enters.length;i++){
      var el = enters[i];
      if(el.dataset.moEntered === '1') continue;
      Motion.pageEnter(el);
      el.dataset.moEntered = '1';
    }
    // 2. Reveal au scroll
    var reveals = root.querySelectorAll ? root.querySelectorAll('.mo-reveal:not(.is-in)') : [];
    for(var j=0;j<reveals.length;j++){
      if(reveals[j].dataset.moRevealArmed === '1') continue;
      reveals[j].dataset.moRevealArmed = '1';
      Motion.reveal(reveals[j]);
    }
    // 3. Count-up
    var counts = root.querySelectorAll ? root.querySelectorAll('[data-count-to]') : [];
    for(var k=0;k<counts.length;k++){
      var ce = counts[k];
      if(ce.dataset.countDone === '1') continue;
      var obs = getCountObserver();
      if(obs) obs.observe(ce);
      else Motion.count(ce);
    }
    // 5. Nav indicator
    var navs = root.querySelectorAll ? root.querySelectorAll('[data-nav-indicator]') : [];
    for(var l=0;l<navs.length;l++){
      Motion.nav(navs[l]);
    }
  };

  // Auto-init
  function boot(){ try { Motion.scan(document); } catch(e){} }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  // Re-scan sur resize (pour l'indicateur de nav)
  var resizeTimer = null;
  window.addEventListener('resize', function(){
    if(resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function(){
      try {
        var navs = document.querySelectorAll('[data-nav-indicator]');
        for(var i=0;i<navs.length;i++){ Motion.nav(navs[i]); }
      } catch(e){}
    }, 80);
  });

  window.Motion = Motion;
})();
