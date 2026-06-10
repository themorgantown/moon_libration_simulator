/* Moon libration laser — interactive century playback.
 *
 * track.bin: Float32 (east, north) offsets of the beam from Earth's center,
 * in Earth radii, one sample per hour from meta.epoch.  Positions between
 * samples are linearly interpolated, so every playback speed stays smooth.
 */

const HOUR_MS = 3600 * 1000;
const VIEW_RE = 11.8;            // half-width of the view, Earth radii

const state = {
  meta: null,
  track: null,                   // Float32Array, 2 floats per hour
  crossings: [],
  hours: 0,                      // current sim time, fractional hours
  playing: false,
  daysPerMinute: 365.25,
  trailHours: 8766,
  lastFrame: null,
  activeCrossing: -1,
};

const $ = (id) => document.getElementById(id);
const canvas = $("sky");
const ctx = canvas.getContext("2d");

async function loadData() {
  const [metaR, binR, crossR] = await Promise.all([
    fetch("data/meta.json"), fetch("data/track.bin"), fetch("data/crossings.json"),
  ]);
  state.meta = await metaR.json();
  state.track = new Float32Array(await binR.arrayBuffer());
  state.crossings = await crossR.json();
  state.epochMs = Date.parse(state.meta.epoch);
  state.maxHour = state.meta.count - 1;
  $("scrub").max = state.maxHour;
}

function sample(h) {
  const i = Math.min(Math.max(h, 0), state.maxHour - 1);
  const i0 = Math.floor(i), f = i - i0;
  const t = state.track;
  return [
    t[2 * i0] * (1 - f) + t[2 * i0 + 2] * f,
    t[2 * i0 + 1] * (1 - f) + t[2 * i0 + 3] * f,
  ];
}

function toPx(e, n, w) {
  return [(e / VIEW_RE + 1) * w / 2, (1 - n / VIEW_RE) * w / 2];
}

function draw() {
  const w = canvas.width;
  ctx.clearRect(0, 0, w, w);

  // range rings every 2 Earth radii
  ctx.strokeStyle = "rgba(110,125,180,0.12)";
  ctx.fillStyle = "rgba(110,125,180,0.35)";
  ctx.font = `${Math.round(w / 75)}px sans-serif`;
  ctx.lineWidth = 1;
  for (let r = 2; r <= 10; r += 2) {
    ctx.beginPath();
    ctx.arc(w / 2, w / 2, (r / VIEW_RE) * w / 2, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.fillText(`${(r * 6371 / 1000).toFixed(0)}k km`,
                 w / 2 + (r / VIEW_RE) * w / 2 + 3, w / 2 - 3);
  }

  // trail: hourly points from (now - trail) to now, alpha ramps with age
  const h = state.hours;
  const trail = state.trailHours || h;       // 0 = everything so far
  const from = Math.max(0, h - trail);
  const span = h - from;
  if (span > 0.5) {
    const maxPts = 12000;
    const step = Math.max(1, Math.floor(span / maxPts));
    const segs = 24;                          // alpha buckets
    for (let s = 0; s < segs; s++) {
      const a0 = from + (span * s) / segs;
      const a1 = from + (span * (s + 1)) / segs;
      ctx.beginPath();
      let first = true;
      for (let i = Math.floor(a0); i <= a1; i += step) {
        const [e, n] = sample(i);
        const [x, y] = toPx(e, n, w);
        first ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        first = false;
      }
      const [eh, nh] = sample(Math.min(a1, h));
      const [xh, yh] = toPx(eh, nh, w);
      ctx.lineTo(xh, yh);
      ctx.strokeStyle = `rgba(255,59,48,${0.06 + 0.5 * ((s + 1) / segs) ** 2})`;
      ctx.lineWidth = 1 + (s + 1) / segs;
      ctx.stroke();
    }
  }

  // Earth
  const [ex, ey] = [w / 2, w / 2];
  const rE = (1 / VIEW_RE) * w / 2;
  const [be, bn] = sample(h);
  const hit = Math.hypot(be, bn) < 1;
  const glow = ctx.createRadialGradient(ex, ey, rE * 0.2, ex, ey, rE * (hit ? 3 : 1.8));
  glow.addColorStop(0, hit ? "rgba(255,214,10,0.5)" : "rgba(58,134,255,0.35)");
  glow.addColorStop(1, "rgba(58,134,255,0)");
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(ex, ey, rE * 3, 0, 2 * Math.PI); ctx.fill();
  const ball = ctx.createRadialGradient(ex - rE * 0.3, ey - rE * 0.3, rE * 0.1, ex, ey, rE);
  ball.addColorStop(0, "#7fb3ff");
  ball.addColorStop(1, "#1d4ed8");
  ctx.fillStyle = ball;
  ctx.beginPath(); ctx.arc(ex, ey, rE, 0, 2 * Math.PI); ctx.fill();

  // beam head
  const [bx, by] = toPx(be, bn, w);
  ctx.fillStyle = hit ? "#ffd60a" : "#ff3b30";
  ctx.shadowColor = ctx.fillStyle;
  ctx.shadowBlur = 14;
  ctx.beginPath(); ctx.arc(bx, by, Math.max(3, w / 220), 0, 2 * Math.PI); ctx.fill();
  ctx.shadowBlur = 0;

  // HUD
  const date = new Date(state.epochMs + h * HOUR_MS);
  $("hud-date").textContent = date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
  const offKm = Math.hypot(be, bn) * 6371;
  $("hud-offset").textContent =
    `beam ${Math.round(offKm).toLocaleString("en-US")} km from Earth's center`;
  const st = $("hud-status");
  st.textContent = hit ? "● HITTING EARTH" : "○ missing Earth";
  st.className = hit ? "hit" : "miss";
  $("scrub").value = Math.round(h);
  $("scrub-label").textContent = date.getUTCFullYear();
  highlightCrossing(date.getTime());
}

function highlightCrossing(nowMs) {
  let active = -1;
  for (let i = 0; i < state.crossings.length; i++) {
    const c = state.crossings[i];
    if (nowMs >= Date.parse(c.entry) - 36 * HOUR_MS &&
        nowMs <= Date.parse(c.exit) + 36 * HOUR_MS) { active = i; break; }
  }
  if (active === state.activeCrossing) return;
  document.querySelectorAll(".crossing.active").forEach(el => el.classList.remove("active"));
  if (active >= 0) {
    const el = document.querySelector(`.crossing[data-i="${active}"]`);
    if (el) { el.classList.add("active"); el.scrollIntoView({ block: "nearest" }); }
  }
  state.activeCrossing = active;
}

function frame(tNow) {
  if (state.playing) {
    const dt = state.lastFrame ? (tNow - state.lastFrame) / 1000 : 0;
    state.hours += dt * state.daysPerMinute * 24 / 60;
    if (state.hours >= state.maxHour) { state.hours = state.maxHour; setPlaying(false); }
  }
  state.lastFrame = tNow;
  draw();
  requestAnimationFrame(frame);
}

function setPlaying(on) {
  state.playing = on;
  $("play").textContent = on ? "❚❚" : "▶";
}

function buildCrossingList() {
  const list = $("crossing-list");
  $("crossing-count").textContent = `(${state.crossings.length} in 100 years)`;
  let year = 0;
  const frag = document.createDocumentFragment();
  state.crossings.forEach((c, i) => {
    const y = +c.entry.slice(0, 4);
    if (y !== year) {
      year = y;
      const head = document.createElement("div");
      head.className = "year-head";
      head.textContent = y;
      frag.appendChild(head);
    }
    const btn = document.createElement("button");
    btn.className = "crossing";
    btn.dataset.i = i;
    // color: dead-center hits yellow, grazes dim blue
    const tint = c.min_re < 0.33 ? "#ffd60a" : c.min_re < 0.66 ? "#37c978" : "#4a5b9e";
    btn.innerHTML =
      `<span class="dot" style="background:${tint}"></span>` +
      `<span class="when">${c.entry.slice(0, 10)} ${c.entry.slice(11, 16)}</span>` +
      `<span class="meta">${c.duration_h.toFixed(0)} h</span>`;
    btn.title = `on the disk ${c.entry.slice(11, 19)} → ${c.exit.slice(11, 19)} UTC, ` +
                `closest approach ${(c.min_re * 6371).toFixed(0)} km from Earth's center`;
    btn.addEventListener("click", () => jumpToCrossing(i));
    frag.appendChild(btn);
  });
  list.appendChild(frag);
}

function jumpToCrossing(i) {
  const c = state.crossings[i];
  state.hours = (Date.parse(c.entry) - state.epochMs) / HOUR_MS - 36;
  if (state.daysPerMinute > 7) {            // slow down so the hit is visible
    state.daysPerMinute = 7;
    $("speed").value = "7";
  }
  setPlaying(true);
}

function fitCanvas() {
  const px = Math.min(canvas.clientWidth, 900) * (window.devicePixelRatio || 1);
  canvas.width = canvas.height = Math.round(px);
}

async function init() {
  await loadData();
  const m = state.meta;
  $("stats").innerHTML =
    `<span><b>${m.crossing_count}</b> Earth crossings, 1926–2026</span>` +
    `<span>beam on Earth <b>${m.hit_percent}%</b> of the time</span>` +
    `<span>canvas swept: <b>±${(m.max_offset_re * 6371 / 1000).toFixed(0)},000 km</b></span>` +
    `<span><b>${(m.count / 1000).toFixed(0)}k</b> hourly ephemeris samples</span>`;
  buildCrossingList();

  $("play").addEventListener("click", () => setPlaying(!state.playing));
  $("speed").addEventListener("change", e => state.daysPerMinute = +e.target.value);
  $("trail").addEventListener("change", e => state.trailHours = +e.target.value);
  $("scrub").addEventListener("input", e => { state.hours = +e.target.value; });
  window.addEventListener("resize", fitCanvas);
  document.addEventListener("keydown", e => {
    if (e.code === "Space" && e.target.tagName !== "SELECT") {
      e.preventDefault(); setPlaying(!state.playing);
    }
  });

  fitCanvas();
  setPlaying(true);
  requestAnimationFrame(frame);
}

init().catch(err => {
  document.getElementById("hud-date").textContent =
    "failed to load data — serve this folder over HTTP (python3 -m http.server)";
  console.error(err);
});
