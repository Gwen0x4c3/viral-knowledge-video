// Earth globe with an arc flying between two places + atmosphere glow + stars; camera dollies in.
// params: {"from":[lat,lon], "to":[lat,lon], "earth_img":"earth_map", "color":"#ff3b30"}
//   earth_img: an equirectangular world map in raw/img/ (e.g. NASA "Land ocean ice 2048.jpg" from Wikimedia Commons, PD).
//   Without it a stylised wireframe globe is drawn.
const DURATION = 3.5;
let globe, arc, head, P, total;
function ll(THREE, lat, lon, r) {
  const phi = (90 - lat) * Math.PI / 180, th = (lon + 180) * Math.PI / 180;
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(th), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th));
}
function setup(ctx) {
  const {THREE, scene, params} = ctx; P = params;
  scene.background = new THREE.Color("#02040a");
  // stars (deterministic pseudo-random)
  const sv = []; let s = 7; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 1500; i++) { const v = new THREE.Vector3(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize().multiplyScalar(120 + rnd() * 60); sv.push(v.x, v.y, v.z); }
  const sg = new THREE.BufferGeometry(); sg.setAttribute("position", new THREE.Float32BufferAttribute(sv, 3));
  scene.add(new THREE.Points(sg, new THREE.PointsMaterial({color: 0xffffff, size: 0.35, sizeAttenuation: true})));
  globe = new THREE.Group(); scene.add(globe);
  const mat = params.earth_img ? new THREE.MeshStandardMaterial({map: ctx.loadTex(params.earth_img), roughness: 0.85, metalness: 0.0})
                               : new THREE.MeshStandardMaterial({color: 0x10233f, roughness: 0.8});
  globe.add(new THREE.Mesh(new THREE.SphereGeometry(5, 96, 96), mat));
  if (!params.earth_img) globe.add(new THREE.LineSegments(new THREE.WireframeGeometry(new THREE.SphereGeometry(5.02, 36, 18)),
                                   new THREE.LineBasicMaterial({color: 0x3b82c4, transparent: true, opacity: 0.5})));
  // atmosphere: back-side fresnel shell
  const atm = new THREE.ShaderMaterial({side: THREE.BackSide, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    vertexShader: "varying vec3 n; void main(){ n = normalize(normalMatrix*normal); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);}",
    fragmentShader: "varying vec3 n; void main(){ float i = pow(0.75 - dot(n, vec3(0,0,1.0)), 3.0); gl_FragColor = vec4(0.35,0.65,1.0,1.0)*i*1.6; }"});
  scene.add(new THREE.Mesh(new THREE.SphereGeometry(5.6, 64, 64), atm));
  scene.add(new THREE.AmbientLight(0xffffff, 0.35));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2); sun.position.set(-10, 6, 12); scene.add(sun);
  const a = ll(THREE, ...(params.from || [19.4, -99.1]), 5.03), b = ll(THREE, ...(params.to || [37.7, -97.3]), 5.03);
  const mid = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(5 + a.distanceTo(b) * 0.55 + 0.4);
  const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
  arc = new THREE.Mesh(new THREE.TubeGeometry(curve, 160, 0.07, 10), new THREE.MeshBasicMaterial({color: params.color || "#ff3b30"}));
  total = arc.geometry.index.count; arc.geometry.setDrawRange(0, 0); globe.add(arc); arc.userData.curve = curve;
  head = new THREE.Mesh(new THREE.SphereGeometry(0.17, 20, 20), new THREE.MeshBasicMaterial({color: "#ffd600"})); globe.add(head);
  for (const p of [a, b]) { const d = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), new THREE.MeshBasicMaterial({color: "#ffffff"})); d.position.copy(p); globe.add(d); }
  // rotate the globe so the arc's midpoint faces the camera
  const target = a.clone().add(b).normalize();
  globe.userData.baseY = -Math.atan2(target.x, target.z); globe.userData.baseX = Math.asin(target.y);
}
function update(t, ctx) {
  const k = Math.min(1, Math.max(0, (t - 0.7) / 1.7)), e = 1 - Math.pow(1 - k, 3);
  arc.geometry.setDrawRange(0, Math.floor(total * e) - (Math.floor(total * e) % 3));
  head.position.copy(arc.userData.curve.getPoint(Math.max(0.001, e)));
  head.visible = k > 0;
  const q = Math.min(1, t / DURATION), ease = 1 - Math.pow(1 - q, 2);
  globe.rotation.set(globe.userData.baseX * ease, globe.userData.baseY + 0.9 * (1 - ease), 0);   // spins into place
  ctx.camera.position.set(0, 0, 24 - 9 * ease); ctx.camera.lookAt(0, 0, 0);
}
