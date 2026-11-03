import argparse, json
from pathlib import Path
import session_open_independent_groups as base

START_BALANCE=1000.0
DAILY_TARGET=20.0
WITHDRAW=10.0
CONTRACT=100.0
LEVERAGE=2000.0
COMM_RT_PER_LOT=7.0
GROUP_TARGET=5.0

MILD4={'lots':[0.01,0.01,0.02,0.02], 'levels':[0.0,10.0,20.0,30.0]}
CAP6W={'lots':[0.01,0.01,0.02,0.02,0.02,0.02], 'levels':[0.0,10.0,25.0,45.0,70.0,100.0]}
CONFIGS={
 'PAUSE_D3_REF':{**MILD4,'pause_depth':3,'loss_cap':None},
 'SL40_MILD4':{**MILD4,'pause_depth':3,'loss_cap':40.0},
 'SL60_MILD4':{**MILD4,'pause_depth':3,'loss_cap':60.0},
 'SL80_MILD4':{**MILD4,'pause_depth':3,'loss_cap':80.0},
 'SL100_MILD4':{**MILD4,'pause_depth':3,'loss_cap':100.0},
 'SL125_MILD4':{**MILD4,'pause_depth':3,'loss_cap':125.0},
 'SL150_MILD4':{**MILD4,'pause_depth':3,'loss_cap':150.0},
 'SL80_D2_MILD4':{**MILD4,'pause_depth':2,'loss_cap':80.0},
 'SL80_CAP6W':{**CAP6W,'pause_depth':3,'loss_cap':80.0},
}

def simulate(bars,schedule,name,cfg):
    balance=START_BALANCE; withdrawn=0.0; failed=False; failure_date=''; failure_reason=''
    groups=[]; arm_idx=0; day=None; day_realized=0.0; day_target=False; withdrew_today=False; cooldown_day=None
    armed=opened=closed_target=trades=recovery_trades=0; target_days=0; emergency_closes=0; emergency_realized=0.0
    skipped=0; cancelled_armed=0; max_groups=max_positions=0; min_equity=START_BALANCE; worst_float=0.0; max_margin=0.0
    close_depth_counts={}; stop_depth_counts={}
    total_buy_lots=total_sell_lots=0.0; total_buy_entry=total_sell_entry=0.0; open_comm=0.0

    def equity_at(bid,ask):
        f=CONTRACT*(bid*total_buy_lots-total_buy_entry+total_sell_entry-ask*total_sell_lots)-open_comm
        return balance+f,f
    def margin_at(bid,ask):
        return (total_buy_lots+total_sell_lots)*CONTRACT*((bid+ask)/2.0)/LEVERAGE
    def can_add(lot,bid,ask):
        eq,_=equity_at(bid,ask); return eq-margin_at(bid,ask)>=lot*CONTRACT*((bid+ask)/2.0)/LEVERAGE
    def add_order(g,lot,px,bid,ask):
        nonlocal total_buy_lots,total_sell_lots,total_buy_entry,total_sell_entry,open_comm,trades,recovery_trades
        if not can_add(lot,bid,ask): return False
        if g['side']==1: total_buy_lots+=lot; total_buy_entry+=px*lot
        else: total_sell_lots+=lot; total_sell_entry+=px*lot
        open_comm+=COMM_RT_PER_LOT*lot; g['orders'].append((lot,px)); trades+=1
        if len(g['orders'])>1: recovery_trades+=1
        return True
    def remove_group(g):
        nonlocal total_buy_lots,total_sell_lots,total_buy_entry,total_sell_entry,open_comm
        lots=sum(x[0] for x in g['orders']); weighted=sum(x[0]*x[1] for x in g['orders']); comm=COMM_RT_PER_LOT*lots
        if g['side']==1: total_buy_lots-=lots; total_buy_entry-=weighted
        else: total_sell_lots-=lots; total_sell_entry-=weighted
        open_comm-=comm
    def danger_active():
        pd=cfg['pause_depth']; return any(g['side']!=0 and len(g['orders'])>=pd for g in groups)

    arr=bars[['bid_o','bid_h','bid_l','bid_c','ask_o','ask_h','ask_l','ask_c']].to_numpy(float)
    for i,ts in enumerate(bars.index):
        if failed: break
        d=ts.date()
        if day!=d:
            day=d; day_realized=0.0; day_target=False; withdrew_today=False; cooldown_day=None
        bo,bh,bl,bc,ao,ah,al,ac=arr[i]

        # If danger/cooldown starts, cancel any armed but not yet triggered groups.
        if danger_active() or cooldown_day==d:
            old=len(groups); groups=[g for g in groups if g['side']!=0]; cancelled_armed+=old-len(groups)

        while arm_idx<len(schedule) and schedule[arm_idx]['arm']<=ts:
            ev=schedule[arm_idx]; arm_idx+=1
            if ev['arm'].date()!=d: continue
            if day_target or cooldown_day==d or danger_active(): skipped+=1; continue
            groups.append({'session':ev['session'],'buy_level':ev['buy_level'],'sell_level':ev['sell_level'],
                           'side':0,'initial':None,'orders':[],'opened_minute':None}); armed+=1

        # first break entry
        for g in list(groups):
            if g['side']!=0: continue
            cross_b=ah>g['buy_level']; cross_s=bl<g['sell_level']
            if not (cross_b or cross_s): continue
            if cross_b and cross_s:
                mid_o=(bo+ao)/2; side=1 if abs(g['buy_level']-mid_o)<=abs(mid_o-g['sell_level']) else -1
            else: side=1 if cross_b else -1
            px=g['buy_level'] if side==1 else g['sell_level']; g['side']=side; g['initial']=px; g['opened_minute']=ts
            if not add_order(g,cfg['lots'][0],px,bc,ac):
                groups.remove(g); failed=True; failure_date=str(ts); failure_reason='insufficient_free_margin_initial'; break
            opened+=1
        if failed: break

        # recovery adds
        for g in list(groups):
            if g['side']==0: continue
            while len(g['orders'])<len(cfg['lots']):
                j=len(g['orders']); lev=cfg['levels'][j]
                if g['side']==1: hit=bl<=g['initial']-lev; px=g['initial']-lev
                else: hit=ah>=g['initial']+lev; px=g['initial']+lev
                if not hit: break
                if not add_order(g,cfg['lots'][j],px,bc,ac):
                    failed=True; failure_date=str(ts); failure_reason='insufficient_free_margin_recovery'; break
            if failed: break
        if failed: break

        # whole-group target / hard loss cap. If both occur within same 1m bar, take stop (conservative ordering).
        keep=[]
        for g in groups:
            if g['side']==0 or not g['orders']:
                keep.append(g); continue
            lots=sum(x[0] for x in g['orders']); weighted=sum(x[0]*x[1] for x in g['orders']); comm=COMM_RT_PER_LOT*lots
            if g['side']==1:
                tp=(weighted+(GROUP_TARGET+comm)/CONTRACT)/lots; target_hit=bh>=tp and g['opened_minute']!=ts
            else:
                tp=(weighted-(GROUP_TARGET+comm)/CONTRACT)/lots; target_hit=al<=tp and g['opened_minute']!=ts
            cap=cfg['loss_cap']; stop_hit=False
            if cap is not None:
                if g['side']==1:
                    sl=(weighted+(comm-cap)/CONTRACT)/lots; stop_hit=bl<=sl
                else:
                    sl=(weighted+(cap-comm)/CONTRACT)/lots; stop_hit=ah>=sl
            if stop_hit:
                remove_group(g); balance-=cap; day_realized-=cap; emergency_closes+=1; emergency_realized-=cap; cooldown_day=d
                stop_depth_counts[str(len(g['orders']))]=stop_depth_counts.get(str(len(g['orders'])),0)+1
                continue
            if target_hit:
                remove_group(g); balance+=GROUP_TARGET; day_realized+=GROUP_TARGET; closed_target+=1
                close_depth_counts[str(len(g['orders']))]=close_depth_counts.get(str(len(g['orders'])),0)+1
                if (not day_target) and day_realized>=DAILY_TARGET:
                    day_target=True; target_days+=1
                    if not withdrew_today: balance-=WITHDRAW; withdrawn+=WITHDRAW; withdrew_today=True
                continue
            keep.append(g)
        groups=keep

        eq,floatp=equity_at(bc,ac); min_equity=min(min_equity,eq); worst_float=min(worst_float,floatp); max_margin=max(max_margin,margin_at(bc,ac))
        max_groups=max(max_groups,sum(1 for g in groups if g['side']!=0)); max_positions=max(max_positions,sum(len(g['orders']) for g in groups if g['side']!=0))
        if balance<=0 or eq<=0:
            failed=True; failure_date=str(ts); failure_reason='account_depleted'; break

    last=bars.iloc[-1]; eq,floatp=equity_at(float(last.bid_c),float(last.ask_c))
    return {'config':name,'failed':failed,'failure_date':failure_date,'failure_reason':failure_reason,
      'loss_cap':cfg['loss_cap'],'pause_depth':cfg['pause_depth'],'lots':cfg['lots'],'levels':cfg['levels'],
      'ending_balance':round(balance,3),'withdrawn':round(withdrawn,3),'economic_total':round(balance+withdrawn,3),
      'net_economic_profit':round(balance+withdrawn-START_BALANCE,3),'marked_equity':round(eq,3),
      'min_equity':round(min_equity,3),'worst_floating':round(worst_float,3),'max_margin':round(max_margin,3),
      'groups_armed':armed,'groups_opened':opened,'groups_closed_target':closed_target,'open_groups_at_end':sum(1 for g in groups if g['side']!=0),
      'trades':trades,'recovery_trades':recovery_trades,'target_days':target_days,'emergency_closes':emergency_closes,
      'emergency_realized':round(emergency_realized,3),'skipped_session_events':skipped,'cancelled_armed':cancelled_armed,
      'max_concurrent_groups':max_groups,'max_open_positions':max_positions,'close_depth_counts':close_depth_counts,'stop_depth_counts':stop_depth_counts}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True)
    a=ap.parse_args(); out=Path(a.outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    bars=base.load_year(a.year,work); sched=base.session_schedule(a.year,bars); results=[]
    for n,c in CONFIGS.items():
        print('RUN',n,flush=True); r=simulate(bars,sched,n,c); results.append(r); print(json.dumps(r,indent=2),flush=True)
    report={'system':'Tail Risk Group Stop v2','year':a.year,'results':results}
    with open(out/f'tailrisk_groupstop_v2_{a.year}.json','w') as f: json.dump(report,f,indent=2)
    print('FINAL',json.dumps(report,indent=2),flush=True)
if __name__=='__main__': main()
