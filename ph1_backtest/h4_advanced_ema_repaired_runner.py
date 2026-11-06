"""Audited full tick-replay runner for nine advanced H4 trend-change confirmations.

Uses the exact previous verified GitHub downloader + portfolio ledger
without alteration. The ONLY engine change is replacing one call to
the previous H4 swing-MSS signal generator by the NEW detector call
from h4_deep_seven_signal_detectors.py. We save the generated engine
source and its SHA256 as part of the artifact for independent audit.
No future price path is consulted for signal selection. Importing
source and explicitly compiling a modified trusted engine allows us to
avoid copy/pasting and accidentally changing prior margin, spread,
commission, no-Friday-exit or stop gap rules.
"""
import argparse,inspect,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import h4_advanced_reversal_detectors as detectors
import h4_major_trend_change_rr3_ten_variants_2020_2026 as previous

ALL_METHODS=detectors.METHOD_NAMES[8:]
STARTING=1000.
OLD_CALL="        signal=observe_h4_reversal(t,bid,sr_i,sr_f,daily_high,daily_low,global_i)"
NEW_CALL=("        signal=detect_confirmed_change(t,bid,sr_i,sr_f,daily_high,daily_low,global_i,"
          "reg_p[0,0],valid,reg_n[0])")

def build_engine(out):
    src=inspect.getsource(previous.engine.py_func)
    if src.count(OLD_CALL)!=1:
        raise RuntimeError("REPRODUCIBILITY FAIL: source engine entry call changed")
    new=src.replace(OLD_CALL,NEW_CALL)
    p=Path(out)
    p.mkdir(parents=True,exist_ok=True)
    (p/'engine_generated_exact.py').write_text(new)
    audit={
       'source_engine_SHA256':hashlib.sha256(src.encode()).hexdigest(),
       'modified_engine_SHA256':hashlib.sha256(new.encode()).hexdigest(),
       'old_exact_entry_expression':OLD_CALL.strip(),
       'new_exact_entry_expression':NEW_CALL.strip(),
       'other_source_change_count':0,
       'engine_modification':'one single entry signal call only',
       'input_algorithm_source':'h4_major_trend_change_rr3_ten_variants_2020_2026.py',
       'new_observer_source':'h4_advanced_reversal_detectors.py'
    }
    (p/'engine_diff_and_sha256.json').write_text(json.dumps(audit,indent=2))
    namespace=dict(vars(previous))
    namespace['detect_confirmed_change']=detectors.detect_confirmed_change
    exec(compile(new,'engine_generated_exact.py','exec'),namespace)
    return namespace['engine']

def configure(method):
    if method not in ALL_METHODS:raise ValueError(method)
    detectors.METHOD=detectors.METHOD_NAMES.index(method)
    arr=[]
    for i in range(1,11):
        tp=3*i;sl=i
        arr.append((f'{method}_TP{30*i}_SL{10*i}',1.,0.,0,0,2000.,
              float(tp),float(sl),float(tp),float(sl),
              1.,0.,0.,0.,0.,0.,0.,0.,0.,0.))
    previous.CONF=arr
    previous.CFG=np.asarray([x[1:] for x in arr],dtype=np.float64)
    previous.NAMES=[x[0] for x in arr]
    return arr

def selftest():
    assert len(previous.CONF)==10 and previous.CFG.shape==(10,19)
    assert detectors.METHOD in range(8,17)
    method=detectors.METHOD_NAMES[detectors.METHOD]
    for i,c in enumerate(previous.CONF):
        assert c[0]==f'{method}_TP{30*(i+1)}_SL{10*(i+1)}'
        assert c[6]==3*(i+1) and c[7]==i+1
        assert c[8]==3*(i+1) and c[9]==i+1
        assert c[3]==0. and c[4]==0 and c[11]==0. and c[12]==0.
    si=np.zeros(4,dtype=np.int64);si[0]=-1
    sf=np.zeros(8,dtype=np.float64)
    hi=np.zeros(5);lo=np.zeros(5)
    gi=np.zeros(7,dtype=np.int64)
    ex=np.zeros(6000,dtype=np.float64)
    flags=np.zeros(4,dtype=np.int64)
    ring=np.zeros(2,dtype=np.int64)
    assert detectors.detect_confirmed_change(0,4000.,si,sf,hi,lo,gi,ex,flags,ring)==0
    assert detectors.detect_confirmed_change(detectors.NS_HOUR,4001.,si,sf,hi,lo,gi,ex,flags,ring)==0
    assert detectors.detect_confirmed_change(4*detectors.NS_HOUR,4002.,si,sf,hi,lo,gi,ex,flags,ring)==0
    assert int(si[1])==1 and int(flags[2])==0
    print("SELFTEST PASS method",method,"H4 no intrabar signal and 10 fixed RR3 TP/SL models",flush=True)

def execute(method,out):
    configure(method)
    out=Path(out)
    previous.engine=build_engine(out)
    previous.selftest=selftest
    previous.run(out)  # last proven real Exness tick streaming execution

    p=out/'model_summary.csv'
    summary=pd.read_csv(p)
    assert len(summary)==10
    assert summary['config'].str.startswith(method+'_').all()
    for _,r in summary.iterrows():
        assert int(r['forced_friday_flat'])==0
        assert int(r['time_stopped_exits'])==0
        assert int(r['breakeven_exits'])==0
        assert int(r['trailing_exits'])==0
        assert int(r['modeled_stopout_liquidations'])==0, "model stopout exception"
        assert int(r['trades_closed'])==int(r['TP'])+int(r['SL'])
        assert int(r['margin_rejections'])==0
    assert summary['raw_eligible_tick_crosses'].nunique()==1
    assert summary['trades_opened'].nunique()==1
    # Each H4 method event is a global causal signal and all RR profiles
    # entered same quote; no outcome-aware filtering or skipped losing paths.
    ledger=pd.read_csv(out/'ticket_ledger.csv')
    try:
        opened=pd.read_csv(out/'open_positions_at_cutoff.csv')
    except pd.errors.EmptyDataError:
        opened=pd.DataFrame(columns=['model','unrealized_gross_usd'])
    for _,r in summary.iterrows():
        sub=ledger[ledger.model==r['config']]
        live=opened[opened.model==r['config']]
        assert len(sub)==int(r['trades_closed'])
        assert len(live)==int(r['active_positions_end'])
        # Net historical account equity includes genuine still-OPEN
        # floating P/L. Full roundtrip commission was booked on entry.
        close_net=float(sub.net_ex_swap.sum())
        floating_net=float(live.unrealized_gross_usd.sum())-0.07*len(live)
        assert abs(close_net+floating_net-float(r['net_profit']))<0.005, (
            r['config'],close_net,floating_net,r['net_profit'])
        assert len(sub[sub.result=='TP'])==int(r['TP'])
        assert len(sub[sub.result=='SL'])==int(r['SL'])
    # Compare ALL entries, including tickets still open at dataset cutoff.
    # Comparing CLOSED tickets alone is invalid for different TP/SL distances.
    first=None
    for name in summary['config']:
        sub=ledger[ledger.model==name]
        live=opened[opened.model==name]
        keys=[(str(t),str(side),round(float(entry),5)) for t,side,entry
              in zip(sub.entered_utc,sub.side,sub.entry)]
        if len(live):
            keys += [(str(t),str(side),round(float(entry),5)) for t,side,entry
                     in zip(live.entry_utc,live.side,live.entry_price)]
        keys.sort()
        if first is None:first=keys
        else:assert keys==first, "actual signals/entry tickets differ across TP SL profiles"
    summary['confirmation_method']=method
    summary['family']='H4_CLOSED_BAR_ADVANCED_NINE_WAY_CONFIRMATION'
    summary['signal_description']=method
    summary.to_csv(p,index=False)
    ledger['source']=method+'_H4_CONFIRMED_CLOSE_NEXT_QUOTE'
    ledger.to_csv(out/'ticket_ledger.csv',index=False)
    provenance=out/'provenance.json'
    meta=json.loads(provenance.read_text())
    meta['entry_strategy']='H4_CLOSED_BAR_'+method+' (9 predeclared advanced confirmations, no future bars)'
    meta['method']=method
    meta['method_details_file']='h4_advanced_reversal_detectors.py'
    meta['previous_h4_strategy_result_not_reused']='All 296709207 real quote ticks replayed, with different method-specific entries'
    meta['trend_confirmation_is_observation_not_guaranteed_direction']=True
    meta['advanced_nine_methods_locked_before_this_replay']=ALL_METHODS
    meta['methodological_clarification']='Nine advanced variants are exploratory after known historical MACD/structural findings; no pristine out-of-sample claim'
    meta['indicator_change_thresholds']='Fixed in detector source; no grid optimization'
    provenance.write_text(json.dumps(meta,indent=2))
    print('NEW_METHOD_FINAL',method,'signals',summary['trades_opened'].iloc[0],flush=True)
    print(summary[['config','trades_opened','trades_closed','TP','SL','win_percent',
                   'net_profit','max_drawdown_usd','closing_cash',
                   'active_positions_end','modeled_stopout_liquidations']].to_string(index=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--method',required=True,choices=ALL_METHODS)
    ap.add_argument('--out',default='results/continuous_2020_2026')
    ap.add_argument('--selftest',action='store_true')
    args=ap.parse_args()
    configure(args.method)
    if args.selftest:
        build_engine(args.out);selftest()
    else:execute(args.method,args.out)
