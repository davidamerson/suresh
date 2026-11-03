import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import session_open_independent_groups as base

START_BALANCE=1000.0; DAILY_TARGET=20.0; WITHDRAW=10.0
CONTRACT=100.0; LEVERAGE=2000.0; COMM_RT_PER_LOT=7.0; GROUP_TARGET=5.0
LOTS=[0.01,0.01,0.02,0.02]; LEVELS=[0.0,10.0,20.0,30.0]

CONFIGS={
 'WICK_REF':{'mode':'wick','buffer':0.0},
 'CLOSE0':{'mode':'close','buffer':0.0},
 'CLOSE05':{'mode':'close','buffer':0.5},
 'CLOSE10':{'mode':'close','buffer':1.0},
 'CONS2_CLOSE0':{'mode':'consecutive','n':2,'buffer':0.0},
 'CONS3_CLOSE0':{'mode':'consecutive','n':3,'buffer':0.0},
 'M5_CLOSE0':{'mode':'m5','buffer':0.0},
 'M5_CLOSE05':{'mode':'m5','buffer':0.5},
 'CLOSE05_EMA60':{'mode':'close_ema','buffer':0.5,'ema':60,'slope_lookback':30},
 'CLOSE05_EMA240':{'mode':'close_ema','buffer':0.5,'ema':240,'slope_lookback':60},
}

def simulate(bars,schedule,name,cfg,features):
    balance=START_BALANCE; withdrawn=0.0; failed=False; failure_date=''; reason=''
    groups=[]; arm_idx=0; day=None; day_realized=0.0; day_target=False; withdrew_today=False
    armed=opened=closed=trades=recovery=target_days=0; max_groups=max_pos=0; min_eq=START_BALANCE; worst_float=0.0
    depth_counts={}; session_stats={s:{'armed':0,'opened':0,'closed':0} for s in base.SESSIONS}
    tbl=0.0; tsl=0.0; tbe=0.0; tse=0.0; ocomm=0.0

    def equity(bid,ask):
        f=CONTRACT*(bid*tbl-tbe+tse-ask*tsl)-ocomm
        return balance+f,f
    def margin(bid,ask): return (tbl+tsl)*CONTRACT*((bid+ask)/2)/LEVERAGE
    def add(g,lot,px,bid,ask):
        nonlocal tbl,tsl,tbe,tse,ocomm,trades,recovery
        eq,_=equity(bid,ask); req=lot*CONTRACT*((bid+ask)/2)/LEVERAGE
        if eq-margin(bid,ask)<req: return False
        if g['side']==1: tbl+=lot; tbe+=lot*px
        else: tsl+=lot; tse+=lot*px
        ocomm+=COMM_RT_PER_LOT*lot; g['orders'].append((lot,px)); trades+=1
        if len(g['orders'])>1: recovery+=1
        return True
    def remove(g):
        nonlocal tbl,tsl,tbe,tse,ocomm
        lots=sum(x[0] for x in g['orders']); w=sum(x[0]*x[1] for x in g['orders']); c=COMM_RT_PER_LOT*lots
        if g['side']==1: tbl-=lots; tbe-=w
        else: tsl-=lots; tse-=w
        ocomm-=c

    arr=bars[['bid_o','bid_h','bid_l','bid_c','ask_o','ask_h','ask_l','ask_c']].to_numpy(float)
    for i,ts in enumerate(bars.index):
        if failed: break
        d=ts.date()
        if day!=d:
            day=d; day_realized=0.0; day_target=False; withdrew_today=False
        bo,bh,bl,bc,ao,ah,al,ac=arr[i]
        while arm_idx<len(schedule) and schedule[arm_idx]['arm']<=ts:
            ev=schedule[arm_idx]; arm_idx+=1
            if ev['arm'].date()==d and not day_target:
                groups.append({'session':ev['session'],'buy_level':ev['buy_level'],'sell_level':ev['sell_level'],
                  'side':0,'initial':None,'orders':[],'opened_minute':None,'buy_count':0,'sell_count':0})
                armed+=1; session_stats[ev['session']]['armed']+=1

        # cancel never-entered armed setups once target is reached; entered groups carry.
        if day_target: groups=[g for g in groups if g['side']!=0]

        # entry confirmation
        for g in groups:
            if g['side']!=0: continue
            b=cfg.get('buffer',0.0); mode=cfg['mode']; buy=False; sell=False
            if mode=='wick':
                buy=ah>g['buy_level']+b; sell=bl<g['sell_level']-b
            elif mode=='close':
                buy=ac>g['buy_level']+b; sell=bc<g['sell_level']-b
            elif mode=='consecutive':
                buy_now=ac>g['buy_level']+b; sell_now=bc<g['sell_level']-b
                g['buy_count']=g['buy_count']+1 if buy_now else 0; g['sell_count']=g['sell_count']+1 if sell_now else 0
                buy=g['buy_count']>=cfg['n']; sell=g['sell_count']>=cfg['n']
            elif mode=='m5':
                if ts.minute%5==4:
                    buy=ac>g['buy_level']+b; sell=bc<g['sell_level']-b
            elif mode=='close_ema':
                e=features[name]['ema'][i]; ep=features[name]['ema_prev'][i]; mid=(bc+ac)/2
                if np.isfinite(e) and np.isfinite(ep):
                    buy=(ac>g['buy_level']+b and mid>e and e>ep)
                    sell=(bc<g['sell_level']-b and mid<e and e<ep)
            if not (buy or sell): continue
            if buy and sell:
                mid_o=(bo+ao)/2; side=1 if abs(g['buy_level']-mid_o)<=abs(mid_o-g['sell_level']) else -1
            else: side=1 if buy else -1
            # Entry at confirmation close (ask for buy, bid for sell), conservative rather than retroactive boundary fill.
            px=ac if side==1 else bc; g['side']=side; g['initial']=px; g['opened_minute']=ts
            if not add(g,LOTS[0],px,bc,ac): failed=True; failure_date=str(ts); reason='margin_initial'; break
            opened+=1; session_stats[g['session']]['opened']+=1
        if failed: break

        # capped MILD4 recovery from initial confirmation price
        for g in groups:
            if g['side']==0: continue
            while len(g['orders'])<len(LOTS):
                j=len(g['orders']); lev=LEVELS[j]
                if g['side']==1: hit=bl<=g['initial']-lev; px=g['initial']-lev
                else: hit=ah>=g['initial']+lev; px=g['initial']+lev
                if not hit: break
                if not add(g,LOTS[j],px,bc,ac): failed=True; failure_date=str(ts); reason='margin_recovery'; break
            if failed: break
        if failed: break

        keep=[]
        for g in groups:
            if g['side']==0 or not g['orders']: keep.append(g); continue
            lots=sum(x[0] for x in g['orders']); w=sum(x[0]*x[1] for x in g['orders']); c=COMM_RT_PER_LOT*lots
            if g['side']==1: trig=(w+(GROUP_TARGET+c)/CONTRACT)/lots; hit=bh>=trig
            else: trig=(w-(GROUP_TARGET+c)/CONTRACT)/lots; hit=al<=trig
            if not hit or g['opened_minute']==ts: keep.append(g); continue
            remove(g); balance+=GROUP_TARGET; day_realized+=GROUP_TARGET; closed+=1
            depth_counts[str(len(g['orders']))]=depth_counts.get(str(len(g['orders'])),0)+1; session_stats[g['session']]['closed']+=1
            if not day_target and day_realized>=DAILY_TARGET:
                day_target=True; target_days+=1
                if not withdrew_today: balance-=WITHDRAW; withdrawn+=WITHDRAW; withdrew_today=True
        groups=keep
        eq,f=equity(bc,ac); min_eq=min(min_eq,eq); worst_float=min(worst_float,f)
        max_groups=max(max_groups,sum(1 for g in groups if g['side']!=0)); max_pos=max(max_pos,sum(len(g['orders']) for g in groups if g['side']!=0))
        if eq<=0: failed=True; failure_date=str(ts); reason='equity_le_zero'; break

    last=bars.iloc[-1]; eq,f=equity(float(last.bid_c),float(last.ask_c))
    return {'config':name,'failed':failed,'failure_date':failure_date,'failure_reason':reason,
      'ending_balance':round(balance,3),'withdrawn':round(withdrawn,3),'economic_total':round(balance+withdrawn,3),
      'net_economic_profit':round(balance+withdrawn-START_BALANCE,3),'marked_equity':round(eq,3),'min_equity':round(min_eq,3),
      'worst_floating':round(worst_float,3),'groups_armed':armed,'groups_opened':opened,'groups_closed_target':closed,
      'open_groups_end':sum(1 for g in groups if g['side']!=0),'trades':trades,'recovery_trades':recovery,'target_days':target_days,
      'max_concurrent_groups':max_groups,'max_open_positions':max_pos,'close_depth_counts':depth_counts,'session_stats':session_stats,
      'entry_rule':cfg}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True)
    a=ap.parse_args(); out=Path(a.outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    bars=base.load_year(a.year,work); sched=base.session_schedule(a.year,bars)
    mid=(bars.bid_c+bars.ask_c)/2.0; features={}
    for n,c in CONFIGS.items():
        if c['mode']=='close_ema':
            e=mid.ewm(span=c['ema'],adjust=False).mean(); ep=e.shift(c['slope_lookback'])
            features[n]={'ema':e.to_numpy(float),'ema_prev':ep.to_numpy(float)}
        else: features[n]={}
    results=[]
    for n,c in CONFIGS.items():
        print('RUN',n,flush=True); r=simulate(bars,sched,n,c,features); results.append(r); print(json.dumps(r,indent=2),flush=True)
    rep={'system':'Session Entry Quality Sweep + MILD4 Recovery','year':a.year,'results':results}
    with open(out/f'entry_quality_{a.year}.json','w') as f: json.dump(rep,f,indent=2)
    print('FINAL',json.dumps(rep,indent=2),flush=True)
if __name__=='__main__': main()
