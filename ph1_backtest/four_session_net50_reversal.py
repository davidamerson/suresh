import argparse,csv,hashlib,json,math,os,time,zipfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import requests
from numba import njit

START=1000.0
LEVERAGE=2000.0
COMMISSION_PER_UNIT=0.07  # 0.01 lot = 1 troy ounce, $0.07 round trip
TARGET_NET=0.5000001
MAX_GROUPS=2400
SESSION_NAMES=['Sydney','Tokyo','London','New_York']
TIMEZONES=['Australia/Sydney','Asia/Tokyo','Europe/London','America/New_York']
OPEN_HOURS=[8,9,8,8]
END_2026=pd.Timestamp('2026-10-29T23:59:59.999999999Z').value

def make_schedule(year):
    events=[]
    for sid in range(4):
        z=ZoneInfo(TIMEZONES[sid])
        d=datetime(year,1,1).date()-timedelta(days=2)
        last=datetime(year,12,31).date() if year==2025 else datetime(year,10,30).date()
        while d<=last:
            if d.weekday()<5:
                local=datetime(d.year,d.month,d.day,OPEN_HOURS[sid],tzinfo=z)
                a=int(local.astimezone(timezone.utc).timestamp()*1e9)
                b=a+3600_000_000_000
                if a>=pd.Timestamp(f'{year}-01-01T00:00:00Z').value and (year!=2026 or a<=END_2026):
                    events.append((a,b,sid))
            d+=timedelta(days=1)
    events.sort()
    return (np.asarray([x[0] for x in events],dtype=np.int64),
            np.asarray([x[1] for x in events],dtype=np.int64),
            np.asarray([x[2] for x in events],dtype=np.int64))

@njit
def account_mark(balance,groupf,groupi,active,active_n,bid,ask):
    gross=0.0
    netunits=0
    for k in range(active_n):
        g=active[k]
        b=groupi[g,0]
        s=groupi[g,1]
        gross+=b*bid-groupf[g,1]+groupf[g,2]-s*ask
        netunits+=b-s
    eq=balance+gross
    margin=abs(netunits)*bid/LEVERAGE
    return eq,margin,netunits

@njit
def try_order(g,side,units,bid,ask,balance,groupf,groupi,active,active_n):
    # Returns status: 1 success, 2 insufficient free margin, 3 excessive order size
    if units<=0:
        return 3,0.0,0.0,0.0
    if units>20000 or (units>6000 and (0<=0)): # global per-ticket max 200; 60-night gate checked by caller
        if units>20000:
            return 3,0.0,0.0,0.0
    eq,margin,netunits=account_mark(balance,groupf,groupi,active,active_n,bid,ask)
    newnet=netunits+side*units
    neweq=eq-COMMISSION_PER_UNIT*units-(ask-bid)*units
    newmargin=abs(newnet)*bid/LEVERAGE
    if neweq-newmargin < -1e-8:
        return 2,neweq,newmargin,neweq-newmargin
    return 1,neweq,newmargin,neweq-newmargin

@njit
def process_chunk(ts,bids,asks,starts,ends,sids,
                  statei,statef,groupf,groupi,active,
                  pendingvalid,pendinghi,pendinglo):
    # statei indices: 0 next session; 1 collecting schedule id; 2 allocated groups;
    # 3 active count; 4 UTC trading day; 5 opened; 6 closed; 7 blocked; 8 equity stopout;
    # 9 failure_ns; 10 max_active; 11 max_positions; 12 orders; 13 max order units;
    # 14 expired pending; 15 no H1 ticks; 16 partial withdrawals; 17 max simultaneous units;
    # 18 failure reason; 19 failing units; 20 failing group; 21 max group order count;
    # 22 last session id; 23 stale H1 windows; 24 max held seconds
    # statef: 0 balance,1 withdrawn,2 daily realized,3 minimum equity,4 min free margin,
    # 5 max margin,6 total completed net profit,7 max drawdown vs start,8 H1 high,
    # 9 H1 low,10 last bid,11 last ask,12 failure equity,13 failure margin,
    # 14 failure free margin,15 failure price,16 last withdrawal,17 longest sec,
    # 18 sum duration,19 max negative basket,20 missing withdrawal total
    for z in range(len(ts)):
        t=ts[z]
        bid=bids[z]
        ask=asks[z]
        if not(math.isfinite(bid) and math.isfinite(ask) and ask>=bid and bid>0):
            continue
        if statei[8]!=0 or statei[7]!=0:
            return
        day=t//86400000000000
        if statei[4]<0:
            statei[4]=day
        if day!=statei[4]:
            eq0,margin0,net0=account_mark(statef[0],groupf,groupi,active,statei[3],statef[10],statef[11])
            desired=max(0.0,statef[2])
            allowed=max(0.0,eq0-margin0)
            take=min(desired,allowed)
            statef[0]-=take
            statef[1]+=take
            statef[16]=take
            if take+1e-6<desired:
                statei[16]+=1
                statef[20]+=desired-take
            statef[2]=0.0
            statei[4]=day
        # Finish the currently forming first-hour candle on its completion.
        old=statei[1]
        if old>=0 and t>=ends[old]:
            sid=sids[old]
            pendingvalid[sid]=1
            pendinghi[sid]=statef[8]
            pendinglo[sid]=statef[9]
            statei[1]=-1
        # Start new H1 reference windows. A missed historical window is not invented.
        while statei[0]<len(starts) and starts[statei[0]]<=t:
            ix=statei[0]
            sid=sids[ix]
            if pendingvalid[sid]!=0:
                statei[14]+=1
            pendingvalid[sid]=0
            if statei[1]>=0:
                oldsid=sids[statei[1]]
                pendingvalid[oldsid]=1
                pendinghi[oldsid]=statef[8]
                pendinglo[oldsid]=statef[9]
                statei[1]=-1
            if t<ends[ix]:
                statei[1]=ix
                statef[8]=bid
                statef[9]=bid
            else:
                statei[15]+=1
            statei[0]+=1
        ix=statei[1]
        if ix>=0 and t<ends[ix]:
            if bid>statef[8]:
                statef[8]=bid
            if bid<statef[9]:
                statef[9]=bid

        # Mark existing account before opening any fresh session.
        eq,margin,netunits=account_mark(statef[0],groupf,groupi,active,statei[3],bid,ask)
        if eq<=0.0:
            statei[8]=1
            statei[9]=t
            statef[12]=eq
            statef[13]=margin
            statef[14]=eq-margin
            statef[15]=bid
            return

        # Check net-profitable group exits first. Groups never cross-close each other.
        k=0
        while k<statei[3]:
            g=active[k]
            p0=groupf[g,0]
            gross=groupi[g,0]*bid-groupf[g,1]+groupf[g,2]-groupi[g,1]*ask
            net=gross-groupf[g,3]
            # Price has moved >= $1.00 from first executed order (diagram +/-10).
            if (bid>=p0+1.0 or ask<=p0-1.0) and net>TARGET_NET:
                statef[0]+=gross
                statef[2]+=net
                statef[6]+=net
                statei[6]+=1
                dt=(t-groupi[g,5])/1e9
                statef[18]+=dt
                if dt>statef[17]:
                    statef[17]=dt
                active[k]=active[statei[3]-1]
                statei[3]-=1
                groupi[g,3]=0
                continue
            if net<statef[19]:
                statef[19]=net
            k+=1

        # Existing groups: one new reversal trade on each alternating +/-$0.50 crossing.
        for k in range(statei[3]):
            g=active[k]
            p0=groupf[g,0]
            side=groupi[g,2]
            if side==1:
                if ask<p0+0.5:
                    continue
                target_bid=p0+1.0
                target_ask=target_bid+(ask-bid)
                perunit=target_bid-ask-COMMISSION_PER_UNIT
            else:
                if bid>p0-0.5:
                    continue
                target_ask=p0-1.0
                target_bid=target_ask-(ask-bid)
                perunit=bid-target_ask-COMMISSION_PER_UNIT
            # Calculate needed units with executable Bid/Ask and all prior round-trip fees.
            base=(groupi[g,0]*target_bid-groupf[g,1]+groupf[g,2]
                 -groupi[g,1]*target_ask-groupf[g,3])
            if perunit<=1e-10:
                statei[7]=1
                statei[18]=4
                statei[19]=-1
                statei[20]=g
            else:
                units=max(1,int(math.floor((TARGET_NET-base)/perunit))+1)
                while base+units*perunit<=TARGET_NET:
                    units+=1
                # Exness per-position max 60 at 21:00-06:59 UTC, otherwise 200.
                hod=(t//3600000000000)%24
                limit=6000 if (hod>=21 or hod<7) else 20000
                if units>limit:
                    statei[7]=1
                    statei[18]=3
                    statei[19]=units
                    statei[20]=g
                else:
                    status,neweq,newmargin,newfree=try_order(g,side,units,bid,ask,statef[0],groupf,groupi,active,statei[3])
                    if status!=1:
                        statei[7]=1
                        statei[18]=2
                        statei[19]=units
                        statei[20]=g
                    else:
                        if side==1:
                            groupi[g,0]+=units
                            groupf[g,1]+=units*ask
                        else:
                            groupi[g,1]+=units
                            groupf[g,2]+=units*bid
                        groupf[g,3]+=COMMISSION_PER_UNIT*units
                        groupi[g,2]=-side
                        groupi[g,4]+=1
                        statef[0]-=COMMISSION_PER_UNIT*units
                        statei[12]+=1
                        if units>statei[13]:statei[13]=units
                        if groupi[g,4]>statei[21]:statei[21]=groupi[g,4]
            if statei[7]!=0:
                statei[9]=t
                statef[12]=eq
                statef[13]=margin
                statef[14]=eq-margin
                statef[15]=bid
                return

        # Trigger an independent new group on first breakout of each completed H1.
        for sid in range(4):
            if pendingvalid[sid]==0:
                continue
            side=0
            if bid>pendinghi[sid]: side=1
            elif bid<pendinglo[sid]: side=-1
            if side==0:
                continue
            pendingvalid[sid]=0
            if statei[2]>=MAX_GROUPS:
                statei[7]=1
                statei[18]=5
                statei[9]=t
                return
            g=statei[2]
            status,neweq,newmargin,newfree=try_order(g,side,1,bid,ask,statef[0],groupf,groupi,active,statei[3])
            if status!=1:
                statei[7]=1
                statei[18]=2
                statei[19]=1
                statei[20]=g
                statei[9]=t
                statef[12]=neweq
                statef[13]=newmargin
                statef[14]=newfree
                statef[15]=bid
                return
            statei[2]+=1
            statei[5]+=1
            groupf[g,0]=ask if side==1 else bid
            groupf[g,1]=ask if side==1 else 0.0
            groupf[g,2]=bid if side==-1 else 0.0
            groupf[g,3]=COMMISSION_PER_UNIT
            groupi[g,0]=1 if side==1 else 0
            groupi[g,1]=1 if side==-1 else 0
            groupi[g,2]=-side
            groupi[g,3]=1
            groupi[g,4]=1
            groupi[g,5]=t
            groupi[g,6]=sid
            statef[0]-=COMMISSION_PER_UNIT
            active[statei[3]]=g
            statei[3]+=1
            statei[12]+=1

        eq,margin,netunits=account_mark(statef[0],groupf,groupi,active,statei[3],bid,ask)
        if eq<statef[3]:statef[3]=eq
        free=eq-margin
        if free<statef[4]:statef[4]=free
        if margin>statef[5]:statef[5]=margin
        if statei[3]>statei[10]:statei[10]=statei[3]
        positions=0
        totalunits=0
        for k in range(statei[3]):
            g=active[k]
            positions+=groupi[g,4]
            totalunits+=groupi[g,0]+groupi[g,1]
        if positions>statei[11]:statei[11]=positions
        if totalunits>statei[17]:statei[17]=totalunits
        statef[10]=bid;statef[11]=ask

        if eq<=0.0:
            statei[8]=1
            statei[9]=t
            statef[12]=eq
            statef[13]=margin
            statef[14]=free
            statef[15]=bid
            return

def download(url,path):
    h=hashlib.sha256();n=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for b in r.iter_content(1024*1024):
                if b:
                    f.write(b);h.update(b);n+=len(b)
    return n,h.hexdigest()

def run(year,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    starts,ends,sids=make_schedule(year)
    statei=np.zeros(32,dtype=np.int64)
    statei[1]=-1;statei[4]=-1;statei[9]=-1
    statef=np.zeros(32,dtype=np.float64)
    statef[0]=START;statef[3]=START;statef[4]=START
    groupf=np.zeros((MAX_GROUPS,6),dtype=np.float64)
    groupi=np.zeros((MAX_GROUPS,9),dtype=np.int64)
    active=np.zeros(MAX_GROUPS,dtype=np.int64)
    pv=np.zeros(4,dtype=np.int64)
    ph=np.zeros(4,dtype=np.float64)
    pl=np.zeros(4,dtype=np.float64)
    provenance=[]
    total_rows=0
    # On first real chunk JIT-compilation is automatic.
    for month in range(1,13 if year==2025 else 11):
        mm=f'{month:02d}'
        fn=f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
        url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}'
        path=out/fn
        print('DOWNLOAD',url,flush=True)
        nbytes,sha=download(url,path)
        count=0
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.lower().endswith('.csv'):continue
                with z.open(name) as f:
                    for df in pd.read_csv(f,usecols=['Timestamp','Bid','Ask'],chunksize=500000):
                        times=pd.to_datetime(df['Timestamp'],utc=True,errors='coerce')
                        valid=times.notna() & df['Bid'].notna() & df['Ask'].notna()
                        if year==2026 and month==10:
                            valid=valid & (times<=pd.Timestamp(END_2026,unit='ns',tz='UTC'))
                        if not bool(valid.all()):
                            df=df.loc[valid];times=times.loc[valid]
                        if len(df)==0:continue
                        ts=times.astype('int64').to_numpy(np.int64)
                        bid=df['Bid'].to_numpy(np.float64)
                        ask=df['Ask'].to_numpy(np.float64)
                        process_chunk(ts,bid,ask,starts,ends,sids,statei,statef,groupf,groupi,active,pv,ph,pl)
                        count+=len(df);total_rows+=len(df)
                        if statei[7]!=0 or statei[8]!=0:break
                if statei[7]!=0 or statei[8]!=0:break
        provenance.append(dict(month=month,url=url,bytes=nbytes,sha256=sha,read_rows=count))
        path.unlink(missing_ok=True)
        print(f'MONTH {year}-{mm}: rows={count:,}, balance={statef[0]:.2f}, closed={statei[6]}, active={statei[3]}, blocked={statei[7]}, stopout={statei[8]}',flush=True)
        if statei[7]!=0 or statei[8]!=0:break
    lastbid=statef[10]
    lastask=statef[11]
    eq,margin,net=account_mark(statef[0],groupf,groupi,active,statei[3],lastbid,lastask)
    # At end of data: no fictitious liquidation. Mark open positions to market.
    if statei[7]==0 and statei[8]==0 and statef[2]>0:
        desired=statef[2]
        take=min(desired,max(0.,eq-margin))
        statef[0]-=take;statef[1]+=take
        eq-=take
        if take<desired-1e-6:statei[16]+=1
    failing_ns=statei[9]
    failtime=str(pd.Timestamp(int(failing_ns),unit='ns',tz='UTC')) if failing_ns>=0 else None
    reason={0:'none',2:'insufficient_free_margin',3:'exceeds_order_size_limit',4:'unprofitable_reverse_order_at_current_spread',5:'group_capacity_exhausted'}.get(int(statei[18]),'unknown')
    summary=dict(year=year,range_end='2025-12-31' if year==2025 else '2026-10-29',
        status='stopout_equity_zero' if statei[8] else ('strategy_order_blocked' if statei[7] else 'completed_historical_window'),
        first_break_time_utc=failtime,reason=reason,
        requested_recovery_lot=(float(statei[19])/100 if statei[19]>0 else None),
        failure_group_id=int(statei[20]) if statei[7] else None,
        balance=round(float(statef[0]),4),
        withdrawn=round(float(statef[1]),4),
        marked_equity=round(float(eq),4),
        minimum_equity=round(float(statef[3]),4),
        minimum_free_margin=round(float(statef[4]),4),
        max_required_margin=round(float(statef[5]),4),
        first_failure_equity=round(float(statef[12]),4),
        first_failure_margin=round(float(statef[13]),4),
        first_failure_free_margin=round(float(statef[14]),4),
        first_failure_gold_bid=round(float(statef[15]),4),
        groups_opened=int(statei[5]),groups_closed=int(statei[6]),
        active_groups_at_end=int(statei[3]),
        highest_simultaneous_groups=int(statei[10]),
        highest_simultaneous_positions=int(statei[11]),
        highest_simultaneous_lot=float(statei[17])/100,
        largest_single_ticket_lot=float(statei[13])/100,
        max_orders_in_one_group=int(statei[21]),
        total_orders=int(statei[12]),
        expired_session_signals_without_breakout=int(statei[14]),
        missing_h1_reference_windows=int(statei[15]),
        withdrawal_partly_blocked_days=int(statei[16]),
        max_group_duration_hours=round(float(statef[17])/3600,4),
        average_closed_group_duration_hours=round(float(statef[18])/max(1,int(statei[6]))/3600,4),
        lowest_unclosed_group_net=round(float(statef[19]),4),
        data_rows_processed=total_rows,provenance=provenance,
        assumptions={'pip_diagram_10_equals_gold_dollar_move':1.0,'reverse_half_distance':0.5,
            'bid_ask':True,'commission_roundtrip_per_0_01_lot':0.07,
            'profit_target_strictly_above':0.5,'leverage':2000,
            'hedged_margin_zero':True,'slippage_extra':0,'overnight_swap':'NOT_MODELED',
            'margin_HMR':'NOT_MODELED','limit_max_lots_night':60,'limit_max_lots_day':200,
            'session_timezones':dict(zip(SESSION_NAMES,TIMEZONES)),
            'session_hours_local':dict(zip(SESSION_NAMES,OPEN_HOURS)),
            'session_signal_expiry':'replaced at next same-session H1',
            'no_forced_group_close':'open until net+0.50, unless broker rejects/stopout',
            'daily_withdrawal':'UTC day realized positive group P/L, capped by free margin'})
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    pd.DataFrame([dict((k,v) for k,v in summary.items() if k not in ('assumptions','provenance'))]).to_csv(out/'summary.csv',index=False)
    print('FINAL_SUMMARY',json.dumps({k:v for k,v in summary.items() if k not in ('provenance','assumptions')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--year',type=int,required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.year,a.out)
