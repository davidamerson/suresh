#!/usr/bin/env python3
import argparse, csv, glob, json, os, sys
from collections import defaultdict


def read_rows(paths):
    rows=[]
    for p in paths:
        with open(p,newline='',encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if not r.get('date'): continue
                r['_file']=p
                r['target_hit']=int(r['target_hit'])
                r['final_pnl']=float(r['final_pnl'])
                r['reversals']=int(r['reversals'])
                r['min_liq']=float(r['min_liq'])
                rows.append(r)
    return rows


def calibration(path):
    rows=read_rows([path])
    d={r['date']:r for r in rows}
    target=d.get('2026-10-09')
    if not target:
        print('CALIBRATION_FAIL: 2026-10-09 missing')
        return 2
    print('CALIBRATION_ROW',json.dumps(target,sort_keys=True))
    # Known from the previously verified 2026 exact raw replay for SW5_D6:
    # approximately +$0.942 final and 7 reversals on 2026-10-09.
    pnl=target['final_pnl']; rev=target['reversals']
    ok=(rev==7 and 0.85 <= pnl <= 1.05 and target['target_hit']==1)
    if ok:
        print(f'CALIBRATION_PASS: 2026-10-09 pnl={pnl:.6f}, reversals={rev}')
        return 0
    print(f'CALIBRATION_FAIL: expected ~+0.942 and 7 reversals; got pnl={pnl:.6f}, reversals={rev}, target={target["target_hit"]}')
    return 3


def summarize(pattern,outdir):
    paths=sorted(glob.glob(pattern))
    if not paths:
        print('No result files',file=sys.stderr); return 4
    rows=read_rows(paths)
    rows.sort(key=lambda r:r['date'])
    os.makedirs(outdir,exist_ok=True)

    daily_path=os.path.join(outdir,'PMRR_D_2025_daily.csv')
    fields=['date','target_hit','final_pnl','reversals','min_liq','entry_side','exit_reason','exit_time']
    with open(daily_path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})

    monthly=defaultdict(list)
    for r in rows: monthly[r['date'][:7]].append(r)
    monthly_path=os.path.join(outdir,'PMRR_D_2025_monthly.csv')
    with open(monthly_path,'w',newline='',encoding='utf-8') as f:
        fields2=['month','days','positive_days','target_hits','total_pnl','worst_day_close','worst_intraday','max_reversals']
        w=csv.DictWriter(f,fieldnames=fields2); w.writeheader()
        for m in sorted(monthly):
            a=monthly[m]
            w.writerow({
                'month':m,'days':len(a),
                'positive_days':sum(r['final_pnl']>0 for r in a),
                'target_hits':sum(r['target_hit'] for r in a),
                'total_pnl':f"{sum(r['final_pnl'] for r in a):.6f}",
                'worst_day_close':f"{min(r['final_pnl'] for r in a):.6f}",
                'worst_intraday':f"{min(r['min_liq'] for r in a):.6f}",
                'max_reversals':max(r['reversals'] for r in a),
            })

    losing=[r for r in rows if r['final_pnl']<=0]
    summary={
        'days':len(rows),
        'positive_days':sum(r['final_pnl']>0 for r in rows),
        'target_hits':sum(r['target_hit'] for r in rows),
        'total_pnl':round(sum(r['final_pnl'] for r in rows),6),
        'worst_day_close':min(r['final_pnl'] for r in rows) if rows else None,
        'worst_intraday':min(r['min_liq'] for r in rows) if rows else None,
        'max_reversals':max(r['reversals'] for r in rows) if rows else None,
        'losing_or_zero_days':[{'date':r['date'],'pnl':r['final_pnl'],'target_hit':r['target_hit'],'reversals':r['reversals'],'min_liq':r['min_liq']} for r in losing],
    }
    with open(os.path.join(outdir,'PMRR_D_2025_summary.json'),'w',encoding='utf-8') as f: json.dump(summary,f,indent=2,sort_keys=True)
    print('PMRR_D_2025_SUMMARY')
    print(json.dumps(summary,indent=2,sort_keys=True))
    print('MONTHLY')
    with open(monthly_path,encoding='utf-8') as f: print(f.read())
    return 0


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--calibrate')
    ap.add_argument('--pattern')
    ap.add_argument('--outdir',default='results/final')
    a=ap.parse_args()
    if a.calibrate: return calibration(a.calibrate)
    if a.pattern: return summarize(a.pattern,a.outdir)
    ap.error('use --calibrate or --pattern')

if __name__=='__main__': sys.exit(main())
