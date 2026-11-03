import argparse, json
from pathlib import Path
import session_open_independent_groups as base

START_BALANCE=1000.0; DAILY_TARGET=20.0; WITHDRAW=10.0
CONTRACT=100.0; LEVERAGE=2000.0; COMM_RT_PER_LOT=7.0; GROUP_TARGET=5.0

CONFIGS={
 'ZR_CONS2':{'confirm':2,'buffer':0.0,'pause_after_flips':None,'range_max':None},
 'ZR_CONS2_PAUSE1':{'confirm':2,'buffer':0.0,'pause_after_flips':1,'range_max':None},
 'ZR_CONS2_PAUSE2':{'confirm':2,'buffer':0.0,'pause_after_flips':2,'range_max':None},
 'ZR_CONS1':{'confirm':1,'buffer':0.0,'pause_after_flips':None,'range_max':None},
 'ZR_CONS2_BUF05':{'confirm':2,'buffer':0.5,'pause_after_flips':None,'range_max':None},
 'ZR_CONS2_BUF10':{'confirm':2,'buffer':1.0,'pause_after_flips':None,'range_max':None},
 'ZR_CONS2_R20':{'confirm':2,'buffer':0.0,'pause_after_flips':None,'range_max':20.0},
 'ZR_CONS2_R30':{'confirm':2,'buffer':0.0,'pause_after_flips':None,'range_max':30.0},
}

def simulate(bars,schedule,name,cfg):
    balance=START_BALANCE; withdrawn=0.0; failed=False; failure_date=''; failure_reason=''
    groups=[]; arm_idx=0; day=None; day_realized=0.0; day_target=False; withdrew_today=False
    armed=opened=closed=target_days=trades=flips=skipped=cancelled=0
    min_eq=START_BALANCE; worst_float=0.0; max_margin=0.0; max_groups=max_pos=max_flips_group=0
    close_flip_counts={}; total_buy_lots=total_sell_lots=total_buy_entry=total_sell_entry=open_comm=0.0

    def equity_at(bid,ask):
        f=CONTRACT*(bid*total_buy_lots-total_buy_entry+total_sell_entry-ask*total_sell_lots)-open_comm
        return balance+f,f
    def margin_at(bid,ask): return (total_buy_lots+total_sell_lots)*CONTRACT*((bid+ask)/2.0)/LEVERAGE
    def can_add(lot,bid,ask):
        eq,_=equity_at(bid,ask); req=lot*CONTRACT*((bid+ask)/2.0)/LEVERAGE
        return eq-margin_at(bid,ask)>=req
    def add_order(g,side,lot,px,bid,ask):
        nonlocal total_buy_lots,total_sell_lots,total_buy_entry,total_sell_entry,open_comm,trades
        if not can_add(lot,bid,ask): return False
        if side==1: total_buy_lots+=lot; total_buy_entry+=lot*px
        else: total_sell_lots+=lot; total_sell_entry+=lot*px
        open_comm+=COMM_RT_PER_LOT*lot; g['orders'].append((side,lot,px)); trades+=1
        return True
    def remove_group(g):
        nonlocal total_buy_lots,total_sell_lots,total_buy_entry,total_sell_entry,open_comm
        for side,lot,px in g['orders']:
            if side==1: total_buy_lots-=lot; total_buy_entry-=lot*px
            else: total_sell_lots-=lot; total_sell_entry-=lot*px
            open_comm-=COMM_RT_PER_LOT*lot
    def group_pnl(g,bid,ask):
        p=0.0; comm=0.0
        for side,lot,px in g['orders']:
            p += CONTRACT*lot*((bid-px) if side==1 else (px-ask)); comm += COMM_RT_PER_LOT*lot
        return p-comm
    def danger_active():
        k=cfg['pause_after_flips']
        return bool(k is not None and any(g['side']!=0 and g['flips']>=k for g in groups))

    arr=bars[['bid_o','bid_h','bid_l','bid_c','ask_o','ask_h','ask_l','ask_c']].to_numpy(float)
    for i,ts in enumerate(bars.index):
        if failed: break
        d=ts.date()
        if day!=d:
            day=d; day_realized=0.0; day_target=False; withdrew_today=False
        bo,bh,bl,bc,ao,ah,al,ac=arr[i]

        # Pause only prevents new/unentered groups; open recovery groups continue.
        if danger_active() or day_target:
            old=len(groups); groups=[g for g in groups if g['side']!=0]; cancelled+=old-len(groups)
        while arm_idx<len(schedule) and schedule[arm_idx]['arm']<=ts:
            ev=schedule[arm_idx]; arm_idx+=1
            if ev['arm'].date()!=d: continue
            width=ev['buy_level']-ev['sell_level']
            if day_target or danger_active() or (cfg['range_max'] is not None and width>cfg['range_max']):
                skipped+=1; continue
            groups.append({'session':ev['session'],'hi':ev['buy_level'],'lo':ev['sell_level'],'side':0,'orders':[],
                           'flips':0,'buy_count':0,'sell_count':0,'opened_minute':None})
            armed+=1

        # Confirmation and boundary flips. All positions remain until whole group +$5.
        for g in groups:
            b=cfg['buffer']; n=cfg['confirm']
            buy_now=ac>g['hi']+b; sell_now=bc<g['lo']-b
            g['buy_count']=g['buy_count']+1 if buy_now else 0
            g['sell_count']=g['sell_count']+1 if sell_now else 0
            if g['side']==0:
                if g['buy_count']>=n:
                    side=1; lot=0.01; px=ac
                elif g['sell_count']>=n:
                    side=-1; lot=0.01; px=bc
                else: continue
                if not add_order(g,side,lot,px,bc,ac):
                    failed=True; failure_date=str(ts); failure_reason='margin_initial'; break
                g['side']=side; g['opened_minute']=ts; opened+=1
                g['buy_count']=0; g['sell_count']=0
            elif g['side']==1 and g['sell_count']>=n:
                if not add_order(g,-1,0.02,bc,bc,ac):
                    failed=True; failure_date=str(ts); failure_reason='margin_flip'; break
                g['side']=-1; g['flips']+=1; flips+=1; g['buy_count']=0; g['sell_count']=0
            elif g['side']==-1 and g['buy_count']>=n:
                if not add_order(g,1,0.02,ac,bc,ac):
                    failed=True; failure_date=str(ts); failure_reason='margin_flip'; break
                g['side']=1; g['flips']+=1; flips+=1; g['buy_count']=0; g['sell_count']=0
            max_flips_group=max(max_flips_group,g['flips'])
        if failed: break

        # Whole group closes only at net +$5; no individual loss close.
        keep=[]
        for g in groups:
            if g['side']==0 or not g['orders']:
                keep.append(g); continue
            # Use bar extremes conservatively only for same-net-direction target; exact group P/L at close below.
            # Since mixed positions reduce to net +/-0.01 by construction, calculate liquidation P/L at favorable extreme.
            if g['side']==1: p=group_pnl(g,bh,ah)
            else: p=group_pnl(g,bl,al)
            if p < GROUP_TARGET or g['opened_minute']==ts:
                keep.append(g); continue
            remove_group(g); balance+=GROUP_TARGET; day_realized+=GROUP_TARGET; closed+=1
            close_flip_counts[str(g['flips'])]=close_flip_counts.get(str(g['flips']),0)+1
            if not day_target and day_realized>=DAILY_TARGET:
                day_target=True; target_days+=1
                if not withdrew_today:
                    balance-=WITHDRAW; withdrawn+=WITHDRAW; withdrew_today=True
        groups=keep

        eq,f=equity_at(bc,ac); m=margin_at(bc,ac)
        min_eq=min(min_eq,eq); worst_float=min(worst_float,f); max_margin=max(max_margin,m)
        max_groups=max(max_groups,sum(1 for g in groups if g['side']!=0)); max_pos=max(max_pos,sum(len(g['orders']) for g in groups if g['side']!=0))
        if eq<=0:
            failed=True; failure_date=str(ts); failure_reason='equity_le_zero'; break

    last=bars.iloc[-1]; eq,f=equity_at(float(last.bid_c),float(last.ask_c))
    return {'config':name,'failed':failed,'failure_date':failure_date,'failure_reason':failure_reason,
      'ending_balance':round(balance,3),'withdrawn':round(withdrawn,3),'economic_total':round(balance+withdrawn,3),
      'net_economic_profit':round(balance+withdrawn-START_BALANCE,3),'marked_equity':round(eq,3),'min_equity':round(min_eq,3),
      'worst_floating':round(worst_float,3),'max_margin':round(max_margin,3),'groups_armed':armed,'groups_opened':opened,
      'groups_closed_target':closed,'open_groups_end':sum(1 for g in groups if g['side']!=0),'trades':trades,'flips':flips,
      'target_days':target_days,'skipped_session_events':skipped,'cancelled_armed':cancelled,'max_concurrent_groups':max_groups,
      'max_open_positions':max_pos,'max_flips_single_group':max_flips_group,'close_flip_counts':close_flip_counts,'rules':cfg}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True)
    a=ap.parse_args(); out=Path(a.outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    bars=base.load_year(a.year,work); sched=base.session_schedule(a.year,bars); results=[]
    for n,c in CONFIGS.items():
        print('RUN',n,flush=True); r=simulate(bars,sched,n,c); results.append(r); print(json.dumps(r,indent=2),flush=True)
    rep={'system':'Four Session CONS Boundary Zone Recovery','year':a.year,'results':results}
    with open(out/f'zone_recovery_{a.year}.json','w') as f: json.dump(rep,f,indent=2)
    print('FINAL',json.dumps(rep,indent=2),flush=True)
if __name__=='__main__': main()
