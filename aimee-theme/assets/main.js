// wordmark letter-by-letter build: AIMEE.AI
  (function(){
    const word = document.getElementById('word');
    const seq = [
      {c:'A'},{c:'I'},{c:'M'},{c:'E'},{c:'E'},
      {c:'.',cls:'dot'},{c:'A',cls:'tld'},{c:'I',cls:'tld'}
    ];
    seq.forEach((it,i)=>{
      const s = document.createElement('span');
      s.className = 'ch' + (it.cls ? ' ' + it.cls : '');
      s.textContent = it.c;
      s.style.animationDelay = (0.35 + i*0.075) + 's';
      word.appendChild(s);
    });
    // shimmer sweep once the letters have landed
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(!reduce){
      setTimeout(()=>{
        word.classList.add('shimmer');
        setTimeout(()=>word.classList.remove('shimmer'), 1700);
      }, 1500);
    }
  })();

  // nav solidify on scroll
  const bar = document.getElementById('bar');
  const onScroll = () => { bar.classList.toggle('solid', window.scrollY > 40); };
  onScroll(); window.addEventListener('scroll', onScroll, {passive:true});

  // scroll reveal
  const io = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target);} });
  }, {threshold:0.12, rootMargin:'0px 0px -8% 0px'});
  document.querySelectorAll('.reveal').forEach(el=>io.observe(el));

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // offer form -> submit via AJAX to WordPress, stay on page, show sent state
  (function(){
    const form=document.getElementById('offerForm');
    const send=document.getElementById('offerSend');
    if(!form||!send)return;
    const val=id=>{const el=document.getElementById(id);return el?el.value.trim():'';};
    const errEl=document.getElementById('offerError');
    const showErr=msg=>{ if(errEl){errEl.textContent=msg;errEl.removeAttribute('hidden');} };
    const clearErr=()=>{ if(errEl){errEl.setAttribute('hidden','');} };

    form.addEventListener('submit',(e)=>{
      e.preventDefault();
      clearErr();

      const name=val('f_name'), email=val('f_email');
      if(!name || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)){
        showErr('Please enter your name and a valid email.');
        return;
      }

      // No AJAX config (e.g. opened as a static file) -> graceful mailto fallback
      if(typeof aimeeAjax==='undefined' || !aimeeAjax.url){
        const lines=['Name: '+name,'Email: '+email];
        if(val('f_co'))lines.push('Company / product: '+val('f_co'));
        lines.push('Offer: '+(val('f_offer')||'—')); lines.push(''); lines.push(val('f_msg')||'(no message)');
        window.location.href='mailto:contact@aimee.ai?subject='+encodeURIComponent('AIMEE.AI — Offer '+(val('f_offer')||'')+' / '+name)+'&body='+encodeURIComponent(lines.join('\n'));
        return;
      }

      const original=send.innerHTML;
      send.disabled=true;
      send.innerHTML='Sending…';

      const data=new URLSearchParams();
      data.append('action','aimee_offer');
      data.append('nonce',aimeeAjax.nonce);
      data.append('name',name);
      data.append('email',email);
      data.append('company',val('f_co'));
      data.append('offer',val('f_offer'));
      data.append('message',val('f_msg'));
      data.append('website',val('f_website')); // honeypot

      fetch(aimeeAjax.url,{
        method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body:data.toString()
      })
      .then(r=>r.json())
      .then(res=>{
        if(res && res.success){
          form.setAttribute('hidden','');
          document.getElementById('offerSent').removeAttribute('hidden');
          document.getElementById('offerSent').scrollIntoView({behavior:'smooth',block:'center'});
        } else {
          const m=(res && res.data && res.data.message) ? res.data.message : 'Something went wrong. Please email contact@aimee.ai directly.';
          showErr(m);
          send.disabled=false; send.innerHTML=original;
        }
      })
      .catch(()=>{
        showErr('Could not send right now. Please email contact@aimee.ai directly.');
        send.disabled=false; send.innerHTML=original;
      });
    });
  })();

  // floating offer tab: smooth-scroll + flash, tuck away when form is in view
  (function(){
    const tab=document.getElementById('offerTab');
    const card=document.getElementById('offer');
    if(!tab||!card)return;
    tab.addEventListener('click',e=>{
      e.preventDefault();
      card.scrollIntoView({behavior:reduceMotion?'auto':'smooth',block:'center'});
      if(!reduceMotion){card.classList.remove('flash');void card.offsetWidth;card.classList.add('flash');}
      const first=document.getElementById('f_name');
      if(first){setTimeout(()=>first.focus({preventScroll:true}), reduceMotion?0:650);}
    });
    const to=new IntersectionObserver(es=>{
      es.forEach(e=>tab.classList.toggle('tucked', e.isIntersecting));
    },{threshold:.25});
    to.observe(card);
  })();