/* Domyos Rower card - shipped with the domyos_rower integration, no dependency. */
const DOMAIN = "domyos_rower";

const TXT = {
  fr: {
    start: "Démarrer la séance", stop: "Terminer la séance",
    ready: "Prêt à enregistrer", recording: "Enregistrement en cours",
    time: "Temps", pace: "Allure /500 m", distance: "Distance", cadence: "Cadence",
    strokes: "Coups", power: "Puissance", calories: "Calories",
    resistance: "Résistance", plug: "Prise rameur", bluetooth: "Bluetooth", program: "Pyramides",
    on: "Allumée", off: "Éteinte", active: "Activé", inactive: "Désactivé",
    chartLive: "Séance en cours", chartLast: "Dernière séance", chartNone: "Aucune séance à afficher",
    last: "Dernière séance", none: "Aucune séance", files: "Générer les fichiers",
    garmin: "Envoyer à Garmin", sent: "Envoyée", failed: "Échec de l'envoi", notSent: "Pas encore envoyée",
    noEntities: "Aucune entité Domyos Rower trouvée. Vérifie que l'intégration est installée.",
    level: "Niveau",
    connected: "Connecté", searching: "Recherche…", connecting: "Connexion…", error: "Erreur",
    workout: "Entraînement", wkNone: "Aucun", wkTitle: "Entraînements", wkNew: "Nouveau", wkNewName: "Nouvel entraînement",
    wkHelp: "L'entraînement choisi démarre avec la séance, se met en pause quand tu arrêtes de ramer et s'arrête avec la séance. Tu peux toujours changer la résistance à la main : le palier suivant la remplace.",
    wkNoneRow: "Aucun entraînement", wkEdit: "Modifier", wkDup: "Dupliquer", wkDel: "Supprimer", wkCopy: "copie",
    wkConfirmDel: "Supprimer cet entraînement ?", wkBack: "Retour", wkSave: "Enregistrer", wkCancel: "Annuler",
    wkName: "Nom", wkEnd: "Niveau à la fin", wkBlock: "Bloc", wkRepeat: "Répéter", wkAddStep: "Ajouter un palier",
    wkAddBlock: "Ajouter un bloc", wkDelBlock: "Supprimer le bloc", wkDuration: "Durée (m:ss)", wkTotal: "Durée totale",
    wkSteps: "paliers", wkLoading: "Chargement…", wkErr: "Impossible de contacter l'intégration.",
    paused: "En pause", finished: "Terminé", wkProfile: "Profil de résistance",
  },
  en: {
    start: "Start session", stop: "End session",
    ready: "Ready to record", recording: "Recording",
    time: "Time", pace: "Pace /500 m", distance: "Distance", cadence: "Cadence",
    strokes: "Strokes", power: "Power", calories: "Calories",
    resistance: "Resistance", plug: "Rower plug", bluetooth: "Bluetooth", program: "Pyramids",
    on: "On", off: "Off", active: "Active", inactive: "Inactive",
    chartLive: "Current session", chartLast: "Last session", chartNone: "No session to show",
    last: "Last session", none: "No session", files: "Generate files",
    garmin: "Send to Garmin", sent: "Sent", failed: "Upload failed", notSent: "Not sent yet",
    noEntities: "No Domyos Rower entity found. Check that the integration is installed.",
    level: "Level",
    connected: "Connected", searching: "Searching…", connecting: "Connecting…", error: "Error",
    workout: "Workout", wkNone: "None", wkTitle: "Workouts", wkNew: "New", wkNewName: "New workout",
    wkHelp: "The chosen workout starts with the session, pauses when you stop rowing and ends with the session. You can still change the resistance by hand: the next step replaces it.",
    wkNoneRow: "No workout", wkEdit: "Edit", wkDup: "Duplicate", wkDel: "Delete", wkCopy: "copy",
    wkConfirmDel: "Delete this workout?", wkBack: "Back", wkSave: "Save", wkCancel: "Cancel",
    wkName: "Name", wkEnd: "Level at the end", wkBlock: "Block", wkRepeat: "Repeat", wkAddStep: "Add a step",
    wkAddBlock: "Add a block", wkDelBlock: "Delete block", wkDuration: "Duration (m:ss)", wkTotal: "Total time",
    wkSteps: "steps", wkLoading: "Loading…", wkErr: "Can't reach the integration.",
    paused: "Paused", finished: "Finished", wkProfile: "Resistance profile",
  },
};

const ICONS = {
  play: "M8 5v14l11-7z",
  stop: "M6 6h12v12H6z",
  minus: "M5 11h14v2H5z",
  plus: "M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6z",
  bt: "M17.71 7.71 12 2h-1v7.59L6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 11 14.41V22h1l5.71-5.71L13.41 12l4.3-4.29zM13 5.83l1.88 1.88L13 9.59V5.83zm1.88 10.46L13 18.17v-3.76l1.88 1.88z",
  pyr: "M3 20 9 8l4 7 3-5 5 10H3z",
  file: "M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6H6zm7 1.5L18.5 9H13V3.5z",
  cloud: "M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z",
  plug: "M16 7V3h-2v4h-4V3H8v4H6v6.5L9.5 17v4h5v-4l3.5-3.5V7z",
  edit: "M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z",
  copy: "M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h11v14z",
  trash: "M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z",
  back: "M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z",
  rower: "M13.5 5.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM9.8 8.9 7 23h2.1l1.8-8 2.1 2v6h2v-7.5l-2.1-2 .6-3A7.3 7.3 0 0 0 19 15v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1L6 8.3V13h2V9.6l1.8-.7z",
};

const svgIcon = (p, size = 22) =>
  `<svg viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true"><path fill="currentColor" d="${p}"/></svg>`;

const STYLE = `
:host{display:block}
ha-card{padding:16px;overflow:hidden}
*{box-sizing:border-box}
.head{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.head .logo{color:var(--primary-color);display:flex}
.head .name{font-size:16px;font-weight:500;color:var(--primary-text-color)}
.cta{width:100%;border:0;border-radius:16px;min-height:84px;padding:12px 18px;display:flex;align-items:center;justify-content:center;gap:14px;
  color:#fff;cursor:pointer;font:inherit;transition:transform .08s ease,filter .2s;
  background:linear-gradient(135deg,var(--primary-color),color-mix(in srgb,var(--primary-color) 70%,#000))}
.cta.rec{background:linear-gradient(135deg,var(--error-color,#db4437),color-mix(in srgb,var(--error-color,#db4437) 70%,#000))}
.cta:active{transform:scale(.985)}
.cta:hover{filter:brightness(1.07)}
.cta .ico{display:flex;width:44px;height:44px;border-radius:50%;background:rgba(255,255,255,.18);align-items:center;justify-content:center}
.cta .t{text-align:left;line-height:1.25}
.cta .t b{display:block;font-size:19px;font-weight:600;letter-spacing:.2px}
.cta .t span{display:flex;align-items:center;gap:7px;font-size:12.5px;opacity:.92}
.dot{width:8px;height:8px;border-radius:50%;background:#fff;display:none}
.rec .dot{display:inline-block;animation:pulse 1.4s infinite}
@keyframes pulse{0%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.7)}100%{opacity:1;transform:scale(1)}}
.hero{text-align:center;padding:18px 0 14px}
.hero .lbl{font-size:12px;letter-spacing:.8px;text-transform:uppercase;color:var(--secondary-text-color)}
.hero .val{font-size:60px;line-height:1.05;font-weight:300;font-variant-numeric:tabular-nums;color:var(--primary-text-color);letter-spacing:-1px}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.tile{background:var(--secondary-background-color,rgba(127,127,127,.08));border-radius:14px;padding:12px 10px;text-align:center;min-width:0}
.tile .l{font-size:11.5px;color:var(--secondary-text-color);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tile .v{font-size:25px;font-weight:500;font-variant-numeric:tabular-nums;color:var(--primary-text-color);margin-top:2px}
.tile .v small{font-size:12px;font-weight:400;color:var(--secondary-text-color);margin-left:3px}
.tile.sm{background:none;padding:6px 4px}
.tile.sm .v{font-size:19px}
.sep{height:1px;background:var(--divider-color);margin:16px 0 12px;opacity:.7}
.chart-h{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--secondary-text-color);margin-bottom:6px;gap:8px;flex-wrap:wrap}
.leg{display:flex;gap:12px}
.leg i{display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:5px;vertical-align:middle}
.chart{position:relative}
.chart svg{width:100%;height:auto;display:block;touch-action:pan-y}
.chart text{font-size:10.5px;fill:var(--secondary-text-color);font-family:inherit}
.tip{position:absolute;pointer-events:none;top:0;transform:translateX(-50%);background:var(--card-background-color);border:1px solid var(--divider-color);
  border-radius:8px;padding:4px 8px;font-size:11.5px;line-height:1.35;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.25);color:var(--primary-text-color);display:none;z-index:2}
.empty{display:flex;align-items:center;justify-content:center;height:150px;color:var(--secondary-text-color);font-size:13px}
.res{display:flex;align-items:center;justify-content:space-between;background:var(--secondary-background-color,rgba(127,127,127,.08));border-radius:16px;padding:8px;margin:14px 0 10px}
.res .mid{text-align:center}
.res .mid .l{font-size:11.5px;color:var(--secondary-text-color)}
.res .mid .v{font-size:30px;font-weight:500;line-height:1.1;font-variant-numeric:tabular-nums;color:var(--primary-text-color)}
.rb{width:56px;height:56px;border-radius:14px;border:0;cursor:pointer;display:flex;align-items:center;justify-content:center;
  background:var(--card-background-color);color:var(--primary-text-color);box-shadow:0 0 0 1px var(--divider-color) inset}
.rb:active{transform:scale(.94)}
.tg{border:0;cursor:pointer;font:inherit;border-radius:14px;padding:12px 6px;display:flex;flex-direction:column;align-items:center;gap:3px;
  background:var(--secondary-background-color,rgba(127,127,127,.08));color:var(--secondary-text-color);box-shadow:0 0 0 1px transparent inset;transition:all .2s}
.tg .n{font-size:13px;color:var(--primary-text-color)}
.tg .s{font-size:11.5px}
.tg.on{color:var(--success-color,#43a047);background:color-mix(in srgb,var(--success-color,#43a047) 14%,transparent);box-shadow:0 0 0 1px color-mix(in srgb,var(--success-color,#43a047) 55%,transparent) inset}
.tg.on.prog{color:var(--primary-color);background:color-mix(in srgb,var(--primary-color) 14%,transparent);box-shadow:0 0 0 1px color-mix(in srgb,var(--primary-color) 55%,transparent) inset}
.tg.warn{color:var(--warning-color,#ffa726);background:color-mix(in srgb,var(--warning-color,#ffa726) 14%,transparent);box-shadow:0 0 0 1px color-mix(in srgb,var(--warning-color,#ffa726) 55%,transparent) inset}
.tg.err{color:var(--error-color,#db4437);background:color-mix(in srgb,var(--error-color,#db4437) 14%,transparent);box-shadow:0 0 0 1px color-mix(in srgb,var(--error-color,#db4437) 55%,transparent) inset}
.last{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:8px;font-size:12.5px}
.last .a{color:var(--secondary-text-color)}
.last .b{color:var(--primary-text-color);text-align:right}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.ab{border:0;cursor:pointer;font:inherit;border-radius:14px;padding:11px 8px;display:flex;align-items:center;justify-content:center;gap:10px;
  background:var(--secondary-background-color,rgba(127,127,127,.08));color:var(--primary-text-color);text-align:left}
.ab:active{transform:scale(.97)}
.ab .x{display:flex;flex-direction:column;line-height:1.25;font-size:13px}
.ab .x small{font-size:11px;color:var(--secondary-text-color)}
.ab .x small.ok{color:var(--success-color,#43a047)}
.ab .x small.ko{color:var(--error-color,#db4437)}
.eh{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.eh .et{flex:1;font-size:16px;font-weight:500;color:var(--primary-text-color)}
.help{font-size:12.5px;color:var(--secondary-text-color);line-height:1.45;margin:0 0 12px}
.wr{display:flex;align-items:center;gap:10px;padding:10px 8px;border-radius:14px;margin-bottom:6px;background:var(--secondary-background-color,rgba(127,127,127,.08));
  box-shadow:0 0 0 1px transparent inset;cursor:pointer}
.wr.sel{box-shadow:0 0 0 1px color-mix(in srgb,var(--primary-color) 60%,transparent) inset;background:color-mix(in srgb,var(--primary-color) 10%,transparent)}
.rad{width:22px;height:22px;border-radius:50%;border:2px solid var(--secondary-text-color);flex:none;display:flex;align-items:center;justify-content:center;background:none;padding:0}
.sel .rad{border-color:var(--primary-color)}
.sel .rad::after{content:"";width:10px;height:10px;border-radius:50%;background:var(--primary-color)}
.wr .wm{flex:1;min-width:0}
.wr .wn{font-size:14.5px;color:var(--primary-text-color);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.wr .wd{font-size:11.5px;color:var(--secondary-text-color)}
.wr svg.mini{width:70px;height:26px;flex:none}
.ib{width:34px;height:34px;border-radius:10px;border:0;background:none;color:var(--secondary-text-color);cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;flex:none}
.ib:hover{background:rgba(127,127,127,.15);color:var(--primary-text-color)}
.fld{display:flex;flex-direction:column;gap:4px;margin-bottom:10px}
.fld label{font-size:11.5px;color:var(--secondary-text-color)}
.in{font:inherit;font-size:14px;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:10px;padding:8px 10px;min-width:0;width:100%}
.in:focus{outline:none;border-color:var(--primary-color)}
.blk{background:var(--secondary-background-color,rgba(127,127,127,.08));border-radius:14px;padding:10px;margin-bottom:10px}
.bh{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:13px;color:var(--primary-text-color)}
.bh .sp{flex:1}
.cnt{display:flex;align-items:center;gap:6px}
.cnt b{min-width:34px;text-align:center;font-weight:500}
.sr{display:grid;grid-template-columns:22px 1fr 1fr 34px;gap:8px;align-items:center;margin-bottom:6px}
.sr .no{font-size:12px;color:var(--secondary-text-color);text-align:center}
.lv{display:flex;align-items:center;gap:6px;font-size:12.5px;color:var(--secondary-text-color)}
.lv .in{text-align:center}
.link{display:block;margin-bottom:8px;border:0;background:none;color:var(--primary-color);font:inherit;font-size:13px;cursor:pointer;padding:6px 2px}
.tot{display:flex;justify-content:space-between;font-size:13px;margin:6px 0 12px;color:var(--secondary-text-color)}
.tot b{color:var(--primary-text-color);font-weight:500}
.err{color:var(--error-color,#db4437);font-size:12.5px;margin:0 0 10px}
.acts{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.prof{width:100%;height:auto;display:block;margin-bottom:12px}
.hidden{display:none!important}
.msg{padding:12px;color:var(--secondary-text-color);font-size:13px}
`;

class DomyosRowerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._ids = {};
    this._built = false;
    this._chartKey = "";
    this._hist = null;
    this._lastFetch = 0;
    this._fetching = false;
    this._view = "main";
    this._wk = null;
    this._draft = null;
    this._wkError = "";
  }

  setConfig(config) {
    this._config = { title: "Rameur Domyos", ...config };
    this._built = false;
  }

  getCardSize() { return 12; }
  static getStubConfig() { return {}; }

  set hass(hass) {
    this._hass = hass;
    this._t = TXT[(hass.language || "en").startsWith("fr") ? "fr" : "en"];
    if (!this._built) this._build();
    this._resolve();
    this._update();
  }

  _resolve() {
    const ents = this._hass.entities || {};
    const dev = this._config.device_id;
    const ids = {};
    for (const [eid, e] of Object.entries(ents)) {
      if (e.platform !== DOMAIN || !e.translation_key) continue;
      if (dev && e.device_id !== dev) continue;
      if (!(e.translation_key in ids)) ids[e.translation_key] = eid;
    }
    this._ids = ids;
  }

  _st(key) { const id = this._ids[key]; return id ? this._hass.states[id] : undefined; }
  _num(key) {
    const s = this._st(key);
    const v = s ? parseFloat(s.state) : NaN;
    return Number.isFinite(v) ? v : null;
  }
  _fmt(v, d = 0) { return v === null || v === undefined ? "–" : v.toFixed(d).replace(".", ","); }
  _call(domain, service, data) { this._hass.callService(domain, service, data); }

  _build() {
    const t = this._t;
    const r = this.shadowRoot;
    r.innerHTML = `<style>${STYLE}</style>
<ha-card>
  <div class="head"><span class="logo">${svgIcon(ICONS.rower, 24)}</span><span class="name"></span></div>
  <div class="msg hidden" id="noent"></div>
  <div id="main">
    <button class="cta" id="cta"><span class="ico" id="ctaico"></span>
      <span class="t"><b id="ctat"></b><span><i class="dot"></i><em id="ctas" style="font-style:normal"></em></span></span></button>
    <div class="hero"><div class="lbl" id="l_time"></div><div class="val" id="time">00:00</div></div>
    <div class="grid3">
      <div class="tile"><div class="l" id="l_pace"></div><div class="v" id="pace"></div></div>
      <div class="tile"><div class="l" id="l_dist"></div><div class="v" id="dist"></div></div>
      <div class="tile"><div class="l" id="l_cad"></div><div class="v" id="cad"></div></div>
    </div>
    <div class="grid3" style="margin-top:6px">
      <div class="tile sm"><div class="l" id="l_str"></div><div class="v" id="str"></div></div>
      <div class="tile sm"><div class="l" id="l_pow"></div><div class="v" id="pow"></div></div>
      <div class="tile sm"><div class="l" id="l_cal"></div><div class="v" id="cal"></div></div>
    </div>
    <div class="sep"></div>
    <div class="chart-h"><span id="ctitle"></span>
      <span class="leg"><span><i style="background:var(--primary-color)"></i><span id="l_lp"></span></span><span><i style="background:#e8a33d"></i><span id="l_lr"></span></span></span></div>
    <div class="chart" id="chart"></div>
    <div class="res">
      <button class="rb" id="rm" aria-label="-">${svgIcon(ICONS.minus)}</button>
      <div class="mid"><div class="l" id="l_res"></div><div class="v" id="res">–</div></div>
      <button class="rb" id="rp" aria-label="+">${svgIcon(ICONS.plus)}</button>
    </div>
    <div class="grid3" id="toggles">
      <button class="tg" id="tg_plug">${svgIcon(ICONS.plug, 24)}<span class="n" id="n_plug"></span><span class="s" id="s_plug"></span></button>
      <button class="tg" id="tg_bt">${svgIcon(ICONS.bt, 24)}<span class="n" id="n_bt"></span><span class="s" id="s_bt"></span></button>
      <button class="tg prog" id="tg_prog">${svgIcon(ICONS.pyr, 24)}<span class="n" id="n_prog"></span><span class="s" id="s_prog"></span></button>
    </div>
    <div class="sep"></div>
    <div class="last"><span class="a" id="l_last"></span><span class="b" id="lastinfo"></span></div>
    <div class="grid2">
      <button class="ab" id="b_files">${svgIcon(ICONS.file, 24)}<span class="x"><span id="n_files"></span></span></button>
      <button class="ab" id="b_garmin">${svgIcon(ICONS.cloud, 24)}<span class="x"><span id="n_garmin"></span><small id="s_garmin"></small></span></button>
    </div>
  </div>
  <div id="editor" class="hidden"></div>
</ha-card>`;
    const $ = (id) => r.getElementById(id);
    this._$ = $;
    r.querySelector(".name").textContent = this._config.title;
    $("noent").textContent = t.noEntities;
    $("l_time").textContent = t.time; $("l_pace").textContent = t.pace; $("l_dist").textContent = t.distance;
    $("l_cad").textContent = t.cadence; $("l_str").textContent = t.strokes; $("l_pow").textContent = t.power;
    $("l_cal").textContent = t.calories; $("l_lp").textContent = t.power; $("l_lr").textContent = t.resistance;
    $("l_res").textContent = t.resistance; $("l_last").textContent = t.last; $("n_files").textContent = t.files;
    $("n_garmin").textContent = t.garmin;
    $("n_plug").textContent = t.plug; $("n_bt").textContent = t.bluetooth; $("n_prog").textContent = t.workout;

    $("cta").onclick = () => this._toggleEntity(this._ids.recording);
    $("rm").onclick = () => this._step(-1);
    $("rp").onclick = () => this._step(1);
    $("tg_plug").onclick = () => this._toggleEntity(this._config.plug_entity);
    $("tg_bt").onclick = () => this._toggleEntity(this._ids.connection);
    $("tg_prog").onclick = () => this._openEditor();
    $("editor").addEventListener("click", (e) => this._onEditorClick(e));
    $("editor").addEventListener("input", (e) => this._onEditorInput(e, false));
    $("editor").addEventListener("change", (e) => this._onEditorInput(e, true));
    $("b_files").onclick = () => this._press(this._ids.generate_files);
    $("b_garmin").onclick = () => this._press(this._ids.upload_garmin);
    this._built = true;
  }

  _toggleEntity(eid) {
    if (!eid) return;
    this._call("homeassistant", "toggle", { entity_id: eid });
  }
  _press(eid) { if (eid) this._call("button", "press", { entity_id: eid }); }
  _step(dir) {
    const eid = this._ids.resistance_target, s = this._st("resistance_target");
    if (!eid || !s) return;
    const cur = parseFloat(s.state); if (!Number.isFinite(cur)) return;
    const min = Number(s.attributes.min ?? 1), max = Number(s.attributes.max ?? 16);
    const step = Number(s.attributes.step ?? 1) || 1;
    const v = Math.min(max, Math.max(min, cur + dir * step));
    this._call("number", "set_value", { entity_id: eid, value: v });
  }

  _update() {
    const $ = this._$, t = this._t;
    const hasAny = Object.keys(this._ids).length > 0;
    $("noent").classList.toggle("hidden", hasAny);
    $("main").classList.toggle("hidden", !hasAny || this._view !== "main");
    if (!hasAny) return;

    const rec = this._st("recording")?.state === "on";
    $("cta").classList.toggle("rec", rec);
    $("ctaico").innerHTML = svgIcon(rec ? ICONS.stop : ICONS.play, 26);
    $("ctat").textContent = rec ? t.stop : t.start;
    $("ctas").textContent = rec ? t.recording : t.ready;

    const el = this._num("elapsed_time");
    const s = Math.round(el ?? 0), h = Math.floor(s / 3600);
    const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0"), ss = String(s % 60).padStart(2, "0");
    $("time").textContent = h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;

    const pace = this._st("pace_mmss")?.state;
    $("pace").textContent = pace && !["unknown", "unavailable"].includes(pace) ? pace : "–";
    const dSt = this._st("distance"), dv = this._num("distance");
    let km = null;
    if (dv !== null) km = (dSt.attributes.unit_of_measurement === "km") ? dv : dv / 1000;
    $("dist").innerHTML = `${this._fmt(km, 2)}<small>km</small>`;
    $("cad").innerHTML = `${this._fmt(this._num("cadence"), 0)}<small>spm</small>`;
    $("str").textContent = this._fmt(this._num("strokes"), 0);
    $("pow").innerHTML = `${this._fmt(this._num("power"), 0)}<small>W</small>`;
    $("cal").textContent = this._fmt(this._num("calories"), 0);

    const rs = this._st("resistance_target");
    $("res").textContent = rs && Number.isFinite(parseFloat(rs.state)) ? Math.round(parseFloat(rs.state)) : "–";

    const tog = (id, eid, on, off, name) => {
      const st = eid ? this._hass.states[eid] : null;
      $("tg_" + id).classList.toggle("hidden", !eid);
      if (!st) return;
      const isOn = st.state === "on";
      $("tg_" + id).classList.toggle("on", isOn);
      $("s_" + id).textContent = isOn ? on : off;
    };
    tog("plug", this._config.plug_entity, t.on, t.off);
    tog("bt", this._ids.connection, t.active, t.inactive);
    const swOn = this._st("connection")?.state === "on";
    const stt = this._st("status")?.state;
    const map = { connected: [t.connected, "on"], waiting: [t.searching, "warn"], connecting: [t.connecting, "warn"], error: [t.error, "err"] };
    const m = swOn && map[stt];
    $("tg_bt").classList.remove("on", "warn", "err");
    if (m) { $("tg_bt").classList.add(m[1]); $("s_bt").textContent = m[0]; }
    else { $("tg_bt").classList.toggle("on", swOn); $("s_bt").textContent = swOn ? t.active : t.inactive; }
    this._updateWorkoutButton();
    const nTog = ["plug", "bt", "prog"].filter((k) => !$("tg_" + k).classList.contains("hidden")).length;
    $("toggles").style.gridTemplateColumns = `repeat(${Math.max(1, nTog)},minmax(0,1fr))`;
    $("toggles").classList.toggle("hidden", nTog === 0);

    const ls = this._st("last_session");
    const a = ls?.attributes || {};
    if (ls && !["unknown", "unavailable"].includes(ls.state)) {
      const d = new Date(ls.state);
      const when = d.toLocaleString(this._hass.language || "fr", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
      const dur = Math.round(Number(a.duration_s) || 0);
      const lk = ((Number(a.distance_m) || 0) / 1000).toFixed(1).replace(".", ",");
      $("lastinfo").textContent = `${when} · ${Math.floor(dur / 60)}:${String(dur % 60).padStart(2, "0")} · ${lk} km`;
    } else {
      $("lastinfo").textContent = t.none;
    }
    $("b_files").classList.toggle("hidden", !this._ids.generate_files);
    $("b_garmin").classList.toggle("hidden", !this._ids.upload_garmin);
    const g = a.garmin_status, sg = $("s_garmin");
    sg.className = g === "uploaded" ? "ok" : g === "error" ? "ko" : "";
    sg.textContent = g === "uploaded" ? t.sent : g === "error" ? t.failed : t.notSent;

    this._maybeChart(rec, el);
  }

  /* ---------- workouts ---------- */
  _updateWorkoutButton() {
    const $ = this._$, t = this._t;
    const sel = this._st("workout");
    const btn = $("tg_prog");
    btn.classList.toggle("hidden", !this._ids.workout);
    if (!sel) return;
    const none = sel.state === "Aucun" || !sel.state;
    const ws = this._st("workout_status");
    const a = ws?.attributes || {};
    const st = ws?.state;
    let txt = none ? t.wkNone : sel.state;
    if (st === "running") txt = `${a.step}/${a.steps_total} · ${t.level} ${a.level}`;
    else if (st === "paused") txt = `${t.paused} · ${t.level} ${a.level}`;
    else if (st === "finished") txt = t.finished;
    $("s_prog").textContent = txt;
    btn.classList.toggle("on", !none);
    btn.classList.toggle("prog", true);
  }

  _wsArgs(extra) { return { ...(this._config.entry_id ? { entry_id: this._config.entry_id } : {}), ...extra }; }

  async _wkCall(msg) {
    try {
      const r = await this._hass.callWS(this._wsArgs(msg));
      this._wkError = "";
      return r;
    } catch (e) {
      this._wkError = (e && e.message) || this._t.wkErr;
      return null;
    }
  }

  _openEditor() {
    this._view = "list"; this._wk = this._wk || null; this._draft = null;
    this._showView();
    this._loadWk();
  }

  _showView() {
    const $ = this._$;
    const inEditor = this._view === "list" || this._view === "edit";
    $("main").classList.toggle("hidden", inEditor);
    $("editor").classList.toggle("hidden", !inEditor);
    this.shadowRoot.querySelector(".head").classList.toggle("hidden", inEditor);
    this._renderEditor();
  }

  async _loadWk() {
    const r = await this._wkCall({ type: "domyos_rower/workouts" });
    if (r) this._wk = r;
    this._renderEditor();
  }

  _flat(w) {
    const out = [];
    for (const b of w.blocks) for (let i = 0; i < b.repeat; i++) for (const s of b.steps) out.push([s.seconds, s.level]);
    return out;
  }
  _total(w) { return this._flat(w).reduce((a, s) => a + s[0], 0); }
  _fmtDur(sec) {
    sec = Math.max(0, Math.round(sec));
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
  }
  _fmtMin(sec) { const m = Math.round(sec / 60); return m >= 1 ? `${m} min` : `${Math.round(sec)} s`; }
  _parseDur(str) {
    str = String(str).trim().replace(",", ".");
    if (!str) return NaN;
    if (str.includes(":")) {
      const p = str.split(":").map((x) => parseFloat(x));
      if (p.some((x) => !Number.isFinite(x))) return NaN;
      return p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p[0] * 60 + p[1];
    }
    const v = parseFloat(str);
    return Number.isFinite(v) ? Math.round(v * 60) : NaN;   // a bare number is minutes
  }
  _profile(w, W, H, LV, cls = "") {
    const flat = this._flat(w), total = flat.reduce((a, s) => a + s[0], 0) || 1;
    const Y = (l) => H - 2 - (Math.min(LV, Math.max(0, l)) / LV) * (H - 4);
    let d = "", t = 0;
    flat.forEach(([sec, lvl], i) => {
      const x = (t / total) * W; t += sec;
      d += i === 0 ? `M${x.toFixed(1)},${Y(lvl).toFixed(1)}` : `V${Y(lvl).toFixed(1)}`;
      d += `H${((t / total) * W).toFixed(1)}`;
    });
    return `<svg class="${cls}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><path d="${d}" fill="none" stroke="#e8a33d" stroke-width="${W > 100 ? 1.6 : 1.4}" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>`;
  }

  _renderEditor() {
    const root = this._$("editor"), t = this._t;
    if (this._view === "main" || !root) return;
    const LV = this._wk ? this._wk.level_range[1] : 15;
    if (this._view === "list") {
      let rows = "";
      if (!this._wk) {
        rows = `<div class="msg">${this._wkError || t.wkLoading}</div>`;
      } else {
        const selId = this._wk.selected;
        rows = `<div class="wr ${selId ? "" : "sel"}" data-act="sel" data-id=""><button class="rad" aria-label="${t.wkNoneRow}"></button>
          <div class="wm"><div class="wn">${t.wkNoneRow}</div></div></div>`;
        for (const w of this._wk.workouts) {
          const tot = this._total(w), n = this._flat(w).length;
          rows += `<div class="wr ${w.id === selId ? "sel" : ""}" data-act="sel" data-id="${w.id}">
            <button class="rad" aria-label="${this._esc(w.name)}"></button>
            <div class="wm"><div class="wn">${this._esc(w.name)}</div><div class="wd">${this._fmtMin(tot)} · ${n} ${t.wkSteps}</div></div>
            ${this._profile(w, 70, 26, LV, "mini")}
            <button class="ib" data-act="edit" data-id="${w.id}" title="${t.wkEdit}">${svgIcon(ICONS.edit, 18)}</button>
            <button class="ib" data-act="dup" data-id="${w.id}" title="${t.wkDup}">${svgIcon(ICONS.copy, 18)}</button>
            <button class="ib" data-act="del" data-id="${w.id}" title="${t.wkDel}">${svgIcon(ICONS.trash, 18)}</button></div>`;
        }
      }
      root.innerHTML = `<div class="eh"><button class="ib" data-act="back" title="${t.wkBack}">${svgIcon(ICONS.back, 22)}</button>
        <span class="et">${t.wkTitle}</span><button class="ab" data-act="new" style="padding:8px 14px">${svgIcon(ICONS.plus, 18)}<span class="x">${t.wkNew}</span></button></div>
        <p class="help">${t.wkHelp}</p>${rows}${this._wkError && this._wk ? `<p class="err">${this._esc(this._wkError)}</p>` : ""}`;
      return;
    }
    // edit view
    const w = this._draft;
    let blocks = "";
    w.blocks.forEach((b, bi) => {
      let steps = "";
      b.steps.forEach((s, si) => {
        steps += `<div class="sr"><span class="no">${si + 1}</span>
          <input class="in" data-f="dur" data-b="${bi}" data-s="${si}" value="${this._fmtDur(s.seconds)}" inputmode="numeric" aria-label="${t.wkDuration}">
          <div class="lv">${t.level}<input class="in" type="number" data-f="lvl" data-b="${bi}" data-s="${si}" min="${this._wk.level_range[0]}" max="${LV}" value="${s.level}"></div>
          <button class="ib" data-act="delStep" data-b="${bi}" data-s="${si}" title="${t.wkDel}">${svgIcon(ICONS.trash, 18)}</button></div>`;
      });
      blocks += `<div class="blk"><div class="bh"><b>${t.wkBlock} ${bi + 1}</b><span class="sp"></span>
        <span class="cnt">${t.wkRepeat}<button class="rb" style="width:32px;height:32px;border-radius:10px" data-act="repMinus" data-b="${bi}">${svgIcon(ICONS.minus, 16)}</button>
        <b>× ${b.repeat}</b><button class="rb" style="width:32px;height:32px;border-radius:10px" data-act="repPlus" data-b="${bi}">${svgIcon(ICONS.plus, 16)}</button></span>
        ${w.blocks.length > 1 ? `<button class="ib" data-act="delBlock" data-b="${bi}" title="${t.wkDelBlock}">${svgIcon(ICONS.trash, 18)}</button>` : ""}</div>
        ${steps}<button class="link" data-act="addStep" data-b="${bi}">+ ${t.wkAddStep}</button></div>`;
    });
    root.innerHTML = `<div class="eh"><button class="ib" data-act="cancel" title="${t.wkBack}">${svgIcon(ICONS.back, 22)}</button>
      <span class="et">${this._esc(w.name || t.wkNewName)}</span></div>
      <div class="fld"><label>${t.wkName}</label><input class="in" data-f="name" value="${this._esc(w.name)}" maxlength="60"></div>
      <div class="chart-h"><span>${t.wkProfile}</span></div><div id="prof">${this._profile(w, 360, 64, LV, "prof")}</div>
      ${blocks}<button class="link" data-act="addBlock">+ ${t.wkAddBlock}</button>
      <div class="fld" style="max-width:160px"><label>${t.wkEnd}</label><input class="in" type="number" data-f="end" min="${this._wk.level_range[0]}" max="${LV}" value="${w.end_level}"></div>
      <div class="tot"><span>${t.wkTotal}</span><b id="tot">${this._fmtDur(this._total(w))}</b></div>
      <p class="err ${this._wkError ? "" : "hidden"}" id="werr">${this._esc(this._wkError || "")}</p>
      <div class="acts"><button class="ab" data-act="cancel"><span class="x">${t.wkCancel}</span></button>
      <button class="ab" data-act="save" style="background:var(--primary-color);color:#fff"><span class="x">${t.wkSave}</span></button></div>`;
  }

  _esc(v) { return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

  _newDraft() {
    const lo = this._wk ? this._wk.level_range[0] : 1;
    return { name: this._t.wkNewName, end_level: lo, blocks: [{ repeat: 1, steps: [{ seconds: 300, level: Math.min(6, this._wk ? this._wk.level_range[1] : 15) }] }] };
  }

  async _onEditorClick(e) {
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const act = el.dataset.act, id = el.dataset.id, b = Number(el.dataset.b), s = Number(el.dataset.s);
    const t = this._t, d = this._draft;
    if (act === "back") { this._view = "main"; this._showView(); return; }
    if (act === "cancel") { this._view = "list"; this._draft = null; this._wkError = ""; this._renderEditor(); return; }
    if (act === "new") { this._draft = this._newDraft(); this._view = "edit"; this._wkError = ""; this._renderEditor(); return; }
    if (act === "sel") {
      const r = await this._wkCall({ type: "domyos_rower/workouts/select", workout_id: id || null });
      if (r) this._wk = r;
      this._renderEditor(); return;
    }
    if (act === "edit" || act === "dup") {
      const w = this._wk.workouts.find((x) => x.id === id);
      if (!w) return;
      this._draft = JSON.parse(JSON.stringify(w));
      if (act === "dup") { delete this._draft.id; this._draft.name = `${w.name} (${t.wkCopy})`; }
      this._view = "edit"; this._wkError = ""; this._renderEditor(); return;
    }
    if (act === "del") {
      if (!window.confirm(t.wkConfirmDel)) return;
      const r = await this._wkCall({ type: "domyos_rower/workouts/delete", workout_id: id });
      if (r) this._wk = r;
      this._renderEditor(); return;
    }
    if (!d) return;
    if (act === "addStep") { const last = d.blocks[b].steps.slice(-1)[0]; d.blocks[b].steps.push({ seconds: last ? last.seconds : 120, level: last ? last.level : 8 }); }
    else if (act === "delStep") { if (d.blocks[b].steps.length > 1) d.blocks[b].steps.splice(s, 1); }
    else if (act === "addBlock") d.blocks.push({ repeat: 1, steps: [{ seconds: 120, level: 8 }] });
    else if (act === "delBlock") d.blocks.splice(b, 1);
    else if (act === "repMinus") d.blocks[b].repeat = Math.max(1, d.blocks[b].repeat - 1);
    else if (act === "repPlus") d.blocks[b].repeat = Math.min(99, d.blocks[b].repeat + 1);
    else if (act === "save") {
      const r = await this._wkCall({ type: "domyos_rower/workouts/save", workout: d });
      if (r) { this._wk = r; this._view = "list"; this._draft = null; }
      this._renderEditor(); return;
    }
    this._renderEditor();
  }

  _onEditorInput(e, commit) {
    const el = e.target.closest("[data-f]");
    const d = this._draft;
    if (!el || !d) return;
    const f = el.dataset.f, b = Number(el.dataset.b), s = Number(el.dataset.s);
    if (f === "name") d.name = el.value;
    else if (f === "end") d.end_level = Math.round(Number(el.value)) || d.end_level;
    else if (f === "lvl") { const v = Math.round(Number(el.value)); if (Number.isFinite(v) && el.value !== "") d.blocks[b].steps[s].level = v; }
    else if (f === "dur") {
      const sec = this._parseDur(el.value);
      if (Number.isFinite(sec) && sec > 0) d.blocks[b].steps[s].seconds = Math.round(sec);
      if (commit) el.value = this._fmtDur(d.blocks[b].steps[s].seconds);
    }
    const LV = this._wk ? this._wk.level_range[1] : 15;
    const prof = this._$("prof"), tot = this._$("tot");
    if (prof) prof.innerHTML = this._profile(d, 360, 64, LV, "prof");
    if (tot) tot.textContent = this._fmtDur(this._total(d));
  }

  /* ---------- chart ---------- */
  _window(rec, el) {
    const ls = this._st("last_session");
    if (rec && el !== null && el > 0) {
      const end = Date.now();
      return { start: end - el * 1000, end, live: true, key: "live:" + (this._st("recording")?.last_changed || "") };
    }
    if (ls && !["unknown", "unavailable"].includes(ls.state)) {
      const start = new Date(ls.state).getTime();
      const dur = (Number(ls.attributes.duration_s) || 0) * 1000;
      if (dur > 0) return { start, end: start + dur, live: false, key: "last:" + start };
    }
    return null;
  }

  _maybeChart(rec, el) {
    const w = this._window(rec, el);
    const $ = this._$, t = this._t;
    if (!w) { $("ctitle").textContent = t.chartNone; $("chart").innerHTML = `<div class="empty">${t.chartNone}</div>`; this._chartKey = ""; return; }
    $("ctitle").textContent = w.live ? t.chartLive : t.chartLast;
    const now = Date.now();
    const need = w.key !== this._chartKey || (w.live && now - this._lastFetch > 15000);
    if (need && !this._fetching) this._fetch(w);
    else if (this._hist && w.live && now - (this._lastDraw || 0) > 4000) this._draw(w);
  }

  async _fetch(w) {
    const p = this._ids.power, r = this._ids.resistance;
    if (!p || !r) return;
    this._fetching = true;
    try {
      const res = await this._hass.callWS({
        type: "history/history_during_period",
        start_time: new Date(w.start).toISOString(),
        end_time: new Date(w.end + 2000).toISOString(),
        entity_ids: [p, r],
        include_start_time_state: true,
        significant_changes_only: false,
        minimal_response: true,
        no_attributes: true,
      });
      const conv = (arr) => (arr || []).map((e) => {
        const ts = e.lu ?? e.lc ?? (e.last_updated ? Date.parse(e.last_updated) / 1000 : null);
        const v = parseFloat(e.s ?? e.state);
        return ts && Number.isFinite(v) ? [ts * 1000, v] : null;
      }).filter(Boolean);
      this._hist = { power: conv(res[p]), res: conv(res[r]) };
      this._chartKey = w.key;
      this._lastFetch = Date.now();
      this._draw(w);
    } catch (e) {
      this._hist = null;
    } finally {
      this._fetching = false;
    }
  }

  _draw(w) {
    this._lastDraw = Date.now();
    const box = this._$("chart"), t = this._t;
    const H = this._hist;
    if (!H || (!H.power.length && !H.res.length)) { box.innerHTML = `<div class="empty">${t.chartNone}</div>`; return; }
    const W = 360, HT = 150, L = 30, R = 28, T = 8, B = 20;
    const pw = W - L - R, ph = HT - T - B;
    const t0 = w.start, t1 = Math.max(w.end, t0 + 60000);
    const X = (ts) => L + ((ts - t0) / (t1 - t0)) * pw;

    // power: bucket average
    const N = 120, buckets = Array.from({ length: N }, () => [0, 0]);
    for (const [ts, v] of H.power) {
      if (ts < t0 || ts > t1) continue;
      const i = Math.min(N - 1, Math.floor(((ts - t0) / (t1 - t0)) * N));
      buckets[i][0] += v; buckets[i][1]++;
    }
    const pts = [];
    buckets.forEach((b, i) => { if (b[1]) pts.push([t0 + ((i + 0.5) / N) * (t1 - t0), b[0] / b[1]]); });
    const pmax = Math.max(50, ...pts.map((p) => p[1]));
    const pTop = Math.ceil(pmax / 50) * 50;
    const YP = (v) => T + ph - (v / pTop) * ph;
    const LV = Number(this._st("resistance_target")?.attributes.max ?? 15) || 15;
    const YR = (v) => T + ph - (Math.min(LV, Math.max(0, v)) / LV) * ph;

    // resistance step path
    let rd = "";
    const rs = H.res.filter(([ts]) => ts <= t1);
    let lastY = null;
    rs.forEach(([ts, v], i) => {
      const x = Math.max(L, X(ts)), y = YR(v);
      rd += i === 0 ? `M${x.toFixed(1)},${y.toFixed(1)}` : `H${x.toFixed(1)}V${y.toFixed(1)}`;
      lastY = y;
    });
    if (lastY !== null) rd += `H${(L + pw).toFixed(1)}`;

    const line = pts.map((p, i) => `${i ? "L" : "M"}${X(p[0]).toFixed(1)},${YP(p[1]).toFixed(1)}`).join("");
    const area = pts.length ? `${line}L${X(pts[pts.length - 1][0]).toFixed(1)},${T + ph}L${X(pts[0][0]).toFixed(1)},${T + ph}Z` : "";

    // x ticks
    const totalMin = (t1 - t0) / 60000;
    const stepMin = [1, 2, 5, 10, 15, 30, 60, 120].find((s) => totalMin / s <= 5) || 120;
    let ticks = "";
    for (let m = 0; m * 60000 <= t1 - t0; m += stepMin) {
      const x = X(t0 + m * 60000);
      ticks += `<line x1="${x}" x2="${x}" y1="${T}" y2="${T + ph}" stroke="var(--divider-color)" stroke-width=".6" stroke-dasharray="2 3"/>` +
        `<text x="${x}" y="${HT - 5}" text-anchor="${m === 0 ? "start" : "middle"}">${m === 0 ? "0" : m + " min"}</text>`;
    }
    let grid = "";
    for (let i = 0; i <= 2; i++) {
      const y = T + (ph * i) / 2;
      grid += `<line x1="${L}" x2="${L + pw}" y1="${y}" y2="${y}" stroke="var(--divider-color)" stroke-width=".6"/>` +
        `<text x="${L - 4}" y="${y + 3.5}" text-anchor="end">${Math.round(pTop * (1 - i / 2))}</text>` +
        `<text x="${L + pw + 4}" y="${y + 3.5}" text-anchor="start">${Math.round(LV * (1 - i / 2))}</text>`;
    }
    const lastP = pts.length ? pts[pts.length - 1] : null;
    box.innerHTML = `<svg viewBox="0 0 ${W} ${HT}" id="svg">
      <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="var(--primary-color)" stop-opacity=".32"/><stop offset="1" stop-color="var(--primary-color)" stop-opacity="0"/></linearGradient></defs>
      ${grid}${ticks}
      ${area ? `<path d="${area}" fill="url(#g)"/>` : ""}
      ${rd ? `<path d="${rd}" fill="none" stroke="#e8a33d" stroke-width="1.8" stroke-linejoin="round"/>` : ""}
      ${line ? `<path d="${line}" fill="none" stroke="var(--primary-color)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>` : ""}
      ${w.live && lastP ? `<circle cx="${X(lastP[0])}" cy="${YP(lastP[1])}" r="3.5" fill="var(--primary-color)"/>` : ""}
      <line id="cur" y1="${T}" y2="${T + ph}" stroke="var(--secondary-text-color)" stroke-width=".8" style="display:none"/>
    </svg><div class="tip" id="tip"></div>`;

    const svg = box.querySelector("#svg"), cur = box.querySelector("#cur"), tip = box.querySelector("#tip");
    const move = (ev) => {
      const rc = svg.getBoundingClientRect();
      const px = ((ev.clientX - rc.left) / rc.width) * W;
      if (px < L || px > L + pw) return leave();
      const ts = t0 + ((px - L) / pw) * (t1 - t0);
      let pv = null, d = Infinity;
      for (const p of pts) { const dd = Math.abs(p[0] - ts); if (dd < d) { d = dd; pv = p[1]; } }
      let rv = null; for (const [rt, v] of rs) { if (rt <= ts) rv = v; }
      const sec = Math.round((ts - t0) / 1000);
      cur.setAttribute("x1", px); cur.setAttribute("x2", px); cur.style.display = "";
      tip.style.display = "block";
      tip.style.left = `${Math.min(Math.max((px / W) * 100, 12), 88)}%`;
      tip.innerHTML = `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}<br>${pv === null ? "–" : Math.round(pv)} W · ${t.level} ${rv === null ? "–" : Math.round(rv)}`;
    };
    const leave = () => { cur.style.display = "none"; tip.style.display = "none"; };
    svg.addEventListener("pointermove", move);
    svg.addEventListener("pointerleave", leave);
  }
}

customElements.define("domyos-rower-card", DomyosRowerCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "domyos-rower-card",
  name: "Domyos Rower",
  description: "Carte complète pour le rameur Domyos : séance, métriques, courbes, résistance.",
  preview: false,
});
