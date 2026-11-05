/* MySifa — scanner caméra de codes-barres, partagé.
 *
 * Sorti de MyStock (réception matière, `recepStartCamera`) le 21/10/2026 pour
 * que MyTools › Étiquettes scanne une bobine avec CE scanner-là, et pas un
 * second qui divergerait au premier correctif. MyStock l'appelle toujours
 * sous le même nom : `recepStartCamera` n'est plus qu'un relais.
 *
 *   MySifaScanner.demarrer({ hint, onCode })   ouvre la caméra, rend le code lu à onCode
 *   MySifaScanner.arreter()                    coupe flux et lecteur, retire l'overlay
 *   MySifaScanner.actif()                      true pendant un scan
 *
 * Les pièges sont ceux de la réception et restent documentés ici :
 * getUserMedia en PREMIER await (Android), BarcodeDetector natif sur Android,
 * ZXing ailleurs, fenêtre anti-scan-parasite de 1,5 s, recadrage + rotation
 * pour les codes tenus à la verticale.
 *
 * Styles : classes `camera-*` (définies par la page si elle les a, sinon
 * injectées ici, aux mêmes valeurs).
 */
(function () {
  'use strict';
  if (window.MySifaScanner) return;

  const ZXING_URL = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
  const DELAI_ANTI_PARASITE_MS = 1500;
  const isAndroid = /Android/.test(navigator.userAgent);

  const etat = { scanning: false, stream: null, reader: null, overlay: null };

  function injecterCss() {
    if (document.getElementById('mysifa-scanner-css')) return;
    const st = document.createElement('style');
    st.id = 'mysifa-scanner-css';
    st.textContent =
      '.camera-modal{position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:9500;' +
      'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:20px}' +
      '.camera-wrap{position:relative;width:100%;max-width:360px}' +
      '.camera-video{width:100%;border-radius:16px;display:block}' +
      '.camera-frame{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);' +
      'width:200px;height:200px;border:2px solid var(--accent);border-radius:12px;' +
      'box-shadow:0 0 0 2000px rgba(0,0,0,.5);pointer-events:none}' +
      '.camera-hint{font-size:13px;color:var(--text2);text-align:center;max-width:300px}' +
      '.camera-result{background:var(--accent-bg);border:1px solid var(--accent);border-radius:10px;' +
      'padding:12px 20px;font-family:monospace;font-size:14px;color:var(--accent);text-align:center;min-width:200px}' +
      '.btn-close-cam{background:var(--danger);color:white;border:none;border-radius:12px;' +
      'padding:12px 32px;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit}';
    document.head.appendChild(st);
  }

  function noeud(tag, cls, texte) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (texte != null) e.textContent = texte;
    return e;
  }

  function signaler(msg) {
    if (typeof window.showToast === 'function') window.showToast(msg, 'error');
  }

  function arreter(overlay) {
    if (etat.stream) { etat.stream.getTracks().forEach(t => t.stop()); etat.stream = null; }
    if (etat.reader) { try { etat.reader.reset(); } catch (e) {} etat.reader = null; }
    etat.scanning = false;
    const o = overlay || etat.overlay || document.querySelector('.camera-modal.recep-overlay');
    if (o) o.remove();
    etat.overlay = null;
  }

  async function demarrer(opts) {
    const o = (opts && typeof opts.onCode === 'function') ? opts : {};
    const onFound = o.onCode || function () {};
    if (etat.scanning) return;
    etat.scanning = true;
    injecterCss();

    // Overlay créé en premier (synchrone) — le geste utilisateur est encore actif
    const overlay = noeud('div', 'camera-modal recep-overlay');
    const wrap = noeud('div', 'camera-wrap');
    const video = noeud('video', 'camera-video');
    video.setAttribute('autoplay', '');
    video.setAttribute('playsinline', '');
    const frame = noeud('div', 'camera-frame');
    wrap.append(video, frame);
    const hint = noeud('p', 'camera-hint', o.hint || 'Pointez vers le code-barres de la bobine');
    const resultEl = noeud('div', 'camera-result', 'En attente…');
    const closeBtn = noeud('button', 'btn-close-cam', '× Fermer');
    closeBtn.type = 'button';
    closeBtn.addEventListener('click', () => arreter(overlay));
    overlay.append(wrap, hint, resultEl, closeBtn);
    document.body.appendChild(overlay);
    etat.overlay = overlay;

    try {
      // getUserMedia est le PREMIER await — Android refuse silencieusement si on a fait
      // un await long (chargement ZXing CDN) avant : le "user gesture token" est expiré
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Caméra non disponible (page non HTTPS ?)');
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      etat.stream = stream;
      video.srcObject = stream;

      // Android Chrome 83+ → BarcodeDetector (ML Kit natif : autofocus, codes 1D fins).
      // iOS + repli Android → ZXing (BarcodeDetector absent sur Safari).
      const useNativeDetector = isAndroid && ('BarcodeDetector' in window);

      const debut = Date.now();
      resultEl.textContent = 'Positionnez-vous devant le code…';
      setTimeout(() => { if (etat.scanning) resultEl.textContent = 'En attente…'; }, DELAI_ANTI_PARASITE_MS);

      // Arrêt IMMÉDIAT des deux moteurs dès détection (ZXing continuerait sinon
      // d'appeler le callback pendant le délai d'animation).
      let detecte = false;
      const surCode = (code) => {
        if (Date.now() - debut < DELAI_ANTI_PARASITE_MS) return;
        if (detecte) return;
        detecte = true;
        etat.scanning = false;
        if (etat.reader) { try { etat.reader.reset(); } catch (e) {} etat.reader = null; }
        if (etat.stream) { etat.stream.getTracks().forEach(t => t.stop()); etat.stream = null; }
        resultEl.textContent = '✓ ' + code;
        resultEl.style.color = 'var(--success)';
        setTimeout(() => { overlay.remove(); etat.overlay = null; onFound(code); }, 600);
      };

      if (typeof ZXing === 'undefined') {
        resultEl.textContent = 'Chargement scanner…';
        await new Promise((res, rej) => {
          const s = document.createElement('script');
          s.src = ZXING_URL;
          s.onload = res; s.onerror = rej; document.head.appendChild(s);
        });
        resultEl.textContent = 'En attente…';
      }

      if (useNativeDetector) {
        // Android : BarcodeDetector (codes 1D) + ZXing decodeFromStream (QR)
        const qrHints = new Map();
        qrHints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.QR_CODE]);
        qrHints.set(ZXing.DecodeHintType.TRY_HARDER, true);
        const qrReader = new ZXing.BrowserMultiFormatReader(qrHints);
        etat.reader = qrReader;

        const detector = new BarcodeDetector({
          formats: ['code_128', 'ean_13', 'ean_8', 'data_matrix', 'code_39', 'upc_a', 'upc_e']
        });
        const boucle1D = async () => {
          if (!etat.scanning) return;
          if (video.readyState < 2 || !video.videoWidth) { setTimeout(boucle1D, 100); return; }
          try {
            const found = await detector.detect(video);
            // Pas de `return` ici : une lecture pendant la fenêtre anti-parasite
            // est ignorée et la boucle doit continuer.
            if (found.length > 0) surCode(found[0].rawValue);
          } catch (e) {}
          if (etat.scanning) setTimeout(boucle1D, 150);
        };
        setTimeout(boucle1D, 500);

        // decodeFromStream est la seule méthode ZXing fiable pour les QR sur Android.
        qrReader.decodeFromStream(stream, video, (result) => {
          if (result) surCode(result.getText().trim());
        });
      } else {
        // iOS + repli : ZXing en boucle sur un canevas, tous formats
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        const hints = new Map();
        hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
          ZXing.BarcodeFormat.CODE_128, ZXing.BarcodeFormat.EAN_13, ZXing.BarcodeFormat.EAN_8,
          ZXing.BarcodeFormat.QR_CODE, ZXing.BarcodeFormat.DATA_MATRIX, ZXing.BarcodeFormat.CODE_39
        ]);
        hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
        // MultiFormatReader.decodeWithState() et NON BrowserMultiFormatReader.decode() :
        // cette dernière attend un <video>/<img>, pas un BinaryBitmap.
        const reader = new ZXing.MultiFormatReader();
        reader.setHints(hints);
        etat.reader = reader;
        // Passes alternées : cadrage du viseur puis plus large, dans les deux
        // orientations (RGBLuminanceSource ne sait pas pivoter : on le fait).
        const PASSES = [
          { zoom: 0.56, rot: 0 }, { zoom: 0.56, rot: 90 },
          { zoom: 0.42, rot: 0 }, { zoom: 0.42, rot: 90 },
          { zoom: 0.75, rot: 0 }, { zoom: 0.75, rot: 90 },
        ];
        let passe = 0;
        const boucle = () => {
          if (!etat.scanning) return;
          if (video.readyState < 2 || !video.videoWidth) { setTimeout(boucle, 100); return; }
          try {
            const p = PASSES[passe++ % PASSES.length];
            const side = Math.min(Math.round(video.videoWidth * p.zoom), video.videoHeight);
            const sx = (video.videoWidth - side) / 2, sy = (video.videoHeight - side) / 2;
            canvas.width = side; canvas.height = side;
            if (p.rot) { ctx.translate(side / 2, side / 2); ctx.rotate(Math.PI / 2); ctx.translate(-side / 2, -side / 2); }
            ctx.drawImage(video, sx, sy, side, side, 0, 0, side, side);
            const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
            // RGBA → niveaux de gris : RGBLuminanceSource ne convertit que les Int32Array.
            const gray = new Uint8ClampedArray(canvas.width * canvas.height);
            const px = img.data;
            for (let i = 0, j = 0; i < gray.length; i++, j += 4) gray[i] = (px[j] * 77 + px[j + 1] * 150 + px[j + 2] * 29) >> 8;
            const lum = new ZXing.RGBLuminanceSource(gray, canvas.width, canvas.height);
            const bmp = new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(lum));
            const result = reader.decodeWithState(bmp);
            if (result) surCode(result.getText().trim());
          } catch (e) {}
          if (etat.scanning) setTimeout(boucle, 60);
        };
        setTimeout(boucle, 400);
      }
    } catch (e) {
      const msg = (e && e.message) || '';
      signaler(msg.includes('HTTPS') ? msg : 'Accès caméra refusé');
      arreter(overlay);
    }
  }

  window.MySifaScanner = { demarrer, arreter, actif: () => etat.scanning };
})();
