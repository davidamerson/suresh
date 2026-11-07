import concurrent.futures as cf
import datetime as dt
import json
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TARGETS={
'Sirasa TV':('sirasatv','sirasa tv'),
'TV Derana':('tvderana','tv derana'),
'Swarnavahini':('swarnavahini','swarnawahini'),
'ITN':('itn','independent television network'),
'Rupavahini':('rupavahini','jathika rupavahini'),
'Hiru TV':('hiru tv','hirutv'),
'Siyatha TV':('siyatha tv','siyathatv'),
'Shakthi TV':('shakthi tv','shakthitv'),
'Supreme TV':('supreme tv','supremetv'),
'TV1':('tv1','tv 1','tv one'),
'Nethra TV':('nethra tv','nethratv'),
'Vasantham TV':('vasantham tv','vasanthamtv'),
'Ada Derana 24':('ada derana 24','adaderana24')
}
ALIAS={re.sub(r'[^a-z0-9]','',a):n for n,v in TARGETS.items() for a in v}
SEEDS={
'Hiru TV':['https://tv.hiruhost.com:1936/8012/8012/playlist.m3u8','https://tv.lotustechnologieslk.net:1936/8012/8012/playlist.m3u8'],
'Rupavahini':['https://rpn.bozztv.com/slrclive/slrc/slrclive/index.m3u8'],
'Siyatha TV':['https://rtmp01.voaplus.com/hls/6x6ik312qk4grfxocfcv.m3u8','https://stvlk.live/live/eml079n7ui3ytg1c6x4/index.m3u8'],
'Sirasa TV':['https://edge2-moblive.yuppcdn.net/transsd/smil:sirtv09.smil/playlist.m3u8?dvr'],
'TV Derana':['https://edge3-moblive.yuppcdn.net/transhd2/smil:detv04.smil/index.m3u8','https://ythls.armelin.one/channel/UCbkMFGQ_RWIf0OiYeOpf6Ng.m3u8'],
'Swarnavahini':['https://teledrama.ebc.lk/TTT/proxy.php','https://jk3lz8xklw79-hls-live.5centscdn.com/efm/098f6bcd4621d373cade4e832627b4f6.sdp/playlist.m3u8'],
'ITN':['https://edge4-moblive.yuppcdn.net/transsd/smil:itn43.smil/playlist.m3u8','https://222103-hls.akamaized.net/668828a00bf80aa436254876/live_aabd3d003af211efadcf7986aa245789/rewind-3600.m3u8','https://j78dp2pnlq5r-hls-live.comcities.net/ITNDigital/cf467ddf13ba30dd3c71435cafa6fd6e.sdp/playlist_dvr.m3u8'],
'Shakthi TV':['https://mumbai-edge.smartplaytv.in/ShakthiTV/index.m3u8','https://edge4-moblive.yuppcdn.net/transsd/smil:saktv10.smil/playlist.m3u8?dvr'],
'TV1':['https://edge4-moblive.yuppcdn.net/trans1sd/smil:tv111.smil/playlist.m3u8'],
'Nethra TV':['https://edge3-moblive.yuppcdn.net/transsd/smil:chii02.smil/playlist.m3u8?dvr','https://ythls.armelin.one/channel/UC6b6XrsNOxQiS-FdfE8-Avw.m3u8'],
'Vasantham TV':['https://edge3-moblive.yuppcdn.net/trans1sd/smil:vatv07.smil/playlist.m3u8?dvr','https://222103-hls.akamaized.net/668828a00bf80aa436254876/live_2cdb4ef03c1311efadcf7986aa245789/rewind-3600.m3u8']
}
FEEDS=[
'https://raw.githubusercontent.com/iptv-org/iptv/master/streams/lk.m3u',
'https://list.iptvcat.com/my_list/889e81cde0b1b16b9f23fdbd1b4f14c0.m3u8'
]
USER_VERIFIED={ch:SEEDS[ch][0] for ch in ['Hiru TV','Rupavahini','Siyatha TV']}
def canonical(extinf):
    name=extinf.split(',')[-1].strip()
    found=re.search(r'tvg-id="([^"]+)',extinf)
    chan_id=found.group(1).split('.')[0].split('@')[0] if found else ''
    for v in (chan_id,name):
        n=re.sub(r'[^a-z0-9]','',v.lower())
        if n in ALIAS:return ALIAS[n]
        n=re.sub(r'\s*(?:\(\d+[ip]\)|\[not 24/7\]|\s+sd|\s+hd)\s*','',v.lower()).strip()
        n=re.sub(r'[^a-z0-9]','',n)
        if n in ALIAS:return ALIAS[n]
    return None
def permitted(url):
    s=url.lower()
    return (s.startswith('https://') or s.startswith('http://')) and not any(x in s for x in ['peotv.com','viu.lk','/drm/','/drm1/','/drm2/','clearkey','license?','token=','username=','password='])
def fetch(url):
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request,timeout=18) as r:return r.read(350000).decode('utf-8','replace')
    except Exception as e:
        print('FEED_ERROR',url,type(e).__name__,str(e)[:110],flush=True)
        return ''
def parse(text):
    prev=''
    for row in text.splitlines():
        row=row.strip()
        if row.startswith('#EXTINF:'):prev=row
        elif row.startswith(('https://','http://')) and prev:
            name=canonical(prev)
            if name and permitted(row):yield name,row
            prev=''
def probe(item):
    name,url=item
    cmd=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-rw_timeout','12000000','-user_agent','Mozilla/5.0','-i',url,'-map','0:v:0','-an','-frames:v','5','-f','null','-','-progress','pipe:1']
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=29)
        counts=[int(x) for x in re.findall(r'^frame=(\d+)\s*$',p.stdout,re.M)]
        count=max(counts or [0])
        return {'name':name,'url':url,'video_frames':count,'success':p.returncode==0 and count>=5,'error':p.stderr.strip().replace('\n',' | ')[:180]}
    except subprocess.TimeoutExpired:return {'name':name,'url':url,'video_frames':0,'success':False,'error':'Timeout after 29s'}
    except Exception as e:return {'name':name,'url':url,'video_frames':0,'success':False,'error':str(e)[:150]}
def main():
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    items=[];seen=set()
    def add(name,url):
        if name not in TARGETS or not permitted(url) or (name,url) in seen:return
        seen.add((name,url));items.append((name,url))
    for name,urls in SEEDS.items():
        for u in urls:add(name,u)
    for feed in FEEDS:
        candidates=list(parse(fetch(feed)))
        print('FEED',feed,'MATCHED',len(candidates),flush=True)
        for name,url in candidates:add(name,url)
    print('TOTAL_CANDIDATES',len(items),flush=True)
    checked=[]
    with cf.ThreadPoolExecutor(max_workers=7) as pool:
        for entry in pool.map(probe,items):
            checked.append(entry)
            print('PROBE',entry['name'],'OK' if entry['success'] else 'FAIL','FRAMES',entry['video_frames'],'URL',entry['url'],'ERROR',entry['error'][:75],flush=True)
    best={}
    for entry in checked:
        if entry['success'] and entry['name'] not in best:best[entry['name']]=dict(entry,verification='five decoded video frames on GitHub runner')
    for name,url in USER_VERIFIED.items():
        if name not in best:best[name]={'name':name,'url':url,'success':True,'verification':'confirmed by user on Android TV; remote runner may be geoblocked'}
    lines=['#EXTM3U','# Last checked '+stamp,'# Contains ONLY decoded streams or streams confirmed working by the TV Box owner.']
    for i,name in enumerate(TARGETS,1):
        if name in best:
            label='TV owner confirmed' if 'user on Android' in best[name]['verification'] else 'GitHub decoder confirmed'
            lines.extend([f'#EXTINF:-1 tvg-chno="{i}" group-title="Sri Lanka - {label}",{name}',best[name]['url']])
    (ROOT/'playlist.m3u').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    absent=[name for name in TARGETS if name not in best]
    report=['# Sri Lanka TV live-stream verification','',f'Last checked: {stamp}',f'**{len(best)} out of {len(TARGETS)} channels with evidence of playback**','', 'Real decoder rule: FFmpeg must decode five consecutive video frames. The 3 user-confirmed streams are included even if an overseas runner cannot play them.','', '## Available','']
    for name,entry in best.items():report.append(f'- {name}: {entry["verification"]}')
    report+=['','## Not verified']+[f'- {name}' for name in absent]+['','## Checks and errors']
    for entry in checked:report.append(f'- {entry["name"]}: {"PASS" if entry["success"] else "FAIL"}; {entry["video_frames"]} frames; {entry["url"]} ; {entry["error"]}')
    (ROOT/'report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    (ROOT/'results.json').write_text(json.dumps({'checked_at':stamp,'included':best,'missing':absent,'probes':checked},indent=2)+'\n',encoding='utf-8')
    print('VERIFIED_LIST',list(best),'NOT_VERIFIED',absent,flush=True)
if __name__=='__main__':main()
