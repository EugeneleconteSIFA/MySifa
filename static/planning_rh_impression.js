/* Planning RH : impression depuis l'application installée sur iPhone.
 *
 * Dans une application ajoutée à l'écran d'accueil, iOS ignore window.print() sans
 * rien signaler : le bouton semble mort. On y produit donc un PDF A4 paysage, remis à
 * la feuille de partage du système, qui propose « Imprimer ». Partout ailleurs, la page
 * continue d'utiliser window.print().
 *
 * html2canvas n'est téléchargé qu'au premier usage.
 */
(function () {
  'use strict';

  var URL_H2C = '/static/html2canvas.min.js';
  var LARGEUR_PX = 1123;               // A4 paysage à 96 dpi : même mise en page que sur un poste
  var ECHELLE = 2;
  var PAGE_L = 841.89, PAGE_H = 595.28, MARGE = 14.17;   // points PDF (marge 0,5 cm, comme @page)
  var UTILE_L = PAGE_L - 2 * MARGE, UTILE_H = PAGE_H - 2 * MARGE;
  var _h2c = null, _enCours = false;

  function estPwaIos() { return window.navigator.standalone === true; }

  function chargerH2C() {
    if (window.html2canvas) return Promise.resolve(window.html2canvas);
    if (_h2c) return _h2c;
    _h2c = new Promise(function (ok, ko) {
      var s = document.createElement('script');
      s.src = URL_H2C;
      s.onload = function () { window.html2canvas ? ok(window.html2canvas) : ko(new Error('html2canvas')); };
      s.onerror = function () { _h2c = null; ko(new Error('html2canvas')); };
      document.head.appendChild(s);
    });
    return _h2c;
  }

  function poserStyles() {
    if (document.getElementById('rh-impr-styles')) return;
    var st = document.createElement('style');
    st.id = 'rh-impr-styles';
    st.textContent =
      // Reprend le bloc @media print de la page, qui ne s'applique pas à une capture.
      '.rh-impr-pdf{position:absolute;left:-20000px;top:0;width:' + LARGEUR_PX + 'px;background:#fff;color:#000;' +
      'font-size:9px;line-height:1.3}' +
      '.rh-impr-pdf .rh-print-pivot-wrap{display:block!important}' +
      '.rh-impr-pdf .rh-pivot-table{border-collapse:collapse;width:100%;margin-bottom:16px}' +
      '.rh-impr-pdf .rh-pivot-table th,.rh-impr-pdf .rh-pivot-table td{border:1px solid #000;font-size:9px;padding:3px 5px}' +
      '.rh-impr-pdf .rh-pivot-table th{font-weight:bold}' +
      // Écran recopié (Congés) : couleurs du thème neutralisées, boutons retirés.
      '.rh-impr-pdf--ecran *{color:#000!important;border-color:#bbb!important;background-color:transparent!important;box-shadow:none!important}' +
      '.rh-impr-pdf--ecran button,.rh-impr-pdf--ecran .rh-icon-btn{display:none!important}' +
      '.rh-impr-barre{position:fixed;left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom));z-index:9000;' +
      'display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--card);color:var(--text);' +
      'border:1px solid var(--border);border-radius:12px;font-size:14px;font-weight:600}' +
      '.rh-impr-barre span{flex:1;min-width:0}' +
      '.rh-impr-barre button{min-height:44px;padding:0 14px;border-radius:10px;border:1px solid var(--border);' +
      'background:transparent;color:var(--text);font:inherit;cursor:pointer}' +
      '.rh-impr-barre button.rh-impr-ok{background:var(--accent);border-color:var(--accent);color:var(--bg)}';
    document.head.appendChild(st);
  }

  /* Coupe de préférence sous une ligne de tableau, jamais au milieu d'un nom. */
  function coupes(noeud, hauteur, hauteurPage) {
    var haut = noeud.getBoundingClientRect().top;
    var bas = Array.prototype.map.call(noeud.querySelectorAll('tr'), function (tr) {
      return tr.getBoundingClientRect().bottom - haut;
    }).sort(function (a, b) { return a - b; });
    var res = [], debut = 0;
    while (hauteur - debut > hauteurPage) {
      var limite = debut + hauteurPage, fin = limite;
      for (var i = bas.length - 1; i >= 0; i--) {
        if (bas[i] <= limite && bas[i] > debut) { fin = bas[i]; break; }
      }
      res.push([debut, fin]);
      debut = fin;
    }
    res.push([debut, hauteur]);
    return res;
  }

  function jpegOctets(canvas) {
    var b64 = canvas.toDataURL('image/jpeg', 0.92).split(',')[1];
    var bin = atob(b64), o = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) o[i] = bin.charCodeAt(i);
    return o;
  }

  /* PDF minimal : une image JPEG par page. images : [{o, l, h, largeurPt, hauteurPt}] */
  function ecrirePdf(images) {
    var morceaux = [], pos = 0, offsets = [];
    var enc = function (s) { var o = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) o[i] = s.charCodeAt(i) & 255; return o; };
    var pousser = function (m) { var o = typeof m === 'string' ? enc(m) : m; morceaux.push(o); pos += o.length; };
    var ouvrir = function (n) { offsets[n] = pos; pousser(n + ' 0 obj\n'); };

    pousser('%PDF-1.4\n');
    var nb = images.length, kids = [];
    for (var k = 0; k < nb; k++) kids.push((3 + k * 3) + ' 0 R');
    ouvrir(1); pousser('<</Type/Catalog/Pages 2 0 R>>\nendobj\n');
    ouvrir(2); pousser('<</Type/Pages/Count ' + nb + '/Kids[' + kids.join(' ') + ']>>\nendobj\n');
    images.forEach(function (im, i) {
      var p = 3 + i * 3;
      var y = (PAGE_H - MARGE - im.hauteurPt).toFixed(2);
      var flux = 'q ' + im.largeurPt.toFixed(2) + ' 0 0 ' + im.hauteurPt.toFixed(2) + ' ' + MARGE + ' ' + y + ' cm /I Do Q';
      ouvrir(p);
      pousser('<</Type/Page/Parent 2 0 R/MediaBox[0 0 ' + PAGE_L + ' ' + PAGE_H + ']/Resources<</XObject<</I ' + (p + 1) + ' 0 R>>>>/Contents ' + (p + 2) + ' 0 R>>\nendobj\n');
      ouvrir(p + 1);
      pousser('<</Type/XObject/Subtype/Image/Width ' + im.l + '/Height ' + im.h + '/ColorSpace/DeviceRGB/BitsPerComponent 8/Filter/DCTDecode/Length ' + im.o.length + '>>\nstream\n');
      pousser(im.o);
      pousser('\nendstream\nendobj\n');
      ouvrir(p + 2);
      pousser('<</Length ' + flux.length + '>>\nstream\n' + flux + '\nendstream\nendobj\n');
    });
    var total = 3 + nb * 3, xref = pos;
    var table = 'xref\n0 ' + total + '\n0000000000 65535 f \n';
    for (var n = 1; n < total; n++) table += String(offsets[n]).padStart(10, '0') + ' 00000 n \n';
    pousser(table + 'trailer\n<</Size ' + total + '/Root 1 0 R>>\nstartxref\n' + xref + '\n%%EOF\n');
    return new Blob(morceaux, { type: 'application/pdf' });
  }

  function fermerBarre() {
    var b = document.getElementById('rh-impr-barre');
    if (b) b.remove();
  }

  function telecharger(fichier) {
    var u = URL.createObjectURL(fichier), a = document.createElement('a');
    a.href = u; a.download = fichier.name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(u); }, 60000);
  }

  function peutPartager(fichier) {
    return !!(navigator.canShare && navigator.share && navigator.canShare({ files: [fichier] }));
  }

  /* Rejette NotAllowedError si le geste de l'utilisateur est trop ancien. */
  function partager(fichier) { return navigator.share({ files: [fichier] }); }

  /* Le calcul du PDF peut épuiser le délai accordé au geste initial : iOS refuse alors
     le partage, et il faut un nouveau toucher pour l'ouvrir. */
  function proposer(fichier, toast) {
    fermerBarre();
    var partage = peutPartager(fichier);
    var b = document.createElement('div');
    b.id = 'rh-impr-barre'; b.className = 'rh-impr-barre'; b.setAttribute('role', 'status');
    var t = document.createElement('span'); t.textContent = 'PDF prêt.';
    var ok = document.createElement('button');
    ok.type = 'button'; ok.className = 'rh-impr-ok';
    ok.textContent = partage ? 'Imprimer' : 'Télécharger';
    ok.onclick = function () {
      if (!partage) { telecharger(fichier); fermerBarre(); return; }
      partager(fichier).then(fermerBarre, function (e) {
        if (e && e.name === 'AbortError') return;
        toast('Partage du PDF refusé par le téléphone — réessayer.', 'error');
      });
    };
    var non = document.createElement('button');
    non.type = 'button'; non.textContent = 'Fermer'; non.onclick = fermerBarre;
    b.appendChild(t); b.appendChild(ok); b.appendChild(non);
    document.body.appendChild(b);
  }

  /* contenu : nœud détaché à imprimer. ecran : true s'il s'agit d'une copie de l'écran. */
  function versPdf(contenu, nomFichier, toast, ecran) {
    if (_enCours) return Promise.resolve();
    _enCours = true;
    fermerBarre();
    poserStyles();
    toast('Préparation du PDF…', 'success');
    var hote = document.createElement('div');
    hote.className = 'rh-impr-pdf' + (ecran ? ' rh-impr-pdf--ecran' : '');
    hote.appendChild(contenu);
    document.body.appendChild(hote);

    return chargerH2C().then(function (h2c) {
      return h2c(hote, { backgroundColor: '#ffffff', scale: ECHELLE, logging: false, windowWidth: LARGEUR_PX });
    }).then(function (canvas) {
      var largeurCss = hote.offsetWidth, hauteurCss = canvas.height / ECHELLE;
      var hauteurPage = largeurCss * UTILE_H / UTILE_L;
      var ptParPx = UTILE_L / largeurCss;
      var images = coupes(hote, hauteurCss, hauteurPage).map(function (c) {
        var h = Math.round((c[1] - c[0]) * ECHELLE);
        var page = document.createElement('canvas');
        page.width = canvas.width; page.height = h;
        var ctx = page.getContext('2d');
        ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, page.width, h);
        ctx.drawImage(canvas, 0, -Math.round(c[0] * ECHELLE));
        return { o: jpegOctets(page), l: page.width, h: h, largeurPt: UTILE_L, hauteurPt: (c[1] - c[0]) * ptParPx };
      });
      var fichier = new File([ecrirePdf(images)], nomFichier, { type: 'application/pdf' });
      if (!peutPartager(fichier)) { proposer(fichier, toast); return; }
      return partager(fichier).catch(function (e) {
        if (e && e.name === 'AbortError') return;
        proposer(fichier, toast);
      });
    }).catch(function () {
      toast('PDF non généré — vérifier la connexion et réessayer.', 'error');
    }).then(function () {
      hote.remove();
      _enCours = false;
    });
  }

  window.RhImpression = { estPwaIos: estPwaIos, versPdf: versPdf };
})();
