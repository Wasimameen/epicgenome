// staggered hero letters — EPIGENETIC . COM
  (function(){
    var el=document.getElementById('word');
    if(!el)return;
    var parts=[
      {t:'EPIGENETIC',cls:'ch'},
      {t:'.',cls:'ch dot'},
      {t:'COM',cls:'ch tld'}
    ];
    var i=0;
    parts.forEach(function(p){
      p.t.split('').forEach(function(c){
        var s=document.createElement('span');
        s.className=p.cls;
        s.textContent=c;
        s.style.animationDelay=(0.25+i*0.05)+'s';
        el.appendChild(s);
        i++;
      });
    });
    // gold shimmer sweep once the letters have landed
    var rm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(!rm){
      setTimeout(function(){
        el.classList.add('shimmer');
        setTimeout(function(){el.classList.remove('shimmer');},1700);
      },1500);
    }
  })();

  // sticky bar
  var bar=document.getElementById('bar');
  window.addEventListener('scroll',function(){
    if(window.scrollY>40)bar.classList.add('solid');else bar.classList.remove('solid');
  });

  // reveal on scroll (with reduced-motion + no-support fallbacks)
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var nodes = document.querySelectorAll('.reveal');
  if(reduce || !('IntersectionObserver' in window)){
    nodes.forEach(function(n){n.classList.add('in');});
  } else {
    var io=new IntersectionObserver(function(es){
      es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});
    },{threshold:.18,rootMargin:'0px 0px -8% 0px'});
    nodes.forEach(function(n){io.observe(n);});
  }

  // offer form -> submit via AJAX to WordPress, stay on page, show sent state
  (function(){
    var form=document.getElementById('offerForm');
    var send=document.getElementById('offerSend');
    if(!form||!send)return;
    function val(id){var el=document.getElementById(id);return el?el.value.trim():'';}
    var errEl=document.getElementById('offerError');
    function showErr(msg){ if(errEl){errEl.textContent=msg;errEl.removeAttribute('hidden');} }
    function clearErr(){ if(errEl){errEl.setAttribute('hidden','');} }

    form.addEventListener('submit',function(e){
      e.preventDefault();
      clearErr();

      var name=val('f_name'), email=val('f_email');
      if(!name || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)){
        showErr('Please enter your name and a valid email.');
        return;
      }

      // No AJAX config (e.g. opened as a static file) -> graceful mailto fallback
      if(typeof epigeneticAjax==='undefined' || !epigeneticAjax.url){
        var lines=['Name: '+name,'Email: '+email];
        if(val('f_co'))lines.push('Company: '+val('f_co'));
        if(val('f_offer'))lines.push('Offer: '+val('f_offer'));
        lines.push(''); lines.push(val('f_msg')||'(no message)');
        window.location.href='mailto:contact@epigenetic.com?subject='+encodeURIComponent('EPIGENETIC.COM — Inquiry'+(val('f_offer')?(' / Offer '+val('f_offer')):''))+'&body='+encodeURIComponent(lines.join('\n'));
        return;
      }

      var original=send.innerHTML;
      send.disabled=true;
      send.innerHTML='Sending…';

      var data=new URLSearchParams();
      data.append('action','epigenetic_offer');
      data.append('nonce',epigeneticAjax.nonce);
      data.append('name',name);
      data.append('email',email);
      data.append('company',val('f_co'));
      data.append('offer',val('f_offer'));
      data.append('message',val('f_msg'));
      data.append('website',val('f_website')); // honeypot

      fetch(epigeneticAjax.url,{
        method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body:data.toString()
      })
      .then(function(r){return r.json();})
      .then(function(res){
        if(res && res.success){
          form.setAttribute('hidden','');
          document.getElementById('offerSent').removeAttribute('hidden');
          document.getElementById('offerSent').scrollIntoView({behavior:'smooth',block:'center'});
        } else {
          var m=(res && res.data && res.data.message) ? res.data.message : 'Something went wrong. Please email contact@epigenetic.com directly.';
          showErr(m);
          send.disabled=false; send.innerHTML=original;
        }
      })
      .catch(function(){
        showErr('Could not send right now. Please email contact@epigenetic.com directly.');
        send.disabled=false; send.innerHTML=original;
      });
    });
  })();

  // floating offer tab: smooth-scroll + flash, and tuck away when form is in view
  (function(){
    var tab=document.getElementById('offerTab');
    var card=document.getElementById('offer');
    if(!tab||!card)return;
    tab.addEventListener('click',function(e){
      e.preventDefault();
      card.scrollIntoView({behavior:reduce?'auto':'smooth',block:'center'});
      if(!reduce){card.classList.remove('flash');void card.offsetWidth;card.classList.add('flash');}
      var first=document.getElementById('f_name');
      if(first){setTimeout(function(){first.focus({preventScroll:true});}, reduce?0:650);}
    });
    if('IntersectionObserver' in window){
      var to=new IntersectionObserver(function(es){
        es.forEach(function(e){ tab.classList.toggle('tucked', e.isIntersecting); });
      },{threshold:.25});
      to.observe(card);
    }
  })();