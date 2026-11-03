import argparse, json, math, zipfile
from pathlib import Path
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import requests

START_BALANCE=1000.0
DAILY_TARGET=20.0
WITHDRAW=10.0
LOT=0.01
CONTRACT=100.0
LEVERAGE=2000.0
COMM_RT_PER_LOT=7.0
EPS_PROFIT=0.01

SESSIONS={
    'AUSTRALIAN':('Australia/Sydney',8),
    'ASIAN':('Asia/Tokyo',9),
    'LONDON':('Europe/London',8),
    'NEW_YORK':('America/New_York',8),
}

def download(url,out):
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with open(out,'wb') as f:
            for c in r.iter_content(1024*1024):
                if c: f.write(c)

def aggregate_month_1m(year,month,workdir):
    mm=f'{month:02d}'; fn=f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
    url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}'
    path=workdir/fn; print('DOWNLOAD',url,flush=True); download(url,path)
    parts=[]
    with zipfile.ZipFile(path) as z:
        csvs=[n for n in z.namelist() if n.lower().endswith('.csv')]
        for name in csvs:
            with z.open(name) as fh:
                for df in pd.read_csv(fh,usecols=['Timestamp','Bid','Ask'],chunksize=600_000):
                    t=pd.to_datetime(df.Timestamp,utc=True,errors='coerce')
                    good=t.notna()&df.Bid.notna()&df.Ask.notna()
                    if year==2026 and month==10:
                        good &= t<=pd.Timestamp('2026-10-29 23:59:59.999999999',tz='UTC')
                    if not bool(good.all()): df=df.loc[good].copy(); t=t.loc[good]
                    if len(df)==0: continue
                    x=pd.DataFrame({'bar':t.dt.floor('min').to_numpy(),'bid':df.Bid.to_numpy(float),'ask':df.Ask.to_numpy(float)})
                    g=x.groupby('bar',sort=False).agg(
                        bid_o=('bid','first'),bid_h=('bid','max'),bid_l=('bid','min'),bid_c=('bid','last'),
                        ask_o=('ask','first'),ask_h=('ask','max'),ask_l=('ask','min'),ask_c=('ask','last'))
                    parts.append(g.reset_index())
    path.unlink(missing_ok=True)
    m=pd.concat(parts,ignore_index=True).sort_values('bar')
    m=m.groupby('bar',sort=True).agg(
        bid_o=('bid_o','first'),bid_h=('bid_h','max'),bid_l=('bid_l','min'),bid_c=('bid_c','last'),
        ask_o=('ask_o','first'),ask_h=('ask_h','max'),ask_l=('ask_l','min'),ask_c=('ask_c','last')).reset_index().set_index('bar')
    print(f'AGG {year}-{mm}: 1m bars={len(m):,}',flush=True)
    return m

def load_year(year,workdir):
    months=range(1,13) if year==2025 else range(1,11)
    x=pd.concat([aggregate_month_1m(year,m,workdir) for m in months]).sort_index()
    return x[~x.index.duplicated(keep='last')]

def session_schedule(year,bars):
    first=bars.index.min().to_pydatetime()-timedelta(days=2)
    last=bars.index.max().to_pydatetime()+timedelta(days=2)
    out=[]
    for s,(zname,hour) in SESSIONS.items():
        z=ZoneInfo(zname)
        local_start=first.astimezone(z).date()-timedelta(days=1)
        local_end=last.astimezone(z).date()+timedelta(days=1)
        d=local_start
        while d<=local_end:
            if d.weekday()<5:
                st=datetime.combine(d,time(hour,0),tzinfo=z).astimezone(timezone.utc)
                en=st+timedelta(hours=1)
                stp=pd.Timestamp(st); enp=pd.Timestamp(en)
                sl=bars.loc[(bars.index>=stp)&(bars.index<enp)]
                if len(sl)>=30:
                    out.append({'session':s,'local_date':str(d),'start':stp,'arm':enp,
                                'buy_level':float(sl.ask_h.max()),'sell_level':float(sl.bid_l.min())})
            d+=timedelta(days=1)
    out.sort(key=lambda q:q['arm'])
    return out

def simulate(bars,schedule,variant):
    # variant FIRST_BREAK or BOTH_SIDES
    balance=START_BALANCE; withdrawn=0.0; failed=False; failure_date=''
    groups=[]; arm_idx=0; day=None; day_pnl=0.0; day_target=False; withdrew_today=False
    started=closed=locked=trades=0; target_days=0; max_groups=max_positions=0; ambiguous=0
    min_equity=START_BALANCE; max_margin=0.0
    session_stats={s:{'armed':0,'opened':0,'closed':0,'locked':0} for s in SESSIONS}
    total_long_lots=total_short_lots=0.0
    total_long_entry=total_short_entry=0.0
    open_commission=0.0

    def equity_at(bid,ask):
        floating=CONTRACT*(bid*total_long_lots-total_long_entry+total_short_entry-ask*total_short_lots)-open_commission
        return balance+floating, floating

    def add_pos(g,side,price,bid,ask):
        nonlocal total_long_lots,total_short_lots,total_long_entry,total_short_entry,open_commission,trades,failed,failure_date
        mid=(bid+ask)/2
        eq,_=equity_at(bid,ask)
        margin=(total_long_lots+total_short_lots)*CONTRACT*mid/LEVERAGE
        req=LOT*CONTRACT*mid/LEVERAGE
        if eq-margin < req:
            failed=True; return False
        if side==1:
            g['buy_entry']=price; total_long_lots+=LOT; total_long_entry+=price*LOT
        else:
            g['sell_entry']=price; total_short_lots+=LOT; total_short_entry+=price*LOT
        open_commission+=COMM_RT_PER_LOT*LOT; trades+=1
        return True

    times=bars.index
    a=bars[['bid_o','bid_h','bid_l','bid_c','ask_o','ask_h','ask_l','ask_c']].to_numpy(float)
    for i,ts in enumerate(times):
        if failed: break
        d=ts.date()
        if day!=d:
            day=d; day_pnl=0.0; day_target=False; withdrew_today=False
        bo,bh,bl,bc,ao,ah,al,ac=a[i]

        while arm_idx<len(schedule) and schedule[arm_idx]['arm']<=ts:
            ev=schedule[arm_idx]; arm_idx+=1
            if ev['arm'].date()==d and not day_target:
                g={'session':ev['session'],'buy_level':ev['buy_level'],'sell_level':ev['sell_level'],
                   'buy_entry':None,'sell_entry':None,'opened_minute':None,'locked_counted':False}
                groups.append(g); started+=1; session_stats[ev['session']]['armed']+=1

        # entries
        for g in groups:
            if failed: break
            has_b=g['buy_entry'] is not None; has_s=g['sell_entry'] is not None
            cross_b=ah>g['buy_level']; cross_s=bl<g['sell_level']
            entered=False
            if not has_b and not has_s:
                if cross_b and cross_s:
                    ambiguous+=1
                    if variant=='BOTH_SIDES':
                        if add_pos(g,1,g['buy_level'],bc,ac) and add_pos(g,-1,g['sell_level'],bc,ac):
                            session_stats[g['session']]['opened']+=1; entered=True
                    else:
                        mid_o=(bo+ao)/2
                        db=abs(g['buy_level']-mid_o); ds=abs(mid_o-g['sell_level'])
                        side=1 if db<=ds else -1
                        px=g['buy_level'] if side==1 else g['sell_level']
                        if add_pos(g,side,px,bc,ac): session_stats[g['session']]['opened']+=1; entered=True
                elif cross_b:
                    if add_pos(g,1,g['buy_level'],bc,ac): session_stats[g['session']]['opened']+=1; entered=True
                elif cross_s:
                    if add_pos(g,-1,g['sell_level'],bc,ac): session_stats[g['session']]['opened']+=1; entered=True
                if entered: g['opened_minute']=ts
            elif variant=='BOTH_SIDES':
                if has_b and not has_s and cross_s:
                    if add_pos(g,-1,g['sell_level'],bc,ac): g['opened_minute']=ts; entered=True
                elif has_s and not has_b and cross_b:
                    if add_pos(g,1,g['buy_level'],bc,ac): g['opened_minute']=ts; entered=True

            if g['buy_entry'] is not None and g['sell_entry'] is not None and not g['locked_counted']:
                g['locked_counted']=True; locked+=1; session_stats[g['session']]['locked']+=1

        if failed: break

        # close groups only from a later minute than a new position, conservative ordering.
        keep=[]
        for g in groups:
            has_b=g['buy_entry'] is not None; has_s=g['sell_entry'] is not None
            if not has_b and not has_s:
                keep.append(g); continue
            if g['opened_minute']==ts:
                keep.append(g); continue
            pnl=None
            if has_b and not has_s:
                comm=COMM_RT_PER_LOT*LOT
                trigger=g['buy_entry']+(comm+EPS_PROFIT)/(CONTRACT*LOT)
                if bh>=trigger: pnl=EPS_PROFIT
            elif has_s and not has_b:
                comm=COMM_RT_PER_LOT*LOT
                trigger=g['sell_entry']-(comm+EPS_PROFIT)/(CONTRACT*LOT)
                if al<=trigger: pnl=EPS_PROFIT
            else:
                # Equal-size long+short after high/low breaks is structurally locked below zero.
                pnl=None
            if pnl is None:
                keep.append(g); continue
            # remove positions from account aggregates
            if has_b:
                total_long_lots-=LOT; total_long_entry-=g['buy_entry']*LOT; open_commission-=COMM_RT_PER_LOT*LOT
            if has_s:
                total_short_lots-=LOT; total_short_entry-=g['sell_entry']*LOT; open_commission-=COMM_RT_PER_LOT*LOT
            balance+=pnl; day_pnl+=pnl; closed+=1; session_stats[g['session']]['closed']+=1
            if (not day_target) and day_pnl>=DAILY_TARGET:
                day_target=True; target_days+=1
                if not withdrew_today:
                    balance-=WITHDRAW; withdrawn+=WITHDRAW; withdrew_today=True
        groups=keep

        eq,floatp=equity_at(bc,ac)
        mid=(bc+ac)/2; margin=(total_long_lots+total_short_lots)*CONTRACT*mid/LEVERAGE
        min_equity=min(min_equity,eq); max_margin=max(max_margin,margin)
        max_groups=max(max_groups,len(groups)); max_positions=max(max_positions,int(round((total_long_lots+total_short_lots)/LOT)))
        if eq<=0:
            failed=True; failure_date=str(ts); break

    if not failed: failure_date=''
    last=bars.iloc[-1]
    eq,floatp=equity_at(float(last.bid_c),float(last.ask_c))
    return {
        'variant':variant,'failed':failed,'failure_date':failure_date,'starting_balance':START_BALANCE,
        'ending_balance':round(balance,3),'withdrawn':round(withdrawn,3),'economic_total':round(balance+withdrawn,3),
        'net_economic_profit':round(balance+withdrawn-START_BALANCE,3),'marked_equity':round(eq,3),
        'floating_pnl_end':round(floatp,3),'min_equity':round(min_equity,3),'max_margin':round(max_margin,3),
        'groups_armed':started,'groups_closed_positive':closed,'groups_locked':locked,'open_groups_end':len(groups),
        'trades':trades,'target_days':target_days,'max_concurrent_groups':max_groups,'max_positions':max_positions,
        'ambiguous_both_break_same_minute':ambiguous,'session_stats':session_stats,
        'rules':{'lot':LOT,'group_close_net_profit_usd':EPS_PROFIT,'daily_target':DAILY_TARGET,'withdraw':WITHDRAW,
                 'commission_rt_per_lot':COMM_RT_PER_LOT,'leverage':LEVERAGE,'no_individual_loss_close':True}
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True)
    args=ap.parse_args(); out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    bars=load_year(args.year,work); sched=session_schedule(args.year,bars)
    print('SESSION EVENTS',len(sched),flush=True)
    results=[simulate(bars,sched,'FIRST_BREAK'),simulate(bars,sched,'BOTH_SIDES')]
    report={'system':'Four Session Opening-H1 Independent Groups','year':args.year,
            'session_definition':{'AUSTRALIAN':'08:00 Australia/Sydney','ASIAN':'09:00 Asia/Tokyo','LONDON':'08:00 Europe/London','NEW_YORK':'08:00 America/New_York','DST':'zoneinfo historical'},
            'results':results}
    with open(out/f'report_{args.year}.json','w') as f: json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__': main()
