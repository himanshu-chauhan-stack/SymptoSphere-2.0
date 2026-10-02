(() => {
  let language='en',bundle={};
  window.SymptoI18n={t:key=>bundle[key]||null};
  async function apply(next){try{const response=await fetch('/api/translations/'+next);if(!response.ok)return;bundle=await response.json();language=next;document.documentElement.lang=next;
    document.querySelectorAll('[data-i18n]').forEach(el=>{const value=bundle[el.dataset.i18n];if(value)el.textContent=value;});
    document.getElementById('languageToggle').textContent=next==='en'?'EN / हिन्दी':'हिन्दी / EN';document.dispatchEvent(new Event('sympto:language'));
  }catch{}}
  document.getElementById('languageToggle')?.addEventListener('click',()=>apply(language==='en'?'hi':'en'));
  apply('en');
})();