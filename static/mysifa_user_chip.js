/**
 * MySifa — encadré profil sidebar partagé.
 * Avec photo : [avatar] nom + service, puis icône modifier + « Mon profil ».
 */
(function (global) {
  'use strict';

  var DEFAULT_ROLE_LABELS = {
    direction: 'Direction',
    administration: 'Administration',
    fabrication: 'Fabrication',
    logistique: 'Logistique',
    comptabilite: 'Comptabilité',
    expedition: 'Expédition',
    commercial: 'Commercial',
    superadmin: 'Super admin',
  };

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function escAttr(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;');
  }

  function avatarUrl(u) {
    return u && u.avatar_url ? String(u.avatar_url).trim() : '';
  }

  function roleText(u, roleLabels) {
    if (!u) return '';
    if (u.ucSubtext != null && u.ucSubtext !== '') return String(u.ucSubtext);
    var labels = roleLabels || DEFAULT_ROLE_LABELS;
    return labels[u.role] || u.role || '';
  }

  function domAttrs(extra) {
    var a = extra || {};
    if (a.className && !a.cls) a.cls = a.className;
    if (a.cls && !a.className) a.className = a.cls;
    return a;
  }

  function profilLinkHtml(editIconHtml) {
    var ico = editIconHtml || '';
    return '<div class="uc-profil">' + ico + ' Mon profil</div>';
  }

  function innerHtml(u, opts) {
    opts = opts || {};
    var labels = opts.roleLabels || DEFAULT_ROLE_LABELS;
    var nom = esc(u && u.nom ? u.nom : '');
    var role = esc(roleText(u, labels));
    var url = avatarUrl(u);
    var editIco = opts.editIconHtml || '';
    var profil = profilLinkHtml(editIco);
    var showProfil = opts.showProfil !== false;

    if (url) {
      var html =
        '<div class="uc-top">' +
        '<img class="uc-avatar" src="' +
        escAttr(url) +
        '" alt="">' +
        '<div class="uc-info">' +
        '<div class="uc-name">' +
        nom +
        '</div>' +
        '<div class="uc-role">' +
        role +
        '</div>' +
        '</div>' +
        '</div>';
      return showProfil ? html + profil : html;
    }
    var plain =
      '<div class="uc-name">' +
      nom +
      '</div>' +
      '<div class="uc-role">' +
      role +
      '</div>';
    return showProfil ? plain + profil : plain;
  }

  function fill(chip, u, opts) {
    if (!chip || !u) return;
    chip.innerHTML = innerHtml(u, opts || {});
  }

  function children(u, hFn, iconElFn, opts) {
    opts = opts || {};
    var labels =
      opts.roleLabels ||
      (typeof global.ROLE_LABELS !== 'undefined' ? global.ROLE_LABELS : DEFAULT_ROLE_LABELS);
    var h = hFn;
    var url = avatarUrl(u);
    var nom = u && u.nom ? u.nom : '';
    var role = roleText(u, labels);
    var showProfil = opts.showProfil !== false;
    var parts = [];

    if (url) {
      parts.push(
        h(
          'div',
          domAttrs({ className: 'uc-top' }),
          h('img', domAttrs({ className: 'uc-avatar', src: url, alt: '', width: 36, height: 36 })),
          h(
            'div',
            domAttrs({ className: 'uc-info' }),
            h('div', domAttrs({ className: 'uc-name' }), nom),
            h('div', domAttrs({ className: 'uc-role' }), role)
          )
        )
      );
    } else {
      parts.push(h('div', domAttrs({ className: 'uc-name' }), nom));
      parts.push(h('div', domAttrs({ className: 'uc-role' }), role));
    }
    if (showProfil) {
      parts.push(
        h(
          'div',
          domAttrs({ className: 'uc-profil' }),
          iconElFn ? iconElFn('edit', 10) : null,
          ' Mon profil'
        )
      );
    }
    return parts;
  }

  function element(u, hFn, iconElFn, opts) {
    opts = opts || {};
    var h = hFn;
    var cls = opts.chipClass || 'user-chip';
    var chipOpts = domAttrs({
      className: cls,
      style: Object.assign({ cursor: 'pointer' }, opts.style || {}),
      title: opts.title || 'Mon profil',
      onClick:
        opts.onClick ||
        function () {
          global.location.href = '/profil';
        },
    });
    return h('div', chipOpts, children(u, hFn, iconElFn, opts));
  }

  global.MySifaUserChip = {
    innerHtml: innerHtml,
    fill: fill,
    children: children,
    element: element,
    roleText: roleText,
    avatarUrl: avatarUrl,
    DEFAULT_ROLE_LABELS: DEFAULT_ROLE_LABELS,
  };
})(typeof window !== 'undefined' ? window : this);
