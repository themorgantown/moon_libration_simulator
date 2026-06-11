/* Period-folding explorer — the pulsar trick.
 *
 * Fold the century-long hourly track by a trial period and stack the
 * cycles as rows of a heatmap.  At an arbitrary period the picture is
 * noise; at a true period of the system the columns lock into vertical
 * structure.  Re-uses data/track.bin (same file app.js fetches, so the
 * browser cache pays for it once).
 */

(function () {
  const PRESETS = [
    ["variation 14.77 d", 14.7653],
    ["draconic 27.21 d", 27.212221],
    ["sidereal 27.32 d", 27.321661],
    ["anomalistic 27.55 d", 27.554550],
    ["synodic 29.53 d", 29.530589],
    ["evection 31.81 d", 31.8119],
    ["6-yr beat", 2190.4],
    ["18.6-yr nodal", 6798.38],
  ];
  const COLS = 480;

  const fold = {
    track: null,        // Float32Array, (east, north) per hour
    n: 0,
    period: 27.0,       // days
    channel: "north",
    pending: false,
  };

  const $ = (id) => document.getElementById(id);
  const canvas = $("fold-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  function channelValue(i) {
    const t = fold.track;
    if (fold.channel === "east") return t[2 * i];
    if (fold.channel === "north") return t[2 * i + 1];
    return Math.hypot(t[2 * i], t[2 * i + 1]);
  }

  // diverging map for signed offsets: blue <- dark -> red
  function divergingRGB(v) {
    const x = Math.max(-1, Math.min(1, v / 8));
    const a = Math.abs(x) ** 0.7;
    return x < 0
      ? [7 + a * 51, 10 + a * 124, 20 + a * 235]
      : [7 + a * 248, 10 + a * 49, 20 + a * 28];
  }

  // heat map for miss distance: hits glow yellow, far misses stay dark
  function distanceRGB(v) {
    const x = Math.max(0, Math.min(1, 1 - v / 9));
    if (x < 0.7) {                       // dark -> red
      const a = x / 0.7;
      return [7 + a * 248, 10 + a * 49, 20 + a * 28];
    }
    const a = (x - 0.7) / 0.3;           // red -> yellow
    return [255, 59 + a * 155, 48 - a * 38];
  }

  function render() {
    const Ph = fold.period * 24;                       // hours per cycle
    const rows = Math.max(2, Math.floor(fold.n / Ph));
    const acc = new Float64Array(rows * COLS);
    const cnt = new Uint32Array(rows * COLS);
    // distance bins keep the minimum (closest approach in the bin), so a
    // brief hit still lights its column; signed offsets average instead
    const useMin = fold.channel === "dist";
    if (useMin) acc.fill(Infinity);

    for (let i = 0; i < fold.n; i++) {
      const r = Math.floor(i / Ph);
      if (r >= rows) break;
      const c = Math.min(COLS - 1, Math.floor(((i - r * Ph) / Ph) * COLS));
      const k = r * COLS + c;
      const v = channelValue(i);
      if (useMin) acc[k] = Math.min(acc[k], v);
      else acc[k] += v;
      cnt[k]++;
    }

    const img = new ImageData(COLS, rows);
    const toRGB = useMin ? distanceRGB : divergingRGB;
    for (let k = 0; k < rows * COLS; k++) {
      const [R, G, B] = cnt[k]
        ? toRGB(useMin ? acc[k] : acc[k] / cnt[k]) : [7, 10, 20];
      img.data[4 * k] = R;
      img.data[4 * k + 1] = G;
      img.data[4 * k + 2] = B;
      img.data[4 * k + 3] = 255;
    }

    const off = new OffscreenCanvas(COLS, rows);
    off.getContext("2d").putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(off, 0, 0, canvas.width, canvas.height);

    $("fold-readout").textContent =
      `${fold.period.toFixed(3)} days  ×  ${rows} stacked cycles`;
  }

  function scheduleRender() {
    if (fold.pending || !fold.track) return;
    fold.pending = true;
    requestAnimationFrame(() => { fold.pending = false; render(); });
  }

  function setPeriod(p) {
    fold.period = p;
    const slider = $("fold-period");
    if (p >= +slider.min && p <= +slider.max) slider.value = p;
    document.querySelectorAll("#fold-presets button").forEach(b =>
      b.classList.toggle("active", Math.abs(+b.dataset.p - p) < 1e-6));
    scheduleRender();
  }

  function fitCanvas() {
    const w = canvas.clientWidth * (window.devicePixelRatio || 1);
    canvas.width = Math.round(w);
    canvas.height = Math.round(w * 0.55);
    scheduleRender();
  }

  async function init() {
    const presets = $("fold-presets");
    for (const [label, p] of PRESETS) {
      const btn = document.createElement("button");
      btn.textContent = label;
      btn.dataset.p = p;
      btn.addEventListener("click", () => setPeriod(p));
      presets.appendChild(btn);
    }
    $("fold-period").addEventListener("input", e => setPeriod(+e.target.value));
    $("fold-channel").addEventListener("change", e => {
      fold.channel = e.target.value;
      scheduleRender();
    });
    window.addEventListener("resize", fitCanvas);

    const r = await fetch("data/track.bin");
    fold.track = new Float32Array(await r.arrayBuffer());
    fold.n = fold.track.length / 2;
    fitCanvas();
  }

  init().catch(err => {
    $("fold-readout").textContent = "failed to load track data";
    console.error(err);
  });
})();
