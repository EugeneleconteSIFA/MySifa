/**
 * MySifa — Emojis au clavier dans la messagerie.
 *
 * Deux comportements sur les champs de message (#cw-input du widget,
 * #chat-input de la page Messages) :
 *  - « : » ouvre une liste d'emojis filtrée par ce qui suit (« :pou » → pouce).
 *    Flèches haut/bas pour choisir, Entrée ou Tab pour insérer, Échap pour fermer.
 *  - Un smiley dessiné au clavier devient un emoji : « :) » → 🙂.
 *    Ceux qui finissent par une lettre (« :D », « :P ») attendent l'espace ou
 *    l'envoi, sinon « :D » couperait la recherche « :drapeau ».
 *
 * Chargé par chat_widget.js. Écoute au niveau window (phase de capture) pour
 * passer avant les gestionnaires Entrée des champs : tant que la liste est
 * ouverte, Entrée choisit un emoji au lieu d'envoyer le message.
 */
(function () {
  'use strict';
  if (window.MysifaEmojiAC) return;

  const SELECTEUR = '#cw-input, #chat-input';
  const MAX_ITEMS = 8;

  // [emoji, nom affiché, mots-clés de recherche]
  const EMOJIS = [
    ['🙂', 'sourire', 'content smile'],
    ['😀', 'grand_sourire', 'rire joie heureux'],
    ['😄', 'rire', 'joie heureux lol'],
    ['😂', 'mort_de_rire', 'pleurs rire lol mdr'],
    ['🤣', 'plie_de_rire', 'mdr ptdr lol'],
    ['😅', 'sueur', 'gene ouf rire'],
    ['😉', 'clin_oeil', 'wink'],
    ['😊', 'rougit', 'timide content'],
    ['😍', 'amoureux', 'coeur yeux love'],
    ['🥰', 'adore', 'amour coeurs'],
    ['😘', 'bisou', 'kiss bise'],
    ['😎', 'cool', 'lunettes soleil'],
    ['🤔', 'reflechit', 'hmm pense question'],
    ['🙄', 'yeux_au_ciel', 'blase agace'],
    ['😐', 'neutre', 'bof'],
    ['😕', 'perplexe', 'confus bof'],
    ['😮', 'surpris', 'oh wow etonne'],
    ['😲', 'stupefait', 'choc wow'],
    ['😱', 'horreur', 'peur cri choc'],
    ['😬', 'grimace', 'gene oups'],
    ['😴', 'dort', 'sommeil fatigue'],
    ['🥱', 'baille', 'fatigue sommeil'],
    ['😢', 'triste', 'larme pleure'],
    ['😭', 'pleure', 'triste sanglot'],
    ['😡', 'colere', 'enerve furieux'],
    ['😤', 'agace', 'souffle enerve'],
    ['🤯', 'explose', 'choc cerveau'],
    ['🥳', 'fete', 'anniversaire bravo'],
    ['😇', 'ange', 'innocent'],
    ['🤗', 'calin', 'merci accueil'],
    ['🤐', 'bouche_cousue', 'secret silence'],
    ['🤒', 'malade', 'fievre'],
    ['😛', 'langue', 'taquin tongue'],
    ['😜', 'langue_clin', 'blague taquin'],
    ['🙃', 'a_l_envers', 'ironie'],
    ['😏', 'narquois', 'malin'],
    ['🫡', 'salut', 'respect garde a vous'],
    ['👍', 'pouce', 'ok oui valide top'],
    ['👎', 'pouce_bas', 'non pas bien'],
    ['👌', 'ok', 'parfait nickel'],
    ['👏', 'bravo', 'applaudir clap'],
    ['🙌', 'hourra', 'youpi bravo'],
    ['🙏', 'merci', 'svp priere'],
    ['💪', 'muscle', 'force courage costaud'],
    ['👋', 'coucou', 'bonjour salut main'],
    ['✌️', 'paix', 'victoire deux'],
    ['🤞', 'croise_doigts', 'chance espoir'],
    ['🤝', 'poignee_main', 'accord deal'],
    ['👀', 'yeux', 'regarde voir'],
    ['🫶', 'coeur_mains', 'merci amour'],
    ['❤️', 'coeur', 'amour love rouge'],
    ['🧡', 'coeur_orange', 'amour'],
    ['💛', 'coeur_jaune', 'amour'],
    ['💚', 'coeur_vert', 'amour'],
    ['💙', 'coeur_bleu', 'amour'],
    ['💔', 'coeur_brise', 'triste'],
    ['🔥', 'feu', 'chaud top urgent'],
    ['✨', 'etincelles', 'nouveau magie'],
    ['⭐', 'etoile', 'favori top'],
    ['🎉', 'confettis', 'fete bravo felicitations'],
    ['🎂', 'gateau', 'anniversaire'],
    ['🎁', 'cadeau', 'surprise'],
    ['☕', 'cafe', 'pause'],
    ['🍕', 'pizza', 'repas manger'],
    ['🍺', 'biere', 'apero'],
    ['🥐', 'croissant', 'petit dejeuner'],
    ['🍾', 'champagne', 'fete'],
    ['✅', 'valide', 'fait ok coche termine'],
    ['❌', 'croix', 'non annule erreur'],
    ['⚠️', 'attention', 'alerte danger'],
    ['❓', 'question', 'interrogation'],
    ['❗', 'exclamation', 'important'],
    ['💯', 'cent', 'parfait total'],
    ['🚀', 'fusee', 'lancement rapide go'],
    ['📦', 'colis', 'carton expedition livraison'],
    ['🚚', 'camion', 'livraison transport expedition'],
    ['🏭', 'usine', 'production atelier'],
    ['🔧', 'cle', 'reparation maintenance outil'],
    ['🛠️', 'outils', 'maintenance reparation'],
    ['⚙️', 'engrenage', 'reglage machine'],
    ['🖨️', 'imprimante', 'impression'],
    ['📄', 'document', 'page fichier'],
    ['📎', 'trombone', 'piece jointe'],
    ['📅', 'calendrier', 'date planning'],
    ['⏰', 'reveil', 'heure retard'],
    ['⏳', 'sablier', 'attente patience'],
    ['📈', 'hausse', 'graphique progression'],
    ['📉', 'baisse', 'graphique chute'],
    ['💡', 'idee', 'ampoule astuce'],
    ['📌', 'punaise', 'epingle important'],
    ['🔔', 'cloche', 'notification rappel'],
    ['☀️', 'soleil', 'beau temps'],
    ['🌧️', 'pluie', 'mauvais temps'],
    ['❄️', 'neige', 'froid'],
    ['🎯', 'cible', 'objectif'],
    ['🏆', 'trophee', 'victoire champion'],
    ['🤷', 'haussement', 'sais pas bof'],
    ['🤦', 'facepalm', 'oups consternation'],
  ];

  // Smileys texte → emoji. « immediat » : converti dès le dernier caractère
  // tapé. Les autres attendent un espace ou l'envoi.
  const SMILEYS = [
    [":')", '🥲', true], [":'(", '😢', true],
    [':-)', '🙂', true], [':)', '🙂', true],
    [':-(', '🙁', true], [':(', '🙁', true],
    [';-)', '😉', true], [';)', '😉', true],
    [':*', '😘', true], ['<3', '❤️', true], ['</3', '💔', true],
    [':-D', '😄', false], [':D', '😄', false],
    [':-P', '😛', false], [':P', '😛', false], [':p', '😛', false],
    [':O', '😮', false], [':o', '😮', false],
    ['xD', '😆', false], ['XD', '😆', false],
    [':/', '😕', false], [':|', '😐', false], ['B)', '😎', false],
  ].sort((a, b) => b[0].length - a[0].length);

  const ST = { pop: null, input: null, items: [], idx: 0, start: -1, ignoreStart: -1, busy: false };

  function norm(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  function recents() {
    try { const v = localStorage.getItem('mysifa-recent-emojis'); return v ? JSON.parse(v) : []; } catch (e) { return []; }
  }
  function saveRecent(emoji) {
    try {
      let arr = recents().filter((x) => x !== emoji);
      arr.unshift(emoji);
      localStorage.setItem('mysifa-recent-emojis', JSON.stringify(arr.slice(0, 16)));
    } catch (e) {}
  }

  function candidates(query) {
    const q = norm(query);
    if (!q) {
      const rec = recents();
      const out = [];
      rec.forEach((e) => {
        const found = EMOJIS.find((x) => x[0] === e);
        if (found && out.length < 24) out.push(found);
      });
      EMOJIS.forEach((x) => { if (out.length < 24 && !out.includes(x)) out.push(x); });
      return out;
    }
    const debut = [], dedans = [];
    EMOJIS.forEach((x) => {
      const nom = x[1], mots = norm(x[2]);
      if (nom.startsWith(q)) debut.push(x);
      else if (nom.includes(q) || mots.split(' ').some((m) => m.startsWith(q))) dedans.push(x);
    });
    return debut.concat(dedans).slice(0, 24);
  }

  function injectCss() {
    if (document.getElementById('mysifa-emoji-ac-css')) return;
    const st = document.createElement('style');
    st.id = 'mysifa-emoji-ac-css';
    st.textContent =
      '.mea-pop{position:fixed;z-index:10050;background:var(--card);border:1px solid var(--border);' +
      'border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.25);overflow-y:auto;padding:4px;' +
      'font-family:inherit;min-width:220px}' +
      '.mea-item{display:flex;align-items:center;gap:10px;padding:6px 10px;border-radius:7px;cursor:pointer;' +
      'font-size:13px;color:var(--text)}' +
      '.mea-item .mea-em{font-size:18px;line-height:1;width:22px;text-align:center}' +
      '.mea-item .mea-nom{color:var(--text2);font-family:ui-monospace,monospace;font-size:12px}' +
      '.mea-item.actif{background:var(--accent-bg)}' +
      '.mea-item.actif .mea-nom{color:var(--accent)}' +
      '.mea-aide{padding:6px 10px 4px;font-size:11px;color:var(--muted);border-top:1px solid var(--border);margin-top:4px}';
    document.head.appendChild(st);
  }

  function close() {
    if (ST.pop) ST.pop.remove();
    ST.pop = null; ST.items = []; ST.idx = 0; ST.start = -1;
  }

  function paint() {
    const pop = ST.pop;
    pop.textContent = '';
    ST.items.forEach((x, i) => {
      const it = document.createElement('div');
      it.className = 'mea-item' + (i === ST.idx ? ' actif' : '');
      const em = document.createElement('span'); em.className = 'mea-em'; em.textContent = x[0];
      const nom = document.createElement('span'); nom.className = 'mea-nom'; nom.textContent = x[3] ? x[1] : ':' + x[1] + ':';
      it.appendChild(em); it.appendChild(nom);
      it.addEventListener('mousedown', (e) => { e.preventDefault(); ST.idx = i; choose(); });
      pop.appendChild(it);
    });
    const aide = document.createElement('div');
    aide.className = 'mea-aide';
    aide.textContent = '↑ ↓ pour choisir · Entrée pour insérer · Échap pour fermer';
    pop.appendChild(aide);
    const actif = pop.querySelector('.mea-item.actif');
    if (actif) actif.scrollIntoView({ block: 'nearest' });
    place();
  }

  function place() {
    const r = ST.input.getBoundingClientRect();
    const pop = ST.pop;
    const itemH = 32;
    pop.style.maxHeight = (MAX_ITEMS * itemH + 34) + 'px';
    pop.style.width = Math.max(220, Math.min(300, r.width)) + 'px';
    const h = pop.offsetHeight;
    let top = r.top - h - 6;
    if (top < 8) top = r.bottom + 6;
    let left = r.left;
    if (left + pop.offsetWidth > window.innerWidth - 8) left = window.innerWidth - pop.offsetWidth - 8;
    pop.style.top = top + 'px';
    pop.style.left = Math.max(8, left) + 'px';
  }

  function setValue(inp, value, caret) {
    ST.busy = true;
    inp.value = value;
    inp.setSelectionRange(caret, caret);
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    ST.busy = false;
  }

  function choose() {
    const x = ST.items[ST.idx];
    const inp = ST.input;
    if (!x || !inp) return close();
    const caret = inp.selectionStart;
    const v = inp.value;
    const avant = v.slice(0, ST.start) + x[0] + ' ';
    saveRecent(x[0]);
    close();
    setValue(inp, avant + v.slice(caret), avant.length);
    inp.focus();
  }

  // Le smiley qui précède le curseur, s'il est en début de texte ou après
  // un espace (évite « http:// » ou « 10:30 »).
  function trailingSmiley(before, immediatSeulement) {
    for (const [txt, emoji, immediat] of SMILEYS) {
      if (immediatSeulement && !immediat) continue;
      if (!before.endsWith(txt)) continue;
      const pos = before.length - txt.length;
      if (pos === 0 || /\s/.test(before[pos - 1])) return { pos, txt, emoji };
    }
    return null;
  }

  function convertAt(inp, caret, immediatSeulement) {
    const v = inp.value;
    const s = trailingSmiley(v.slice(0, caret), immediatSeulement);
    if (!s) return false;
    const avant = v.slice(0, s.pos) + s.emoji;
    setValue(inp, avant + v.slice(caret), avant.length);
    return true;
  }

  function onInput(e) {
    const inp = e.target;
    if (ST.busy || !inp.matches || !inp.matches(SELECTEUR)) return;
    const caret = inp.selectionStart;
    if (caret !== inp.selectionEnd) return close();
    const efface = String(e.inputType || '').startsWith('delete');

    if (!efface) {
      const v = inp.value;
      const dernier = v.slice(caret - 1, caret);
      if (/\s/.test(dernier)) {
        // Espace tapé : convertit un smiley « différé » juste avant lui.
        const s = trailingSmiley(v.slice(0, caret - 1), false);
        if (s) {
          const avant = v.slice(0, s.pos) + s.emoji + dernier;
          close();
          setValue(inp, avant + v.slice(caret), avant.length);
          return;
        }
      } else if (convertAt(inp, caret, true)) {
        close();
        return;
      }
    }

    const before = inp.value.slice(0, inp.selectionStart);
    const m = before.match(/(^|\s):([a-z0-9_\u00c0-\u017f]*)$/i);
    if (!m) { ST.ignoreStart = -1; return close(); }
    const start = before.length - m[2].length - 1;
    if (start === ST.ignoreStart) return close();
    let items = candidates(m[2]);
    // « :D », « :P »… : le smiley lui-même en tête de liste. Entrée le
    // convertit et laisse partir le message (voir onKeydown).
    const smiley = trailingSmiley(before, false);
    if (smiley && smiley.pos === start) {
      items = [[smiley.emoji, smiley.txt, '', true]].concat(items.filter((x) => x[0] !== smiley.emoji));
    }
    if (!items.length) return close();
    if (!ST.pop) {
      injectCss();
      ST.pop = document.createElement('div');
      ST.pop.className = 'mea-pop';
      ST.pop.setAttribute('role', 'listbox');
      document.body.appendChild(ST.pop);
    }
    const memeRecherche = ST.input === inp && ST.start === start && ST.items.length === items.length &&
      ST.items.every((x, i) => x[0] === items[i][0]);
    ST.input = inp; ST.start = start; ST.items = items;
    if (!memeRecherche) ST.idx = 0;
    paint();
  }

  function onKeydown(e) {
    const inp = e.target;
    if (!inp.matches || !inp.matches(SELECTEUR) || e.isComposing) return;
    if (ST.pop && ST.input === inp) {
      const stop = () => { e.preventDefault(); e.stopImmediatePropagation(); };
      if (e.key === 'ArrowDown') { stop(); ST.idx = (ST.idx + 1) % ST.items.length; paint(); return; }
      if (e.key === 'ArrowUp') { stop(); ST.idx = (ST.idx - 1 + ST.items.length) % ST.items.length; paint(); return; }
      const choisi = ST.items[ST.idx];
      if (e.key === 'Enter' && !e.shiftKey && choisi && choisi[3]) {
        close();
        convertAt(inp, inp.selectionStart, false);
        return;
      }
      if ((e.key === 'Enter' && !e.shiftKey) || e.key === 'Tab') { stop(); choose(); return; }
      if (e.key === 'Escape') { stop(); ST.ignoreStart = ST.start; close(); return; }
    }
    // Envoi : un smiley en fin de message (« ok :D ») est converti avant
    // que le gestionnaire du champ ne lise la valeur.
    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.altKey) {
      convertAt(inp, inp.selectionStart, false);
    }
  }

  window.addEventListener('input', onInput, true);
  window.addEventListener('keydown', onKeydown, true);
  window.addEventListener('blur', (e) => { if (ST.input && e.target === ST.input) setTimeout(close, 120); }, true);
  window.addEventListener('resize', () => { if (ST.pop) place(); });

  window.MysifaEmojiAC = { close };
})();
