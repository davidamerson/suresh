import argparse, json, math, zipfile, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from numba import njit

COMMISSION=0.07
GRID=1.0
MAX_BASKETS=50000

@njit(cache=True)
def proc(ts,bid,ask, st_i, st_f,
         out_start,out_end,out_pnl,out_reason,out_dir,out_ref_range,out_entry_spread,
         out_dur,out_maxpos,out_maxbal,out_switches,out_minliq,out_span,
         out_b5,out_s5,out_l5,out_r5,out_b15,out_s15,out_l15,out_r15,
         out_b30,out_s30,out_l30,out_r30,out_b60,out_s60,out_l60,out_r60):
    # st_i: last_day,cur_hour,init,has_ref,armed,stopped,open,buy_n,sell_n,maxpl,minnl,maxpos,lastside,switches,bcount,dir,snapmask
    # st_f: hour_hi,hour_lo,prev_bid,prev_ask,last_bid,last_ask,ref_hi,ref_lo,p0,buy_sum,sell_sum,day_realized,start_ts,entry_spread,minliq,hi,lo
    last_day,cur_hour,init,has_ref,armed,stopped,op,bn,sn,maxpl,minnl,maxpos,lastside,switches,bcnt,idir,snapmask = st_i
    hour_hi,hour_lo,prev_bid,prev_ask,last_bid,last_ask,ref_hi,ref_lo,p0,bsum,ssum,dayreal,start_ts,espread,minliq,phi,plo = st_f

    for j in range(len(ts)):
        t=ts[j]; b=bid[j]; a=ask[j]
        if not (math.isfinite(b) and math.isfinite(a)): continue
        day=t//86400000000000; hour=t//3600000000000
        if init==0:
            init=1; last_day=day; cur_hour=hour; hour_hi=b; hour_lo=b; prev_bid=b; prev_ask=a; last_bid=b; last_ask=a

        # Friday flat at previous day's final quote, then day reset.
        if day!=last_day:
            pdow=(last_day+3)%7
            if pdow==4 and op!=0:
                liq=bn*last_bid-bsum+ssum-sn*last_ask-op*COMMISSION
                if bcnt<MAX_BASKETS:
                    k=bcnt; out_end[k]=int(st_f[5] if False else 0)  # overwritten below using final tick approximation
                    out_end[k]=t-1; out_pnl[k]=liq; out_reason[k]=3
                    out_dur[k]=(t-start_ts)/60000000000.0; out_maxpos[k]=maxpos; out_maxbal[k]=min(maxpl,-minnl); out_switches[k]=switches; out_minliq[k]=minliq; out_span[k]=maxpl-minnl
                    bcnt+=1
                dayreal+=liq; op=0; bn=0; sn=0; bsum=0.0; ssum=0.0; armed=0
            dayreal=0.0; stopped=0; last_day=day

        if hour!=cur_hour:
            if op==0:
                ref_hi=hour_hi; ref_lo=hour_lo; has_ref=1
            cur_hour=hour; hour_hi=b; hour_lo=b
        else:
            if b>hour_hi: hour_hi=b
            if b<hour_lo: hour_lo=b

        if op!=0:
            liq=bn*b-bsum+ssum-sn*a-op*COMMISSION
            if liq<minliq: minliq=liq
            if b>phi: phi=b
            if b<plo: plo=b
            elapsed=(t-start_ts)/60000000000.0
            # Snapshots encode balanced depth, switches, liq, price range at/after threshold.
            if elapsed>=5.0 and (snapmask&1)==0:
                k=bcnt; out_b5[k]=min(maxpl,-minnl); out_s5[k]=switches; out_l5[k]=liq; out_r5[k]=phi-plo; snapmask|=1
            if elapsed>=15.0 and (snapmask&2)==0:
                k=bcnt; out_b15[k]=min(maxpl,-minnl); out_s15[k]=switches; out_l15[k]=liq; out_r15[k]=phi-plo; snapmask|=2
            if elapsed>=30.0 and (snapmask&4)==0:
                k=bcnt; out_b30[k]=min(maxpl,-minnl); out_s30[k]=switches; out_l30[k]=liq; out_r30[k]=phi-plo; snapmask|=4
            if elapsed>=60.0 and (snapmask&8)==0:
                k=bcnt; out_b60[k]=min(maxpl,-minnl); out_s60[k]=switches; out_l60[k]=liq; out_r60[k]=phi-plo; snapmask|=8
            if dayreal+liq>=10.0:
                if bcnt<MAX_BASKETS:
                    k=bcnt; out_end[k]=t; out_pnl[k]=liq; out_reason[k]=2; out_dur[k]=elapsed; out_maxpos[k]=maxpos; out_maxbal[k]=min(maxpl,-minnl); out_switches[k]=switches; out_minliq[k]=minliq; out_span[k]=maxpl-minnl; bcnt+=1
                dayreal+=liq; op=0; bn=0; sn=0; bsum=0.; ssum=0.; stopped=1; armed=0

        if op==0 and stopped==0 and has_ref!=0 and armed==0 and b>=ref_lo and b<=ref_hi:
            armed=1

        if op==0 and stopped==0 and has_ref!=0 and armed!=0:
            d=0; fill=0.
            if prev_ask<=ref_hi and a>ref_hi: d=1; fill=a
            elif prev_bid>=ref_lo and b<ref_lo: d=-1; fill=b
            if d!=0 and bcnt<MAX_BASKETS:
                p0=fill; op=1; idir=d
                if d==1: bn=1; sn=0; bsum=fill; ssum=0.
                else: sn=1; bn=0; ssum=fill; bsum=0.
                maxpl=0; minnl=0; maxpos=1; lastside=0; switches=0; snapmask=0
                start_ts=float(t); espread=a-b; minliq=-COMMISSION-(a-b if d==1 else 0.0); phi=b; plo=b; armed=0
                k=bcnt; out_start[k]=t; out_dir[k]=d; out_ref_range[k]=ref_hi-ref_lo; out_entry_spread[k]=espread
                out_b5[k]=-1; out_s5[k]=-1; out_l5[k]=np.nan; out_r5[k]=np.nan
                out_b15[k]=-1; out_s15[k]=-1; out_l15[k]=np.nan; out_r15[k]=np.nan
                out_b30[k]=-1; out_s30[k]=-1; out_l30[k]=np.nan; out_r30[k]=np.nan
                out_b60[k]=-1; out_s60[k]=-1; out_l60[k]=np.nan; out_r60[k]=np.nan

        if op!=0:
            # positive virgin levels
            while b>=p0+(maxpl+1)*GRID and op!=0:
                liq=bn*b-bsum+ssum-sn*a-op*COMMISSION
                if liq>0.0:
                    if bcnt<MAX_BASKETS:
                        k=bcnt; out_end[k]=t; out_pnl[k]=liq; out_reason[k]=1; out_dur[k]=(t-start_ts)/60000000000.; out_maxpos[k]=maxpos; out_maxbal[k]=min(maxpl,-minnl); out_switches[k]=switches; out_minliq[k]=minliq; out_span[k]=maxpl-minnl; bcnt+=1
                    dayreal+=liq; op=0; bn=0; sn=0; bsum=0.; ssum=0.; armed=0; break
                bn+=1; bsum+=a; op+=1; maxpl+=1; maxpos=max(maxpos,op)
                if lastside!=0 and lastside!=1: switches+=1
                lastside=1
            while op!=0 and b<=p0+(minnl-1)*GRID:
                liq=bn*b-bsum+ssum-sn*a-op*COMMISSION
                if liq>0.0:
                    if bcnt<MAX_BASKETS:
                        k=bcnt; out_end[k]=t; out_pnl[k]=liq; out_reason[k]=1; out_dur[k]=(t-start_ts)/60000000000.; out_maxpos[k]=maxpos; out_maxbal[k]=min(maxpl,-minnl); out_switches[k]=switches; out_minliq[k]=minliq; out_span[k]=maxpl-minnl; bcnt+=1
                    dayreal+=liq; op=0; bn=0; sn=0; bsum=0.; ssum=0.; armed=0; break
                sn+=1; ssum+=b; op+=1; minnl-=1; maxpos=max(maxpos,op)
                if lastside!=0 and lastside!=-1: switches+=1
                lastside=-1
            if op==0 and stopped==0 and dayreal>=10.0:
                stopped=1; armed=0

        prev_bid=b; prev_ask=a; last_bid=b; last_ask=a

    st_i[:] = np.array([last_day,cur_hour,init,has_ref,armed,stopped,op,bn,sn,maxpl,minnl,maxpos,lastside,switches,bcnt,idir,snapmask],dtype=np.int64)
    st_f[:] = np.array([hour_hi,hour_lo,prev_bid,prev_ask,last_bid,last_ask,ref_hi,ref_lo,p0,bsum,ssum,dayreal,start_ts,espread,minliq,phi,plo],dtype=np.float64)


def dl(url,path):
    h=hashlib.sha256(); n=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for x in r.iter_content(1024*1024):
                if x: f.write(x);h.update(x);n+=len(x)
    return n,h.hexdigest()


def run(year,months,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    I=lambda fill=0: np.full(MAX_BASKETS,fill,dtype=np.int64)
    F=lambda fill=np.nan: np.full(MAX_BASKETS,fill,dtype=np.float64)
    start=I(-1);end=I(-1);pnl=F();reason=I(0);direc=I(0);ref=F();spread=F();dur=F();maxpos=I(0);maxbal=I(0);sw=I(0);minliq=F();span=I(0)
    b5=I(-1);s5=I(-1);l5=F();r5=F();b15=I(-1);s15=I(-1);l15=F();r15=F();b30=I(-1);s30=I(-1);l30=F();r30=F();b60=I(-1);s60=I(-1);l60=F();r60=F()
    sti=np.array([-1,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],dtype=np.int64)
    stf=np.zeros(17,dtype=np.float64)
    prov=[]
    # compile
    proc(np.empty(0,dtype=np.int64),np.empty(0),np.empty(0),sti,stf,start,end,pnl,reason,direc,ref,spread,dur,maxpos,maxbal,sw,minliq,span,b5,s5,l5,r5,b15,s15,l15,r15,b30,s30,l30,r30,b60,s60,l60,r60)
    for m in months:
        mm=f'{m:02d}';fn=f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip';url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}';path=outdir/fn
        print('DOWNLOAD',url,flush=True);n,sha=dl(url,path);rows=0
        with zipfile.ZipFile(path) as z:
            for name in [x for x in z.namelist() if x.lower().endswith('.csv')]:
                with z.open(name) as fh:
                    for df in pd.read_csv(fh,usecols=['Timestamp','Bid','Ask'],chunksize=500000):
                        t=pd.to_datetime(df.Timestamp,utc=True,errors='coerce');good=t.notna()&df.Bid.notna()&df.Ask.notna();df=df.loc[good];t=t.loc[good]
                        proc(t.astype('int64').to_numpy(np.int64,copy=False),df.Bid.to_numpy(np.float64,copy=False),df.Ask.to_numpy(np.float64,copy=False),sti,stf,start,end,pnl,reason,direc,ref,spread,dur,maxpos,maxbal,sw,minliq,span,b5,s5,l5,r5,b15,s15,l15,r15,b30,s30,l30,r30,b60,s60,l60,r60);rows+=len(df)
        path.unlink(missing_ok=True);prov.append({'month':m,'rows':rows,'bytes':n,'sha256':sha});print('DONE',year,mm,rows,'baskets',sti[14],flush=True)
    n=int(sti[14]);
    data=pd.DataFrame({'start_ns':start[:n],'end_ns':end[:n],'pnl':pnl[:n],'reason':reason[:n],'direction':direc[:n],'ref_h1_range':ref[:n],'entry_spread':spread[:n],'duration_min':dur[:n],'max_positions':maxpos[:n],'max_balanced_depth':maxbal[:n],'side_switches':sw[:n],'min_liq_pnl':minliq[:n],'level_span':span[:n],
        'bal5':b5[:n],'switch5':s5[:n],'liq5':l5[:n],'range5':r5[:n],'bal15':b15[:n],'switch15':s15[:n],'liq15':l15[:n],'range15':r15[:n],'bal30':b30[:n],'switch30':s30[:n],'liq30':l30[:n],'range30':r30[:n],'bal60':b60[:n],'switch60':s60[:n],'liq60':l60[:n],'range60':r60[:n]})
    data['start']=pd.to_datetime(data.start_ns,unit='ns',utc=True);data['end']=pd.to_datetime(data.end_ns,unit='ns',utc=True,errors='coerce');data['start_dow']=data.start.dt.day_name();data['start_hour']=data.start.dt.hour
    data.to_csv(outdir/f'ph1_forensic_baskets_{year}.csv',index=False)
    severe=data[data.pnl<=-50].copy(); severe.to_csv(outdir/f'ph1_forensic_severe_{year}.csv',index=False)
    # Simple threshold scan: capture severe long-lived baskets vs fraction of all baskets flagged at early checkpoints.
    scans=[]
    for mins in [5,15,30,60]:
        for feature,prefix in [('bal','bal'),('switch','switch')]:
            col=f'{prefix}{mins}'
            for th in ([1,2,3,4,5] if feature=='bal' else [1,2,3,4,5,6,8,10]):
                valid=data[col]>=0; flag=valid&(data[col]>=th); sev=(data.pnl<=-50)
                scans.append({'minutes':mins,'feature':feature,'threshold':th,'all_flagged':int(flag.sum()),'all_baskets':len(data),'flag_pct':100*flag.mean(),'severe_captured':int((flag&sev).sum()),'severe_total':int(sev.sum())})
        col=f'liq{mins}'
        for th in [-5,-10,-20,-30,-50,-75,-100]:
            valid=data[col].notna();flag=valid&(data[col]<=th);sev=data.pnl<=-50
            scans.append({'minutes':mins,'feature':'liq_le','threshold':th,'all_flagged':int(flag.sum()),'all_baskets':len(data),'flag_pct':100*flag.mean(),'severe_captured':int((flag&sev).sum()),'severe_total':int(sev.sum())})
    pd.DataFrame(scans).to_csv(outdir/f'ph1_forensic_thresholds_{year}.csv',index=False)
    print('\nSEVERE BASKETS',year,len(severe),'of',len(data))
    if len(severe): print(severe[['start','end','pnl','duration_min','max_positions','max_balanced_depth','side_switches','min_liq_pnl','ref_h1_range','entry_spread','bal15','switch15','liq15','bal30','switch30','liq30','bal60','switch60','liq60']].to_string(index=False))
    print('\nMEDIANS severe vs nonsevere')
    cols=['duration_min','max_positions','max_balanced_depth','side_switches','min_liq_pnl','ref_h1_range','entry_spread','bal15','switch15','liq15','bal30','switch30','liq30','bal60','switch60','liq60']
    for c in cols:
        print(c,'sev=',severe[c].median() if len(severe) else np.nan,'other=',data.loc[data.pnl>-50,c].median())
    with open(outdir/f'ph1_forensic_provenance_{year}.json','w') as f: json.dump({'year':year,'months':months,'files':prov,'baskets':len(data),'severe_le_-50':len(severe)},f,indent=2)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--year',type=int,required=True);ap.add_argument('--outdir',required=True);a=ap.parse_args();months=list(range(1,13)) if a.year==2025 else list(range(1,11));run(a.year,months,a.outdir)
