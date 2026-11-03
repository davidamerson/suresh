import argparse, json
from pathlib import Path
import session_open_independent_groups as base

START_BALANCE=1000.0; DAILY_TARGET=20.0; WITHDRAW=10.0
CONTRACT=100.0; LEVERAGE=2000.0; COMM_RT_PER_LOT=7.0; GROUP_TARGET=5.0
LOTS=[0.01,0.01,0.02,0.02]; LEVELS=[0.0,10.0,20.0,30.0]

CONFIGS={
 'CONS2_REF': {'fixed':None,'ratio':None,'floor':0.0,'pause_depth':None},
 'F100_D3': {'fixed':100.0,'ratio':None,'floor':0.0,'pause_depth':3},
 'F125_D3': {'fixed':125.0,'ratio':None,'floor':0.0,'pause_depth':3},
 'F150_D3': {'fixed':150.0,'ratio':None,'floor':0.0,'pause_depth':3},
 'F200_D3': {'fixed':200.0,'ratio':None,'floor':0.0,'pause_depth':3},
 'F250_D3': {'fixed':250.0,'ratio':None,'floor':0.0,'pause_depth':3},
 'R10_F100_D3': {'fixed':None,'ratio':0.10,'floor':100.0,'pause_depth':3},
 'R125_F100_D3': {'fixed':None,'ratio':0.125,'floor':100.0,'pause_depth':3},
 'R15_F100_D3': {'fixed':None,'ratio':0.15,'floor':100.0,'pause_depth':3},
 'R20_F100_D3': {'fixed':None,'ratio':0.20,'floor':100.0,'pause_depth':3},
 'R15_F125_D3': {'fixed':None,'ratio':0.15,'floor':125.0,'pause_depth':3},
 'R15_F100_D2': {'fixed':None,'ratio':0.15,'floor':100.0,'pause_depth':2},
}

def simulate(bars,schedule,name,cfg):
    balance=START_BALANCE; withdrawn=0.0; failed=False; failure_date=''; failure_reason=''
    groups=[]; arm_idx=0; day=None; day_realized=0.0; day_target=False; withdrew_today=False; cooldown_day=None
    armed=opened=closed=trades=recovery=target_days=stops=skipped=cancelled=0
    stop_loss_total=0.0; max_groups=max_pos=0; min_eq=START_BALANCE; worst_float=0.0; max_margin=0.0
    close_depth={}; stop_depth={}; tbl=tsl=tbe=tse=ocomm=0.0

    def equity(bid,ask):
        f=CONTRACT*(bid*tbl-tbe+tse-ask*tsl)-ocomm
        return balance+f,f
    def margin(bid,ask): return (tbl+tsl)*CONTRACT*((bid+ask)/2.0)/LEVERAGE
    def add(g,lot,px,bid,ask):
        nonlocal tbl,tsl,tbe,tse,ocomm,trades,recovery
        eq,_=equity(bid,ask); req=lot*CONTRACT*((bid+ask)/2.0)/LEVERAGE
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
    def danger():
        pd=cfg['pause_depth']; return bool(pd and any(g['side']!=0 and len(g['orders'])>=pd for g in groups))
    def cap_now():
        if cfg['fixed'] is not None: return cfg['fixed']
        if cfg['ratio'] is not None: return max(cfg['floor'], cfg['ratio']*max(balance,1.0))
        return None

    arr=bars[['bid_o','bid_h','bid_l','bid_c','ask_o','ask_h','ask_l','ask_c']].to_numpy(float)
    for i,ts in enumerate(bars.index):
        if failed: break
        d=ts.date()
        if day!=d:
            day=d; day_realized=0.0; day_target=False; withdrew_today=False; cooldown_day=None
        bo,bh,bl,bc,ao,ah,al,ac=arr[i]

        # danger/cooldown cancels only unentered setups
        if danger() or cooldown_day==d:
            old=len(groups); groups=[g for g in groups if g['side']!=0]; cancelled+=old-len(groups)

        while arm_idx<len(schedule) and schedule[arm_idx]['arm']<=ts:
            ev=schedule[arm_idx]; arm_idx+=1
            if ev['arm'].date()!=d: continue
            if day_target or cooldown_day==d or danger(): skipped+=1; continue
            groups.append({'session':ev['session'],'buy_level':ev['buy_level'],'sell_level':ev['sell_level'],
                           'side':0,'initial':None,'orders':[],'opened_minute':None,'bcnt':0,'scnt':0})
            armed+=1

        if day_target:
            old=len(groups); groups=[g for g in groups if g['side']!=0]; cancelled+=old-len(groups)

        # CONS2 entry: two consecutive completed 1m closes beyond the H1 boundary.
        for g in list(groups):
            if g['side']!=0: continue
            buy_now=ac>g['buy_level']; sell_now=bc<g['sell_level']
            g['bcnt']=g['bcnt']+1 if buy_now else 0; g['scnt']=g['scnt']+1 if sell_now else 0
            if g['bcnt']<2 and g['scnt']<2: continue
            side=1 if g['bcnt']>=2 else -1; px=ac if side==1 else bc
            g['side']=side; g['initial']=px; g['opened_minute']=ts
            if not add(g,LOTS[0],px,bc,ac):
                groups.remove(g); failed=True; failure_date=str(ts); failure_reason='margin_initial'; break
            opened+=1
        if failed: break

        # same-direction MILD4 recovery
        for g in groups:
            if g['side']==0: continue
            while len(g['orders'])<len(LOTS):
                j=len(g['orders']); lev=LEVELS[j]
                if g['side']==1: hit=bl<=g['initial']-lev; px=g['initial']-lev
                else: hit=ah>=g['initial']+lev; px=g['initial']+lev
                if not hit: break
                if not add(g,LOTS[j],px,bc,ac):
                    failed=True; failure_date=str(ts); failure_reason='margin_recovery'; break
            if failed: break
        if failed: break

        # Whole-group TP and emergency tail stop. Conservative: if both touched in same 1m bar, stop wins.
        keep=[]
        for g in groups:
            if g['side']==0 or not g['orders']: keep.append(g); continue
            lots=sum(x[0] for x in g['orders']); w=sum(x[0]*x[1] for x in g['orders']); comm=COMM_RT_PER_LOT*lots
            if g['side']==1:
                tp=(w+(GROUP_TARGET+comm)/CONTRACT)/lots; target_hit=(bh>=tp and g['opened_minute']!=ts)
            else:
                tp=(w-(GROUP_TARGET+comm)/CONTRACT)/lots; target_hit=(al<=tp and g['opened_minute']!=ts)
            cap=cap_now(); stop_hit=False
            if cap is not None:
                if g['side']==1:
                    sl=(w+(comm-cap)/CONTRACT)/lots; stop_hit=bl<=sl
                else:
                    sl=(w+(cap-comm)/CONTRACT)/lots; stop_hit=ah>=sl
            if stop_hit:
                remove(g); balance-=cap; day_realized-=cap; stops+=1; stop_loss_total+=cap; cooldown_day=d
                stop_depth[str(len(g['orders']))]=stop_depth.get(str(len(g['orders'])),0)+1
                continue
            if target_hit:
                remove(g); balance+=GROUP_TARGET; day_realized+=GROUP_TARGET; closed+=1
                close_depth[str(len(g['orders']))]=close_depth.get(str(len(g['orders'])),0)+1
                if (not day_target) and day_realized>=DAILY_TARGET:
                    day_target=True; target_days+=1
                    if not withdrew_today:
                        balance-=WITHDRAW; withdrawn+=WITHDRAW; withdrew_today=True
                continue
            keep.append(g)
        groups=keep

        eq,f=equity(bc,ac); min_eq=min(min_eq,eq); worst_float=min(worst_float,f); max_margin=max(max_margin,margin(bc,ac))
        max_groups=max(max_groups,sum(1 for g in groups if g['side']!=0)); max_pos=max(max_pos,sum(len(g['orders']) for g in groups if g['side']!=0))
        if balance<=0 or eq<=0:
            failed=True; failure_date=str(ts); failure_reason='account_depleted'; break

    last=bars.iloc[-1]; eq,f=equity(float(last.bid_c),float(last.ask_c))
    return {'config':name,'failed':failed,'failure_date':failure_date,'failure_reason':failure_reason,
      'fixed_cap':cfg['fixed'],'ratio_cap':cfg['ratio'],'cap_floor':cfg['floor'],'pause_depth':cfg['pause_depth'],
      'ending_balance':round(balance,3),'withdrawn':round(withdrawn,3),'economic_total':round(balance+withdrawn,3),
      'net_economic_profit':round(balance+withdrawn-START_BALANCE,3),'marked_equity':round(eq,3),'min_equity':round(min_eq,3),
      'worst_floating':round(worst_float,3),'max_margin':round(max_margin,3),'groups_armed':armed,'groups_opened':opened,
      'groups_closed_target':closed,'open_groups_end':sum(1 for g in groups if g['side']!=0),'trades':trades,'recovery_trades':recovery,
      'target_days':target_days,'emergency_stops':stops,'emergency_loss_total':round(stop_loss_total,3),
      'skipped_session_events':skipped,'cancelled_armed':cancelled,'max_concurrent_groups':max_groups,'max_open_positions':max_pos,
      'close_depth_counts':close_depth,'stop_depth_counts':stop_depth}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True)
    a=ap.parse_args(); out=Path(a.outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    bars=base.load_year(a.year,work); sched=base.session_schedule(a.year,bars); results=[]
    for n,c in CONFIGS.items():
        print('RUN',n,flush=True); r=simulate(bars,sched,n,c); results.append(r); print(json.dumps(r,indent=2),flush=True)
    rep={'system':'CONS2 Entry + MILD4 Recovery + Tail Guard Sweep','year':a.year,'results':results}
    with open(out/f'cons2_tailguard_{a.year}.json','w') as f: json.dump(rep,f,indent=2)
    print('FINAL',json.dumps(rep,indent=2),flush=True)
if __name__=='__main__': main()
