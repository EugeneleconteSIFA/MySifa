/* Coûts matières — fiches techniques (matière et produit BOM).
 *
 * Une modale : l'aperçu PDF à gauche du geste, le téléchargement à côté, et
 * pour qui peut écrire, la saisie des caractéristiques. Le PDF est celui que
 * produit le serveur — l'aperçu et le fichier téléchargé sont le même rendu.
 *
 * Exposé : window.PricingFiches.open(objet, id, { canWrite, toast }).
 */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  const ROLES = { FRONTAL: "Frontal", ADHESIF: "Adhésif", GLASSINE: "Dorsal", AUTRE: "Autre" };

  async function api(path, opts) {
    opts = opts || {};
    const res = await fetch(path, {
      method: opts.method || "GET",
      credentials: "include",
      headers: opts.body ? { "Content-Type": "application/json" } : {},
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    let j = null;
    try { j = await res.json(); } catch (e) { /* corps vide */ }
    if (!res.ok) throw new Error((j && typeof j.detail === "string" && j.detail) || "Erreur " + res.status);
    return j;
  }

  function pdfUrl(objet, id, telecharger) {
    return `/api/pricing/fiches/${objet}/${id}/pdf?${telecharger ? "telecharger=1&" : ""}t=${Date.now()}`;
  }

  function formHtml(f) {
    return f.champs.map((c) => {
      const val = f.data[c.cle] || "";
      const h = f.herite[c.cle];
      const ph = h ? "Repris de " + h.source + " : " + h.valeur : "";
      const lab = `${esc(c.label)}${c.unite ? ` <span class="lbl-unit">${esc(c.unite)}</span>` : ""}`;
      const input = c.multi
        ? `<textarea rows="3" data-ft="${esc(c.cle)}" placeholder="${esc(ph)}">${esc(val)}</textarea>`
        : `<input type="text" data-ft="${esc(c.cle)}" value="${esc(val)}" placeholder="${esc(ph)}"/>`;
      const src = h && !val ? ` <span class="ft-src" title="Valeur reprise tant que ce champ reste vide">${esc(h.source)}</span>` : "";
      return `<div class="field"><label>${lab}${src}</label>${input}</div>`;
    }).join("");
  }

  function composantsHtml(f) {
    if (!f.composants.length) return "";
    return `<div class="ft-bom"><div class="ft-bom-t">Composition (BOM)</div>${
      f.composants.map((c) => `<div class="ft-bom-l">
          <span class="ft-bom-r">${esc(ROLES[c.role] || c.role)}</span>
          <span class="ft-bom-n">${esc(c.reference)} <span class="muted">${esc(c.designation || "")}</span></span>
          <button type="button" class="btn btn-soft btn-sm" data-ft-mat="${c.matiere_id}"
            title="${c.renseignee ? "Ouvrir la fiche de cette matière" : "Fiche matière vide — à compléter"}">
            Fiche${c.renseignee ? "" : ' <span class="ft-vide" aria-hidden="true"></span>'}</button>
        </div>`).join("")
    }</div>`;
  }

  async function open(objet, id, opts) {
    opts = opts || {};
    const toast = opts.toast || function () {};
    const root = document.getElementById("modal-root");
    if (!root) return;
    let f;
    try {
      f = await api(`/api/pricing/fiches/${objet}/${id}`);
    } catch (e) {
      toast(e.message, "danger");
      return;
    }
    let edition = false;

    const rendre = () => {
      const maj = f.updated_at
        ? `Mise à jour le ${esc(f.updated_at.slice(0, 10).split("-").reverse().join("/"))}${f.updated_by_name ? " par " + esc(f.updated_by_name) : ""}`
        : "Fiche jamais renseignée — le PDF reprend MyStock et RVGI";
      root.innerHTML = `
        <div class="modal-backdrop" id="ft-back">
          <div class="modal ft-modal" role="dialog" aria-label="Fiche technique">
            <div class="modal-head">
              <h2>Fiche technique · ${esc(f.titre || "")}</h2>
              <button type="button" class="icon-btn" id="ft-close" aria-label="Fermer">×</button>
            </div>
            <div class="ft-meta muted">${objet === "produit" ? "Fiche produit" : "Fiche matière"} · ${maj}</div>
            <div class="ft-corps${edition ? " ft-edition" : ""}">
              ${edition
                ? `<div class="ft-form">${formHtml(f)}</div>`
                : `${composantsHtml(f)}<iframe class="ft-pdf" title="Aperçu de la fiche" src="${pdfUrl(objet, id, false)}"></iframe>`}
            </div>
            <div class="modal-actions">
              ${edition
                ? `<button type="button" class="btn btn-accent" id="ft-save">Enregistrer</button>
                   <button type="button" class="btn btn-soft" id="ft-cancel">Annuler</button>`
                : `<a class="btn btn-accent" href="${pdfUrl(objet, id, true)}" download>Télécharger le PDF</a>
                   <a class="btn btn-soft" href="${pdfUrl(objet, id, false)}" target="_blank" rel="noopener">Ouvrir dans un onglet</a>
                   ${opts.canWrite ? '<button type="button" class="btn btn-soft" id="ft-edit">Modifier la fiche</button>' : ""}
                   <button type="button" class="btn btn-soft" id="ft-fermer">Fermer</button>`}
            </div>
          </div>
        </div>`;

      const fermer = () => { root.innerHTML = ""; };
      document.getElementById("ft-back").onclick = (e) => { if (e.target.id === "ft-back") fermer(); };
      document.getElementById("ft-close").onclick = fermer;
      const b = (idEl, fn) => { const el = document.getElementById(idEl); if (el) el.onclick = fn; };
      b("ft-fermer", fermer);
      b("ft-edit", () => { edition = true; rendre(); });
      b("ft-cancel", () => { edition = false; rendre(); });
      b("ft-save", async () => {
        const data = {};
        root.querySelectorAll("[data-ft]").forEach((el) => { data[el.getAttribute("data-ft")] = el.value; });
        try {
          f = await api(`/api/pricing/fiches/${objet}/${id}`, { method: "PUT", body: { data } });
          toast("Fiche enregistrée.", "success");
          edition = false;
          rendre();
        } catch (e) {
          toast(e.message, "danger");
        }
      });
      root.querySelectorAll("[data-ft-mat]").forEach((el) => {
        el.onclick = () => open("matiere", parseInt(el.getAttribute("data-ft-mat"), 10), opts);
      });
    };
    rendre();
  }

  window.PricingFiches = { open };
})();
