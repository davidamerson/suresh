import concurrent.futures
import frida
import json
import re
import subprocess
import threading
import urllib.request
from urllib.parse import urlsplit

ALLOWED_CHANNELS={
"Rupavahini","Nethra TV","ITN","Vasantham TV","TV Derana",
"Swarnavahini","Sirasa TV","Shakthi TV","TV1","Hiru TV",
"Supreme TV","Ada Derana 24","Siyatha TV"
}
candidates={}
finished=threading.Event()
agent=r"""
setTimeout(function() {
Java.perform(function() {
  try {
    const DB=Java.use('android.database.sqlite.SQLiteDatabase');
    const Splash=Java.use('com.cy.cybertv.SplashScreen');
    const decrypt=Splash.nativeDecryptName.overload('java.lang.String');
    const db=DB.openDatabase('/data/user/0/com.cy.cybertv/databases/channelss.db',null,DB.OPEN_READONLY.value);
    const cur=db.rawQuery("SELECT channels_name,link,type FROM tvlist WHERE categories='Local'",null);
    let count=0;
    while(cur.moveToNext()){
      const name=String(cur.getString(0)), enc=String(cur.getString(1)),type=String(cur.getString(2));
      if (type!=='DDDD'||!/^(Rupavahini|Nethra TV|ITN|Vasantham TV|TV Derana|Swarnavahini|Sirasa TV|Shakthi TV|TV1|Hiru TV|Supreme TV|Ada Derana 24|Siyatha TV)$/.test(name)) continue;
      let url=null;
      try{url=String(decrypt.call(Splash,enc));}catch(e){send({type:'decode-error',name:name,error:String(e).slice(0,90)});}
      if(url && /^https:\/\//.test(url)){
        send({type:'candidate',name:name,url:url});
        count++;
      }
    }
    cur.close();db.close();
    send({type:'done',count:count});
  }catch(e){send({type:'error',error:String(e).slice(0,150)});}
});
},11000);
"""
def on_message(msg,_data):
    if msg.get('type')!='send':
        print('HOOK_EXCEPTION',str(msg)[:180],flush=True);finished.set();return
    obj=msg.get('payload') or {}
    ty=obj.get('type')
    if ty=='candidate':
        url=obj.get('url') or ''
        name=obj.get('name') or ''
        if name in ALLOWED_CHANNELS and url.startswith('https://tv1.floodsupport.site/') and len(url)<200:
            candidates[name]=url
            print('DECODED_PRIVATE',name,'DASH',('.mpd' in url),'LEN',len(url),flush=True)
    elif ty in ('done','error'):
        print('DECODER_STATUS',str({k:v for k,v in obj.items() if k!='url'})[:150],flush=True)
        finished.set()
    elif ty=='decode-error':print('DECODER_ERROR',obj.get('name'),obj.get('error'),flush=True)
def probe(item):
    name,url=item
    record={'name':name,'manifest_http':None,'mpd_xml':False,'content_protection':None,'pssh':None,'frames':0,'decoder_pass':False,'error':''}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/dash+xml,*/*'})
        with urllib.request.urlopen(req,timeout=10) as response:
            record['manifest_http']=response.status
            raw=response.read(180000)
            record['content_type']=response.headers.get('Content-Type','')[:50]
        text=raw.decode('utf-8','replace')
        record['mpd_xml']=bool(re.search(r'<(?:\w+:)?MPD(?:\s|>)',text,re.I))
        record['content_protection']=bool(re.search(r'<(?:\w+:)?ContentProtection\b',text,re.I))
        record['pssh']=bool(re.search(r'<(?:\w+:)?pssh\b',text,re.I))
        record['manifest_bytes']=len(raw)
        if not record['mpd_xml'] or record['content_protection'] or record['pssh']:
            return record
        cmd=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-rw_timeout','10000000','-user_agent','Mozilla/5.0','-i',url,'-map','0:v:0','-an','-frames:v','5','-f','null','-','-progress','pipe:1']
        out=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        frames=max([int(x) for x in re.findall(r'^frame=(\d+)',out.stdout,re.M)] or [0])
        record['frames']=frames
        record['decoder_pass']=out.returncode==0 and frames>=5
        record['error']=out.stderr.strip().replace('\n',' | ')[:140]
    except Exception as e:
        record['error']=type(e).__name__+': '+str(e)[:105]
    return record

try:
    device=frida.get_usb_device(timeout=20)
    try:
        pid=device.get_process('com.cy.cybertv').pid
        session=device.attach(pid);spawned=False
    except frida.ProcessNotFoundError:
        pid=device.spawn(['com.cy.cybertv'])
        session=device.attach(pid);spawned=True
    print('INSTRUMENTED_PID',pid,flush=True)
    script=session.create_script(agent)
    script.on('message',on_message)
    script.load()
    if spawned:device.resume(pid)
    finished.wait(60)
    script.unload()
    session.detach()
except Exception as e:print('HOOK_FAILURE',type(e).__name__,str(e)[:160],flush=True)

print('CANDIDATES_COUNT',len(candidates),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    for record in pool.map(probe,candidates.items()):
        print('MEDIA_PROBE',json.dumps(record,sort_keys=True),flush=True)
print('FINISHED_MANIFEST_VIDEO_CHECK')
