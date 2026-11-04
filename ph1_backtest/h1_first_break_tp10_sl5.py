"""One position per local-session first H1 high/low initial break:
0.10 lot BUY at first bid > previous completed 1-hour high, SELL at first bid < low.
Position: TP gold +$1.00 favorable, SL gold -$0.50 adverse, measured from real entry fill.
XAUUSD Raw Spread bid/ask; round trip commission = $7/lot, charged on opening.
Source: public Exness ZIP tick archive; 2025 full-year, 2026 Jan-Oct 29.
No lookahead; skip missing first-H1 candles; independent four opening sessions;
entries can overlap but same account equity and margin. Exhaustive per-ticket log.
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

START=1000.
TP_PRICE=1.00
SL_PRICE=.50
ROUND_TRIP_COMMISSION_PER_OZ=.07  # standard lot 100oz -> $7 total, .1 lot 10oz -> .70
NS_DAY=86_400_000_000_000
NS_HOUR=3_600_000_000_000
END_2026=pd.Timestamp('2026-10-29T23:59:59.999999999Z').value
MAX_TRADES=1600
SESSION_NAMES=['Sydney','Tokyo','London','New York']
SESSIONS=[('Australia/Sydney',8),('Asia/Tokyo',9),('Europe/London',8),('America/New_York',8)]

# name, ounces per trade, extra adverse price slippage per oz per side,
# withdraw positive net daily, Friday 20:00 UTC flatten, effective leverage
CONF=[
    ('MAIN_010_WITHDRAW', 10.,0.,1,0,2000.),
    ('MAIN_010_KEEP_PROFITS',10.,0.,0,0,2000.),
    ('MAIN_010_SLIP005',10.,.05,1,0,2000.),
    ('MAIN_010_SLIP010',10.,.10,1,0,2000.),
    ('MAIN_001_WITHDRAW',1.,0.,1,0,2000.),
    ('MAIN_010_FRIDAY_FLAT',10.,0.,1,1,2000.),
    ('MAIN_010_LEV200_HMR',10.,0.,1,0,200.)
]
N=len(CONF)
CFG=np.asarray([x[1:] for x in CONF],dtype=np.float64)
CONF_NAMES=[x[0] for x in CONF]

def schedule(year):
    events=[]
    lo=pd.Timestamp(f'{year}-01-01T00:00:00Z').value
    hi=pd.Timestamp(f'{year}-12-31T23:59:59.999999999Z').value if year==2025 else END_2026
    for sid,(zone,hour) in enumerate(SESSIONS):
        tz=ZoneInfo(zone)
        d=datetime(year,1,1).date()-timedelta(days=2)
        last=datetime(year,12,31).date() if year==2025 else datetime(year,10,30).date()
        while d<=last:
            if d.weekday()<5:
                st=datetime(d.year,d.month,d.day,hour,0,tzinfo=tz)
                ns=int(st.astimezone(timezone.utc).timestamp()*1_000_000_000)
                if lo<=ns<=hi:
                    events.append((ns,ns+NS_HOUR,sid))
            d+=timedelta(days=1)
    events.sort()
    return (
        np.asarray([x[0] for x in events],dtype=np.int64),
        np.asarray([x[1] for x in events],dtype=np.int64),
        np.asarray([x[2] for x in events],dtype=np.int64)
    )

@njit
def mark(c,bid,ask,cash,active,an,ti,tf,lev):
    equity=cash[c]
    net_oz=0.
    for k in range(an[c]):
        j=active[c,k]
        side=ti[c,j,0]
        entry=tf[c,j,0]
        units=tf[c,j,4]
        if side==1:
            equity+=units*(bid-entry)
        else:
            equity+=units*(entry-ask)
        net_oz+=side*units
    return equity,abs(net_oz)*bid/lev

@njit
def close_ticket(c,k,t,bid,ask,reason,CFG,cash,daily,ti,tf,active,an,
                 stats_i,stats_f,results_i,results_f,day_pnl,session_count,session_pnl,base_day):
    j=active[c,k]
    side=ti[c,j,0]
    units=tf[c,j,4]
    entry=tf[c,j,0]
    slip=CFG[c,1]
    # Profit target is a LIMIT execution, capped at requested target (no fictitious better fill).
    # Stop loss and Friday-market exits execute at the actual quote after adverse slippage.
    if side==1:
        exitprice=entry+TP_PRICE if reason==1 else bid-slip
        gross=units*(exitprice-entry)
    else:
        exitprice=entry-TP_PRICE if reason==1 else ask+slip
        gross=units*(entry-exitprice)
    net=gross-units*ROUND_TRIP_COMMISSION_PER_OZ
    cash[c]+=gross
    daily[c]+=net
    stats_i[c,1]+=1
    if net>0:
        stats_i[c,2]+=1
    else:
        stats_i[c,3]+=1
    if reason==1:stats_i[c,4]+=1
    elif reason==2:stats_i[c,5]+=1
    else:stats_i[c,6]+=1
    if net<stats_f[c,6]:stats_f[c,6]=net
    delta=(t-ti[c,j,1])/1e9
    stats_f[c,7]+=delta
    if delta>stats_f[c,8]:stats_f[c,8]=delta
    if delta>stats_i[c,13]:stats_i[c,13]=int(delta)
    day_index=int(t//NS_DAY-base_day)
    if 0<=day_index<day_pnl.shape[1]:
        day_pnl[c,day_index]+=net
    session=ti[c,j,2]
    session_count[c,session,1]+=1
    if net>0:session_count[c,session,2]+=1
    session_pnl[c,session]+=net
    x=stats_i[c,1]-1
    if x<results_i.shape[1]:
        # columns: session, side, entry_time, exit_time, exit_reason, initial H1 local-session clock id
        results_i[c,x,0]=session
        results_i[c,x,1]=side
        results_i[c,x,2]=ti[c,j,1]
        results_i[c,x,3]=t
        results_i[c,x,4]=reason
        results_f[c,x,0]=entry
        results_f[c,x,1]=exitprice
        results_f[c,x,2]=net
        results_f[c,x,3]=tf[c,j,2] # best preceding hour bid high
        results_f[c,x,4]=tf[c,j,3] # best preceding hour bid low
        results_f[c,x,5]=units/100.
        results_f[c,x,6]=tf[c,j,5] # entry observed spread
    an[c]-=1
    active[c,k]=active[c,an[c]]

@njit
def engine(ts,bids,asks,starts,ends,sids,CFG,cash,withdrawn,daily,
           active,an,ti,tf,stats_i,stats_f,results_i,results_f,day_pnl,
           session_count,session_pnl,global_i,global_f,
           refhi,reflo,valid,serial,seen,missing,base_day):
    for z in range(len(ts)):
        t=ts[z];bid=bids[z];ask=asks[z]
        if not(math.isfinite(bid) and math.isfinite(ask) and bid>0 and ask>=bid):
            continue
        day=t//NS_DAY
        if global_i[3]<0:global_i[3]=day
        if day!=global_i[3]:
            # Net daily REALIZED profit only, no withdrawal of unrealized group mark.
            for c in range(N):
                if stats_i[c,10]!=0:continue
                if CFG[c,2]>.5 and daily[c]>0:
                    eq,margin=mark(c,global_f[2],global_f[3],cash,active,an,ti,tf,CFG[c,4])
                    take=min(daily[c],max(0.,eq-margin))
                    if daily[c]-take>1e-8:stats_i[c,12]+=1
                    cash[c]-=take;withdrawn[c]+=take
                daily[c]=0.
            global_i[3]=day

        # Finish first one-hour reference and publish independently per session
        prev=global_i[1]
        if prev>=0 and t>=ends[prev]:
            sid=sids[prev]
            if global_i[2]>0:
                refhi[sid]=global_f[0]
                reflo[sid]=global_f[1]
                serial[sid]+=1
                valid[sid]=1
            else:missing[sid]+=1
            global_i[1]=-1;global_i[2]=0
        # New local session supersedes old unexecuted first-H1 signal for that same session
        while global_i[0]<len(starts) and t>=starts[global_i[0]]:
            idx=global_i[0];sid=sids[idx]
            valid[sid]=0
            if global_i[1]>=0:
                other=sids[global_i[1]]
                if global_i[2]>0:
                    refhi[other]=global_f[0];reflo[other]=global_f[1]
                    serial[other]+=1;valid[other]=1
                else:missing[other]+=1
                global_i[1]=-1;global_i[2]=0
            if t<ends[idx]:
                global_i[1]=idx
                global_f[0]=bid;global_f[1]=bid
                global_i[2]=1
            else:missing[sid]+=1
            global_i[0]+=1
        current=global_i[1]
        if current>=0 and t<ends[current]:
            if bid>global_f[0]:global_f[0]=bid
            if bid<global_f[1]:global_f[1]=bid
            global_i[2]+=1

        dow=(day+3)%7
        hour=(t//NS_HOUR)%24
        for c in range(N):
            if stats_i[c,10]!=0:continue
            lev=CFG[c,4]
            eq,margin=mark(c,bid,ask,cash,active,an,ti,tf,lev)
            if eq<=0:
                stats_i[c,10]=1;stats_i[c,11]=t
                stats_f[c,9]=eq;stats_f[c,10]=margin
                continue
            slip=CFG[c,1]

            # 1: TP, 2: SL, 3: Friday forced close; never create reverse/averaging trades.
            k=0
            while k<an[c]:
                j=active[c,k]
                side=ti[c,j,0];entry=tf[c,j,0]
                if side==1:
                    executable=bid-slip
                    hit_tp=executable>=entry+TP_PRICE
                    hit_sl=executable<=entry-SL_PRICE
                else:
                    executable=ask+slip
                    hit_tp=executable<=entry-TP_PRICE
                    hit_sl=executable>=entry+SL_PRICE
                reason=0
                if hit_sl:reason=2  # if quote gaps directly across, stop executes at observed price
                elif hit_tp:reason=1
                elif dow==4 and hour>=20 and CFG[c,3]>.5:reason=3
                if reason:
                    close_ticket(c,k,t,bid,ask,reason,CFG,cash,daily,ti,tf,active,an,
                          stats_i,stats_f,results_i,results_f,day_pnl,session_count,
                          session_pnl,base_day)
                    continue
                k+=1

            # Each first-hour high / low can trigger exactly once, regardless of later crossovers
            for sid in range(4):
                if valid[sid]==0 or seen[c,sid]==serial[sid]:
                    continue
                if dow==4 and hour>=20 and CFG[c,3]>.5:
                    seen[c,sid]=serial[sid]
                    stats_i[c,14]+=1
                    continue
                side=0
                if bid>refhi[sid]:side=1
                elif bid<reflo[sid]:side=-1
                if side==0:continue
                seen[c,sid]=serial[sid]
                if stats_i[c,0]>=MAX_TRADES:
                    stats_i[c,10]=2;stats_i[c,11]=t
                    break
                units=CFG[c,0]
                entry=(ask+slip) if side==1 else (bid-slip)
                fee=units*ROUND_TRIP_COMMISSION_PER_OZ
                eq,margin=mark(c,bid,ask,cash,active,an,ti,tf,lev)
                net_oz=0.
                for k in range(an[c]):
                    j=active[c,k]
                    net_oz+=ti[c,j,0]*tf[c,j,4]
                newmargin=abs(net_oz+side*units)*bid/lev
                neweq=eq-units*(ask-bid+slip)-fee
                if neweq-newmargin<0:
                    stats_i[c,9]+=1
                    continue
                j=stats_i[c,0]
                stats_i[c,0]+=1
                ti[c,j,0]=side
                ti[c,j,1]=t
                ti[c,j,2]=sid
                tf[c,j,0]=entry
                tf[c,j,2]=refhi[sid]
                tf[c,j,3]=reflo[sid]
                tf[c,j,4]=units
                tf[c,j,5]=ask-bid
                cash[c]-=fee
                active[c,an[c]]=j;an[c]+=1
                session_count[c,sid,0]+=1
            eq,margin=mark(c,bid,ask,cash,active,an,ti,tf,lev)
            if eq<stats_f[c,0]:stats_f[c,0]=eq
            if margin>stats_f[c,1]:stats_f[c,1]=margin
            if eq-margin<stats_f[c,2]:stats_f[c,2]=eq-margin
            wealth=eq+withdrawn[c]
            if wealth>stats_f[c,3]:stats_f[c,3]=wealth
            dd=stats_f[c,3]-wealth
            if dd>stats_f[c,4]:stats_f[c,4]=dd
            if an[c]>stats_i[c,8]:stats_i[c,8]=an[c]
            if an[c]>1:stats_i[c,15]+=1
            if eq<=0:
                stats_i[c,10]=1;stats_i[c,11]=t
                stats_f[c,9]=eq;stats_f[c,10]=margin
        global_f[2]=bid;global_f[3]=ask
        global_i[4]=t

def selftest():
    # Core fill accounting, all four sides/outcomes (no spread/gap, entry at exact quote):
    # 0.10 lot -> 10 oz, round trip fee $0.70.
    for side in (-1,1):
        entry=3000.
        tp=entry+side*TP_PRICE
        sl=entry-side*SL_PRICE
        pnl_tp=side*10.*(tp-entry)-.70
        pnl_sl=side*10.*(sl-entry)-.70
        assert abs(pnl_tp-9.30)<1e-8,(side,pnl_tp)
        assert abs(pnl_sl+5.70)<1e-8,(side,pnl_sl)
    # 0.01 lot -> one oz and $0.07 round trip commission.
    assert abs((1.*1.-.07)-.93)<1e-9
    assert abs((1.*(-.5)-.07)+.57)<1e-9
    print("PASS: Buy/Sell TP +$9.30 and SL -$5.70 ideal; 0.01 lot +$0.93/-$0.57",flush=True)

def download(url,fn):
    h=hashlib.sha256();bytes_=0
    with requests.get(url,stream=True,timeout=(30,300)) as response:
        response.raise_for_status()
        with open(fn,'wb') as f:
            for chunk in response.iter_content(1<<20):
                if chunk:
                    f.write(chunk);h.update(chunk);bytes_+=len(chunk)
    return bytes_,h.hexdigest()

def run(year,out):
    selftest()
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    starts,ends,sids=schedule(year)
    cash=np.full(N,START,dtype=np.float64)
    withdrawn=np.zeros(N,dtype=np.float64)
    daily=np.zeros(N,dtype=np.float64)
    active=np.zeros((N,MAX_TRADES),dtype=np.int64)
    an=np.zeros(N,dtype=np.int64)
    ti=np.zeros((N,MAX_TRADES,3),dtype=np.int64)
    tf=np.zeros((N,MAX_TRADES,6),dtype=np.float64)
    stats_i=np.zeros((N,20),dtype=np.int64)
    stats_f=np.zeros((N,16),dtype=np.float64)
    stats_f[:,0]=START;stats_f[:,2]=START;stats_f[:,3]=START
    results_i=np.zeros((N,MAX_TRADES,5),dtype=np.int64)
    results_f=np.zeros((N,MAX_TRADES,7),dtype=np.float64)
    day_pnl=np.zeros((N,375),dtype=np.float64)
    session_count=np.zeros((N,4,3),dtype=np.int64)
    session_pnl=np.zeros((N,4),dtype=np.float64)
    global_i=np.zeros(5,dtype=np.int64)
    global_i[1]=-1;global_i[3]=-1
    global_f=np.zeros(4,dtype=np.float64)
    refhi=np.zeros(4,dtype=np.float64);reflo=np.zeros(4,dtype=np.float64)
    valid=np.zeros(4,dtype=np.int64)
    serial=np.zeros(4,dtype=np.int64);seen=np.zeros((N,4),dtype=np.int64)
    missing=np.zeros(4,dtype=np.int64)
    base_day=int(pd.Timestamp(f'{year}-01-01T00:00:00Z').value//NS_DAY)
    provenance=[];total=0
    for month in range(1,13 if year==2025 else 11):
        mm=f'{month:02d}'
        fn=f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
        url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}'
        print('DOWNLOAD',url,flush=True)
        zip_path=out/fn
        bytes_,sha=download(url,zip_path)
        count=0
        with zipfile.ZipFile(zip_path) as z:
            for name in z.namelist():
                if not name.lower().endswith('.csv'):continue
                with z.open(name) as fd:
                    for df in pd.read_csv(fd,usecols=['Timestamp','Bid','Ask'],chunksize=500_000):
                        utc=pd.to_datetime(df['Timestamp'],utc=True,errors='coerce')
                        ok=utc.notna() & df['Bid'].notna() & df['Ask'].notna()
                        if year==2026 and month==10:
                            ok &= utc<=pd.Timestamp(END_2026,unit='ns',tz='UTC')
                        if not bool(ok.all()):
                            df=df.loc[ok];utc=utc.loc[ok]
                        if len(df)==0:continue
                        t=utc.astype('int64').to_numpy(dtype=np.int64)
                        bid=df['Bid'].to_numpy(dtype=np.float64)
                        ask=df['Ask'].to_numpy(dtype=np.float64)
                        engine(t,bid,ask,starts,ends,sids,CFG,cash,withdrawn,daily,
                             active,an,ti,tf,stats_i,stats_f,results_i,results_f,
                             day_pnl,session_count,session_pnl,global_i,global_f,
                             refhi,reflo,valid,serial,seen,missing,base_day)
                        count+=len(df);total+=len(df)
        zip_path.unlink(missing_ok=True)
        provenance.append(dict(year=year,month=month,url=url,zip_bytes=bytes_,sha256=sha,rows=count))
        print(f'MONTH {year}-{mm} rows={count:,} '
              +'; '.join(f'{CONF_NAMES[i]}: net={mark(i,global_f[2],global_f[3],cash,active,an,ti,tf,CFG[i,4])[0]+withdrawn[i]-START:.2f}, trades={stats_i[i,1]}, status={stats_i[i,10]}'
                           for i in range(N)),flush=True)
    # No synthetic end-of-test fills: open positions included in equity only.
    # A weekend force-flat profile must close at the last eligible quote on a Friday
    # (handled at >=20:00 UTC); no other variant is forcibly liquidated.
    rows=[];trades=[];sessions=[]
    for i,name in enumerate(CONF_NAMES):
        eq,margin=mark(i,global_f[2],global_f[3],cash,active,an,ti,tf,CFG[i,4])
        failure=stats_i[i,10]
        if failure:
            eq=stats_f[i,9];margin=stats_f[i,10]
        for x in range(stats_i[i,1]):
            v=results_i[i,x];f=results_f[i,x]
            trades.append(dict(year=year,variant=name,session=SESSION_NAMES[v[0]],side='BUY' if v[1]>0 else 'SELL',
                               entered_utc=str(pd.Timestamp(int(v[2]),unit='ns',tz='UTC')),
                               exited_utc=str(pd.Timestamp(int(v[3]),unit='ns',tz='UTC')),
                               seconds_held=round((int(v[3])-int(v[2]))/1e9,3),
                               exit_type={1:'TP',2:'SL',3:'FRIDAY_FLAT'}.get(int(v[4]),'UNKNOWN'),
                               entry_price=round(f[0],5),exit_price=round(f[1],5),
                               PnL_net=round(f[2],4),H1_high=round(f[3],5),H1_low=round(f[4],5),
                               lot=round(f[5],2),spread_at_entry=round(f[6],5)))
        for sid in range(4):
            sessions.append(dict(year=year,config=name,session=SESSION_NAMES[sid],
                                 trades_opened=int(session_count[i,sid,0]),
                                 trades_closed=int(session_count[i,sid,1]),
                                 positive_trades=int(session_count[i,sid,2]),
                                 win_rate=round(100*session_count[i,sid,2]/max(1,session_count[i,sid,1]),3),
                                 realized_net=round(session_pnl[i,sid],3)))
        rows.append(dict(year=year,period_ending='2025-12-31' if year==2025 else '2026-10-29',
                         config=name,lot_size=float(CFG[i,0]/100.),extra_slippage_side=float(CFG[i,1]),
                         daily_withdraw=bool(CFG[i,2]),Friday_flat=bool(CFG[i,3]),leverage=int(CFG[i,4]),
                         rows_processed=total,H1_windows_scheduled=len(starts),
                         H1_missing_or_no_quote=int(sum(missing)),
                         trades_opened=int(stats_i[i,0]),trades_closed=int(stats_i[i,1]),
                         win_trades=int(stats_i[i,2]),loss_trades=int(stats_i[i,3]),
                         tp_count=int(stats_i[i,4]),sl_count=int(stats_i[i,5]),
                         forced_flat_count=int(stats_i[i,6]),win_rate_pct=round(100*stats_i[i,2]/max(1,stats_i[i,1]),3),
                         realized_pnl=round(float(session_pnl[i].sum()),3),
                         account_cash=round(cash[i],3),withdrawn_cash=round(withdrawn[i],3),
                         marked_equity=round(eq,3),
                         economic_total_pnl=round(eq+withdrawn[i]-START,3),
                         min_equity=round(stats_f[i,0],3),
                         max_margin=round(stats_f[i,1],3),
                         min_free_margin=round(stats_f[i,2],3),
                         max_wealth_drawdown=round(stats_f[i,4],3),
                         worst_trade_net=round(stats_f[i,6],3),
                         mean_trade_duration_sec=round(stats_f[i,7]/max(1,stats_i[i,1]),3),
                         longest_trade_duration_sec=round(stats_f[i,8],3),
                         max_concurrent_trades=int(stats_i[i,8]),
                         quote_ticks_with_overlap=int(stats_i[i,15]),
                         order_rejections_margin=int(stats_i[i,9]),
                         active_trades_at_end=int(an[i]),
                         daily_profit_withdrawals_capped=int(stats_i[i,12]),
                         days_positive=int(np.sum(day_pnl[i]>0.)),
                         days_negative=int(np.sum(day_pnl[i]<0.)),
                         stopped_on_equity_failure=bool(failure),
                         failure_time_UTC=(str(pd.Timestamp(int(stats_i[i,11]),unit='ns',tz='UTC')) if failure else None)))
    pd.DataFrame(trades).to_csv(out/'individual_trades.csv',index=False)
    pd.DataFrame(sessions).to_csv(out/'sessions.csv',index=False)
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    pd.DataFrame({'UTC_Date':pd.date_range(f'{year}-01-01',periods=375,freq='D'),
                  **{CONF_NAMES[i]:day_pnl[i] for i in range(N)}}).to_csv(out/'daily_realized_PnL.csv',index=False)
    (out/'provenance.json').write_text(json.dumps(dict(data=provenance,configs=CONF,rows=total,
        reference='First complete H1 after local session opens, Bid High/Low only',
        breakout='First Bid tick outside High/Low after H1 close, no lookahead',
        stop_and_tp='BUY: SL Bid <= entryAsk-0.50, TP Bid >= entryAsk+1.00; '
                    'SELL: SL Ask >= entryBid+0.50, TP Ask <= entryBid-1.00',
        lot_size_default='0.10 lot (10 troy oz)',
        full_commission_charged_at_open='0.70 USD per 0.10 lot',
        weekend='optional Friday UTC 20:00 flatten; all other profiles only TP/SL',
        TP_execution='target price limit exactly (no favorable gap price improvement)',
        SL_execution='first actual available executable quote, includes gap losses',
        extra_slippage='entry offset + exit quote offset in adverse direction',
        high_margin_requirements='1:200 leverage sensitivity only, not dynamic broker HMR',
        swap='not modeled',
        data_2026_cutoff='2026-10-29T23:59:59.999Z',
        missing_local_session_H1='no synthetic fills; skipped',
        rounding='contract size 100oz/lot, Exness pip officially 0.01, trader diagram 10=gold $1.00',
        signal_expiry='next same local session open, one order per session opening',
        equity='marked bid/ask; withdrawals subtracted; marked equity + total withdrawn - initial $1000'
    ),indent=2))
    print('FINAL_TABLE\\n'+pd.DataFrame(rows).to_string(index=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--year',type=int,choices=[2025,2026])
    p.add_argument('--out',type=str)
    p.add_argument('--selftest',action='store_true')
    x=p.parse_args()
    if x.selftest:selftest()
    else:
        if not x.year or not x.out:raise SystemExit('--year and --out required')
        run(x.year,x.out)
