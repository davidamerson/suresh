import argparse, json, math, hashlib, zipfile, time
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from numba import njit

# One 0.01-lot XAUUSD position is one ounce, and $0.07 is its round-trip commission.
# Trader diagram: +10/-10 is a $1.00 gold-price change, +5/-5 is $0.50.
START_BALANCE = 1000.0
RT_COMM_PER_OUNCE = 0.07
DAY_NS = 86_400_000_000_000
HOUR_NS = 3_600_000_000_000
MAX_GROUPS = 2600
BASE_DAY = lambda year: pd.Timestamp(f"{year}-01-01T00:00:00Z").value // DAY_NS

# (name, max_orders, max_group_ounces, stop_loss_net, max_hours,
#  group_tp, breakout_buffer, max_spread, withdraw_fraction,
#  friday_flat, max_active_groups, margin_reserve)
CONF = [
    ("ORIGINAL_UNBOUNDED", 99, 20000, 999999., 99999., .50, 0., 999., 1., 0, 99, 0.),
    ("FIXED01_TP050_SL2", 1, 1, 2., 2., .50, 0., 999., 1., 1, 99, 25.),
    ("FIXED01_TP100_SL2", 1, 1, 2., 3., 1., 0., 999., 1., 1, 99, 25.),
    ("FIXED01_TP150_SL2", 1, 1, 2., 3., 1.5, 0., 999., 1., 1, 99, 25.),
    ("RECOVERY1_TP050_SL3", 2, 9, 3., 3., .50, 0., 999., 1., 1, 99, 25.),
    ("RECOVERY1_TP100_SL4", 2, 9, 4., 4., 1., 0., 999., 1., 1, 99, 25.),
    ("RECOVERY2_TP050_SL5", 3, 50, 5., 4., .50, 0., 999., 1., 1, 99, 25.),
    ("RECOVERY2_TP100_SL6", 3, 50, 6., 4., 1., 0., 999., 1., 1, 99, 25.),
    ("RECOVERY3_TP050_SL8", 4, 150, 8., 4., .50, 0., 999., 1., 1, 99, 25.),
    ("R1_BUFFER020_SPR020", 2, 9, 3., 3., .50, .20, .20, 1., 1, 99, 25.),
    ("R1_BUFFER020_SPR020_KEEP", 2, 9, 3., 3., .50, .20, .20, 0., 1, 99, 25.),
    ("FIXED01_SPR020_KEEP", 1, 1, 2., 3., .50, 0., .20, 0., 1, 99, 25.)
]
N = len(CONF)
C_INT = np.array([[c[1], c[2], int(c[4]*3600), c[9], c[10]] for c in CONF], dtype=np.int64)
C_FLOAT = np.array([[c[3], c[5], c[6], c[7], c[8], c[11]] for c in CONF], dtype=np.float64)
NAMES = [x[0] for x in CONF]

def schedule(year):
    events = []
    sessions = [('Australia/Sydney',8),('Asia/Tokyo',9),('Europe/London',8),('America/New_York',8)]
    lo = pd.Timestamp(f'{year}-01-01T00:00:00Z').value
    hi = pd.Timestamp(f'{year}-12-31T23:59:59Z').value if year==2025 else pd.Timestamp('2026-10-29T23:59:59Z').value
    for sid,(zone,hour) in enumerate(sessions):
        zone=ZoneInfo(zone)
        day=datetime(year,1,1).date()-timedelta(days=2)
        final=datetime(year,12,31).date() if year==2025 else datetime(year,10,30).date()
        while day<=final:
            if day.weekday()<5:
                local=datetime(day.year,day.month,day.day,hour,0,tzinfo=zone)
                t=int(local.astimezone(timezone.utc).timestamp()*1_000_000_000)
                if lo<=t<=hi:
                    events.append((t,t+HOUR_NS,sid))
            day+=timedelta(days=1)
    events.sort()
    return (np.array([x[0] for x in events],np.int64),
            np.array([x[1] for x in events],np.int64),
            np.array([x[2] for x in events],np.int64))

# group_i: 0 buy units,1 sell units,2 next side,3 trade count,4 open timestamp ns,
# 5 source session id,6 last order timestamp,7 allocated?
# group_f: 0 P0,1 buy cost,2 sell proceeds,3 commissions,4 maximum adverse
# state_i: 0 active_n,1 created,2 closed,3 wins,4 losses,5 reversals,
# 6 margin rejects,7 skipped reversals,8 max_active,9 max_trades_group,
# 10 max_ticket_units,11 max_total_positions,12 no_entry_margin,13 skipped_busy,
# 14 skipped_spread,15 timed_exits,16 stoploss_exits,17 friday_exits,
# 18 account_failure,19 failure_time_ns,20 max_overlap_groups,21 entry_count,
# 22 forced_exit_orders,23 max_open_seconds,24 max_no_new,25 unfillable_reverse
# state_f: 0 cash,1 withdrawn,2 day net realized,3 min equity,4 max margin,
# 5 max dd wealth,6 peak wealth,7 worst group,8 max open exposure ounces,
# 9 minimum free margin,10 longest completed duration sec,11 sum duration sec,
# 12 group profit positive sum,13 group loss negative sum,14 last bid,15 last ask,
# 16 forced withdrawals blocked,17 equity at fail,18 margin at fail
@njit
def mark(c,bid,ask,state_f,group_i,group_f,active,state_i,leverage):
    gross=0.0
    net_units=0
    tradecount=0
    total_units=0
    for j in range(state_i[c,0]):
        g=active[c,j]
        b=group_i[c,g,0]; s=group_i[c,g,1]
        gross+=b*bid-group_f[c,g,1]+group_f[c,g,2]-s*ask
        net_units+=b-s
        tradecount+=group_i[c,g,3]
        total_units+=b+s
    eq=state_f[c,0]+gross
    margin=abs(net_units)*bid/leverage
    return eq,margin,net_units,tradecount,total_units

@njit
def close_g(c,k,t,bid,ask,kind,state_i,state_f,group_i,group_f,active,days_pnl,base_day):
    g=active[c,k]
    b=group_i[c,g,0];s=group_i[c,g,1]
    gross=b*bid-group_f[c,g,1]+group_f[c,g,2]-s*ask
    pnl=gross-group_f[c,g,3]
    state_f[c,0]+=gross
    state_f[c,2]+=pnl
    state_i[c,2]+=1
    if pnl>0.000001:
        state_i[c,3]+=1
        state_f[c,12]+=pnl
    else:
        state_i[c,4]+=1
        state_f[c,13]+=pnl
    if pnl<state_f[c,7]:state_f[c,7]=pnl
    secs=(t-group_i[c,g,4])/1e9
    if secs>state_f[c,10]:state_f[c,10]=secs
    state_f[c,11]+=secs
    if secs>state_i[c,23]:state_i[c,23]=int(secs)
    if kind==2:state_i[c,15]+=1
    if kind==3:state_i[c,16]+=1
    if kind==4:state_i[c,17]+=1
    di=int(t//DAY_NS-base_day)
    if 0<=di<days_pnl.shape[1]:
        days_pnl[c,di]+=pnl
    state_i[c,0]-=1
    active[c,k]=active[c,state_i[c,0]]
    return pnl

@njit
def process(ts,bids,asks,events_start,events_end,events_sid,
            cfg_i,cfg_f,gi,gf,active,si,sf,days_pnl,
            global_i,global_f,signal_dir,signal_valid,signal_tok,signal_hi,signal_lo,
            seen,base_day,leverage,slippage):
    # global_i: 0 next event,1 active H1 event,2 next signal token,3 last UTC day,4 last market hour
    # global_f: 0 H1 high,1 H1 low,2 last bid,3 last ask
    C=len(cfg_i)
    for row in range(len(ts)):
        t=ts[row];bid=bids[row];ask=asks[row]
        if not(math.isfinite(bid) and math.isfinite(ask) and bid>0 and ask>=bid):
            continue
        day=t//DAY_NS
        if global_i[3]<0:global_i[3]=day
        if day!=global_i[3]:
            for c in range(C):
                if si[c,18]!=0:continue
                eq,margin,_,_,_=mark(c,global_f[2],global_f[3],sf,gi,gf,active,si,leverage)
                take=sf[c,2]*cfg_f[c,4]
                if take>0:
                    allowed=max(0.0,eq-margin-cfg_f[c,5])
                    take=min(take,allowed)
                    if take+1e-6<sf[c,2]*cfg_f[c,4]:sf[c,16]+=1.0
                    sf[c,0]-=take
                    sf[c,1]+=take
                sf[c,2]=0.0
            global_i[3]=day
        # H1 first-hour completion / session schedule tracking
        prev=global_i[1]
        if prev>=0 and t>=events_end[prev]:
            sid=events_sid[prev]
            signal_hi[sid]=global_f[0]
            signal_lo[sid]=global_f[1]
            global_i[2]+=1
            signal_tok[sid]=global_i[2]
            signal_valid[sid]=1
            signal_dir[sid]=0
            global_i[1]=-1
        while global_i[0]<len(events_start) and t>=events_start[global_i[0]]:
            ix=global_i[0];sid=events_sid[ix]
            signal_valid[sid]=0
            if global_i[1]>=0:
                osid=events_sid[global_i[1]]
                signal_hi[osid]=global_f[0]
                signal_lo[osid]=global_f[1]
                global_i[2]+=1
                signal_tok[osid]=global_i[2]
                signal_dir[osid]=0
                signal_valid[osid]=1
                global_i[1]=-1
            if t<events_end[ix]:
                global_i[1]=ix
                global_f[0]=bid
                global_f[1]=bid
            global_i[0]+=1
        ix=global_i[1]
        if ix>=0 and t<events_end[ix]:
            if bid>global_f[0]:global_f[0]=bid
            if bid<global_f[1]:global_f[1]=bid
        for sid in range(4):
            if signal_valid[sid]==0:continue
            if signal_dir[sid]==0:
                if bid>signal_hi[sid]:
                    signal_dir[sid]=1
                elif bid<signal_lo[sid]:
                    signal_dir[sid]=-1
        hour=(t//HOUR_NS)%24
        fri=(day+3)%7==4
        for c in range(C):
            if si[c,18]!=0:continue
            eq,margin,net_units,total_pos,total_ounces=mark(c,bid,ask,sf,gi,gf,active,si,leverage)
            if eq<=0:
                si[c,18]=1;si[c,19]=t;sf[c,17]=eq;sf[c,18]=margin
                continue
            # Take profit, time cap, loss cap, weekend-flatten for bounded candidates
            j=0
            while j<si[c,0]:
                g=active[c,j]
                b=gi[c,g,0];s=gi[c,g,1]
                pnl=b*bid-gf[c,g,1]+gf[c,g,2]-s*ask-gf[c,g,3]
                target_hit=(bid>=gf[c,g,0]+1.0 or ask<=gf[c,g,0]-1.0)
                kind=0
                if target_hit and pnl>cfg_f[c,1]+1e-8:
                    kind=1
                elif pnl<=-cfg_f[c,0] and c>0:
                    kind=3
                elif c>0 and t-gi[c,g,4]>=cfg_i[c,2]*1_000_000_000:
                    kind=2
                elif c>0 and cfg_i[c,3]==1 and fri and hour>=20:
                    kind=4
                if kind:
                    close_g(c,j,t,bid,ask,kind,si,sf,gi,gf,active,days_pnl,base_day)
                    continue
                j+=1
            # Reversal additions. One side is armed at any time, virgin +0.5/-0.5 alternation.
            for j in range(si[c,0]):
                g=active[c,j]
                next_side=gi[c,g,2]
                p0=gf[c,g,0]
                if (next_side==1 and ask<p0+0.5) or (next_side==-1 and bid>p0-0.5):
                    continue
                if gi[c,g,3]>=cfg_i[c,0]:
                    continue
                # Potential future fill at +/- $1, with current spread assumed unchanged.
                spread=ask-bid
                if next_side==1:
                    hypothetical_bid=p0+1.0
                    hypothetical_ask=hypothetical_bid+spread
                    openprice=ask+slippage
                    gain_per_unit=hypothetical_bid-openprice-RT_COMM_PER_OUNCE
                else:
                    hypothetical_ask=p0-1.0
                    hypothetical_bid=hypothetical_ask-spread
                    openprice=bid-slippage
                    gain_per_unit=openprice-hypothetical_ask-RT_COMM_PER_OUNCE
                prior=(gi[c,g,0]*hypothetical_bid-gf[c,g,1]
                       +gf[c,g,2]-gi[c,g,1]*hypothetical_ask-gf[c,g,3])
                if gain_per_unit<=0.0000001:
                    si[c,25]+=1
                    continue
                need=int(math.floor((cfg_f[c,1]+0.000001-prior)/gain_per_unit))+1
                if need<1:need=1
                if gi[c,g,0]+gi[c,g,1]+need>cfg_i[c,1]:
                    si[c,7]+=1
                    continue
                # Per-position Exness XAUUSD maximum 200 lots.
                if need>20000:
                    si[c,7]+=1
                    if c==0:
                        si[c,18]=3;si[c,19]=t
                    continue
                newnet=net_units+next_side*need
                required_margin=abs(newnet)*bid/leverage
                would_eq=eq-need*(RT_COMM_PER_OUNCE+spread+slippage)
                if would_eq-required_margin < cfg_f[c,5]:
                    si[c,6]+=1
                    if c==0:
                        si[c,18]=2;si[c,19]=t;sf[c,17]=would_eq;sf[c,18]=required_margin
                    continue
                if next_side==1:
                    gi[c,g,0]+=need
                    gf[c,g,1]+=need*openprice
                else:
                    gi[c,g,1]+=need
                    gf[c,g,2]+=need*openprice
                gf[c,g,3]+=need*RT_COMM_PER_OUNCE
                sf[c,0]-=need*RT_COMM_PER_OUNCE
                gi[c,g,2]=-next_side
                gi[c,g,3]+=1
                gi[c,g,6]=t
                si[c,5]+=1
                si[c,21]+=1
                if need>si[c,10]:si[c,10]=need
                if gi[c,g,3]>si[c,9]:si[c,9]=gi[c,g,3]
                eq,margin,net_units,_,_=mark(c,bid,ask,sf,gi,gf,active,si,leverage)
            # New groups for each session, from first confirmed breakout
            for sid in range(4):
                if signal_valid[sid]==0 or signal_dir[sid]==0:continue
                token=signal_tok[sid]
                if seen[c,sid]==token:continue
                # Avoid accepting very stale first-hour signals after 6h
                # The session event is updated on next corresponding session.
                if (ask-bid)>cfg_f[c,3]:
                    si[c,14]+=1
                    continue
                side=signal_dir[sid]
                # buffered breakout must already be over reference + buffer
                if (side==1 and bid<=signal_hi[sid]+cfg_f[c,2]) or (side==-1 and bid>=signal_lo[sid]-cfg_f[c,2]):
                    continue
                # If account already has many active groups, don't silently borrow arbitrary margin.
                if si[c,0]>=cfg_i[c,4]:
                    si[c,13]+=1
                    seen[c,sid]=token
                    continue
                if si[c,1]>=MAX_GROUPS:
                    seen[c,sid]=token
                    si[c,24]+=1
                    continue
                op=(ask+slippage) if side==1 else (bid-slippage)
                new_net=net_units+side
                reqmargin=abs(new_net)*bid/leverage
                if eq-(ask-bid)-slippage-RT_COMM_PER_OUNCE-reqmargin<cfg_f[c,5]:
                    si[c,12]+=1
                    seen[c,sid]=token
                    continue
                g=si[c,1];si[c,1]+=1
                gf[c,g,0]=op
                gf[c,g,1]=op if side==1 else 0.0
                gf[c,g,2]=op if side==-1 else 0.0
                gf[c,g,3]=RT_COMM_PER_OUNCE
                gi[c,g,0]=1 if side==1 else 0
                gi[c,g,1]=1 if side==-1 else 0
                gi[c,g,2]=-side
                gi[c,g,3]=1
                gi[c,g,4]=t
                gi[c,g,5]=sid
                gi[c,g,6]=t
                active[c,si[c,0]]=g
                si[c,0]+=1
                si[c,21]+=1
                sf[c,0]-=RT_COMM_PER_OUNCE
                seen[c,sid]=token
                eq,margin,net_units,_,_=mark(c,bid,ask,sf,gi,gf,active,si,leverage)
            eq,margin,_,positions,units=mark(c,bid,ask,sf,gi,gf,active,si,leverage)
            if eq<sf[c,3]:sf[c,3]=eq
            if margin>sf[c,4]:sf[c,4]=margin
            if eq+sf[c,1]>sf[c,6]:sf[c,6]=eq+sf[c,1]
            dd=(sf[c,6]-(eq+sf[c,1]))
            if dd>sf[c,5]:sf[c,5]=dd
            free=eq-margin
            if free<sf[c,9]:sf[c,9]=free
            if units>sf[c,8]:sf[c,8]=units
            if si[c,0]>si[c,8]:si[c,8]=si[c,0]
            if positions>si[c,11]:si[c,11]=positions
            if eq<=0:
                si[c,18]=1
                si[c,19]=t
                sf[c,17]=eq
                sf[c,18]=margin
            sf[c,14]=bid;sf[c,15]=ask
        global_f[2]=bid;global_f[3]=ask

def download(url,path):
    h=hashlib.sha256();bytes_=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for chunk in r.iter_content(1024*1024):
                if chunk:
                    f.write(chunk);h.update(chunk);bytes_+=len(chunk)
    return bytes_,h.hexdigest()

def main(year,out,leverage,slippage):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    evs,eve,sid=schedule(year)
    gi=np.zeros((N,MAX_GROUPS,8),dtype=np.int64)
    gf=np.zeros((N,MAX_GROUPS,5),dtype=np.float64)
    active=np.zeros((N,MAX_GROUPS),dtype=np.int64)
    si=np.zeros((N,32),dtype=np.int64)
    sf=np.zeros((N,32),dtype=np.float64)
    sf[:,0]=START_BALANCE;sf[:,3]=START_BALANCE;sf[:,6]=START_BALANCE;sf[:,9]=START_BALANCE
    gp=np.zeros(5,dtype=np.float64);gi0=np.zeros(5,dtype=np.int64)
    gi0[1]=-1;gi0[3]=-1
    sigdir=np.zeros(4,dtype=np.int64)
    sigvalid=np.zeros(4,dtype=np.int64)
    sigtok=np.zeros(4,dtype=np.int64)
    sighi=np.zeros(4,dtype=np.float64)
    siglo=np.zeros(4,dtype=np.float64)
    seen=np.zeros((N,4),dtype=np.int64)
    daypnl=np.zeros((N,375),dtype=np.float64)
    provenance=[]
    tickrows=0
    for month in range(1,13 if year==2025 else 11):
        mm=f'{month:02d}'
        name=f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
        url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{name}'
        print('DOWNLOAD',url,flush=True)
        file=out/name
        nbytes,sha=download(url,file)
        count=0
        with zipfile.ZipFile(file) as z:
            for name in z.namelist():
                if not name.endswith('.csv'):continue
                with z.open(name) as f:
                    for df in pd.read_csv(f,usecols=['Timestamp','Bid','Ask'],chunksize=500_000):
                        t=pd.to_datetime(df['Timestamp'],utc=True,errors='coerce')
                        mask=t.notna() & df['Bid'].notna() & df['Ask'].notna()
                        if year==2026 and month==10:
                            mask=mask & (t<=pd.Timestamp('2026-10-29T23:59:59.999999999Z'))
                        if not bool(mask.all()):
                            df=df.loc[mask];t=t.loc[mask]
                        if len(df)==0:continue
                        ts=t.astype('int64').to_numpy(dtype=np.int64,copy=False)
                        bd=df['Bid'].to_numpy(dtype=np.float64,copy=False)
                        ak=df['Ask'].to_numpy(dtype=np.float64,copy=False)
                        process(ts,bd,ak,evs,eve,sid,C_INT,C_FLOAT,gi,gf,active,si,sf,
                                daypnl,gi0,gp,sigdir,sigvalid,sigtok,sighi,siglo,
                                seen,int(BASE_DAY(year)),leverage,slippage)
                        count+=len(df);tickrows+=len(df)
        file.unlink(missing_ok=True)
        provenance.append(dict(url=url,sha256=sha,zip_bytes=nbytes,rows=count))
        print(f'MONTH {year}-{mm} ticks={count:,} legacy_status={si[0,18]} bounded_completed={si[4,2]} bounded_balance={sf[4,0]:.2f}',flush=True)
    rows=[]
    for c,name in enumerate(NAMES):
        if sf[c,2]>0 and C_FLOAT[c,4]>0 and si[c,18]==0:
            eq,margin,_,_,_=mark(c,sf[c,14],sf[c,15],sf,gi,gf,active,si,leverage)
            take=min(max(0.,sf[c,2]*C_FLOAT[c,4]),max(0.,eq-margin-C_FLOAT[c,5]))
            sf[c,0]-=take;sf[c,1]+=take
        eq,margin,_,_,_=mark(c,sf[c,14],sf[c,15],sf,gi,gf,active,si,leverage)
        dur=sf[c,11]/max(1,si[c,2])/60
        rows.append(dict(config=name,year=year,rows_processed=tickrows,account_balance=round(sf[c,0],3),
                         cash_withdrawn=round(sf[c,1],3),equity_at_cutoff=round(eq,3),
                         economic_total_pnl=round(eq+sf[c,1]-START_BALANCE,3),
                         min_equity=round(sf[c,3],3),max_wealth_drawdown=round(sf[c,5],3),
                         maximum_margin_used=round(sf[c,4],3),min_free_margin=round(sf[c,9],3),
                         groups_opened=int(si[c,1]),groups_closed=int(si[c,2]),
                         winning_groups=int(si[c,3]),nonwinning_groups=int(si[c,4]),
                         open_groups_at_end=int(si[c,0]),win_rate_pct=round(100*si[c,3]/max(1,si[c,2]),2),
                         max_simultaneous_groups=int(si[c,8]),max_simultaneous_positions=int(si[c,11]),
                         maximum_ticket_lot=round(float(si[c,10])/100,2),
                         largest_open_exposure_lot=round(sf[c,8]/100,2),
                         max_orders_per_group=int(si[c,9]),total_orders=int(si[c,21]),
                         mean_closed_group_minutes=round(dur,4),
                         max_closed_group_minutes=round(sf[c,10]/60,4),
                         take_profit_gross=round(sf[c,12],3),
                         loss_exit_gross=round(sf[c,13],3),
                         stop_loss_count=int(si[c,16]),time_exit_count=int(si[c,15]),
                         friday_exit_count=int(si[c,17]),reversal_skipped=int(si[c,7]),
                         insufficient_margin_reversals=int(si[c,6]),
                         unfillable_reversal_ticks=int(si[c,25]),
                         blocked_entries_margin=int(si[c,12]),
                         spread_filter_skips=int(si[c,14]),
                         account_failure=int(si[c,18]),
                         failure_time_utc=str(pd.Timestamp(int(si[c,19]),unit='ns',tz='UTC')) if si[c,19]>0 else None,
                         failure_eq=round(sf[c,17],3),failure_margin=round(sf[c,18],3),
                         daily_positive_days=int(np.sum(daypnl[c]>0.00001)),
                         daily_negative_days=int(np.sum(daypnl[c]<-0.00001)),
                         daily_realized_gross_pnl=round(float(np.sum(daypnl[c])),3),
                         max_daily_loss=round(float(np.min(daypnl[c])),3)))
    pd.DataFrame(rows).to_csv(out/'all_strategy_results.csv',index=False)
    pd.DataFrame({'date':pd.date_range(f'{year}-01-01',periods=daypnl.shape[1],freq='D')[:daypnl.shape[1]],**{NAMES[c]:daypnl[c] for c in range(N)}}).to_csv(out/'daily_pnl.csv',index=False)
    (out/'provenance.json').write_text(json.dumps({'year':year,'rows':tickrows,'archive_files':provenance,'configs':CONF,'execution':{'bid_ask':'real quotes','slippage_USD_per_ounce_per_side':slippage,'commission_round_trip_001_lot':.07,'leverage':leverage,'swap':'NOT modeled','dynamic_HMR':'NOT modeled','daily_withdrawal':'positive day net realized capped by free margin','session_open_local':{'Sydney':'08:00 Australia/Sydney','Tokyo':'09:00 Asia/Tokyo','London':'08:00 Europe/London','New York':'08:00 America/New_York'},'first_H1_bid_high_low':'completed first hour','target_from_P0_USD':1.0,'reversal_half_band_USD':0.5,'max_groups_per_day':'4 session opportunities, not guaranteed executions'}},indent=2))
    print('SUMMARY',pd.DataFrame(rows)[['config','economic_total_pnl','min_equity','groups_closed','win_rate_pct','max_wealth_drawdown','max_simultaneous_groups','account_failure']].to_string(index=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--year',type=int,choices=[2025,2026],required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--leverage',type=float,default=2000)
    p.add_argument('--slippage',type=float,default=0.)
    a=p.parse_args()
    main(a.year,a.out,a.leverage,a.slippage)
