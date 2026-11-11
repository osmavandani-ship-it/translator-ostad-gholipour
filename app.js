const $ = (id) => document.getElementById(id);
let lastResult = null;
let currentAudio = null;

async function checkStatus(){
  try{
    const r=await fetch('/api/status'); const d=await r.json();
    $('status').textContent=d.configured?'آماده استفاده':'نیازمند تنظیم کلید API';
    $('status').style.color=d.configured?'#16845d':'#b54708';
  }catch{$('status').textContent='سرور در دسترس نیست';}
}
checkStatus();

$('translate').addEventListener('click', async ()=>{
  const text=$('source').value.trim();
  hideError();
  if(!text){showError('لطفاً یک واژه یا متن وارد کنید.');return;}
  $('translate').disabled=true;$('translate').textContent='در حال ترجمه...';
  try{
    const response=await fetch('/api/translate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
    const data=await response.json();
    if(!response.ok) throw new Error(data.error||'خطا در ترجمه');
    lastResult=data;
    $('originalText').textContent=data.source_text;
    $('translatedText').textContent=data.translated_text;
    $('pronunciationText').textContent=data.pronunciation_fa;
    $('translatedListen').dataset.lang=data.translated_language;
    $('results').classList.remove('hidden');
    $('results').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){showError(e.message);}
  finally{$('translate').disabled=false;$('translate').textContent='ترجمه کن';}
});

$('clear').addEventListener('click',()=>{
  $('source').value='';$('results').classList.add('hidden');hideError();lastResult=null;
  if(currentAudio){currentAudio.pause();currentAudio=null;}
});

document.querySelectorAll('.listen').forEach(btn=>{
  btn.addEventListener('click',()=>speak($(btn.dataset.target).textContent,btn.dataset.lang));
});

async function speak(text,lang){
  if(!text.trim())return;
  hideError();
  if(currentAudio){currentAudio.pause();currentAudio=null;}
  document.querySelectorAll('.listen').forEach(b=>b.textContent='▶ پخش');
  try{
    const response=await fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,language:lang==='auto'?(lastResult?.source_language||'en'):lang})});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'خطا در تولید صدا');
    currentAudio=new Audio('data:'+data.mime+';base64,'+data.audio);
    currentAudio.play();
    currentAudio.onended=()=>{currentAudio=null;};
  }catch(e){showError(e.message);}
}
function showError(message){$('error').textContent=message;$('error').classList.remove('hidden');}
function hideError(){$('error').classList.add('hidden');$('error').textContent='';}
