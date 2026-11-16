// Moving, interconnected word cloud of the most used terms in the course notes.
// Data: assets/wordcloud.json, written by scripts/wordcloud.py.
// Each word is a link to the page that uses it most; lines join words that
// often appear in the same paragraph. Hover (or focus) a word to light up its
// connections; drag a word to pull the network around.
(function () {
  var host = document.querySelector('.wordcloud');
  if (!host) return;
  var stage = host.querySelector('.wc-stage');
  var tip = host.querySelector('.wc-tip');
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var SVGNS = 'http://www.w3.org/2000/svg';

  fetch(host.getAttribute('data-src'))
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(build)
    .catch(function () { host.hidden = true; });

  function build(data) {
    var W = 0, H = 0;
    var svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('class', 'wc-links');
    svg.setAttribute('aria-hidden', 'true');
    stage.appendChild(svg);

    var maxN = Math.max.apply(null, data.nodes.map(function (n) { return n.n; }));
    var minN = Math.min.apply(null, data.nodes.map(function (n) { return n.n; }));
    var nodes = data.nodes.map(function (d, i) {
      var a = document.createElement('a');
      a.className = 'wc-word wc-' + d.c;
      a.href = d.url;
      a.textContent = d.t;
      var course = data.courses[d.c].name;
      a.setAttribute('aria-label', d.t + ': ' + d.page + ' (' + course + ')');
      var k = (Math.sqrt(d.n) - Math.sqrt(minN)) / (Math.sqrt(maxN) - Math.sqrt(minN));
      a.style.setProperty('--k', k.toFixed(3));
      stage.appendChild(a);
      return { d: d, el: a, k: k, i: i, x: 0, y: 0, vx: 0, vy: 0, w: 0, h: 0,
               phase: Math.random() * Math.PI * 2, nb: [] };
    });
    var links = data.links.map(function (l) {
      var line = document.createElementNS(SVGNS, 'line');
      line.style.setProperty('--s', Math.min(1, l[2] * 3).toFixed(3));
      svg.appendChild(line);
      var L = { a: nodes[l[0]], b: nodes[l[1]], s: l[2], el: line };
      L.a.nb.push(L); L.b.nb.push(L);
      return L;
    });

    // Start the words in rings by course so the clusters form quickly.
    var order = Object.keys(data.courses);
    // Narrow screens show fewer, smaller words.
    // Order the words by use within each course, then take them in turn from
    // each course, so every course keeps its share when the list is cut.
    var byUse = [], perCourse = Object.keys(data.courses).map(function (c) {
      return nodes.filter(function (n) { return n.d.c === c; }).sort(function (a, b) { return b.d.n - a.d.n; });
    });
    for (var r = 0; byUse.length < nodes.length; r++) {
      perCourse.forEach(function (list) { if (list[r]) byUse.push(list[r]); });
    }
    var act = nodes, alinks = links;
    function measure() {
      W = stage.clientWidth; H = stage.clientHeight;
      svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
      host.style.setProperty('--wc-scale', Math.max(0.7, Math.min(1, 0.45 + W / 1600)).toFixed(3));
      var limit = W < 480 ? 34 : W < 760 ? 48 : nodes.length;
      byUse.forEach(function (n, r) { n.on = r < limit; n.el.hidden = !n.on; });
      act = nodes.filter(function (n) { return n.on; });
      alinks = links.filter(function (L) { var on = L.a.on && L.b.on; L.el.style.display = on ? '' : 'none'; return on; });
      act.forEach(function (n) { n.w = n.el.offsetWidth; n.h = n.el.offsetHeight; });
    }
    measure();
    nodes.forEach(function (n) {
      var ci = order.indexOf(n.d.c);
      var ang = (ci / order.length) * Math.PI * 2 - Math.PI / 2;
      n.x = W / 2 + Math.cos(ang) * W * 0.22 + (Math.random() - 0.5) * W * 0.25;
      n.y = H / 2 + Math.sin(ang) * H * 0.22 + (Math.random() - 0.5) * H * 0.3;
    });

    // ---- forces
    var t = 0, heat = 1, CENTRE = 0.004, REP = 0.9;
    function tick() {
      t += 1;
      var cx = W / 2, cy = H / 2, i, j, n, m;
      var R2 = Math.pow(Math.max(90, Math.min(W, H) * 0.28), 2);
      for (i = 0; i < act.length; i++) {
        n = act[i];
        // pull to centre, stretched to the stage's shape
        n.vx += (cx - n.x) * CENTRE;
        n.vy += (cy - n.y) * CENTRE * Math.min(2.5, W / H);
        // slow drift so the cloud never quite stands still
        if (!reduce) {
          n.vx += Math.cos(t * 0.004 + n.phase) * 0.02;
          n.vy += Math.sin(t * 0.005 + n.phase * 1.3) * 0.02;
        }
        for (j = i + 1; j < act.length; j++) {
          m = act[j];
          var dx = m.x - n.x, dy = m.y - n.y;
          // overlap of the two word boxes (with a margin)
          var ox = (n.w + m.w) / 2 + 6 - Math.abs(dx);
          var oy = (n.h + m.h) / 2 + 2 - Math.abs(dy);
          if (ox > 0 && oy > 0) {
            var push = 0.12;
            if (ox < oy * 2.5) { var sx = dx < 0 ? -1 : 1; n.vx -= sx * ox * push; m.vx += sx * ox * push; }
            else { var sy = dy < 0 ? -1 : 1; n.vy -= sy * oy * push; m.vy += sy * oy * push; }
          }
          // short-range repulsion spaces the words out
          var d2 = dx * dx + dy * dy;
          if (d2 < R2) {
            var f = REP * (1 - d2 / R2) / Math.sqrt(d2 + 100);
            n.vx -= dx * f; n.vy -= dy * f;
            m.vx += dx * f; m.vy += dy * f;
          }
        }
      }
      for (i = 0; i < alinks.length; i++) {
        var L = alinks[i], a = L.a, b = L.b;
        var lx = b.x - a.x, ly = b.y - a.y;
        var dist = Math.sqrt(lx * lx + ly * ly) || 1;
        var rest = 70 + (a.w + b.w) / 4;
        var k = 0.0035 * (0.4 + L.s * 3) * (dist - rest) / dist;
        a.vx += lx * k; a.vy += ly * k; b.vx -= lx * k; b.vy -= ly * k;
      }
      for (i = 0; i < act.length; i++) {
        n = act[i];
        if (n === drag) { n.vx = n.vy = 0; continue; }
        n.vx *= 0.86; n.vy *= 0.86;
        var cap = 4 * heat + 0.6;
        n.vx = Math.max(-cap, Math.min(cap, n.vx));
        n.vy = Math.max(-cap, Math.min(cap, n.vy));
        n.x += n.vx; n.y += n.vy;
        // stay on stage
        var hw = n.w / 2 + 4, hh = n.h / 2 + 2;
        if (n.x < hw) { n.x = hw; n.vx = Math.abs(n.vx); }
        if (n.x > W - hw) { n.x = W - hw; n.vx = -Math.abs(n.vx); }
        if (n.y < hh) { n.y = hh; n.vy = Math.abs(n.vy); }
        if (n.y > H - hh) { n.y = H - hh; n.vy = -Math.abs(n.vy); }
      }
      heat *= 0.995;
    }
    function draw() {
      for (var i = 0; i < act.length; i++) {
        var n = act[i];
        n.el.style.transform = 'translate(' + (n.x - n.w / 2).toFixed(1) + 'px,' + (n.y - n.h / 2).toFixed(1) + 'px)';
      }
      for (i = 0; i < alinks.length; i++) {
        var L = alinks[i];
        L.el.setAttribute('x1', L.a.x.toFixed(1)); L.el.setAttribute('y1', L.a.y.toFixed(1));
        L.el.setAttribute('x2', L.b.x.toFixed(1)); L.el.setAttribute('y2', L.b.y.toFixed(1));
      }
    }

    // Settle off-screen first, so the cloud appears already formed.
    for (var s = 0; s < 260; s++) tick();
    draw();
    host.classList.add('ready');

    // ---- animation loop: only while visible on screen and in a visible tab
    var running = false, onScreen = true, raf = 0;
    function loop() {
      tick(); draw();
      raf = (running = shouldRun()) ? requestAnimationFrame(loop) : 0;
    }
    function shouldRun() { return onScreen && !document.hidden && (!reduce || drag || heat > 0.05); }
    function wake() { if (!running && shouldRun()) { running = true; raf = requestAnimationFrame(loop); } }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { onScreen = es[0].isIntersecting; wake(); }).observe(host);
    }
    document.addEventListener('visibilitychange', wake);
    if (reduce) heat = 0; // settled layout, moves only when dragged
    wake();

    var rsz;
    window.addEventListener('resize', function () {
      clearTimeout(rsz);
      rsz = setTimeout(function () { measure(); heat = Math.max(heat, 0.5); if (reduce) { for (var s = 0; s < 150; s++) tick(); draw(); } wake(); }, 120);
    });

    // ---- highlight a word and its neighbours
    function focus(n) {
      host.classList.toggle('focused', !!n);
      nodes.forEach(function (m) { m.el.classList.remove('on', 'near'); });
      links.forEach(function (L) { L.el.classList.remove('on'); });
      if (!n) { tip.hidden = true; return; }
      n.el.classList.add('on');
      n.nb.forEach(function (L) {
        L.el.classList.add('on');
        (L.a === n ? L.b : L.a).el.classList.add('near');
      });
      var also = n.d.also.map(function (c) { return data.courses[c].name; });
      tip.innerHTML = '';
      var b = document.createElement('strong'); b.textContent = n.d.t; tip.appendChild(b);
      tip.appendChild(document.createTextNode(' · ' + n.d.n + ' mentions'));
      var p = document.createElement('span');
      p.textContent = 'Most used in ' + data.courses[n.d.c].name + ': ' + n.d.page;
      tip.appendChild(p);
      if (also.length) {
        var q = document.createElement('span');
        q.textContent = 'Also in ' + also.join(', ');
        tip.appendChild(q);
      }
      tip.hidden = false;
    }
    nodes.forEach(function (n) {
      n.el.addEventListener('pointerenter', function () { if (!drag) focus(n); });
      n.el.addEventListener('pointerleave', function () { if (!drag) focus(null); });
      n.el.addEventListener('focus', function () { focus(n); });
      n.el.addEventListener('blur', function () { focus(null); });
    });

    // ---- drag (a click without movement follows the link)
    var drag = null, moved = false, start = null;
    stage.addEventListener('pointerdown', function (e) {
      var n = nodes.find(function (m) { return m.el === e.target; });
      if (!n || e.button !== 0) return;
      drag = n; moved = false; start = { x: e.clientX, y: e.clientY };
      n.el.setPointerCapture(e.pointerId);
    });
    stage.addEventListener('pointermove', function (e) {
      if (!drag) return;
      if (!moved && Math.hypot(e.clientX - start.x, e.clientY - start.y) < 5) return;
      if (!moved) { moved = true; focus(drag); host.classList.add('dragging'); }
      var r = stage.getBoundingClientRect();
      drag.x = e.clientX - r.left; drag.y = e.clientY - r.top;
      heat = Math.max(heat, 0.3);
      wake();
    });
    function end() {
      if (!drag) return;
      var n = drag; drag = null;
      host.classList.remove('dragging');
      if (moved) {
        // swallow the click that follows a drag
        n.el.addEventListener('click', function stop(ev) { ev.preventDefault(); n.el.removeEventListener('click', stop); }, { once: true });
        focus(null);
      }
      wake();
    }
    stage.addEventListener('pointerup', end);
    stage.addEventListener('pointercancel', end);
    nodes.forEach(function (n) { n.el.addEventListener('dragstart', function (e) { e.preventDefault(); }); });
  }
})();
