import argparse, json, zipfile, hashlib
from pathlib import Path
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import requests
from numba import njit

START_BALANCE=1000.0
DAILY_TARGET=20.0
WITHDRAW=10.0
CONTRACT=100.0
LEVERAGE=2000.0
COMM_RT_PER_LOT=7.0
GROUP_TARGET=5.0
CONFIRM=2
MAX_GROUPS=64
CONFIG_NAMES=['ZR_CONS2_PAUSE1','ZR_CONS2_PAUSE2']
PAUSE=np.array([1,2],dtype=np.int64)
SESSIONS=[('AUSTRALIAN','Australia/Sydney',8),('ASIAN','Asia/Tokyo',9),('LONDON','Europe/London',8),('NEW_YORK','America/New_York',8)]


def download(url,out):
    h=hashlib.sha256(); total=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with open(out,'wb') as f:
            for c in r.iter_content(1024*1024):
                if c:
                    f.write(c); h.update(c); total+=len(c)
    return total,h.hexdigest()


def build_intervals(year):
    # Generate every local weekday opening hour; actual arming later requires >=30 distinct raw-data minutes.
    rows=[]
    d0=date(year,1,1)-timedelta(days=2)
    d1=(date(year,12,31) if year==2025 else date(2026,10,31))+timedelta(days=2)
    for sid,(_,zname,hour) in enumerate(SESSIONS):
        z=ZoneInfo(zname); d=d0
        while d<=d1:
            if d.weekday()<5:
                st=datetime.combine(d,time(hour,0),tzinfo=z).astimezone(timezone.utc)
                en=st+timedelta(hours=1)
                rows.append((int(pd.Timestamp(st).value),int(pd.Timestamp(en).value),sid))
            d+=timedelta(days=1)
    rows.sort()
    return (np.array([r[0] for r in rows],dtype=np.int64),
            np.array([r[1] for r in rows],dtype=np.int64),
            np.array([r[2] for r in rows],dtype=np.int64))


@njit(cache=True)
def process_chunk(ts,bids,asks,starts,ends,sids,pause,
                  balance,withdrawn,failed,failure_day,day_key,day_realized,day_target,
                  tlots,tshort,tle,tse,tcomm,
                  active,side,flips,bcnt,scnt,hi,lo,glots,gshort,gle,gse,gcomm,order_count,initial_tick,
                  groups_armed,groups_opened,groups_closed,trades,flip_total,target_days,skipped,cancelled,
                  min_eq,worst_float,max_margin,max_groups,max_positions,max_flips_group,
                  close_flip_hist,
                  shared_i,shared_f):
    # shared_i: cur_minute, interval_ptr, collecting, coll_last_min, coll_min_count, initialized, last_day
    # shared_f: minute_last_bid, minute_last_ask, coll_hi, coll_lo, last_bid, last_ask
    C=len(balance); G=active.shape[1]
    cur_min=shared_i[0]; ip=shared_i[1]; collecting=shared_i[2]; coll_last_min=shared_i[3]; coll_min_count=shared_i[4]; initialized=shared_i[5]
    minute_last_bid=shared_f[0]; minute_last_ask=shared_f[1]; coll_hi=shared_f[2]; coll_lo=shared_f[3]

    for j in range(len(ts)):
        t=ts[j]; bid=bids[j]; ask=asks[j]
        if not (np.isfinite(bid) and np.isfinite(ask)): continue
        mn=t//60000000000; day=t//86400000000000
        if initialized==0:
            initialized=1; cur_min=mn; minute_last_bid=bid; minute_last_ask=ask
            for c in range(C): day_key[c]=day

        # UTC day reset independently per configuration.
        for c in range(C):
            if failed[c]!=0: continue
            if day_key[c]!=day:
                day_key[c]=day; day_realized[c]=0.0; day_target[c]=0

        # A completed 1m close becomes known at this first tick of the next minute.
        if mn!=cur_min:
            cbid=minute_last_bid; cask=minute_last_ask
            for c in range(C):
                if failed[c]!=0: continue
                # Process confirmations and market orders at current tick.
                for g in range(G):
                    if active[c,g]==0: continue
                    buy_now=cask>hi[c,g]; sell_now=cbid<lo[c,g]
                    if buy_now: bcnt[c,g]+=1
                    else: bcnt[c,g]=0
                    if sell_now: scnt[c,g]+=1
                    else: scnt[c,g]=0
                    act_side=0; lot=0.0
                    if side[c,g]==0:
                        if bcnt[c,g]>=CONFIRM: act_side=1; lot=0.01
                        elif scnt[c,g]>=CONFIRM: act_side=-1; lot=0.01
                    elif side[c,g]==1 and scnt[c,g]>=CONFIRM:
                        act_side=-1; lot=0.02
                    elif side[c,g]==-1 and bcnt[c,g]>=CONFIRM:
                        act_side=1; lot=0.02
                    if act_side!=0:
                        # account equity and gross margin before the order
                        fl=CONTRACT*(bid*tlots[c]-tle[c]+tse[c]-ask*tshort[c])-tcomm[c]
                        eq=balance[c]+fl; mid=0.5*(bid+ask)
                        mar=(tlots[c]+tshort[c])*CONTRACT*mid/LEVERAGE
                        req=lot*CONTRACT*mid/LEVERAGE
                        if eq-mar<req:
                            failed[c]=1; failure_day[c]=day; break
                        px=ask if act_side==1 else bid
                        if act_side==1:
                            tlots[c]+=lot; tle[c]+=lot*px; glots[c,g]+=lot; gle[c,g]+=lot*px
                        else:
                            tshort[c]+=lot; tse[c]+=lot*px; gshort[c,g]+=lot; gse[c,g]+=lot*px
                        cc=COMM_RT_PER_LOT*lot; tcomm[c]+=cc; gcomm[c,g]+=cc
                        trades[c]+=1; order_count[c,g]+=1
                        if side[c,g]==0:
                            side[c,g]=act_side; initial_tick[c,g]=t; groups_opened[c]+=1
                        else:
                            side[c,g]=act_side; flips[c,g]+=1; flip_total[c]+=1
                            if flips[c,g]>max_flips_group[c]: max_flips_group[c]=flips[c,g]
                        bcnt[c,g]=0; scnt[c,g]=0
                if failed[c]!=0: continue
            cur_min=mn

        minute_last_bid=bid; minute_last_ask=ask

        # Tick-exact group liquidation target. Conservative accounting realizes exactly +$5.
        for c in range(C):
            if failed[c]!=0: continue
            for g in range(G):
                if active[c,g]==0 or side[c,g]==0: continue
                # Do not close an initial entry on its exact fill tick.
                if initial_tick[c,g]==t: continue
                gp=CONTRACT*(bid*glots[c,g]-gle[c,g]+gse[c,g]-ask*gshort[c,g])-gcomm[c,g]
                if gp>=GROUP_TARGET:
                    tlots[c]-=glots[c,g]; tle[c]-=gle[c,g]; tshort[c]-=gshort[c,g]; tse[c]-=gse[c,g]; tcomm[c]-=gcomm[c,g]
                    balance[c]+=GROUP_TARGET; day_realized[c]+=GROUP_TARGET; groups_closed[c]+=1
                    f=flips[c,g]
                    if f>=close_flip_hist.shape[1]: f=close_flip_hist.shape[1]-1
                    close_flip_hist[c,f]+=1
                    active[c,g]=0; side[c,g]=0; flips[c,g]=0; bcnt[c,g]=0; scnt[c,g]=0
                    glots[c,g]=0.0; gshort[c,g]=0.0; gle[c,g]=0.0; gse[c,g]=0.0; gcomm[c,g]=0.0; order_count[c,g]=0; initial_tick[c,g]=-1
                    if day_target[c]==0 and day_realized[c]>=DAILY_TARGET:
                        day_target[c]=1; target_days[c]+=1; balance[c]-=WITHDRAW; withdrawn[c]+=WITHDRAW

        # Risk marks and account failure.
        for c in range(C):
            if failed[c]!=0: continue
            fl=CONTRACT*(bid*tlots[c]-tle[c]+tse[c]-ask*tshort[c])-tcomm[c]; eq=balance[c]+fl
            mid=0.5*(bid+ask); mar=(tlots[c]+tshort[c])*CONTRACT*mid/LEVERAGE
            if eq<min_eq[c]: min_eq[c]=eq
            if fl<worst_float[c]: worst_float[c]=fl
            if mar>max_margin[c]: max_margin[c]=mar
            if eq<=0.0:
                failed[c]=1; failure_day[c]=day

        # Cancel unentered setups while danger mode or daily target is active.
        for c in range(C):
            if failed[c]!=0: continue
            danger=0
            for g in range(G):
                if active[c,g]!=0 and side[c,g]!=0 and flips[c,g]>=pause[c]: danger=1; break
            if danger!=0 or day_target[c]!=0:
                for g in range(G):
                    if active[c,g]!=0 and side[c,g]==0:
                        active[c,g]=0; cancelled[c]+=1

        # Finalize any completed opening-H1 interval before activating a later one.
        while collecting!=0 and ip<len(starts) and t>=ends[ip]:
            if coll_min_count>=30:
                for c in range(C):
                    if failed[c]!=0: continue
                    danger=0
                    for g in range(G):
                        if active[c,g]!=0 and side[c,g]!=0 and flips[c,g]>=pause[c]: danger=1; break
                    if day_target[c]!=0 or danger!=0:
                        skipped[c]+=1
                    else:
                        slot=-1
                        for g in range(G):
                            if active[c,g]==0: slot=g; break
                        if slot<0:
                            failed[c]=1; failure_day[c]=day
                        else:
                            active[c,slot]=1; side[c,slot]=0; flips[c,slot]=0; bcnt[c,slot]=0; scnt[c,slot]=0
                            hi[c,slot]=coll_hi; lo[c,slot]=coll_lo; glots[c,slot]=0.0; gshort[c,slot]=0.0; gle[c,slot]=0.0; gse[c,slot]=0.0; gcomm[c,slot]=0.0; order_count[c,slot]=0; initial_tick[c,slot]=-1
                            groups_armed[c]+=1
            collecting=0; ip+=1; coll_last_min=-1; coll_min_count=0; coll_hi=0.0; coll_lo=0.0

        # Skip intervals already entirely before this tick.
        while collecting==0 and ip<len(starts) and t>=ends[ip]: ip+=1
        # Activate interval if current tick is inside its opening hour.
        if collecting==0 and ip<len(starts) and t>=starts[ip] and t<ends[ip]:
            collecting=1; coll_hi=ask; coll_lo=bid; coll_last_min=mn; coll_min_count=1
        elif collecting!=0 and ip<len(starts) and t<ends[ip]:
            if ask>coll_hi: coll_hi=ask
            if bid<coll_lo: coll_lo=bid
            if mn!=coll_last_min:
                coll_last_min=mn; coll_min_count+=1

        # Current maxima after possible arming/closing.
        for c in range(C):
            if failed[c]!=0: continue
            ng=0; np_=0
            for g in range(G):
                if active[c,g]!=0 and side[c,g]!=0:
                    ng+=1; np_+=order_count[c,g]
            if ng>max_groups[c]: max_groups[c]=ng
            if np_>max_positions[c]: max_positions[c]=np_

        shared_f[4]=bid; shared_f[5]=ask

    shared_i[0]=cur_min; shared_i[1]=ip; shared_i[2]=collecting; shared_i[3]=coll_last_min; shared_i[4]=coll_min_count; shared_i[5]=initialized
    shared_f[0]=minute_last_bid; shared_f[1]=minute_last_ask; shared_f[2]=coll_hi; shared_f[3]=coll_lo


def run(year,outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True)
    starts,ends,sids=build_intervals(year)
    C=2; G=MAX_GROUPS
    balance=np.full(C,START_BALANCE); withdrawn=np.zeros(C); failed=np.zeros(C,dtype=np.int64); failure_day=np.full(C,-1,dtype=np.int64)
    day_key=np.full(C,-1,dtype=np.int64); day_realized=np.zeros(C); day_target=np.zeros(C,dtype=np.int64)
    tlots=np.zeros(C); tshort=np.zeros(C); tle=np.zeros(C); tse=np.zeros(C); tcomm=np.zeros(C)
    active=np.zeros((C,G),dtype=np.int64); side=np.zeros((C,G),dtype=np.int64); flips=np.zeros((C,G),dtype=np.int64); bcnt=np.zeros((C,G),dtype=np.int64); scnt=np.zeros((C,G),dtype=np.int64)
    hi=np.zeros((C,G)); lo=np.zeros((C,G)); glots=np.zeros((C,G)); gshort=np.zeros((C,G)); gle=np.zeros((C,G)); gse=np.zeros((C,G)); gcomm=np.zeros((C,G)); order_count=np.zeros((C,G),dtype=np.int64); initial_tick=np.full((C,G),-1,dtype=np.int64)
    groups_armed=np.zeros(C,dtype=np.int64); groups_opened=np.zeros(C,dtype=np.int64); groups_closed=np.zeros(C,dtype=np.int64); trades=np.zeros(C,dtype=np.int64); flip_total=np.zeros(C,dtype=np.int64); target_days=np.zeros(C,dtype=np.int64); skipped=np.zeros(C,dtype=np.int64); cancelled=np.zeros(C,dtype=np.int64)
    min_eq=np.full(C,START_BALANCE); worst_float=np.zeros(C); max_margin=np.zeros(C); max_groups=np.zeros(C,dtype=np.int64); max_positions=np.zeros(C,dtype=np.int64); max_flips_group=np.zeros(C,dtype=np.int64)
    close_flip_hist=np.zeros((C,128),dtype=np.int64)
    shared_i=np.array([-1,0,0,-1,0,0],dtype=np.int64); shared_f=np.zeros(6)
    # compile
    process_chunk(np.empty(0,dtype=np.int64),np.empty(0),np.empty(0),starts,ends,sids,PAUSE,balance,withdrawn,failed,failure_day,day_key,day_realized,day_target,tlots,tshort,tle,tse,tcomm,active,side,flips,bcnt,scnt,hi,lo,glots,gshort,gle,gse,gcomm,order_count,initial_tick,groups_armed,groups_opened,groups_closed,trades,flip_total,target_days,skipped,cancelled,min_eq,worst_float,max_margin,max_groups,max_positions,max_flips_group,close_flip_hist,shared_i,shared_f)

    provenance=[]; total_rows=0; months=range(1,13) if year==2025 else range(1,11)
    for month in months:
        mm=f'{month:02d}'; fn=f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'; url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}'; path=out/fn
        print('DOWNLOAD',url,flush=True); nbytes,sha=download(url,path); mrows=0
        with zipfile.ZipFile(path) as z:
            for csv_name in [x for x in z.namelist() if x.lower().endswith('.csv')]:
                with z.open(csv_name) as fh:
                    for df in pd.read_csv(fh,usecols=['Timestamp','Bid','Ask'],chunksize=500_000):
                        t=pd.to_datetime(df.Timestamp,utc=True,errors='coerce'); good=t.notna()&df.Bid.notna()&df.Ask.notna()
                        if year==2026 and month==10: good &= t<=pd.Timestamp('2026-10-29 23:59:59.999999999',tz='UTC')
                        if not bool(good.all()): df=df.loc[good]; t=t.loc[good]
                        if len(df)==0: continue
                        ts=t.astype('int64').to_numpy(np.int64,copy=False); bids=df.Bid.to_numpy(np.float64,copy=False); asks=df.Ask.to_numpy(np.float64,copy=False)
                        process_chunk(ts,bids,asks,starts,ends,sids,PAUSE,balance,withdrawn,failed,failure_day,day_key,day_realized,day_target,tlots,tshort,tle,tse,tcomm,active,side,flips,bcnt,scnt,hi,lo,glots,gshort,gle,gse,gcomm,order_count,initial_tick,groups_armed,groups_opened,groups_closed,trades,flip_total,target_days,skipped,cancelled,min_eq,worst_float,max_margin,max_groups,max_positions,max_flips_group,close_flip_hist,shared_i,shared_f)
                        mrows+=len(df); total_rows+=len(df)
        path.unlink(missing_ok=True); provenance.append({'month':month,'url':url,'bytes':nbytes,'sha256':sha,'rows':mrows})
        print('DONE',year,mm,'rows',mrows,'balance',balance.tolist(),'failed',failed.tolist(),flush=True)
        if bool((failed!=0).all()): break

    results=[]
    lb,la=shared_f[4],shared_f[5]
    for c,name in enumerate(CONFIG_NAMES):
        fl=CONTRACT*(lb*tlots[c]-tle[c]+tse[c]-la*tshort[c])-tcomm[c]; eq=balance[c]+fl
        open_groups=int(sum(1 for g in range(G) if active[c,g]!=0 and side[c,g]!=0))
        hist={str(i):int(n) for i,n in enumerate(close_flip_hist[c]) if n}
        results.append({'config':name,'year':year,'failed':bool(failed[c]),'failure_date': '' if failure_day[c]<0 else str(pd.Timestamp('1970-01-01',tz='UTC')+pd.Timedelta(days=int(failure_day[c])))[:10],
          'starting_balance':START_BALANCE,'ending_balance':round(float(balance[c]),3),'withdrawn':round(float(withdrawn[c]),3),'economic_total':round(float(balance[c]+withdrawn[c]),3),'net_economic_profit':round(float(balance[c]+withdrawn[c]-START_BALANCE),3),
          'marked_equity':round(float(eq),3),'floating_pnl_end':round(float(fl),3),'min_equity':round(float(min_eq[c]),3),'worst_floating':round(float(worst_float[c]),3),'max_margin':round(float(max_margin[c]),3),
          'groups_armed':int(groups_armed[c]),'groups_opened':int(groups_opened[c]),'groups_closed_target':int(groups_closed[c]),'open_groups_end':open_groups,'trades':int(trades[c]),'flips':int(flip_total[c]),'target_days':int(target_days[c]),'skipped_session_events':int(skipped[c]),'cancelled_armed':int(cancelled[c]),'max_concurrent_groups':int(max_groups[c]),'max_open_positions':int(max_positions[c]),'max_flips_single_group':int(max_flips_group[c]),'close_flip_counts':hist,
          'rules':{'entry':'2 consecutive completed 1m closes beyond opening H1 boundary; market entry first raw tick after confirmation','initial_lot':0.01,'opposite_boundary_flip_lot':0.02,'pause_new_groups_after_flips':int(PAUSE[c]),'group_target_net_usd':GROUP_TARGET,'daily_target':DAILY_TARGET,'withdraw':WITHDRAW,'commission_roundtrip_per_lot':COMM_RT_PER_LOT,'leverage':LEVERAGE,'no_individual_loss_close':True,'true_tick_liquidation':True}})
    rep={'system':'Raw Tick Validation: CONS2 Boundary Zone Recovery Pause','year':year,'total_rows':total_rows,'results':results,'provenance':provenance}
    with open(out/f'zone_recovery_rawtick_{year}.json','w') as f: json.dump(rep,f,indent=2)
    print('FINAL',json.dumps(rep,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True); a=ap.parse_args(); run(a.year,a.outdir)
