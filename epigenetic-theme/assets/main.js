(function(){
  'use strict';

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var canHover = window.matchMedia && window.matchMedia('(hover:hover) and (pointer:fine)').matches;

  /* ============================================================
   * Wordmark — letter by letter
   * ========================================================== */
  var wm = document.getElementById('wordmark');
  if (wm) {
    var name = "EPIGENETIC", tld = ".COM", html = "";
    for (var i = 0; i < name.length; i++) {
      html += '<span class="ch" style="animation-delay:' + (0.35 + i * 0.055) + 's,' + (1.4 + i * 0.04) + 's">' + name[i] + '</span>';
    }
    html += '<span class="ch tld" style="animation-delay:' + (0.35 + name.length * 0.055) + 's">' + tld + '</span>';
    wm.innerHTML = html;
  }

  /* ============================================================
   * Scroll reveal
   * ========================================================== */
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.16 });
    document.querySelectorAll('.reveal,.scale-row,.sig-strike,.stagger').forEach(function (el) { io.observe(el); });
  } else {
    document.querySelectorAll('.reveal,.scale-row,.sig-strike,.stagger').forEach(function (el) { el.classList.add('in'); });
  }

  /* ============================================================
   * Count-up numbers
   * ========================================================== */
  function fmt(n){ return Math.round(n).toLocaleString('en-US'); }
  function runCount(el){
    var to = parseFloat(el.getAttribute('data-count')) || 0;
    var pre = el.getAttribute('data-prefix') || '';
    var suf = el.getAttribute('data-suffix') || '';
    if (reduce){ el.textContent = pre + fmt(to) + suf; return; }
    var dur = 1500, start = null;
    function step(ts){
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 4);
      el.textContent = pre + fmt(to * eased) + suf;
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = pre + fmt(to) + suf;
    }
    requestAnimationFrame(step);
  }
  var counters = document.querySelectorAll('.count[data-count]');
  if (counters.length){
    if ('IntersectionObserver' in window){
      var cio = new IntersectionObserver(function(entries){
        entries.forEach(function(e){ if (e.isIntersecting){ runCount(e.target); cio.unobserve(e.target); } });
      }, { threshold: 0.6 });
      counters.forEach(function(el){ cio.observe(el); });
    } else {
      counters.forEach(runCount);
    }
  }

  /* ============================================================
   * Header state, scroll progress, floating controls, active nav
   * ========================================================== */
  var siteTop = document.getElementById('siteTop');
  var progress = document.getElementById('scrollProgress');
  var offerTab = document.getElementById('offerTab');
  var toTop = document.getElementById('toTop');
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.nav-link[href^="#"]'));
  var sections = navLinks.map(function(l){ return document.querySelector(l.getAttribute('href')); });

  var ticking = false;
  function onScroll(){
    var y = window.pageYOffset || document.documentElement.scrollTop;
    var h = document.documentElement.scrollHeight - window.innerHeight;

    if (siteTop) siteTop.classList.toggle('scrolled', y > 30);
    if (progress) progress.style.width = (h > 0 ? (y / h) * 100 : 0) + '%';

    var past = y > window.innerHeight * 0.55;
    if (offerTab) offerTab.classList.toggle('show', past);
    if (toTop) toTop.classList.toggle('show', past);

    // active nav link
    var mid = y + window.innerHeight * 0.32, current = -1;
    for (var i = 0; i < sections.length; i++){
      var s = sections[i];
      if (s && s.offsetTop <= mid) current = i;
    }
    navLinks.forEach(function(l, idx){ l.classList.toggle('active', idx === current); });

    ticking = false;
  }
  function requestScroll(){ if (!ticking){ ticking = true; requestAnimationFrame(onScroll); } }
  window.addEventListener('scroll', requestScroll, { passive: true });
  window.addEventListener('resize', requestScroll);
  onScroll();

  if (toTop) toTop.addEventListener('click', function(){
    window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
  });

  /* ============================================================
   * Mobile menu
   * ========================================================== */
  var navToggle = document.getElementById('navToggle');
  function closeMenu(){
    document.body.classList.remove('nav-open');
    if (navToggle){ navToggle.setAttribute('aria-expanded', 'false'); navToggle.setAttribute('aria-label', 'Open menu'); }
  }
  if (navToggle){
    navToggle.addEventListener('click', function(){
      var open = document.body.classList.toggle('nav-open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      navToggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
  }
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeMenu(); });

  /* ============================================================
   * Smooth in-page scrolling with header offset
   * ========================================================== */
  document.querySelectorAll('a[href^="#"]').forEach(function(a){
    a.addEventListener('click', function(e){
      var id = a.getAttribute('href');
      if (!id || id === '#') return;
      var target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      closeMenu();
      var top = target.getBoundingClientRect().top + window.pageYOffset - 68;
      window.scrollTo({ top: top, behavior: reduce ? 'auto' : 'smooth' });
    });
  });

  /* ============================================================
   * Magnetic buttons & 3D tilt cards (desktop only)
   * ========================================================== */
  if (canHover && !reduce){
    document.querySelectorAll('.magnetic').forEach(function(el){
      el.addEventListener('mousemove', function(e){
        var r = el.getBoundingClientRect();
        var dx = e.clientX - (r.left + r.width / 2);
        var dy = e.clientY - (r.top + r.height / 2);
        el.style.transform = 'translate(' + dx * 0.22 + 'px,' + dy * 0.3 + 'px)';
      });
      el.addEventListener('mouseleave', function(){ el.style.transform = ''; });
    });

    document.querySelectorAll('.tilt').forEach(function(el){
      el.addEventListener('mouseenter', function(){ el.style.transition = 'transform .12s ease'; });
      el.addEventListener('mousemove', function(e){
        var r = el.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width;
        var py = (e.clientY - r.top) / r.height;
        var rx = (0.5 - py) * 7;
        var ry = (px - 0.5) * 7;
        el.style.transform = 'perspective(900px) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg)';
        el.style.setProperty('--mx', (px * 100) + '%');
        el.style.setProperty('--my', (py * 100) + '%');
      });
      el.addEventListener('mouseleave', function(){
        el.style.transition = 'transform .5s cubic-bezier(.2,.7,.2,1)';
        el.style.transform = '';
      });
    });

    /* Cursor glow */
    var glow = document.getElementById('cursorGlow');
    if (glow){
      var gx = 0, gy = 0, cx = 0, cy = 0, raf;
      window.addEventListener('mousemove', function(e){
        gx = e.clientX; gy = e.clientY; glow.classList.add('on');
        if (!raf) raf = requestAnimationFrame(function loop(){
          cx += (gx - cx) * 0.16; cy += (gy - cy) * 0.16;
          glow.style.transform = 'translate(' + cx + 'px,' + cy + 'px)';
          raf = requestAnimationFrame(loop);
        });
      });
      document.addEventListener('mouseleave', function(){ glow.classList.remove('on'); });
    }
  }

  /* ============================================================
   * Hero DNA double-helix + drifting particles
   * ========================================================== */
  var canvas = document.getElementById('heroCanvas');
  if (canvas && !reduce && canvas.getContext){
    var ctx = canvas.getContext('2d');
    var hero = canvas.parentElement;
    var W = 0, H = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
    var particles = [];

    function size(){
      var r = hero.getBoundingClientRect();
      W = r.width; H = r.height;
      canvas.width = W * dpr; canvas.height = H * dpr;
      canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var count = Math.max(18, Math.min(54, Math.round(W / 26)));
      particles = [];
      for (var i = 0; i < count; i++){
        particles.push({
          x: Math.random() * W, y: Math.random() * H,
          vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25,
          r: Math.random() * 1.6 + 0.6
        });
      }
    }

    var t = 0;
    function draw(){
      ctx.clearRect(0, 0, W, H);

      /* particles + faint constellation links */
      for (var i = 0; i < particles.length; i++){
        var p = particles[i];
        p.x += p.vx; p.y += p.vy;
        if (p.x < -10) p.x = W + 10; if (p.x > W + 10) p.x = -10;
        if (p.y < -10) p.y = H + 10; if (p.y > H + 10) p.y = -10;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(201,168,76,0.30)';
        ctx.fill();
        for (var j = i + 1; j < particles.length; j++){
          var q = particles[j], dx = p.x - q.x, dy = p.y - q.y, d = dx * dx + dy * dy;
          if (d < 13000){
            ctx.beginPath();
            ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = 'rgba(201,168,76,' + (0.10 * (1 - d / 13000)) + ')';
            ctx.lineWidth = 1; ctx.stroke();
          }
        }
      }

      /* DNA double helix (right side) */
      var cxH = W > 760 ? W * 0.8 : W * 0.5;
      var amp = Math.min(W * 0.12, 150);
      var freq = 0.018, step = 16, prev1 = null, prev2 = null, k = 0;
      for (var y = -20; y < H + 20; y += step){
        var a = y * freq + t;
        var x1 = cxH + Math.sin(a) * amp;
        var x2 = cxH + Math.sin(a + Math.PI) * amp;
        var depth = (Math.cos(a) + 1) / 2; // 0..1 front/back

        if (prev1){
          ctx.beginPath(); ctx.moveTo(prev1.x, prev1.y); ctx.lineTo(x1, y);
          ctx.strokeStyle = 'rgba(201,168,76,0.5)'; ctx.lineWidth = 2; ctx.stroke();
        }
        if (prev2){
          ctx.beginPath(); ctx.moveTo(prev2.x, prev2.y); ctx.lineTo(x2, y);
          ctx.strokeStyle = 'rgba(63,111,95,0.55)'; ctx.lineWidth = 2; ctx.stroke();
        }
        /* rungs */
        if (k % 2 === 0){
          ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y);
          ctx.strokeStyle = 'rgba(233,236,232,' + (0.05 + depth * 0.10) + ')'; ctx.lineWidth = 1; ctx.stroke();
        }
        /* nodes */
        var rad = 1.6 + depth * 2.4;
        ctx.beginPath(); ctx.arc(x1, y, rad, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(232,200,106,' + (0.35 + depth * 0.5) + ')'; ctx.fill();
        ctx.beginPath(); ctx.arc(x2, y, 1.6 + (1 - depth) * 2.4, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(143,212,187,' + (0.3 + (1 - depth) * 0.45) + ')'; ctx.fill();

        prev1 = { x: x1, y: y }; prev2 = { x: x2, y: y }; k++;
      }

      t += 0.012;
    }

    var running = true;
    function loop(){ if (running){ draw(); requestAnimationFrame(loop); } }
    document.addEventListener('visibilitychange', function(){
      running = !document.hidden;
      if (running) loop();
    });
    var rt;
    window.addEventListener('resize', function(){ clearTimeout(rt); rt = setTimeout(size, 150); });

    size();
    requestAnimationFrame(function(){ canvas.classList.add('ready'); loop(); });
  }

  /* ============================================================
   * Offer form -> WordPress admin-ajax  (unchanged behaviour)
   * ========================================================== */
  var form = document.getElementById('offerForm');
  if (!form) return;
  var msg = document.getElementById('formMsg');
  var btn = document.getElementById('submitBtn');
  function show(text, kind){ msg.textContent = text; msg.className = 'form-msg ' + kind; }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (form.website.value) { return; } /* honeypot tripped */
    var nm = form.name.value.trim();
    var email = form.email.value.trim();
    if (!nm) { show('Please add your name so I know who I’m replying to.', 'err'); form.name.focus(); return; }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { show('That email doesn’t look right — mind checking it?', 'err'); form.email.focus(); return; }

    btn.disabled = true; btn.textContent = 'Sending…';

    var data = new FormData();
    data.append('action', 'epigenetic_offer');
    data.append('nonce', EPIGENETIC_AJAX.nonce);
    data.append('name', nm);
    data.append('company', form.company.value.trim());
    data.append('email', email);
    data.append('offer', form.offer.value.trim());
    data.append('message', form.message.value.trim());
    data.append('website', form.website.value);

    fetch(EPIGENETIC_AJAX.url, { method: 'POST', body: data, credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.success) {
          show('Thanks — your note is on its way to the owner. Expect a personal reply at ' + email + '.', 'ok');
          form.reset();
        } else {
          show((res && res.data && res.data.message) || 'Something went wrong sending that. Email contact@epigenetic.com directly and it’ll reach me.', 'err');
        }
      })
      .catch(function () {
        show('Network hiccup. Email contact@epigenetic.com directly and it’ll reach me.', 'err');
      })
      .finally(function () { btn.disabled = false; btn.textContent = 'Send to the owner'; });
  });
})();
