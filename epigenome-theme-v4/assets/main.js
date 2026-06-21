(function(){
  /* wordmark letter-by-letter */
  var wm=document.getElementById('wordmark');
  if(wm){
    var name="EPIGENOME", tld=".COM", html="";
    for(var i=0;i<name.length;i++){
      html+='<span class="ch" style="animation-delay:'+(0.35+i*0.055)+'s,'+(1.4+i*0.04)+'s">'+name[i]+'</span>';
    }
    html+='<span class="ch tld" style="animation-delay:'+(0.35+name.length*0.055)+'s">'+tld+'</span>';
    wm.innerHTML=html;
  }

  /* scroll reveal */
  var io=new IntersectionObserver(function(entries){
    entries.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); } });
  },{threshold:0.16});
  document.querySelectorAll('.reveal,.scale-row,.sig-strike').forEach(function(el){io.observe(el);});

  /* form -> WordPress admin-ajax */
  var form=document.getElementById('offerForm');
  if(!form) return;
  var msg=document.getElementById('formMsg');
  var btn=document.getElementById('submitBtn');
  function show(t,kind){ msg.textContent=t; msg.className='form-msg '+kind; }

  form.addEventListener('submit',function(ev){
    ev.preventDefault();
    if(form.website.value){ return; } /* honeypot tripped */
    var nm=form.name.value.trim();
    var email=form.email.value.trim();
    if(!nm){ show('Please add your name so I know who I\u2019m replying to.','err'); form.name.focus(); return; }
    if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)){ show('That email doesn\u2019t look right \u2014 mind checking it?','err'); form.email.focus(); return; }

    btn.disabled=true; btn.textContent='Sending\u2026';

    var data=new FormData();
    data.append('action','epigenome_offer');
    data.append('nonce', EPIGENOME_AJAX.nonce);
    data.append('name', nm);
    data.append('company', form.company.value.trim());
    data.append('email', email);
    data.append('offer', form.offer.value.trim());
    data.append('message', form.message.value.trim());
    data.append('website', form.website.value);

    fetch(EPIGENOME_AJAX.url,{method:'POST',body:data,credentials:'same-origin'})
      .then(function(r){return r.json();})
      .then(function(res){
        if(res && res.success){
          var d = res.data || {};
          if(d.emailed){
            show('Thanks \u2014 your offer is in and a notification has gone to the owner. Expect a personal reply at '+email+'.','ok');
          }else{
            show('Thanks \u2014 your offer has been received and recorded. The owner reviews every submission and will reply to '+email+'. You can also reach them directly at contact@epigenome.com.','ok');
          }
          form.reset();
        }else{
          show((res && res.data && res.data.message) || 'Something went wrong sending that. Email contact@epigenome.com directly and it\u2019ll reach me.','err');
        }
      })
      .catch(function(){
        show('Network hiccup. Email contact@epigenome.com directly and it\u2019ll reach me.','err');
      })
      .finally(function(){ btn.disabled=false; btn.textContent='Send to the owner'; });
  });
})();
