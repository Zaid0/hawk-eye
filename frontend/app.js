// HawkEye SPA - app.js (refactored module)
// Encapsulated in an IIFE to avoid globals and duplicate initializations.

const HawkEyeApp = (function () {
  'use strict';

  // ---------- Config / State ----------
  const currentUser = { username: "JohnDoe", role: "operator" };
  const allowedExportRoles = ['admin', 'operator'];

  let telemetry = [];
  let detectionEvents = [
    { t: 2.2, boxes: [ { x:0.18, y:0.20, w:0.22, h:0.30, label:'Attacker', score:0.82 } ] },
    { t: 5.8, boxes: [ { x:0.55, y:0.24, w:0.20, h:0.26, label:'Weapon', score:0.91 } ] },
    { t: 9.0, boxes: [
        { x:0.36, y:0.34, w:0.16, h:0.22, label:'Attacker', score:0.79 },
        { x:0.70, y:0.38, w:0.14, h:0.18, label:'Weapon', score:0.75 }
      ]
    },
    { t: 12.3, boxes: [ { x:0.24, y:0.46, w:0.16, h:0.20, label:'Threat', score:0.87 } ] }
  ];

  let waypoints = [];
  let mapDashboard = null, mapMission = null, hawkMarker = null, hawkPath = null, hawkIndex = 0;
  const simulatedPath = [
    [31.9539,35.9106],[31.9542,35.9110],[31.9546,35.9115],[31.9550,35.9120],
    [31.9554,35.9126],[31.9559,35.9132],[31.9562,35.9137]
  ];
  const jordanCenter = [31.9454, 35.9284];
  const defaultZoom = 7;

  // DOM helpers
  const $ = id => document.getElementById(id);
  const q = sel => document.querySelector(sel);
  const qa = sel => Array.from(document.querySelectorAll(sel));
  const safe = (fn) => { try { fn(); } catch (e) { console.warn(e); } };

  // UI elements (may be null until DOM loaded)
  let playback = null;
  let overlay = null;
  let ctx = null;
  let liveOverlay = null;
  let liveCtx = null;

  // timers holders to avoid duplicates
  let telemetryInterval = null;
  let movementInterval = null;
  let aiInterval = null;
  let overlayResizeTimer = null;

  // ---------- Initialization ----------
  function init() {
    if (document.__hawkeye_initialized) {
      console.info('HawkEyeApp already initialized, skipping duplicate init.');
      return;
    }
    document.__hawkeye_initialized = true;

    // get elements that must exist
    playback = $('playback');
    overlay = $('overlay');
    ctx = overlay ? overlay.getContext('2d') : null;
    liveOverlay = $('overlay-drone') || $('overlay-live');
    liveCtx = liveOverlay ? liveOverlay.getContext('2d') : null;

    initUI();
    initMaps();
    initVideoOverlay();
    initLiveOverlay();
    startSimulations();

    // single router + hash listener
    router();
    window.addEventListener('hashchange', router);

    // background telemetry update (safe)
    if (!telemetryInterval) telemetryInterval = setInterval(simulateTelemetry, 1000);
    if (!aiInterval) aiInterval = setInterval(simulateAI, 1000);
  }

 // ---------- Router ----------
function router(){
  const hash = location.hash.replace('#/','') || 'dashboard';
  const views = document.querySelectorAll('.view');
  views.forEach(v => v.style.display = (v.id === 'view-' + hash) ? '' : 'none');

  const navLinks = document.querySelectorAll('#nav a');
  navLinks.forEach(a => a.classList.toggle('active', a.dataset.view === hash));

  updatePageTitle(hash);
  applyRBAC();

  const homeBtn = document.getElementById('nav-home');
  if(homeBtn) homeBtn.style.display = (hash === 'dashboard') ? 'none' : 'inline-block';
}

  function router() {
  const hash = location.hash.replace('#', '') || 'dashboard';
  const targetView = `view-${hash}`;

  // show only the active view
  document.querySelectorAll('.view').forEach(v => {
    v.style.display = (v.id === targetView) ? 'block' : 'none';
  });

  // update active link in sidebar
  document.querySelectorAll('.sidebar-link').forEach(link => {
    link.classList.toggle('active', link.getAttribute('href') === `#${hash}`);
  });

  // update page title text
  const titleMap = {
    dashboard: "Dashboard",
    mission: "Mission Control",
    live: "Live View",
    telemetry: "Telemetry Data",
    settings: "Settings"
  };

  const titleElement = document.getElementById("page-title");
  if (titleElement) titleElement.textContent = titleMap[hash] || "";
}

// initialize
window.addEventListener('hashchange', router);
window.addEventListener('DOMContentLoaded', router);


  function updatePageTitle(view) {
    const titles = {
      dashboard: ['HawkEye Drone Dashboard', 'Operational Center — Live monitoring • Playback • Exports'],
      mission: ['Mission Planner', 'Plan and export drone missions'],
      live: ['Live Video Feed', 'Real-time camera & detection'],
      telemetry: ['Telemetry Logs', 'Full telemetry view & exports'],
      settings: ['Settings', 'Users & system preferences']
    };
    const pt = $('page-title');
    const ps = $('page-sub');
    if (pt && titles[view]) pt.innerText = titles[view][0];
    if (ps && titles[view]) ps.innerText = titles[view][1];
  }

  // ---------- RBAC ----------
  function applyRBAC(){
    qa('.rbac-control').forEach(el => el.style.display = (currentUser.role === 'viewer') ? 'none' : '');
    qa('.rbac-export').forEach(el => {
      el.disabled = !allowedExportRoles.includes(currentUser.role);
      el.style.opacity = el.disabled ? 0.6 : 1;
    });
    const missionLink = document.querySelector('[data-view="mission"]');
    if (missionLink) missionLink.style.display = (currentUser.role === 'viewer') ? 'none' : '';
  }

  // ---------- UI wiring (safe) ----------
  function initUI(){
    // Protect against multiple calls
    if (initUI._done) return; initUI._done = true;

    // Telemetry filter buttons
    safe(() => {
      const applyBtn = $('apply-filter');
      applyBtn && applyBtn.addEventListener('click', applyFilter);

      const clearBtn = $('clear-filter');
      clearBtn && clearBtn.addEventListener('click', () => {
        ['filter-from','filter-to','filter-label'].forEach(id => { const el = $(id); if(el) el.value = ''; });
        applyFilter();
      });
    });

    // Playback controls
    safe(() => {
      $('play-btn')?.addEventListener('click', playRecording);
      $('pause-btn')?.addEventListener('click', pauseRecording);
      $('rewind-btn')?.addEventListener('click', rewindRecording);
      $('forward-btn')?.addEventListener('click', forwardRecording);
    });

    // Export / mission buttons
    safe(() => {
      $('export-clip-btn')?.addEventListener('click', exportClip);
      $('export-report-btn')?.addEventListener('click', exportReport); // fixed name
      $('export-csv-telemetry')?.addEventListener('click', () => exportTelemetryCSV(telemetry));
      $('reset-data')?.addEventListener('click', resetSimulatedData);

      $('btn-takeoff')?.addEventListener('click', takeoff);
      $('btn-land')?.addEventListener('click', land);
      $('btn-return')?.addEventListener('click', returnHome);
      $('btn-hover')?.addEventListener('click', hover);

      $('clear-waypoints')?.addEventListener('click', clearWaypoints);
      $('export-mission')?.addEventListener('click', exportMission);

      // Refresh to camera feed button
      $('refresh-feed-btn')?.addEventListener('click', refreshToCamera);
    });

    // Header settings / nav
    const headerSettings = $('header-settings') || $('header-settings-icon') || $('header-settings-btn');
    if (headerSettings) {
      headerSettings.addEventListener('click', () => {
        showView('view-settings');
        $('page-title') && ($('page-title').textContent = 'Settings');
        $('page-sub') && ($('page-sub').textContent = 'Manage Users & System');
      });
    }
    $('back-to-dashboard')?.addEventListener('click', () => {
      showView('view-dashboard');
      $('page-title') && ($('page-title').innerText = 'HawkEye Drone Dashboard');
      $('page-sub') && ($('page-sub').innerText = 'Operational Center — Live monitoring • Playback • Exports');
    });
  }

 function showView(id) {
  // hide all main views
  qa('.view').forEach(v => v.style.display = 'none');
  const el = $(id);
  if (el) el.style.display = 'block';

  // hide all settings sections first
  qa('.settings-section').forEach(s => s.style.display = 'none');

  // show only the Users table if we're in settings
  if (id === 'view-settings') {
    const usersSection = $('users-table-section');
    if (usersSection) usersSection.style.display = 'block';

    // hide dashboard-specific elements
    qa('#view-dashboard .panel, #view-dashboard .mission-wrap').forEach(el => el.style.display = 'none');
  } else {
    // if leaving settings, restore dashboard panels
    qa('#view-dashboard .panel, #view-dashboard .mission-wrap').forEach(el => el.style.display = 'block');
  }

  // hide header settings button if in settings view
  const headerSettings = $('header-settings');
  if (headerSettings) headerSettings.style.display = (id === 'view-settings') ? 'none' : 'block';
}


  // ---------- Maps ----------
  function initMaps(){
    // guard for Leaflet presence and DOM elements
    safe(() => {
      if (typeof L === 'undefined') { console.warn('Leaflet not loaded — map initialization skipped'); return; }
      if ($('map-dashboard')) {
        mapDashboard = L.map('map-dashboard', { zoomControl:true }).setView(jordanCenter, defaultZoom);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19, attribution:''}).addTo(mapDashboard);
        const iconHtml = `<div style="width:36px;height:36px;border-radius:8px;background:linear-gradient(180deg,var(--accent),var(--accent-2));display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800">HE</div>`;
        const CustomIcon = L.divIcon({ html: iconHtml, className: '', iconSize:[36,36], iconAnchor:[18,18] });
        hawkMarker = L.marker(simulatedPath[0], { icon: CustomIcon }).addTo(mapDashboard);
        hawkPath = L.polyline([], { color:'#1e90ff', weight:4, opacity:0.9 }).addTo(mapDashboard);
      }

      if ($('map-mission')) {
        mapMission = L.map('map-mission', { zoomControl:true }).setView(jordanCenter, defaultZoom);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19, attribution:''}).addTo(mapMission);
        mapMission.on('click', (e)=> {
          const latlng = e.latlng;
          waypoints.push([latlng.lat, latlng.lng]);
          L.marker(latlng).addTo(mapMission).bindPopup(`WP ${waypoints.length}`).openPopup();
          updateWaypointsList();
          drawMissionPoly();
        });
      }
    });
  }

  function drawMissionPoly(){
    if (!mapMission) return;
    if (window.missionPoly) mapMission.removeLayer(window.missionPoly);
    if (waypoints.length > 1) {
      window.missionPoly = L.polyline(waypoints, { color:'#00d18a', dashArray:'6 4' }).addTo(mapMission);
    }
  }

  // ---------- Waypoints UI ----------
  function updateWaypointsList(){
    const tbody = $('waypoints-list');
    if(!tbody) return;
    tbody.innerHTML = '';
    waypoints.forEach((wp, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${i+1}</td><td>${wp[0].toFixed(5)}</td><td>${wp[1].toFixed(5)}</td><td><button data-i="${i}" class="btn land remove-wp">Remove</button></td>`;
      tbody.appendChild(tr);
    });
    qa('.remove-wp').forEach(b => b.addEventListener('click', (ev) => {
      const i = +ev.currentTarget.dataset.i;
      waypoints.splice(i,1);
      // re-render: remove markers then re-add
      if (mapMission) {
        mapMission.eachLayer(layer => { if (layer instanceof L.Marker) mapMission.removeLayer(layer); });
        waypoints.forEach((wp, idx)=> L.marker(wp).addTo(mapMission).bindPopup(`WP ${idx+1}`));
      }
      updateWaypointsList();
      drawMissionPoly();
    }));
  }

  function clearWaypoints(){ waypoints = []; if (mapMission) { mapMission.eachLayer(layer => { if(layer instanceof L.Marker) mapMission.removeLayer(layer); }); drawMissionPoly(); } updateWaypointsList(); }

  // ---------- Telemetry simulation & update ----------
  function startSimulations(){
    // seed telemetry once
    telemetry = [];
    simulatedPath.forEach((p, idx) => {
      telemetry.push({ time: new Date(Date.now() - (simulatedPath.length-idx)*7000).toLocaleTimeString(), label: '', lat: p[0], lng: p[1], alt: 120 + idx*5, speed: 40 + idx*2 });
    });
    updateTelemetryTables();

    // drone movement every 7s (single interval)
    if (movementInterval) clearInterval(movementInterval);
    movementInterval = setInterval(()=> {
      hawkIndex = (hawkIndex + 1) % simulatedPath.length;
      const pos = simulatedPath[hawkIndex];
      if (hawkMarker && typeof hawkMarker.setLatLng === 'function') hawkMarker.setLatLng(pos);
      if (hawkPath && typeof hawkPath.addLatLng === 'function') hawkPath.addLatLng(pos);
      $('altitude') && ($('altitude').innerText = `${120 + hawkIndex*5} m`);
      $('speed') && ($('speed').innerText = `${40 + hawkIndex*2} km/h`);
      const now = new Date().toLocaleTimeString();
      telemetry.unshift({ time: now, label: '', lat: pos[0], lng: pos[1], alt: `${120 + hawkIndex*5} m`, speed: `${40 + hawkIndex*2} km/h` });
      if(telemetry.length > 200) telemetry.pop();
      updateTelemetryTables();
      // occasional alerts
      const r = Math.random();
      if(r < 0.22) pushAlert('warning', 'HawkEye low battery warning');
      else if(r < 0.5) pushAlert('info', 'HawkEye new object detected');
    }, 7000);
  }

  function updateTelemetryTables(){
    // dashboard small table
    const tbody = document.querySelector('#telemetry-table tbody');
    if (tbody) {
      tbody.innerHTML = '';
      telemetry.slice(0,10).forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${row.time}</td><td>${(row.lat && row.lat.toFixed)?row.lat.toFixed(4):row.lat}</td><td>${(row.lng && row.lng.toFixed)?row.lng.toFixed(4):row.lng}</td><td>${row.alt}</td><td>${row.speed}</td>`;
        tbody.appendChild(tr);
      });
    }

    // full telemetry
    const full = document.querySelector('#telemetry-full tbody');
    if (full) {
      full.innerHTML = '';
      telemetry.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${row.time}</td><td>${row.label||''}</td><td>${(row.lat && row.lat.toFixed)?row.lat.toFixed(6):row.lat}</td><td>${(row.lng && row.lng.toFixed)?row.lng.toFixed(6):row.lng}</td><td>${row.alt}</td><td>${row.speed}</td>`;
        full.appendChild(tr);
      });
    }

    // populate filter labels
    const sel = $('filter-label');
    if(sel){
      const labelSet = new Set(telemetry.map(r => r.label).filter(l => l));
      // keep the sample 'C' from original file if desired — but only add if not empty
      if (!labelSet.has('C')) labelSet.add('C');
      sel.innerHTML = '<option value="">— any —</option>';
      Array.from(labelSet).sort().forEach(l => {
        const o = document.createElement('option'); 
        o.value = l; 
        o.textContent = l; 
        sel.appendChild(o);
      });
    }
  }

  // telemetry 'live' -> this demo also calls a backend; if not available, it's safe because errors are caught
  async function updateTelemetryFromServer() {
    // Disabled - not needed for simulator mode
    // The telemetry is simulated locally instead of calling the backend
    return;

    /* Original code (disabled):
    try {
      const res = await fetch('/api/drone/telemetry');
      if (!res.ok) throw new Error('non-OK');
      const data = await res.json();
      $('battery') && ($('battery').textContent = data.battery + "%");
      $('altitude') && ($('altitude').textContent = data.altitude + " m");
      $('speed') && ($('speed').textContent = data.speed + " km/h");
      $('gps') && ($('gps').textContent = data.gps);
    } catch (err) {
      // ignore network errors in demo mode
      // console.warn('updateTelemetryFromServer failed, using simulated values', err);
    }
    */
  }
  // refresh every 1 second (single interval)
  setInterval(updateTelemetryFromServer, 1000);

  function simulateTelemetry(){
    $('battery') && ($('battery').innerText = Math.floor(Math.random() * 100) + '%');
    $('altitude') && ($('altitude').innerText = (Math.random() * 100).toFixed(1) + ' m');
    $('speed') && ($('speed').innerText = (Math.random() * 50).toFixed(1) + ' km/h');
    $('gps') && ($('gps').innerText = 'Lat ' + (35 + Math.random()).toFixed(4) + ', Lng ' + (33 + Math.random()).toFixed(4));
  }

  // ---------- Alerts ----------
  let unread = 0;
  function pushAlert(level, text){
    unread++;
    const badge = $('badge-count');
    if (badge) { badge.innerText = unread; badge.style.display = 'inline-block'; }
    const pane = $('alerts-pane');
    const d = document.createElement('div'); d.className = 'alert-item';
    const ts = new Date().toLocaleTimeString();
    d.innerText = `(${level.toUpperCase()}) ${ts} — ${text}`;
    if(pane) pane.insertBefore(d, pane.firstChild);
    const livePane = $('live-alerts');
    if(livePane) livePane.insertBefore(d.cloneNode(true), livePane.firstChild);
    setTimeout(()=>{ if(d.parentNode) d.remove(); }, 20000);
  }
  $('notif-pill')?.addEventListener('click', ()=> { unread = 0; const b = $('badge-count'); if(b) b.style.display='none'; });

  // ---------- Video overlay (playback) ----------
  function initVideoOverlay(){
    if (!playback || !overlay || !ctx) return;
    playback.addEventListener('loadedmetadata', resizeOverlay);
    playback.addEventListener('play', ()=> { drawLoop(); });
    playback.addEventListener('timeupdate', ()=> { if(!playback.paused && !playback.ended) drawLoop(); });
    buildDetectionList();

    window.addEventListener('resize', ()=> {
      clearTimeout(overlayResizeTimer);
      overlayResizeTimer = setTimeout(()=> { resizeOverlay(); if (!playback.paused) drawLoop(); }, 120);
    });
  }

  function resizeOverlay(){
    if (!playback || !overlay) return;
    overlay.width = playback.clientWidth;
    overlay.height = playback.clientHeight;
    overlay.style.width = playback.clientWidth + 'px';
    overlay.style.height = playback.clientHeight + 'px';
  }

  function buildDetectionList(){
    const list = $('detections-list');
    if(!list) return;
    list.innerHTML = '';
    detectionEvents.forEach((evt, idx) => {
      const item = document.createElement('div'); item.className = 'detect-item';
      const left = document.createElement('div');
      left.innerHTML = `<strong style="color:#ffd3b6">${evt.boxes.map(b=>b.label).join(', ')}</strong><div class="muted">t = ${evt.t.toFixed(1)}s</div>`;
      const btn = document.createElement('button'); btn.className = 'btn'; btn.textContent = 'Jump';
      btn.addEventListener('click', ()=> { if (playback) { playback.currentTime = Math.max(0, evt.t - 0.5); playback.play(); } });
      item.appendChild(left); item.appendChild(btn);
      list.appendChild(item);
    });
  }

  let playing = false;
  function drawLoop(){
    if (!playback || !overlay || !ctx) return;
    if(playback.paused || playback.ended){ playing = false; clearCanvas(); return; }
    playing = true;
    clearCanvas();
    const t = playback.currentTime;
    detectionEvents.forEach(evt => {
      if(Math.abs(evt.t - t) < 0.6){
        evt.boxes.forEach(box => drawBox(box, overlay, ctx));
      }
    });
    requestAnimationFrame(drawLoop);
  }
  function clearCanvas(){ if (ctx && overlay) ctx.clearRect(0,0,overlay.width, overlay.height); }

  function drawBox(box, overlayEl, ctxLocal){
    if(!ctxLocal || !overlayEl) return;
    const w = overlayEl.width, h = overlayEl.height;
    const x = box.x * w, y = box.y * h, bw = box.w * w, bh = box.h * h;
    ctxLocal.lineWidth = Math.max(2, Math.round(Math.min(w,h) * 0.003));

    // Color mapping for different object types
    let color;
    const labelLower = box.label.toLowerCase();
    if (labelLower === 'weapon') {
      color = 'rgba(255,80,80,0.98)';  // Red for weapons
    } else if (labelLower === 'threat') {
      color = 'rgba(255,165,0,0.95)';  // Orange for threats
    } else if (labelLower === 'soldier' || labelLower === 'human') {
      color = 'rgba(0,255,0,0.95)';    // Green for soldiers/humans
    } else if (labelLower === 'vehicle') {
      color = 'rgba(255,200,0,0.95)';  // Yellow for vehicles
    } else if (labelLower === 'drone') {
      color = 'rgba(255,0,0,0.98)';    // Red for drones
    } else {
      color = 'rgba(30,200,255,0.95)'; // Blue for others
    }

    ctxLocal.strokeStyle = color;
    ctxLocal.fillStyle = color.replace('0.98','0.06').replace('0.95','0.06');
    roundRect(ctxLocal, x, y, bw, bh, 6, true, true);
    // label
    const label = `${box.label} ${(box.score*100).toFixed(0)}%`;
    ctxLocal.font = '14px Inter, Arial';
    const metrics = ctxLocal.measureText(label);
    const pad = 8;
    ctxLocal.fillStyle = 'rgba(10,12,16,0.9)';
    ctxLocal.fillRect(x, Math.max(0, y - 28), metrics.width + pad*2, 22);
    ctxLocal.fillStyle = '#fff';
    ctxLocal.fillText(label, x + pad, Math.max(12, y - 13));
  }
  function roundRect(ctxLocal, x, y, w, h, r, fill, stroke){
    if (typeof r === 'undefined') r = 5;
    ctxLocal.beginPath();
    ctxLocal.moveTo(x + r, y);
    ctxLocal.arcTo(x + w, y, x + w, y + h, r);
    ctxLocal.arcTo(x + w, y + h, x, y + h, r);
    ctxLocal.arcTo(x, y + h, x, y, r);
    ctxLocal.arcTo(x, y, x + w, y, r);
    ctxLocal.closePath();
    if (fill) ctxLocal.fill();
    if (stroke) ctxLocal.stroke();
  }

  // ---------- Exports ----------
  async function exportClip(){
    if(!allowedExportRoles.includes(currentUser.role)){ alert('Insufficient permissions'); return; }
    if(!playback || playback.readyState < 2){ alert('Video not ready'); return; }
    const duration = Math.max(1, parseInt( $('clip-duration')?.value || '6', 10));
    let stream;
    try {
      stream = playback.captureStream ? playback.captureStream() : playback.mozCaptureStream && playback.mozCaptureStream();
    } catch(e){
      alert('captureStream not supported by this browser for this video/source.');
      return;
    }
    if(!stream){ alert('Unable to capture video stream (CORS or browser limitation).'); return; }

    const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' :
                 MediaRecorder.isTypeSupported('video/webm;codecs=vp8') ? 'video/webm;codecs=vp8' : 'video/webm';
    const recorder = new MediaRecorder(stream, { mimeType: mime });
    const chunks = [];
    recorder.ondataavailable = e => { if(e.data && e.data.size) chunks.push(e.data); };
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const fileName = `HawkEye_clip_${(new Date()).toISOString().replace(/[:.]/g,'-')}.webm`;
      a.href = url; a.download = fileName; document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      pushAlert('info', `Clip exported (${fileName})`);
    };

    try {
      recorder.start();
      pushAlert('info', `Recording clip (${duration}s)`);
      const wasPaused = playback.paused;
      if(wasPaused) playback.play();
      setTimeout(()=>{ recorder.stop(); if(wasPaused) playback.pause(); }, duration * 1000);
    } catch (err){
      alert('Failed to start recorder: ' + err.message);
    }
  }

  // Export report (CSV-like). original had exportReportCSV name; expose as exportReport for UI
  function exportReport(){
    if(!allowedExportRoles.includes(currentUser.role)){ alert('Insufficient permissions'); return; }
    const telemetryRows = telemetry.map(r => `${r.time},${r.lat},${r.lng},${r.alt},${r.speed}`);
    const detRows = detectionEvents.map(evt => `${evt.t.toFixed(2)},${evt.boxes.map(b=>b.label+'('+Math.round(b.score*100)+'%)').join('|')}`);
    const parts = ['---Telemetry---','Time,Lat,Lng,Alt,Speed', ...telemetryRows, '', '---Detections---','Time(s),Objects', ...detRows];
    const blob = new Blob([parts.join('\n')], { type:'text/csv' });
    downloadBlob(blob, `HawkEye_report_${(new Date()).toISOString().replace(/[:.]/g,'-')}.csv`);
    pushAlert('info', `Report exported`);
  }

  function exportTelemetryCSV(rows){
    if(!allowedExportRoles.includes(currentUser.role)){ alert('Insufficient permissions'); return; }
    const parts = ['Time,Label,Lat,Lng,Alt,Speed', ...rows.map(r=>`${r.time},${r.label || ''},${r.lat},${r.lng},${r.alt},${r.speed}`)];
    const blob = new Blob([parts.join('\n')], { type:'text/csv' });
    downloadBlob(blob, `HawkEye_telemetry_${(new Date()).toISOString().replace(/[:.]/g,'-')}.csv`);
    pushAlert('info', `Telemetry exported`);
  }

  function exportMission(){
    if(!allowedExportRoles.includes(currentUser.role)){ alert('Insufficient permissions'); return; }
    if(waypoints.length === 0){ alert('No waypoints to export'); return; }
    const mission = { name: `Mission_${(new Date()).toISOString()}`, waypoints: waypoints.map(w=>({lat:w[0],lng:w[1]})) };
    const blob = new Blob([JSON.stringify(mission, null, 2)], { type:'application/json' });
    downloadBlob(blob, `HawkEye_mission_${(new Date()).toISOString().replace(/[:.]/g,'-')}.json`);
    pushAlert('info', `Mission exported`);
  }

  // ---------- Live overlay (for live feed) ----------
  function initLiveOverlay(){
    const liveVideo = $('live-video');
    const overlayLive = $('overlay-live') || liveOverlay;
    if(!liveVideo || !overlayLive) return;
    function resizeLive(){ overlayLive.width = liveVideo.clientWidth; overlayLive.height = liveVideo.clientHeight; overlayLive.style.width = liveVideo.clientWidth + 'px'; overlayLive.style.height = liveVideo.clientHeight + 'px'; }
    liveVideo.addEventListener('loadedmetadata', resizeLive);
    window.addEventListener('resize', resizeLive);
    // periodic demo alert
    setInterval(()=> pushAlert('info', 'AI detected object in live feed'), 15000);
  }

  function resizeLiveOverlay(){
    const v = $('live-video') || $('live-video-demo');
    if(!liveOverlay || !v) return;
    liveOverlay.width = v.clientWidth;
    liveOverlay.height = v.clientHeight;
    liveOverlay.style.width = v.clientWidth + 'px';
    liveOverlay.style.height = v.clientHeight + 'px';
  }
  window.addEventListener('resize', resizeLiveOverlay);
  $('live-video')?.addEventListener('loadedmetadata', resizeLiveOverlay);

  // ---------- Filters ----------
  function applyFilter(){
    const from = parseFloat($('filter-from')?.value);
    const to = parseFloat($('filter-to')?.value);
    const label = $('filter-label')?.value;
    const list = $('detections-list');
    if(!list) return;
    list.innerHTML = '';
    detectionEvents.filter(evt=>{
      if(!isNaN(from) && evt.t < from) return false;
      if(!isNaN(to) && evt.t > to) return false;
      if(label && !evt.boxes.some(b=>b.label === label)) return false;
      return true;
    }).forEach(evt=>{
      const item = document.createElement('div'); item.className='detect-item';
      const left = document.createElement('div');
      left.innerHTML = `<strong style="color:#ffd3b6">${evt.boxes.map(b=>b.label).join(', ')}</strong><div class="muted">t = ${evt.t.toFixed(1)}s</div>`;
      const btn = document.createElement('button'); btn.className='btn'; btn.textContent='Jump'; btn.onclick = ()=> { if(playback) { playback.currentTime = Math.max(0, evt.t - 0.5); playback.play(); } }
      item.appendChild(left); item.appendChild(btn); list.appendChild(item);
    });
  }

  // ---------- Users table (settings) ----------
  const users = [
    { username:'edx', role:'admin', email:'edx@example.com' },
    { username:'JohnDoe', role:'operator', email:'john@example.com' },
    { username:'viewer1', role:'viewer', email:'viewer@example.com' }
  ];
  function renderUsersTable(){
    const tbody = $('users-table');
    if(!tbody) return;
    tbody.innerHTML = '';
    const visibleUsers = users.filter(u => u.role !== 'viewer'); // intentionally same as original
    visibleUsers.forEach((u, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>
          <select data-i="${i}" class="role-select">
            <option value="admin"${u.role==='admin'?' selected':''}>admin</option>
            <option value="operator"${u.role==='operator'?' selected':''}>operator</option>
            <option value="viewer"${u.role==='viewer'?' selected':''}>viewer</option>
            <option value="C"${u.role==='C'?' selected':''}>C</option>
          </select>
        </td>
        <td>
          <button data-i="${i}" class="btn remove-user">Remove</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
    qa('.remove-user').forEach(btn => btn.addEventListener('click', e => {
      const i = +e.currentTarget.dataset.i;
      users.splice(i, 1);
      renderUsersTable();
    }));
    qa('.role-select').forEach(sel => sel.addEventListener('change', e => {
      const i = +e.target.dataset.i;
      users[i].role = e.target.value;
    }));
  }

  // ---------- Playback helpers ----------
  function playVideo(){ playback?.play(); }
  function pauseVideo(){ playback?.pause(); }
  function rewindVideo(){ if(playback) playback.currentTime = Math.max(0, playback.currentTime - 5); }
  function forwardVideo(){ if(playback) playback.currentTime = Math.min(playback.duration || Infinity, playback.currentTime + 5); }

  // ---------- Mission controls (placeholders) ----------
  function takeoff(){ pushAlert('info','Takeoff command (simulated)'); }
  function land(){ pushAlert('info','Land command (simulated)'); }
  function returnHome(){ pushAlert('info','Return home (simulated)'); }
  function hover(){ pushAlert('info','Hover (simulated)'); }
  function resetSimulatedData(){ telemetry = []; waypoints = []; updateTelemetryTables(); updateWaypointsList(); pushAlert('info','Simulation data reset'); }

  // ---------- Simulated AI overlay ----------
  function simulateAI() {
    if(!liveOverlay || !liveCtx) return; // skip if canvas not ready
    try {
      liveCtx.clearRect(0, 0, liveOverlay.width, liveOverlay.height);
      const box = {
        x: Math.random() * 0.7,
        y: Math.random() * 0.7,
        w: 0.2,
        h: 0.2,
        label: ['Threat','Attacker','Weapon'][Math.floor(Math.random()*3)],
        score: Math.random() * 0.9 + 0.1
      };
      drawBox(box, liveOverlay, liveCtx);
    } catch(err) {
      console.error('simulateAI error:', err);
    }
  }

  // ---------- Helper: download blob ----------
  function downloadBlob(blob, filename){
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  // ---------- WebSocket for Live Drone Feed ----------
  let ws = null;
  let liveDroneVideo = null;
  let recordedFrames = [];  // Store frames for playback
  let currentFrameIndex = 0;
  let isPlaying = false;
  let playbackInterval = null;

  function initWebSocket() {
    const wsUrl = 'ws://localhost:8000/ws';
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('✓ WebSocket connected to drone feed');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket closed, reconnecting in 3s...');
      setTimeout(initWebSocket, 3000);
    };
  }

  function handleWebSocketMessage(message) {
    if (message.type === 'video_frame') {
      updateLiveDroneFeed(message.data);
      updateRecordedFootage(message.data);
      updateDetectionsList(message.data);
    } else if (message.type === 'video_complete') {
      console.log('✓ Video processing complete');
      pushAlert('info', 'Video playback complete - returning to camera feed in 3s');
      setTimeout(refreshToCamera, 3000);
    } else if (message.type === 'feed_refresh') {
      console.log('✓ Feed refreshed to camera mode');
      clearRecordedFrames();
    }
  }

  function updateLiveDroneFeed(data) {
    // Update "HawkEye Live Drone Camera" with original frame
    liveDroneVideo = $('live-drone-video');
    if (liveDroneVideo && data.frame) {
      liveDroneVideo.src = data.frame;
    }
  }

  function updateRecordedFootage(data) {
    // Store frame for playback
    if (data.annotated_frame && data.frame_number) {
      recordedFrames.push({
        frameNumber: data.frame_number,
        image: data.annotated_frame,
        timestamp: data.timestamp,
        detections: data.detections
      });

      // Update display to latest frame
      const playback = $('playback');
      if (playback) {
        playback.src = data.annotated_frame;
        currentFrameIndex = recordedFrames.length - 1;
      }
    }
  }

  function updateDetectionsList(data) {
    // Update detection events list
    const detectionsList = $('detections-list');
    if (!detectionsList || !data.detections || data.detections.length === 0) return;

    // Calculate time from frame number
    const timeInSeconds = data.timestamp || (data.frame_number / 25); // Assume 25 FPS

    // Add to detection events
    data.detections.forEach(det => {
      // Create detection event in same format as mock data
      const existingEvent = detectionEvents.find(e => Math.abs(e.t - timeInSeconds) < 0.5);

      if (!existingEvent) {
        detectionEvents.push({
          t: timeInSeconds,
          boxes: data.detections.map(d => ({
            x: d.bbox[0] / 1920,
            y: d.bbox[1] / 1080,
            w: (d.bbox[2] - d.bbox[0]) / 1920,
            h: (d.bbox[3] - d.bbox[1]) / 1080,
            label: d.class,
            score: d.confidence
          }))
        });
      }
    });

    // Rebuild detection list
    buildDetectionList();
  }

  // ---------- Playback Controls ----------
  function playRecording() {
    if (recordedFrames.length === 0) {
      pushAlert('warning', 'No recorded frames available');
      return;
    }

    isPlaying = true;
    if (playbackInterval) clearInterval(playbackInterval);

    playbackInterval = setInterval(() => {
      if (currentFrameIndex < recordedFrames.length - 1) {
        currentFrameIndex++;
        displayFrame(currentFrameIndex);
      } else {
        // Loop back to beginning
        currentFrameIndex = 0;
        displayFrame(currentFrameIndex);
      }
    }, 40); // 25 FPS = 40ms per frame
  }

  function pauseRecording() {
    isPlaying = false;
    if (playbackInterval) {
      clearInterval(playbackInterval);
      playbackInterval = null;
    }
  }

  function rewindRecording() {
    pauseRecording();
    // Go back 5 seconds (5 * 25 FPS = 125 frames)
    const targetIndex = Math.max(0, currentFrameIndex - 125);
    currentFrameIndex = targetIndex;
    displayFrame(currentFrameIndex);
  }

  function forwardRecording() {
    pauseRecording();
    // Go forward 5 seconds (5 * 25 FPS = 125 frames)
    const targetIndex = Math.min(recordedFrames.length - 1, currentFrameIndex + 125);
    currentFrameIndex = targetIndex;
    displayFrame(currentFrameIndex);
  }

  function displayFrame(index) {
    if (index < 0 || index >= recordedFrames.length) return;

    const frame = recordedFrames[index];
    const playback = $('playback');
    if (playback && frame) {
      playback.src = frame.image;
    }
  }

  // ---------- Camera Feed Controls ----------
  async function refreshToCamera() {
    try {
      const response = await fetch('http://localhost:8000/refresh-feed', {
        method: 'POST'
      });

      const result = await response.json();

      if (result.status === 'ok') {
        console.log('✓ Returned to camera feed mode');
        clearRecordedFrames();
        pushAlert('success', 'Camera feed activated');
      }
    } catch (error) {
      console.error('Error refreshing to camera:', error);
      pushAlert('error', 'Failed to return to camera feed');
    }
  }

  function clearRecordedFrames() {
    recordedFrames = [];
    currentFrameIndex = 0;
    isPlaying = false;

    if (playbackInterval) {
      clearInterval(playbackInterval);
      playbackInterval = null;
    }

    // Reset playback display
    const playback = $('playback');
    if (playback) {
      playback.src = 'https://via.placeholder.com/640x480/1a1a2e/ffffff?text=AI+Detection+Feed';
    }

    // Clear detections list
    detectionEvents = [];
    buildDetectionList();

    console.log('✓ Recorded frames cleared');
  }

  function exportClip() {
    if (recordedFrames.length === 0) {
      pushAlert('warning', 'No recorded frames to export');
      return;
    }

    const clipDurationInput = $('clip-duration');
    const clipDuration = clipDurationInput ? parseInt(clipDurationInput.value) || 6 : 6;

    // Calculate frames to export (duration * 25 FPS)
    const framesToExport = clipDuration * 25;
    const startIndex = Math.max(0, currentFrameIndex - Math.floor(framesToExport / 2));
    const endIndex = Math.min(recordedFrames.length, startIndex + framesToExport);

    const clipFrames = recordedFrames.slice(startIndex, endIndex);

    // Create a simple JSON export with frame data
    const exportData = {
      clip_duration: clipDuration,
      total_frames: clipFrames.length,
      start_frame: startIndex,
      end_frame: endIndex,
      frames: clipFrames.map(f => ({
        frame_number: f.frameNumber,
        timestamp: f.timestamp,
        detections: f.detections,
        image_data: f.image.substring(0, 100) + '...' // Truncate for JSON size
      }))
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    downloadBlob(blob, `hawkeye_clip_${clipDuration}s_${Date.now()}.json`);
    pushAlert('success', `Clip exported: ${clipFrames.length} frames (${clipDuration}s)`);
  }

  function exportReport() {
    if (recordedFrames.length === 0 && detectionEvents.length === 0) {
      pushAlert('warning', 'No data to export');
      return;
    }

    const report = {
      generated_at: new Date().toISOString(),
      total_frames: recordedFrames.length,
      total_detections: detectionEvents.length,
      detection_summary: {},
      detection_events: detectionEvents.map(evt => ({
        time: evt.t.toFixed(2) + 's',
        objects: evt.boxes.map(b => ({
          class: b.label,
          confidence: (b.score * 100).toFixed(1) + '%',
          bbox: [b.x, b.y, b.w, b.h].map(v => v.toFixed(3))
        }))
      })),
      frames_analyzed: recordedFrames.map(f => ({
        frame_number: f.frameNumber,
        timestamp: f.timestamp,
        detection_count: f.detections ? f.detections.length : 0,
        objects_detected: f.detections ? f.detections.map(d => d.class).join(', ') : 'none'
      }))
    };

    // Calculate detection summary
    detectionEvents.forEach(evt => {
      evt.boxes.forEach(b => {
        if (!report.detection_summary[b.label]) {
          report.detection_summary[b.label] = 0;
        }
        report.detection_summary[b.label]++;
      });
    });

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    downloadBlob(blob, `hawkeye_report_${Date.now()}.json`);
    pushAlert('success', 'Detection report exported');
  }

  // ---------- Init on DOM ready ----------
  document.addEventListener('DOMContentLoaded', () => {
    init();      // main initialization
    initWebSocket();  // initialize WebSocket for live drone feed
    renderUsersTable();
    // ensure detection list is built if playback loaded later
    setTimeout(buildDetectionList, 500);
  });

  // Expose a minimal public API (for debugging)
  return {
    init,
    exportReport,
    exportTelemetryCSV,
    exportMission,
    pushAlert,
    getState: () => ({ telemetry, detectionEvents, waypoints, users, currentUser })
  };
})(); // end HawkEyeApp
