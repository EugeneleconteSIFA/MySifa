"""Bloc JS partagé : guide code-barre traça fournisseur (MyStock + MyProd + Paramètres)."""

TRACA_GUIDE_SCRIPT_BLOCK = r"""
function _tgEsc(s){
  if(s==null||s==='')return'';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function showTracaGuide(fournisseurId, fournisseurNom, fournisseursList){
  document.getElementById('traca-guide-modal')?.remove();
  const list=Array.isArray(fournisseursList)?fournisseursList:[];
  const backdrop=document.createElement('div');
  backdrop.id='traca-guide-modal';
  backdrop.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9000;display:flex;align-items:center;justify-content:center;padding:16px';
  const box=document.createElement('div');
  box.style.cssText='background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:480px;width:100%;max-height:90vh;overflow:auto';
  function renderContent(selId){
    const f=list.find(x=>Number(x.id)===Number(selId));
    const hasInfo=f&&(f.traca_photo_url||f.traca_explication||f.traca_exemple_code);
    let bodyHtml='';
    if(!selId){
      bodyHtml='<p style="color:var(--muted);font-size:13px;text-align:center;padding:12px 0">Sélectionnez un fournisseur pour afficher le guide.</p>';
    }else if(!hasInfo){
      bodyHtml='<p style="color:var(--muted);font-size:13px;padding:12px 0">Pas d\'indication disponible pour ce fournisseur.</p>';
    }else{
      if(f.traca_explication){
        bodyHtml+='<div style="margin-bottom:14px"><p style="font-size:12px;color:var(--text2);margin:0 0 4px;font-weight:600;text-transform:uppercase;letter-spacing:.04em">Où trouver le code</p><p style="margin:0;font-size:14px;color:var(--text);line-height:1.5;white-space:pre-wrap">'+_tgEsc(f.traca_explication)+'</p></div>';
      }
      if(f.traca_exemple_code){
        bodyHtml+='<div style="margin-bottom:14px"><p style="font-size:12px;color:var(--text2);margin:0 0 6px;font-weight:600;text-transform:uppercase;letter-spacing:.04em">Format du code</p><code style="display:inline-block;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 12px;font-size:15px;letter-spacing:.08em;color:var(--text)">'+_tgEsc(f.traca_exemple_code)+'</code></div>';
      }
      if(f.traca_photo_url){
        const u=_tgEsc(f.traca_photo_url);
        bodyHtml+='<div><p style="font-size:12px;color:var(--text2);margin:0 0 8px;font-weight:600;text-transform:uppercase;letter-spacing:.04em">Photo de l\'étiquette</p><img src="'+u+'" alt="" style="max-width:100%;border-radius:10px;border:1px solid var(--border);display:block"></div>';
      }
    }
    const opts=list.map(x=>'<option value="'+Number(x.id)+'"'+(Number(x.id)===Number(selId)?' selected':'')+'>'+_tgEsc(x.nom)+'</option>').join('');
    box.innerHTML='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px"><h3 style="margin:0;font-size:16px;font-weight:600">Quel code scanner ?</h3><button type="button" id="tg-close" style="background:none;border:none;cursor:pointer;color:var(--text2);font-size:20px;line-height:1;padding:2px 6px">&times;</button></div><label style="font-size:12px;color:var(--text2);display:block;margin-bottom:6px">Fournisseur</label><select id="tg-select" style="width:100%;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;font-size:14px;margin-bottom:16px"><option value="">— Choisir un fournisseur —</option>'+opts+'</select><div id="tg-body">'+bodyHtml+'</div>';
    box.querySelector('#tg-close').onclick=function(){backdrop.remove()};
    const sel=box.querySelector('#tg-select');
    if(sel)sel.onchange=function(){renderContent(sel.value?Number(sel.value):null)};
  }
  renderContent(fournisseurId||null);
  backdrop.appendChild(box);
  backdrop.onclick=function(e){if(e.target===backdrop)backdrop.remove()};
  document.body.appendChild(backdrop);
}
async function startTracaExampleScan(onDone){
  if(typeof onDone!=='function')return;
  const isAndroid=/Android/.test(navigator.userAgent||'');
  let scanning=true,stream=null,reader=null;
  const overlay=document.createElement('div');
  overlay.className='camera-modal';
  overlay.style.cssText='position:fixed;inset:0;z-index:9500;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;padding:16px';
  const inner=document.createElement('div');
  inner.style.cssText='background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px;max-width:420px;width:100%';
  const video=document.createElement('video');
  video.setAttribute('autoplay','');video.setAttribute('playsinline','');video.setAttribute('muted','');
  video.style.cssText='width:100%;max-height:220px;border-radius:8px;background:#000';
  const hint=document.createElement('p');
  hint.style.cssText='font-size:12px;color:var(--text2);margin:10px 0';
  hint.textContent='Pointez vers un code-barres d\'exemple sur une bobine.';
  const stop=function(){
    scanning=false;
    if(reader){try{reader.reset()}catch(e){}reader=null}
    if(stream){stream.getTracks().forEach(function(t){t.stop()});stream=null}
    if(overlay.parentNode)overlay.remove();
  };
  const btn=document.createElement('button');
  btn.type='button';btn.textContent='Fermer';btn.style.cssText='margin-top:10px;padding:8px 14px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);cursor:pointer;font-family:inherit';
  btn.onclick=stop;
  inner.appendChild(video);inner.appendChild(hint);inner.appendChild(btn);overlay.appendChild(inner);document.body.appendChild(overlay);
  try{
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)throw new Error('Caméra non disponible');
    stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});
    video.srcObject=stream;
    const delay=1500;var t0=Date.now();
    if(typeof ZXing==='undefined'){
      await new Promise(function(res,rej){
        var s=document.createElement('script');
        s.src='https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
        s.onload=res;s.onerror=rej;document.head.appendChild(s);
      });
    }
    const onCode=function(txt){
      if(!scanning)return;
      if(Date.now()-t0<delay)return;
      scanning=false;
      var c=(txt||'').trim();
      if(reader){try{reader.reset()}catch(e){}reader=null}
      if(stream){stream.getTracks().forEach(function(t){t.stop()});stream=null}
      if(overlay.parentNode)overlay.remove();
      if(c)onDone(c);
    };
    if(isAndroid&&('BarcodeDetector'in window)){
      var qrHints=new Map();
      qrHints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS,[ZXing.BarcodeFormat.QR_CODE]);
      qrHints.set(ZXing.DecodeHintType.TRY_HARDER,true);
      reader=new ZXing.BrowserMultiFormatReader(qrHints);
      reader.decodeFromStream(stream,video,function(result){if(result&&scanning)onCode(result.getText())});
      var det=new BarcodeDetector({formats:['code_128','ean_13','ean_8','data_matrix','code_39','upc_a','upc_e','qr_code']});
      var tick=async function(){
        if(!scanning)return;
        if(video.readyState<2||!video.videoWidth){setTimeout(tick,100);return}
        try{var found=await det.detect(video);if(found.length)onCode(found[0].rawValue)}catch(e){}
        if(scanning)setTimeout(tick,150);
      };
      setTimeout(tick,500);
    }else{
      var canvas=document.createElement('canvas');
      var ctx=canvas.getContext('2d',{willReadFrequently:true});
      var hints=new Map();
      hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS,[ZXing.BarcodeFormat.CODE_128,ZXing.BarcodeFormat.EAN_13,ZXing.BarcodeFormat.EAN_8,ZXing.BarcodeFormat.QR_CODE,ZXing.BarcodeFormat.DATA_MATRIX]);
      hints.set(ZXing.DecodeHintType.TRY_HARDER,true);
      reader=new ZXing.BrowserMultiFormatReader(hints);
      var loop=function(){
        if(!scanning)return;
        if(video.readyState<2||!video.videoWidth){setTimeout(loop,100);return}
        try{
          canvas.width=video.videoWidth;canvas.height=video.videoHeight;
          ctx.drawImage(video,0,0);
          var img=ctx.getImageData(0,0,canvas.width,canvas.height);
          var lum=new ZXing.RGBLuminanceSource(img.data,canvas.width,canvas.height);
          var bmp=new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(lum));
          var res=reader.decode(bmp);
          if(res)onCode(res.getText());
        }catch(e){}
        if(scanning)setTimeout(loop,150);
      };
      setTimeout(loop,400);
    }
  }catch(e){
    stop();
    if(typeof toast==='function')toast((e&&e.message)||'Caméra indisponible',true);
    else if(typeof showToast==='function')showToast((e&&e.message)||'Caméra indisponible','danger');
  }
}
"""
