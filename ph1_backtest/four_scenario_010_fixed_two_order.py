"""Exact 4-scenario two-order XAUUSD session system: 2025/2026 tick audit.

Strictly implements diagrams:
- first complete H1 candle after Sydney/Tokyo/London/NY local session starts
- whichever prior-hour Bid high/low breaks first opens initial 0.10 lot Buy/Sell
- P0 = quote midpoint at first fill; '+' and '-' figure levels are $0.10 per diagram unit
- after +/-$0.50 from P0 add ONE 0.10-lot trade:
    initial BUY: P0+0.50 -> SELL; P0-0.50 -> BUY
    initial SELL: P0-0.50 -> BUY;  P0+0.50 -> SELL
- upper favorable branch: either +/-$1.00 profit end or return to P0 profit end
- adverse branch: return P0 profit end or +/-$1.00 losing end
- no further orders; quote fills Bid/Ask with $0.70 round-trip 0.10-lot commission.
- optional withdrawal, extra adverse slippage and Friday flat sensitivity.
"""
import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from numba import njit

OZ = 10.0                 # 0.10 standard lot * 100 oz
COMMISSION = 0.70         # Exness raw spread $7 round trip per 1.00 lot
LEVERAGE = 2000.0
START_BAL = 1000.0
NS_DAY = 86_400_000_000_000
NS_HR = 3_600_000_000_000
MAX_GROUPS = 1600
MAX_EVENTS = 1600
END_2026 = pd.Timestamp('2026-10-29T23:59:59.999999999Z').value
CONF_NAMES = [
    'EXACT_withdraw_daily',
    'EXACT_keep_profits',
    'EXACT_slip005_withdraw',
    'EXACT_slip010_withdraw',
    'EXACT_Friday_flat_withdraw',
]
# (additional slippage per ounce per side, daily withdraw fraction, Friday force-flat)
CONFIGS = np.array([
    [0.00,1.0,0],
    [0.00,0.0,0],
    [0.05,1.0,0],
    [0.10,1.0,0],
    [0.00,1.0,1],
],dtype=np.float64)

def schedule(year):
    sessions=[
        ('Sydney','Australia/Sydney',8),
        ('Tokyo','Asia/Tokyo',9),
        ('London','Europe/London',8),
        ('New York','America/New_York',8),
    ]
    low=pd.Timestamp(f'{year}-01-01T00:00:00Z').value
    high=pd.Timestamp(f'{year}-12-31T23:59:59Z').value if year==2025 else END_2026
    ev=[]
    for sid,(_,name,hour) in enumerate(sessions):
        d=datetime(year,1,1).date()-timedelta(days=2)
        last=datetime(year,12,31).date() if year==2025 else datetime(year,10,30).date()
        zone=ZoneInfo(name)
        while d<=last:
            if d.weekday()<5:
                at=datetime(d.year,d.month,d.day,hour,0,tzinfo=zone)
                ts=int(at.astimezone(timezone.utc).timestamp()*1e9)
                if low<=ts<=high:
                    ev.append((ts,ts+NS_HR,sid))
            d+=timedelta(days=1)
    ev.sort()
    return (np.asarray([x[0] for x in ev],dtype=np.int64),
            np.asarray([x[1] for x in ev],dtype=np.int64),
            np.asarray([x[2] for x in ev],dtype=np.int64),
            sessions)

@njit
def mark(v,bid,ask,cash,withdrawn,active,active_count,gf,gi,slip):
    # Cash has ALREADY paid commission for each order; here only mark open trades.
    total=cash[v]
    units=0.0
    buys=0.0;sells=0.0
    for k in range(active_count[v]):
        g=active[v,k]
        b=gi[v,g,0];s=gi[v,g,1]
        total+=b*bid-gf[v,g,1]+gf[v,g,2]-s*ask
        units+=b-s
        buys+=b;sells+=s
    margin=abs(units)*bid/LEVERAGE
    return total, margin, buys, sells

@njit
def group_liquidation(v,g,bid,ask,gf,gi,slippage):
    # Group commission (already debited cash) is subtracted only in group statistics.
    gross=(gi[v,g,0]*(bid-slippage)-gf[v,g,1]
           +gf[v,g,2]-gi[v,g,1]*(ask+slippage))
    net=gross-gf[v,g,3]
    return gross,net

@njit
def finish_group(v,k,t,bid,ask,scenario,gf,gi,active,active_count,cash,
                 day_realized,day_pnl,base_day,statsi,statsf,events_i,events_f,slip):
    g=active[v,k]
    gross,net=group_liquidation(v,g,bid,ask,gf,gi,slip)
    cash[v]+=gross
    day_realized[v]+=net
    index=int(t//NS_DAY-base_day)
    if 0<=index<day_pnl.shape[1]:
        day_pnl[v,index]+=net
    sc=scenario-1
    statsi[v,8+sc]+=1
    statsi[v,2]+=1
    if net>0: statsi[v,3]+=1
    else: statsi[v,4]+=1
    dt=(t-gi[v,g,3])/1e9
    statsf[v,7]+=dt
    if dt>statsf[v,8]:statsf[v,8]=dt
    if net<statsf[v,9]:statsf[v,9]=net
    ei=statsi[v,2]-1
    if ei<events_i.shape[1]:
        # event columns: 0 session,1 scenario,2 first side,3 open ns,4 close ns,5 orders
        events_i[v,ei,0]=gi[v,g,4]
        events_i[v,ei,1]=scenario
        events_i[v,ei,2]=gi[v,g,2]
        events_i[v,ei,3]=gi[v,g,3]
        events_i[v,ei,4]=t
        events_i[v,ei,5]=gi[v,g,5]
        # event floats: pnl, p0, second_fill mid, close mid, maximum adverse pnl
        events_f[v,ei,0]=net
        events_f[v,ei,1]=gf[v,g,0]
        events_f[v,ei,2]=gf[v,g,4]
        events_f[v,ei,3]=(bid+ask)*0.5
        events_f[v,ei,4]=gf[v,g,5]
    active_count[v]-=1
    active[v,k]=active[v,active_count[v]]

@njit
def add_second(v,g,side,bid,ask,slippage,cash,gf,gi,active,active_count,
               statsi,statsf,t):
    equity,margin,buyunits,sellunits=mark(v,bid,ask,cash,np.zeros(1),active,active_count,gf,gi,slippage)
    # Check free margin AFTER the real Bid/Ask entry and commission.
    newnet=buyunits-sellunits+side*OZ
    next_margin=abs(newnet)*bid/LEVERAGE
    newequity=equity-OZ*(ask-bid+slippage)-COMMISSION
    if newequity-next_margin < -1e-8:
        statsi[v,6]=2
        statsi[v,7]=t
        statsf[v,10]=newequity
        statsf[v,11]=next_margin
        statsf[v,12]=equity
        statsf[v,13]=margin
        statsf[v,14]=bid
        statsf[v,15]=ask
        return 0
    if side==1:
        gi[v,g,0]+=OZ
        gf[v,g,1]+=OZ*(ask+slippage)
    else:
        gi[v,g,1]+=OZ
        gf[v,g,2]+=OZ*(bid-slippage)
    gf[v,g,3]+=COMMISSION
    cash[v]-=COMMISSION
    gi[v,g,5]=2
    return 1

@njit
def consume(ts,bids,asks,event_start,event_end,event_sid,
            configs,cash,withdrawn,day_realized,active,active_count,gf,gi,
            statsi,statsf,events_i,events_f,day_pnl,
            glob_i,glob_f,ref_hi,ref_lo,pending,serial,seen,
            base_day,missing):
    ncfg=configs.shape[0]
    for z in range(len(ts)):
        t=ts[z];bid=bids[z];ask=asks[z]
        if not(math.isfinite(bid) and math.isfinite(ask) and ask>=bid and bid>0):
            continue
        mid=(bid+ask)*0.5
        day=t//NS_DAY
        if glob_i[3]<0:glob_i[3]=day
        if day!=glob_i[3]:
            prev_dow=(glob_i[3]+3)%7
            for v in range(ncfg):
                if statsi[v,6]!=0:continue
                # Flat Friday at last quote on Friday, not at Sunday's gap.
                if prev_dow==4 and configs[v,2]>0.5:
                    k=0
                    while k<active_count[v]:
                        g=active[v,k]
                        gross,net=group_liquidation(v,g,glob_f[2],glob_f[3],gf,gi,configs[v,0])
                        finish_group(v,k,glob_i[5],glob_f[2],glob_f[3],5,gf,gi,active,active_count,cash,
                            day_realized,day_pnl,base_day,statsi,statsf,events_i,events_f,configs[v,0])
                if configs[v,1]>0:
                    eq,margin,_,_=mark(v,glob_f[2],glob_f[3],cash,withdrawn,active,active_count,gf,gi,configs[v,0])
                    want=max(0.,day_realized[v])*configs[v,1]
                    take=min(want,max(0.,eq-margin))
                    withdrawn[v]+=take
                    cash[v]-=take
                    if want-take>1e-6:statsi[v,15]+=1
                day_realized[v]=0.
            glob_i[3]=day

        old=glob_i[1]
        if old>=0 and t>=event_end[old]:
            sid=event_sid[old]
            if glob_i[2]>0:
                ref_hi[sid]=glob_f[0]
                ref_lo[sid]=glob_f[1]
                serial[sid]+=1
                pending[sid]=1
            else:
                missing[sid]+=1
            glob_i[1]=-1
            glob_i[2]=0
        # On a new session day, expire previous unused signal from that same session.
        while glob_i[0]<len(event_start) and event_start[glob_i[0]]<=t:
            eid=glob_i[0];sid=event_sid[eid]
            pending[sid]=0
            if glob_i[1]>=0:
                prior_sid=event_sid[glob_i[1]]
                if glob_i[2]>0:
                    ref_hi[prior_sid]=glob_f[0];ref_lo[prior_sid]=glob_f[1]
                    serial[prior_sid]+=1;pending[prior_sid]=1
                else:
                    missing[prior_sid]+=1
                glob_i[1]=-1;glob_i[2]=0
            if t<event_end[eid]:
                glob_i[1]=eid
                glob_f[0]=bid;glob_f[1]=bid
                glob_i[2]=1
            else:
                missing[sid]+=1
            glob_i[0]+=1
        cur=glob_i[1]
        if cur>=0 and t<event_end[cur]:
            if bid>glob_f[0]:glob_f[0]=bid
            if bid<glob_f[1]:glob_f[1]=bid
            glob_i[2]+=1

        for v in range(ncfg):
            if statsi[v,6]!=0:continue
            slip=configs[v,0]
            eq,margin,_,_=mark(v,bid,ask,cash,withdrawn,active,active_count,gf,gi,slip)
            if eq<=0.:
                statsi[v,6]=3
                statsi[v,7]=t
                statsf[v,10]=eq;statsf[v,11]=margin
                statsf[v,12]=eq;statsf[v,13]=margin
                statsf[v,14]=bid;statsf[v,15]=ask
                continue
            # First close existing groups if they reached one of four exact endpoints.
            k=0
            while k<active_count[v]:
                g=active[v,k]
                p0=gf[v,g,0]
                first_side=gi[v,g,2]
                stage=gi[v,g,6] # 0 only initial, 1: favorable second order, 2: adverse second order
                if stage==0:
                    is_favor=(first_side==1 and mid>=p0+0.5) or (first_side==-1 and mid<=p0-0.5)
                    is_against=(first_side==1 and mid<=p0-0.5) or (first_side==-1 and mid>=p0+0.5)
                    if is_favor or is_against:
                        newside=(-first_side if is_favor else first_side)
                        success=add_second(v,g,newside,bid,ask,slip,cash,gf,gi,active,active_count,statsi,statsf,t)
                        if success==0:
                            break
                        gi[v,g,6]=1 if is_favor else 2
                        gf[v,g,4]=mid
                        stage=gi[v,g,6]
                sc=0
                if stage==1:
                    if (first_side==1 and mid>=p0+1.) or (first_side==-1 and mid<=p0-1.):
                        sc=1
                    elif (first_side==1 and mid<=p0) or (first_side==-1 and mid>=p0):
                        sc=2
                elif stage==2:
                    if (first_side==1 and mid>=p0) or (first_side==-1 and mid<=p0):
                        sc=3
                    elif (first_side==1 and mid<=p0-1.) or (first_side==-1 and mid>=p0+1.):
                        sc=4
                if sc!=0:
                    finish_group(v,k,t,bid,ask,sc,gf,gi,active,active_count,cash,
                        day_realized,day_pnl,base_day,statsi,statsf,events_i,events_f,slip)
                    continue
                # Track worst group P/L before resolution.
                gross,net=group_liquidation(v,g,bid,ask,gf,gi,0.0)
                if net<gf[v,g,5]:gf[v,g,5]=net
                k+=1

            if statsi[v,6]!=0:
                continue

            # Each session first-hour H/L can trigger once only; no future lookahead.
            for sid in range(4):
                if pending[sid]==0 or seen[v,sid]==serial[sid]:
                    continue
                side=0
                if bid>ref_hi[sid]:side=1
                elif bid<ref_lo[sid]:side=-1
                if side==0:continue
                seen[v,sid]=serial[sid]
                if statsi[v,0]>=MAX_GROUPS:
                    statsi[v,6]=4;statsi[v,7]=t
                    statsf[v,12]=eq;statsf[v,13]=margin
                    statsf[v,14]=bid;statsf[v,15]=ask
                    break
                eq,margin,buyunits,sellunits=mark(v,bid,ask,cash,withdrawn,active,active_count,gf,gi,slip)
                newnet=buyunits-sellunits+side*OZ
                nextmargin=abs(newnet)*bid/LEVERAGE
                neweq=eq-OZ*(ask-bid+slip)-COMMISSION
                if neweq-nextmargin<-1e-8:
                    statsi[v,6]=1;statsi[v,7]=t;statsf[v,10]=neweq;statsf[v,11]=nextmargin
                    statsf[v,12]=eq;statsf[v,13]=margin
                    statsf[v,14]=bid;statsf[v,15]=ask
                    break
                g=statsi[v,0]
                statsi[v,0]+=1;statsi[v,1]+=1
                gi[v,g,0]=OZ if side==1 else 0.
                gi[v,g,1]=OZ if side==-1 else 0.
                gi[v,g,2]=side
                gi[v,g,3]=t
                gi[v,g,4]=sid
                gi[v,g,5]=1
                gi[v,g,6]=0
                gf[v,g,0]=mid
                gf[v,g,1]=OZ*(ask+slip) if side==1 else 0.
                gf[v,g,2]=OZ*(bid-slip) if side==-1 else 0.
                gf[v,g,3]=COMMISSION
                gf[v,g,4]=np.nan
                gf[v,g,5]=0.
                cash[v]-=COMMISSION
                active[v,active_count[v]]=g
                active_count[v]+=1

            eq,margin,_,_=mark(v,bid,ask,cash,withdrawn,active,active_count,gf,gi,slip)
            if eq<statsf[v,0]:statsf[v,0]=eq
            if margin>statsf[v,1]:statsf[v,1]=margin
            wealth=eq+withdrawn[v]
            if wealth>statsf[v,2]:statsf[v,2]=wealth
            dd=statsf[v,2]-wealth
            if dd>statsf[v,3]:statsf[v,3]=dd
            if eq-margin<statsf[v,4]:statsf[v,4]=eq-margin
            if active_count[v]>statsi[v,16]:statsi[v,16]=active_count[v]
            if active_count[v]>1:statsi[v,13]+=1
            numorders=0
            for j in range(active_count[v]):
                g=active[v,j]
                numorders+=gi[v,g,5]
            if numorders>statsi[v,14]:statsi[v,14]=numorders
            if eq<=0:
                statsi[v,6]=3;statsi[v,7]=t;statsf[v,10]=eq;statsf[v,11]=margin
                statsf[v,12]=eq;statsf[v,13]=margin
                statsf[v,14]=bid;statsf[v,15]=ask
        glob_f[2]=bid;glob_f[3]=ask
        glob_i[5]=t

def check_scenarios():
    # Run the SAME Numba simulator on synthetic zero-spread paths, both first sides.
    scenarios=[
        [0.5,1.0],    # 1
        [0.5,0.0],    # 2
        [-0.5,0.0],   # 3
        [-0.5,-1.0],  # 4
    ]
    for first_side in (1,-1):
        for sc,path in enumerate(scenarios,1):
            # initial H1 price=100. First breakout enters at 100 +/-0.2.
            op=100.+first_side*0.2
            arr=[100.,op]+[op+first_side*p for p in path]
            ts=np.array([int(1e9),NS_HR+int(1e9),NS_HR+int(2e9),NS_HR+int(3e9)],np.int64)
            if len(arr)==4:
                ticks=np.array([100.,op,arr[2],arr[3]],np.float64)
            else:raise AssertionError('synthetic data')
            st=np.array([int(1e9)],np.int64);en=np.array([int(1e9)+NS_HR],np.int64)
            sid=np.array([0],np.int64)
            C=1;G=8
            cn=np.array([[0.,0.,0.]],np.float64)
            cash=np.full(C,1000.,np.float64);withd=np.zeros(C);daily=np.zeros(C)
            active=np.zeros((C,G),np.int64);active_n=np.zeros(C,np.int64)
            gf=np.zeros((C,G,6),np.float64);gi=np.zeros((C,G,7),np.int64)
            si=np.zeros((C,18),np.int64);sf=np.zeros((C,12),np.float64);sf[:,0]=1000;sf[:,4]=1000;sf[:,2]=1000
            ei=np.zeros((C,G,6),np.int64);ef=np.zeros((C,G,5),np.float64)
            dp=np.zeros((C,375),np.float64)
            glo_i=np.zeros(6,np.int64);glo_i[1]=-1;glo_i[3]=-1
            glo_f=np.zeros(6,np.float64)
            rh=np.zeros(4);rl=np.zeros(4);p=np.zeros(4,np.int64);serial=np.zeros(4,np.int64);seen=np.zeros((C,4),np.int64);missing=np.zeros(4,np.int64)
            consume(ts,ticks,ticks,st,en,sid,cn,cash,withd,daily,active,active_n,
                    gf,gi,si,sf,ei,ef,dp,glo_i,glo_f,rh,rl,p,serial,seen,0,missing)
            target=3.6 if sc<4 else -16.4
            assert si[0,2]==1 and int(ei[0,0,1])==sc, (first_side,sc,'classification',si[0,:],ei[0,0,:])
            assert abs(ef[0,0,0]-target)<1e-7,(first_side,sc,target,ef[0,0,0])
    print('PASS: all 8 exact first-side/scenario synthetic unit tests = +/-$3.60 / -$16.40')

def fetch(url,path):
    sha=hashlib.sha256()
    count=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for block in r.iter_content(1024*1024):
                if block:
                    f.write(block);sha.update(block);count+=len(block)
    return count,sha.hexdigest()

def run(year,output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    check_scenarios()
    es,ee,esid,snames=schedule(year)
    C=len(CONF_NAMES);G=MAX_GROUPS
    cash=np.full(C,START_BAL,np.float64);withdrawn=np.zeros(C);daily=np.zeros(C)
    active=np.zeros((C,G),np.int64);active_n=np.zeros(C,np.int64)
    gf=np.zeros((C,G,6),np.float64);gi=np.zeros((C,G,7),np.int64)
    statsi=np.zeros((C,18),np.int64)
    statsf=np.zeros((C,20),np.float64);statsf[:,0]=START_BAL;statsf[:,4]=START_BAL;statsf[:,2]=START_BAL
    ev_i=np.zeros((C,MAX_EVENTS,6),np.int64);ev_f=np.zeros((C,MAX_EVENTS,5),np.float64)
    daily_pnl=np.zeros((C,375),np.float64)
    glob_i=np.zeros(6,np.int64);glob_i[1]=-1;glob_i[3]=-1
    glob_f=np.zeros(6,np.float64)
    refhi=np.zeros(4);reflo=np.zeros(4);pending=np.zeros(4,np.int64)
    serial=np.zeros(4,np.int64);seen=np.zeros((C,4),np.int64);missing=np.zeros(4,np.int64)
    provenance=[];total=0
    for month in range(1,13 if year==2025 else 11):
        mm=f'{month:02d}'
        fn=f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
        url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}'
        filepath=output/fn
        print('DOWNLOAD',url,flush=True)
        nbytes,sha=fetch(url,filepath)
        num=0
        with zipfile.ZipFile(filepath) as z:
            for csvname in z.namelist():
                if not csvname.lower().endswith('.csv'):continue
                with z.open(csvname) as f:
                    for df in pd.read_csv(f,usecols=['Timestamp','Bid','Ask'],chunksize=500_000):
                        dt=pd.to_datetime(df['Timestamp'],utc=True,errors='coerce')
                        ok=dt.notna() & df['Bid'].notna() & df['Ask'].notna()
                        if year==2026 and month==10:ok&=(dt<=pd.Timestamp(END_2026,unit='ns',tz='UTC'))
                        if not bool(ok.all()):
                            df=df.loc[ok];dt=dt.loc[ok]
                        if len(df)==0:continue
                        ts=dt.astype('int64').to_numpy(np.int64)
                        bid=df['Bid'].to_numpy(np.float64)
                        ask=df['Ask'].to_numpy(np.float64)
                        consume(ts,bid,ask,es,ee,esid,CONFIGS,cash,withdrawn,daily,active,active_n,
                                gf,gi,statsi,statsf,ev_i,ev_f,daily_pnl,glob_i,glob_f,
                                refhi,reflo,pending,serial,seen,int(pd.Timestamp(f'{year}-01-01T00:00:00Z').value//NS_DAY),missing)
                        num+=len(df);total+=len(df)
        filepath.unlink(missing_ok=True)
        provenance.append(dict(url=url,sha256=sha,bytes=nbytes,rows=num))
        print(f'MONTH {year}-{mm} {num:,} ticks '+', '.join(
            f'{CONF_NAMES[v]}:closed={statsi[v,2]},eq={mark(v,glob_f[2],glob_f[3],cash,withdrawn,active,active_n,gf,gi,CONFIGS[v,0])[0]:.2f},status={statsi[v,6]}' for v in range(C)
        ),flush=True)
    # Complete Friday-flat at very last Friday quote to avoid leaving that variant in the market.
    if (glob_i[3]+3)%7==4:
        v=4
        k=0
        while k<active_n[v]:
            finish_group(v,k,glob_i[5],glob_f[2],glob_f[3],5,gf,gi,active,active_n,cash,
                         daily,daily_pnl,int(pd.Timestamp(f'{year}-01-01T00:00:00Z').value//NS_DAY),
                         statsi,statsf,ev_i,ev_f,CONFIGS[v,0])

    cols=['Sydney','Tokyo','London','New York']
    evrows=[];outrows=[]
    for v,name in enumerate(CONF_NAMES):
        # Every scenario is a terminal two-order group; status 1-4. Scenario 5 is optional Friday flat.
        eq,margin,buy,sell=mark(v,glob_f[2],glob_f[3],cash,withdrawn,active,active_n,gf,gi,CONFIGS[v,0])
        for i in range(int(statsi[v,2])):
            si=ev_i[v,i];sf=ev_f[v,i]
            start=int(si[3]);stop=int(si[4])
            evrows.append(dict(year=year,variant=name,session=cols[si[0]],scenario=int(si[1]),
                initial_side=('BUY' if si[2]==1 else 'SELL'),
                opened_utc=str(pd.Timestamp(start,unit='ns',tz='UTC')),
                closed_utc=str(pd.Timestamp(stop,unit='ns',tz='UTC')),
                duration_seconds=(stop-start)/1e9,
                net_profit=round(float(sf[0]),5),p0=round(float(sf[1]),5),
                second_mid=round(float(sf[2]),5),exit_mid=round(float(sf[3]),5),
                worst_open_group_pnl=round(float(sf[4]),4)))
        failure=int(statsi[v,6])
        tim=str(pd.Timestamp(int(statsi[v,7]),unit='ns',tz='UTC')) if failure else ''
        # A failed strategy is TERMINATED at the first unfillable order. Never carry
        # a stranded position into future months and present phantom mark-to-market gains.
        if failure:
            eq=statsf[v,12]
            margin=statsf[v,13]
        min_eq=min(float(statsf[v,0]),float(eq))
        dd=max(float(statsf[v,3]),float(statsf[v,2]-eq-withdrawn[v]))
        outrows.append(dict(year=year,period_end='2025-12-31' if year==2025 else '2026-10-29',
            config=name,slippage_side=float(CONFIGS[v,0]),withdraw_fraction=float(CONFIGS[v,1]),
            friday_flat=bool(CONFIGS[v,2]),rows_processed=total,
            scheduled_reference_windows=len(es),missing_h1_windows=sum(missing),
            groups_opened=int(statsi[v,1]),groups_closed=int(statsi[v,2]),
            win_groups=int(statsi[v,3]),loss_groups=int(statsi[v,4]),
            scenario1=int(statsi[v,8]),scenario2=int(statsi[v,9]),
            scenario3=int(statsi[v,10]),scenario4=int(statsi[v,11]),
            scenario5_friday_forced=int(statsi[v,12]),
            open_groups_at_end=int(active_n[v]),win_rate_pct=round(100*statsi[v,3]/max(1,statsi[v,2]),4),
            closed_group_pnl=round(sum(float(ev_f[v,i,0]) for i in range(int(statsi[v,2]))),4),
            cash_balance=round(float(cash[v]),4),cash_withdrawn=round(float(withdrawn[v]),4),
            marked_equity=round(float(eq),4),economic_total_pnl=round(float(eq+withdrawn[v]-START_BAL),4),
            minimum_equity=round(min_eq,4),maximum_margin=round(float(statsf[v,1]),4),
            minimum_free_margin=round(float(statsf[v,4]),4),max_drawdown_total_wealth=round(dd,4),
            max_concurrent_groups=int(statsi[v,16]),quote_ticks_with_overlap=int(statsi[v,13]),
            max_simultaneous_orders=int(statsi[v,14]),
            average_closed_duration_minutes=round(statsf[v,7]/max(1,statsi[v,2])/60,3),
            longest_closed_duration_minutes=round(statsf[v,8]/60,3),
            worst_closed_group_pnl=round(statsf[v,9],4),
            margin_block_code=failure,failure_time=tim,
            failure_projected_equity=round(statsf[v,10],4),failure_projected_margin=round(statsf[v,11],4),
            termination_actual_equity=round(float(statsf[v,12]),4) if failure else None,
            termination_actual_margin=round(float(statsf[v,13]),4) if failure else None,
            result_asof_utc=(tim if failure else ('2025-12-31' if year==2025 else '2026-10-29')),
            termination_reason={0:'period_completed',1:'first_order_margin_unavailable',2:'second_order_margin_unavailable',3:'equity_stopout',4:'group_capacity'}.get(failure,'unknown'),
            days_with_partial_withdraw=int(statsi[v,15]),
            days_positive=int(np.sum(daily_pnl[v]>1e-8)),days_negative=int(np.sum(daily_pnl[v]<-1e-8))))
    df=pd.DataFrame(outrows)
    # Avoid reporting scenarios as a win simply because quote price reached diagram boundary.
    pd.DataFrame(evrows).to_csv(output/'trade_group_events.csv',index=False)
    pd.DataFrame(outrows).to_csv(output/'summary.csv',index=False)
    pd.DataFrame({'UTC_date':pd.date_range(f'{year}-01-01',periods=375,freq='D'),**{CONF_NAMES[v]:daily_pnl[v] for v in range(C)}}).to_csv(output/'daily_results.csv',index=False)
    pd.DataFrame(evrows).groupby(['variant','session','scenario'],as_index=False).agg(groups=('net_profit','count'),total_net=('net_profit','sum')).to_csv(output/'by_session_scenario.csv',index=False)
    (output/'provenance.json').write_text(json.dumps(dict(year=year,files=provenance,total_rows=total,
        config_names=CONF_NAMES,configs=CONFIGS.tolist(),
        assumptions={'XAUUSD_contract_oz_per_lot':100,'lot_each_order':0.10,
            'diagram_10_equals_gold_USD_move':1.0,'diagram_5_equals_gold_USD_move':0.5,
            'commission_round_trip_per_0.10_lot':0.70,'reference':'Bid candle H/L, P0=mid at first fill',
            'fills':'BUY at Ask+slippage; SELL at Bid-slippage; closes at opposite executable quote',
            'possible_adverse_slippage':'fixed parameter both entry and exit',
            'first_H1_timezones':[(x[0],x[1],x[2]) for x in snames],
            'start_equity':START_BAL,'leverage':LEVERAGE,
            'hedged_margin':'matched XAUUSD units cancel, unmatched units require margin',
            'withdraw':'at UTC day boundaries, net realized positive day, capped by free margin',
            'signal_expires':'at next local session opening',
            'no_trade_if_H1_missing':True,
            'swaps':'NOT MODELED','high_margin_requirements':'NOT MODELED',
            'fixed_spread_assumption':False,'quote_data':'original Bid/Ask',
            'Friday_flat_only_experimental_sensitivity_variant':True,
            'post_failure_behavior':'stop trading for variant',
        }),indent=2,default=str))
    print('FINAL_SUMMARY\\n'+df.to_string(index=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--year',type=int,choices=[2025,2026])
    p.add_argument('--out',type=str)
    p.add_argument('--selftest',action='store_true')
    x=p.parse_args()
    if x.selftest:check_scenarios()
    else:
        if x.year is None or x.out is None:raise SystemExit('Please set --year and --out')
        run(x.year,x.out)
