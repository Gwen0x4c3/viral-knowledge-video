// 3D bar chart: bars rise one after another, the hero bar (last) glows in the accent colour, camera cranes up.
// params: {"values":[2,5,3,9], "accent":"#ffd600", "base":"#9aa3b5", "bg":"#0b0d14"}
// Frame layout (9:16): bars occupy the middle third (y≈700-1250) — leave the top for a vidkit title label and the
// bottom band for subtitles.
const DURATION = 3.5;
let bars = [], glow;
function setup(ctx) {
  const {THREE, scene, camera, params} = ctx;
  const values = params.values || [2, 5, 3, 9];
  const accent = params.accent || "#ffd600", base = params.base || "#9aa3b5";
  scene.background = new THREE.Color(params.bg || "#0b0d14");
  scene.fog = new THREE.Fog(params.bg || "#0b0d14", 18, 45);
  scene.add(new THREE.HemisphereLight(0xbfd4ff, 0x10131c, 0.6));
  const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(5, 12, 8); scene.add(key);
  const rim = new THREE.DirectionalLight(0x4fc3ff, 1.2); rim.position.set(-8, 5, -6); scene.add(rim);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(30, 64), new THREE.MeshStandardMaterial({color: 0x121722, roughness: 0.55, metalness: 0.3}));
  floor.rotation.x = -Math.PI / 2; scene.add(floor);
  const grid = new THREE.GridHelper(40, 40, 0x2a3550, 0x1a2133); grid.position.y = 0.01; scene.add(grid);
  const max = Math.max(...values);
  values.forEach((v, i) => {
    const hero = i === values.length - 1;
    const mat = new THREE.MeshStandardMaterial({color: hero ? accent : base, roughness: 0.3, metalness: 0.15,
                                                emissive: hero ? accent : 0x000000, emissiveIntensity: hero ? 0.25 : 0});
    const m = new THREE.Mesh(new THREE.BoxGeometry(1.3, 1, 1.3), mat);
    m.position.x = (i - (values.length - 1) / 2) * 1.9;
    m.userData = {h: 7 * v / max, delay: 0.2 + i * 0.32};
    scene.add(m); bars.push(m);
  });
  glow = new THREE.PointLight(accent, 0, 12); scene.add(glow);
}
const easeOutBack = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const easeInOut = x => x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
function update(t, ctx) {
  for (const m of bars) {
    const k = Math.min(1, Math.max(0, (t - m.userData.delay) / 0.65));
    const h = Math.max(0.001, m.userData.h * (k > 0 ? easeOutBack(k) : 0));
    m.scale.y = h; m.position.y = h / 2;
  }
  const hero = bars[bars.length - 1];
  glow.position.set(hero.position.x, hero.scale.y + 1, 2); glow.intensity = 3 * Math.min(1, Math.max(0, (t - hero.userData.delay - 0.3) / 0.5));
  const e = easeInOut(Math.min(1, t / DURATION));
  const a = -0.55 + e * 0.5;                                   // slow orbit
  const r = 18 - 2 * e;                                        // gentle dolly-in
  ctx.camera.fov = 42; ctx.camera.updateProjectionMatrix();
  ctx.camera.position.set(Math.sin(a) * r, 3.5 + 3.5 * e, Math.cos(a) * r);
  ctx.camera.lookAt(0, 3.0, 0);
}
