import argparse
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

START_BALANCE = 1000.0
DAILY_TARGET = 20.0
DAILY_WITHDRAW = 10.0
LEVERAGE = 2000.0
COMMISSION_PER_LOT_RT = 7.0
LOT_STEP = 0.01
MAX_LOT = 0.20
MAX_HOLD_MIN = 300
SPREAD_HARD_CAP = 0.80
DAY_NS = 86_400_000_000_000
MIN_NS = 60_000_000_000


def download(url, out):
    with requests.get(url, stream=True, timeout=(30, 300)) as r:
        r.raise_for_status()
        with open(out, 'wb') as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)


def aggregate_month_5m(year, month, workdir):
    mm = f'{month:02d}'
    fn = f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
    url = f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}'
    path = workdir / fn
    print('DOWNLOAD', url, flush=True)
    download(url, path)
    parts = []
    with zipfile.ZipFile(path) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if not csvs:
            raise RuntimeError(f'No CSV in {fn}')
        for csv_name in csvs:
            with z.open(csv_name) as fh:
                for df in pd.read_csv(fh, usecols=['Timestamp', 'Bid', 'Ask'], chunksize=500_000):
                    t = pd.to_datetime(df['Timestamp'], utc=True, errors='coerce')
                    good = t.notna() & df['Bid'].notna() & df['Ask'].notna()
                    if year == 2026 and month == 10:
                        good &= (t <= pd.Timestamp('2026-10-29 23:59:59.999999999', tz='UTC'))
                    if not bool(good.all()):
                        df = df.loc[good].copy(); t = t.loc[good]
                    if len(df) == 0:
                        continue
                    bar = t.dt.floor('5min').to_numpy()
                    bid = df['Bid'].to_numpy(float); ask = df['Ask'].to_numpy(float)
                    mid = 0.5 * (bid + ask); spread = ask - bid
                    x = pd.DataFrame({'bar':bar,'bid':bid,'ask':ask,'mid':mid,'spread':spread})
                    g = x.groupby('bar', sort=False).agg(
                        bid_o=('bid','first'), bid_h=('bid','max'), bid_l=('bid','min'), bid_c=('bid','last'),
                        ask_o=('ask','first'), ask_h=('ask','max'), ask_l=('ask','min'), ask_c=('ask','last'),
                        mid_o=('mid','first'), mid_h=('mid','max'), mid_l=('mid','min'), mid_c=('mid','last'),
                        spread_sum=('spread','sum'), ticks=('spread','size'))
                    parts.append(g.reset_index())
    path.unlink(missing_ok=True)
    m = pd.concat(parts, ignore_index=True).sort_values('bar')
    m = m.groupby('bar', sort=True).agg(
        bid_o=('bid_o','first'), bid_h=('bid_h','max'), bid_l=('bid_l','min'), bid_c=('bid_c','last'),
        ask_o=('ask_o','first'), ask_h=('ask_h','max'), ask_l=('ask_l','min'), ask_c=('ask_c','last'),
        mid_o=('mid_o','first'), mid_h=('mid_h','max'), mid_l=('mid_l','min'), mid_c=('mid_c','last'),
        spread_sum=('spread_sum','sum'), ticks=('ticks','sum')).reset_index()
    m['spread_mean'] = m['spread_sum']/m['ticks']
    m = m.drop(columns=['spread_sum']).set_index('bar')
    print(f'AGG {year}-{mm}: 5m bars={len(m):,}', flush=True)
    return m


def load_year(year, workdir):
    if year in (2024, 2025): months = range(1, 13)
    else: months = range(1, 11)
    out = [aggregate_month_5m(year, m, workdir) for m in months]
    df = pd.concat(out).sort_index()
    return df[~df.index.duplicated(keep='last')]


def add_indicators(m5):
    x = m5.copy()
    c=x['mid_c']; h=x['mid_h']; l=x['mid_l']; o=x['mid_o']
    pc=c.shift(1)
    tr=pd.concat([(h-l),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    x['atr']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    x['ema20']=c.ewm(span=20,adjust=False,min_periods=20).mean()
    x['ema50']=c.ewm(span=50,adjust=False,min_periods=50).mean()
    x['ema200']=c.ewm(span=200,adjust=False,min_periods=200).mean()
    rng=(h-l).replace(0,np.nan)
    x['body_ratio']=(c-o).abs()/rng
    x['range_atr']=(h-l)/x['atr']
    diff=c.diff().abs()
    x['eff12']=(c-c.shift(12)).abs()/diff.rolling(12).sum()
    x['roll6_hi']=h.shift(1).rolling(6).max(); x['roll6_lo']=l.shift(1).rolling(6).min()
    x['roll12_hi']=h.shift(1).rolling(12).max(); x['roll12_lo']=l.shift(1).rolling(12).min()
    x['roll24_hi']=h.shift(1).rolling(24).max(); x['roll24_lo']=l.shift(1).rolling(24).min()

    # True tick-weighted daily VWAP proxy using midpoint typical price and tick count.
    typical=(h+l+c)/3.0; day=x.index.normalize(); pv=typical*x['ticks']
    x['tvwap']=pv.groupby(day).cumsum()/x['ticks'].groupby(day).cumsum()

    # Previous UTC-day high/low, available with no look-ahead.
    daily=x.resample('1D').agg(dhi=('mid_h','max'),dlo=('mid_l','min'))
    daily['pdh']=daily['dhi'].shift(1); daily['pdl']=daily['dlo'].shift(1)
    x['pdh']=pd.Series(day,index=x.index).map(daily['pdh'])
    x['pdl']=pd.Series(day,index=x.index).map(daily['pdl'])

    # Asian range 00:00-07:00 UTC, then fixed for rest of day.
    asia=x[(x.index.hour>=0)&(x.index.hour<7)].groupby(x[(x.index.hour>=0)&(x.index.hour<7)].index.normalize()).agg(
        asia_hi=('mid_h','max'),asia_lo=('mid_l','min'))
    x['asia_hi']=pd.Series(day,index=x.index).map(asia['asia_hi'])
    x['asia_lo']=pd.Series(day,index=x.index).map(asia['asia_lo'])

    # Completed H1 regime. Shift availability by one hour to prevent look-ahead.
    h1=x.resample('1h',label='left',closed='left').agg(mid_o=('mid_o','first'),mid_h=('mid_h','max'),mid_l=('mid_l','min'),mid_c=('mid_c','last')).dropna()
    h1c=h1['mid_c']; h1pc=h1c.shift(1)
    h1tr=pd.concat([(h1['mid_h']-h1['mid_l']),(h1['mid_h']-h1pc).abs(),(h1['mid_l']-h1pc).abs()],axis=1).max(axis=1)
    h1['h1_atr']=h1tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    h1['h1_ema20']=h1c.ewm(span=20,adjust=False,min_periods=20).mean()
    h1['h1_ema50']=h1c.ewm(span=50,adjust=False,min_periods=50).mean()
    h1['h1_ema200']=h1c.ewm(span=200,adjust=False,min_periods=200).mean()
    h1['h1_close']=h1c
    h1.index=h1.index+pd.Timedelta(hours=1)
    h1a=h1[['h1_close','h1_atr','h1_ema20','h1_ema50','h1_ema200']].reindex(x.index,method='ffill')
    for col in h1a.columns: x[col]=h1a[col]
    return x


def active_window(ts):
    # Broad NY activity window covering DST/standard-time differences; research shows 12-14 UTC is structurally widest.
    hm=ts.hour*60+ts.minute
    return 12*60 <= hm < 18*60


def entry_allowed_time(ts):
    hm=ts.hour*60+ts.minute
    # Avoid new positions late in the session.
    return 12*60+15 <= hm < 17*60+30


def session_end(ts):
    return ts.normalize()+pd.Timedelta(hours=20)


def signal(ts,direction,atr,anchor,strength,source):
    return {'time':ts+pd.Timedelta(minutes=5),'direction':int(direction),'atr':float(atr),'anchor':float(anchor),'strength':float(strength),'source':source,'session_end':session_end(ts)}


def valid_regime(r,direction):
    if not all(math.isfinite(float(r[k])) for k in ['atr','h1_ema20','h1_ema50','h1_ema200','h1_close','tvwap','eff12']): return False
    if direction>0:
        return r['h1_close']>r['h1_ema50']>r['h1_ema200'] and r['h1_ema20']>=r['h1_ema50'] and r['mid_c']>r['tvwap'] and r['eff12']>=0.20
    return r['h1_close']<r['h1_ema50']<r['h1_ema200'] and r['h1_ema20']<=r['h1_ema50'] and r['mid_c']<r['tvwap'] and r['eff12']>=0.20


def shock_bar(r):
    return (not math.isfinite(float(r['atr']))) or r['atr']<=0 or (r['mid_h']-r['mid_l'])>1.9*r['atr']


def gen_bos_retest(x, lookback=12, family='NY_BOS_RETEST'):
    sig=[]; pending=None; cooldown=None
    hi_col='roll12_hi' if lookback==12 else 'roll24_hi'; lo_col='roll12_lo' if lookback==12 else 'roll24_lo'
    for ts,r in x.iterrows():
        if not active_window(ts): pending=None; continue
        if cooldown is not None and ts<cooldown: continue
        if shock_bar(r):
            if pending is not None: pending=None
            cooldown=ts+pd.Timedelta(minutes=15); continue
        atr=float(r['atr'])
        if pending is not None:
            if ts>pending['expiry']:
                pending=None
            else:
                lvl=pending['level']; d=pending['direction']
                if d>0:
                    touched=r['mid_l']<=lvl+0.30*atr
                    accepted=r['mid_c']>lvl and r['mid_c']>r['mid_o'] and r['body_ratio']>=0.25 and valid_regime(r,1)
                    invalid=r['mid_c']<lvl-0.35*atr
                    if touched and accepted and entry_allowed_time(ts):
                        anchor=min(r['mid_l']-0.15*atr,lvl-0.20*atr)
                        sig.append(signal(ts,1,atr,anchor,r['body_ratio']+r['eff12'],family)); pending=None; cooldown=ts+pd.Timedelta(minutes=20)
                    elif invalid: pending=None
                else:
                    touched=r['mid_h']>=lvl-0.30*atr
                    accepted=r['mid_c']<lvl and r['mid_c']<r['mid_o'] and r['body_ratio']>=0.25 and valid_regime(r,-1)
                    invalid=r['mid_c']>lvl+0.35*atr
                    if touched and accepted and entry_allowed_time(ts):
                        anchor=max(r['mid_h']+0.15*atr,lvl+0.20*atr)
                        sig.append(signal(ts,-1,atr,anchor,r['body_ratio']+r['eff12'],family)); pending=None; cooldown=ts+pd.Timedelta(minutes=20)
                    elif invalid: pending=None
        if pending is None and entry_allowed_time(ts):
            hi=r[hi_col]; lo=r[lo_col]
            if not (math.isfinite(float(hi)) and math.isfinite(float(lo))): continue
            if valid_regime(r,1) and r['mid_c']>hi+0.08*atr and r['mid_c']>r['mid_o'] and r['body_ratio']>=0.45 and r['range_atr']<=1.8:
                pending={'direction':1,'level':float(hi),'expiry':ts+pd.Timedelta(minutes=40)}
            elif valid_regime(r,-1) and r['mid_c']<lo-0.08*atr and r['mid_c']<r['mid_o'] and r['body_ratio']>=0.45 and r['range_atr']<=1.8:
                pending={'direction':-1,'level':float(lo),'expiry':ts+pd.Timedelta(minutes=40)}
    return pd.DataFrame(sig)


def gen_prevday_break_retest(x):
    sig=[]; pending=None; used_day=None; used_long=False; used_short=False
    for ts,r in x.iterrows():
        day=ts.normalize()
        if used_day is None or day!=used_day:
            used_day=day; used_long=False; used_short=False; pending=None
        if not active_window(ts) or shock_bar(r): continue
        atr=float(r['atr'])
        if pending is not None:
            if ts>pending['expiry']: pending=None
            else:
                lvl=pending['level']; d=pending['direction']
                if d>0:
                    if r['mid_l']<=lvl+0.25*atr and r['mid_c']>lvl and r['mid_c']>r['mid_o'] and valid_regime(r,1) and entry_allowed_time(ts):
                        sig.append(signal(ts,1,atr,min(r['mid_l']-0.15*atr,lvl-0.20*atr),r['body_ratio']+0.5,'PDH_RETEST')); used_long=True; pending=None
                    elif r['mid_c']<lvl-0.4*atr: pending=None
                else:
                    if r['mid_h']>=lvl-0.25*atr and r['mid_c']<lvl and r['mid_c']<r['mid_o'] and valid_regime(r,-1) and entry_allowed_time(ts):
                        sig.append(signal(ts,-1,atr,max(r['mid_h']+0.15*atr,lvl+0.20*atr),r['body_ratio']+0.5,'PDL_RETEST')); used_short=True; pending=None
                    elif r['mid_c']>lvl+0.4*atr: pending=None
        if pending is None and entry_allowed_time(ts):
            pdh=r['pdh']; pdl=r['pdl']
            if math.isfinite(float(pdh)) and not used_long and valid_regime(r,1) and r['mid_c']>pdh+0.08*atr and r['body_ratio']>=0.40:
                pending={'direction':1,'level':float(pdh),'expiry':ts+pd.Timedelta(minutes=50)}
            elif math.isfinite(float(pdl)) and not used_short and valid_regime(r,-1) and r['mid_c']<pdl-0.08*atr and r['body_ratio']>=0.40:
                pending={'direction':-1,'level':float(pdl),'expiry':ts+pd.Timedelta(minutes=50)}
    return pd.DataFrame(sig)


def gen_asia_sweep_reversal(x):
    sig=[]; setup=None; day_seen=None; used=False
    for ts,r in x.iterrows():
        day=ts.normalize()
        if day_seen is None or day!=day_seen: day_seen=day; setup=None; used=False
        if used or not entry_allowed_time(ts) or shock_bar(r): continue
        atr=float(r['atr']); ah=r['asia_hi']; al=r['asia_lo']
        if not (math.isfinite(float(ah)) and math.isfinite(float(al))): continue
        if setup is None:
            # Sweep then close back inside. Do not require H1 alignment yet; reversal confirmation comes from BOS.
            if r['mid_h']>ah+0.12*atr and r['mid_c']<ah and r['body_ratio']>=0.30:
                setup={'direction':-1,'expiry':ts+pd.Timedelta(minutes=60),'sweep_extreme':float(r['mid_h'])}
            elif r['mid_l']<al-0.12*atr and r['mid_c']>al and r['body_ratio']>=0.30:
                setup={'direction':1,'expiry':ts+pd.Timedelta(minutes=60),'sweep_extreme':float(r['mid_l'])}
        else:
            if ts>setup['expiry']: setup=None; continue
            d=setup['direction']
            if d>0 and r['mid_c']>r['roll6_hi'] and r['mid_c']>r['tvwap'] and r['mid_c']>r['mid_o'] and r['body_ratio']>=0.40:
                anchor=min(setup['sweep_extreme']-0.10*atr,r['mid_l']-0.15*atr)
                sig.append(signal(ts,1,atr,anchor,r['body_ratio']+0.7,'ASIA_SWEEP_BOS')); used=True; setup=None
            elif d<0 and r['mid_c']<r['roll6_lo'] and r['mid_c']<r['tvwap'] and r['mid_c']<r['mid_o'] and r['body_ratio']>=0.40:
                anchor=max(setup['sweep_extreme']+0.10*atr,r['mid_h']+0.15*atr)
                sig.append(signal(ts,-1,atr,anchor,r['body_ratio']+0.7,'ASIA_SWEEP_BOS')); used=True; setup=None
    return pd.DataFrame(sig)


def gen_vwap_pullback(x):
    sig=[]; last=None
    prev=None
    for ts,r in x.iterrows():
        if not entry_allowed_time(ts) or shock_bar(r) or prev is None:
            prev=r; continue
        if last is not None and ts-last<pd.Timedelta(minutes=30): prev=r; continue
        atr=float(r['atr'])
        if valid_regime(r,1):
            touched=min(prev['mid_l'],r['mid_l'])<=max(r['tvwap'],r['ema20'])+0.15*atr
            reclaim=r['mid_c']>r['ema20'] and r['mid_c']>r['tvwap'] and r['mid_c']>prev['mid_h'] and r['mid_c']>r['mid_o'] and r['body_ratio']>=0.38
            if touched and reclaim:
                anchor=min(prev['mid_l'],r['mid_l'])-0.15*atr
                sig.append(signal(ts,1,atr,anchor,r['body_ratio']+r['eff12'],'VWAP_PULLBACK')); last=ts
        elif valid_regime(r,-1):
            touched=max(prev['mid_h'],r['mid_h'])>=min(r['tvwap'],r['ema20'])-0.15*atr
            reclaim=r['mid_c']<r['ema20'] and r['mid_c']<r['tvwap'] and r['mid_c']<prev['mid_l'] and r['mid_c']<r['mid_o'] and r['body_ratio']>=0.38
            if touched and reclaim:
                anchor=max(prev['mid_h'],r['mid_h'])+0.15*atr
                sig.append(signal(ts,-1,atr,anchor,r['body_ratio']+r['eff12'],'VWAP_PULLBACK')); last=ts
        prev=r
    return pd.DataFrame(sig)


def merge_signals(*dfs):
    arr=[d for d in dfs if d is not None and len(d)]
    if not arr: return pd.DataFrame(columns=['time','direction','atr','anchor','strength','source','session_end'])
    z=pd.concat(arr,ignore_index=True).sort_values(['time','strength'],ascending=[True,False])
    return z.drop_duplicates(['time','direction'],keep='first').reset_index(drop=True)


def make_families(x):
    bos12=gen_bos_retest(x,12,'BOS60_RETEST')
    bos24=gen_bos_retest(x,24,'BOS120_RETEST')
    pdbr=gen_prevday_break_retest(x)
    sweep=gen_asia_sweep_reversal(x)
    vwap=gen_vwap_pullback(x)
    return {
        'BOS60_RETEST':bos12,
        'BOS120_RETEST':bos24,
        'PD_BREAK_RETEST':pdbr,
        'ASIA_SWEEP_BOS':sweep,
        'VWAP_PULLBACK':vwap,
        'STRUCTURE_COMBO':merge_signals(bos12,bos24,pdbr),
        'ALL_ROBUST':merge_signals(bos12,bos24,pdbr,sweep,vwap),
    }


def trade_pnl(direction,entry,exit_price,lots):
    gross=(exit_price-entry)*100.0*lots*direction
    return gross-COMMISSION_PER_LOT_RT*lots


def simulate(x,signals,rr,risk_usd,daily_loss_cap,max_trades_day,start,end):
    d=x[(x.index>=start)&(x.index<=end)]
    if len(d)==0: return None
    sig=signals[(signals['time']>=start)&(signals['time']<=end)].copy() if len(signals) else signals.copy()
    smap={}
    if len(sig):
        for r in sig.to_dict('records'):
            key=int(pd.Timestamp(r['time']).value)
            rec=dict(r); rec['session_end_ns']=int(pd.Timestamp(r['session_end']).value)
            smap.setdefault(key,[]).append(rec)

    idx=d.index.view('int64'); daykey=idx//DAY_NS
    bo=d['bid_o'].to_numpy(float); bh=d['bid_h'].to_numpy(float); bl=d['bid_l'].to_numpy(float); bc=d['bid_c'].to_numpy(float)
    ao=d['ask_o'].to_numpy(float); ah=d['ask_h'].to_numpy(float); al=d['ask_l'].to_numpy(float); ac=d['ask_c'].to_numpy(float)
    spread=d['spread_mean'].to_numpy(float)

    balance=START_BALANCE; withdrawn=0.0; trade=None; curday=-1; dayreal=0.0; daytrades=0; stopped=False
    target_days=0; traded_days=set(); trades=0; wins=0; losses=0; daily=[]; peak=START_BALANCE; maxdd=0.0; failed=False; faildate=''
    max_lot=0.0; max_risk=0.0; source_counts={}

    def close_trade(px):
        nonlocal balance,dayreal,trade,trades,wins,losses
        pnl=trade_pnl(trade['direction'],trade['entry'],px,trade['lots']); balance+=pnl; dayreal+=pnl; trades+=1
        if pnl>0: wins+=1
        else: losses+=1
        trade=None
        return pnl

    for i,tns0 in enumerate(idx):
        tns=int(tns0); dk=int(daykey[i])
        if dk!=curday:
            if curday>=0: daily.append(dayreal)
            curday=dk; dayreal=0.0; daytrades=0; stopped=False

        if trade is not None:
            direction=trade['direction']; exit_px=None; reason=None
            # Conservative ordering: stop first if stop and favorable target occur inside same 5m bar.
            if direction>0:
                if bl[i]<=trade['stop']: exit_px=trade['stop']; reason='SL'
                else:
                    exact=(DAILY_TARGET-dayreal+COMMISSION_PER_LOT_RT*trade['lots'])/(100.0*trade['lots'])+trade['entry']
                    if dayreal<DAILY_TARGET and bh[i]>=exact: exit_px=exact; reason='DAY_TARGET'
                    elif bh[i]>=trade['tp']: exit_px=trade['tp']; reason='TP'
            else:
                if ah[i]>=trade['stop']: exit_px=trade['stop']; reason='SL'
                else:
                    exact=trade['entry']-(DAILY_TARGET-dayreal+COMMISSION_PER_LOT_RT*trade['lots'])/(100.0*trade['lots'])
                    if dayreal<DAILY_TARGET and al[i]<=exact: exit_px=exact; reason='DAY_TARGET'
                    elif al[i]<=trade['tp']: exit_px=trade['tp']; reason='TP'
            if exit_px is None and (tns>=trade['session_end_ns'] or (tns-trade['entry_ns'])/MIN_NS>=MAX_HOLD_MIN):
                exit_px=bc[i] if direction>0 else ac[i]; reason='TIME'
            if exit_px is not None:
                close_trade(exit_px); traded_days.add(dk)
                if dayreal>=DAILY_TARGET-1e-8:
                    withdrawn+=DAILY_WITHDRAW; balance-=DAILY_WITHDRAW; target_days+=1; stopped=True
                elif dayreal<=-daily_loss_cap+1e-8:
                    stopped=True

        equity=balance
        if trade is not None:
            px=bc[i] if trade['direction']>0 else ac[i]
            equity+=trade_pnl(trade['direction'],trade['entry'],px,trade['lots'])
        if equity>peak: peak=equity
        if peak>0: maxdd=max(maxdd,(peak-equity)/peak)
        if equity<=0 or balance<=0:
            failed=True; faildate=str(pd.Timestamp(tns,unit='ns',tz='UTC').date()); break

        if trade is None and not stopped and daytrades<max_trades_day and tns in smap:
            opts=sorted(smap[tns],key=lambda r:r['strength'],reverse=True)
            for r in opts:
                atr=float(r['atr']); direction=int(r['direction'])
                if not math.isfinite(atr) or atr<=0: continue
                if spread[i]>SPREAD_HARD_CAP or spread[i]>0.16*atr: continue
                entry=ao[i] if direction>0 else bo[i]
                if direction>0:
                    rawstop=min(float(r['anchor']),entry-0.85*atr); dist=entry-rawstop
                else:
                    rawstop=max(float(r['anchor']),entry+0.85*atr); dist=rawstop-entry
                if dist<=0 or dist>2.20*atr: continue
                lots_raw=risk_usd/(dist*100.0+COMMISSION_PER_LOT_RT)
                lots=math.floor((lots_raw+1e-12)/LOT_STEP)*LOT_STEP; lots=min(MAX_LOT,round(lots,2))
                if lots<LOT_STEP: continue
                actualrisk=dist*100.0*lots+COMMISSION_PER_LOT_RT*lots
                if actualrisk>risk_usd*1.20: continue
                mid=0.5*(bo[i]+ao[i]); margin=lots*100.0*mid/LEVERAGE
                if equity<=margin*1.25: continue
                tp=entry+rr*dist if direction>0 else entry-rr*dist
                trade={'direction':direction,'entry':entry,'stop':rawstop,'tp':tp,'lots':lots,'entry_ns':tns,'session_end_ns':int(r['session_end_ns']),'source':r['source']}
                daytrades+=1; max_lot=max(max_lot,lots); max_risk=max(max_risk,actualrisk); source_counts[r['source']]=source_counts.get(r['source'],0)+1
                break

    if curday>=0: daily.append(dayreal)
    if trade is not None and len(idx):
        i=len(idx)-1; close_trade(bc[i] if trade['direction']>0 else ac[i])

    arr=np.array(daily,float) if daily else np.array([])
    gp=float(arr[arr>0].sum()) if len(arr) else 0.0; gl=float(-arr[arr<0].sum()) if len(arr) else 0.0
    pf=gp/gl if gl>1e-9 else (999.0 if gp>0 else 0.0)
    market_days=int(np.unique(daykey).size)
    return {
        'failed':failed,'failure_date':faildate,'ending_balance':round(balance,3),'withdrawn':round(withdrawn,3),'economic_total':round(balance+withdrawn,3),'net_economic_profit':round(balance+withdrawn-START_BALANCE,3),
        'market_days':market_days,'target_days':target_days,'target_day_rate_pct':round(100*target_days/market_days,3) if market_days else 0.0,'traded_days':len(traded_days),'trades':trades,'wins':wins,'losses':losses,'win_rate_pct':round(100*wins/trades,3) if trades else 0.0,
        'loss_days':int((arr<0).sum()) if len(arr) else 0,'profit_factor_day':round(pf,3),'max_drawdown_pct':round(100*maxdd,3),'worst_day_pnl':round(float(arr.min()),3) if len(arr) else 0.0,
        'max_lot':round(max_lot,3),'max_planned_trade_risk':round(max_risk,3),'source_entries':source_counts
    }


def score_pair(train,hold):
    if train is None or hold is None or train['failed'] or hold['failed']: return -1e9
    # Require positive economics in both sub-periods for robustness.
    if train['net_economic_profit']<=0 or hold['net_economic_profit']<=0: return -1e6 + train['net_economic_profit']+hold['net_economic_profit']
    min_target=min(train['target_day_rate_pct'],hold['target_day_rate_pct'])
    min_pf=min(train['profit_factor_day'],hold['profit_factor_day'])
    worst_dd=max(train['max_drawdown_pct'],hold['max_drawdown_pct'])
    return 6.0*min_target + 14.0*min(min_pf,2.0) + 0.04*(train['net_economic_profit']+hold['net_economic_profit']) - 1.5*worst_dd


def main(outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    print('=== DEVELOPMENT YEAR 2024 ===',flush=True)
    x24=add_indicators(load_year(2024,work)); fam24=make_families(x24)
    print('SIGNAL COUNTS 2024', {k:len(v) for k,v in fam24.items()}, flush=True)
    train_start=pd.Timestamp('2024-01-01',tz='UTC'); train_end=pd.Timestamp('2024-08-31 23:59:59',tz='UTC')
    hold_start=pd.Timestamp('2024-09-01',tz='UTC'); hold_end=pd.Timestamp('2024-12-31 23:59:59',tz='UTC')
    rows=[]
    for family,sigs in fam24.items():
        for rr in [1.5,1.75,2.0,2.25,2.5]:
            for risk in [10.0,12.5,15.0,17.5]:
                for cap in [20.0,25.0,30.0,35.0]:
                    for mt in [2,3]:
                        tr=simulate(x24,sigs,rr,risk,cap,mt,train_start,train_end)
                        ho=simulate(x24,sigs,rr,risk,cap,mt,hold_start,hold_end)
                        sc=score_pair(tr,ho)
                        rows.append({'family':family,'rr':rr,'risk_usd':risk,'daily_loss_cap':cap,'max_trades_day':mt,'score':sc,
                                     'train_target_rate':tr['target_day_rate_pct'],'train_profit':tr['net_economic_profit'],'train_pf':tr['profit_factor_day'],'train_dd':tr['max_drawdown_pct'],
                                     'hold_target_rate':ho['target_day_rate_pct'],'hold_profit':ho['net_economic_profit'],'hold_pf':ho['profit_factor_day'],'hold_dd':ho['max_drawdown_pct']})
    sweep=pd.DataFrame(rows).sort_values('score',ascending=False); sweep.to_csv(out/'development_sweep_2024.csv',index=False)
    best=sweep.iloc[0].to_dict(); winner={k:best[k] for k in ['family','rr','risk_usd','daily_loss_cap','max_trades_day']}
    print('FROZEN WINNER',winner,flush=True)
    full24=simulate(x24,fam24[winner['family']],winner['rr'],winner['risk_usd'],winner['daily_loss_cap'],int(winner['max_trades_day']),pd.Timestamp('2024-01-01',tz='UTC'),pd.Timestamp('2024-12-31 23:59:59',tz='UTC'))
    del x24,fam24

    print('=== VALIDATION 2025 ===',flush=True)
    x25=add_indicators(load_year(2025,work)); fam25=make_families(x25)
    r25=simulate(x25,fam25[winner['family']],winner['rr'],winner['risk_usd'],winner['daily_loss_cap'],int(winner['max_trades_day']),pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2025-12-31 23:59:59',tz='UTC'))
    counts25={k:len(v) for k,v in fam25.items()}; del x25,fam25

    print('=== VALIDATION 2026 ===',flush=True)
    x26=add_indicators(load_year(2026,work)); fam26=make_families(x26)
    r26=simulate(x26,fam26[winner['family']],winner['rr'],winner['risk_usd'],winner['daily_loss_cap'],int(winner['max_trades_day']),pd.Timestamp('2026-01-01',tz='UTC'),pd.Timestamp('2026-10-29 23:59:59',tz='UTC'))
    counts26={k:len(v) for k,v in fam26.items()}

    report={
      'system_name':'NY Structural-Retest Day Trader',
      'research_basis':'New York active-window structural break/retest; completed-H1 regime; tick-weighted daily VWAP proxy; ATR structural risk; volatility-shock avoidance',
      'development_protocol':'2024 Jan-Aug development + Sep-Dec internal holdout only; frozen before 2025 and 2026 validation',
      'winner':winner,
      'accounting':{'start_balance':START_BALANCE,'daily_target':DAILY_TARGET,'withdraw_on_target':DAILY_WITHDRAW},
      'execution':{'data':'Exness XAUUSD Raw Spread public ticks aggregated to 5-minute bid/ask OHLC','commission_usd_per_lot_round_trip':COMMISSION_PER_LOT_RT,'leverage':LEVERAGE,'same_bar_stop_vs_target':'stop first (conservative)','max_hold_minutes':MAX_HOLD_MIN,'max_lot':MAX_LOT},
      '2024_development_full':full24,'2025_validation':r25,'2026_validation_to_oct29':r26,'signal_counts_2025':counts25,'signal_counts_2026':counts26
    }
    (out/'final_report.json').write_text(json.dumps(report,indent=2))
    pd.DataFrame([{'period':'2024 development',**full24},{'period':'2025 validation',**r25},{'period':'2026 validation',**r26}]).to_csv(out/'period_results.csv',index=False)
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); a=ap.parse_args(); main(a.outdir)
