import csv,glob,json,sys,os

def load(pattern):
    rows=[]
    for p in sorted(glob.glob(pattern)):
        with open(p,newline='') as f:
            for r in csv.DictReader(f):
                for k in ['day_pnl','worst_day_delta','max_margin_1_2000']:
                    r[k]=float(r[k])
                for k in ['target_hit','emergency','baskets','cycle_wins','forced_closes','total_orders','max_open']:
                    r[k]=int(r[k])
                rows.append(r)
    return rows

def summary(name,rows,start=1000.0):
    traded=[r for r in rows if r['baskets']>0 or abs(r['day_pnl'])>1e-12]
    bal=start; minbal=bal; minequity=bal; target=0; emergencies=0; pos=0; neg=0; zero=0
    worst=None; best=None
    for r in rows:
        daystart=bal
        minequity=min(minequity,daystart+r['worst_day_delta'])
        bal+=r['day_pnl']; minbal=min(minbal,bal)
        target+=r['target_hit']; emergencies+=r['emergency']
        if r['day_pnl']>1e-12: pos+=1
        elif r['day_pnl']<-1e-12: neg+=1
        else: zero+=1
        if worst is None or r['day_pnl']<worst['day_pnl']: worst=r
        if best is None or r['day_pnl']>best['day_pnl']: best=r
    out={
        'name':name,'calendar_days':len(rows),'traded_days':len(traded),
        'target_hit_days':target,'positive_days':pos,'negative_days':neg,'zero_days':zero,
        'target_rate_pct':round(100*target/len(rows),3) if rows else 0,
        'target_rate_traded_pct':round(100*target/len(traded),3) if traded else 0,
        'total_pnl':round(sum(r['day_pnl'] for r in rows),6),
        'end_balance_from_1000':round(bal,6),'min_closed_balance':round(minbal,6),'min_intraday_equity':round(minequity,6),
        'emergency_days':emergencies,
        'max_open':max((r['max_open'] for r in rows),default=0),
        'max_orders_day':max((r['total_orders'] for r in rows),default=0),
        'max_baskets_day':max((r['baskets'] for r in rows),default=0),
        'max_margin_1_2000':round(max((r['max_margin_1_2000'] for r in rows),default=0),6),
        'worst_day': {'date':worst['date'],'pnl':worst['day_pnl'],'target':worst['target_hit'],'emergency':worst['emergency'],'baskets':worst['baskets'],'max_open':worst['max_open'],'worst_delta':worst['worst_day_delta']} if worst else None,
        'best_day': {'date':best['date'],'pnl':best['day_pnl']} if best else None,
        'loss_days':[{'date':r['date'],'pnl':r['day_pnl'],'emergency':r['emergency'],'baskets':r['baskets'],'max_open':r['max_open'],'worst_delta':r['worst_day_delta']} for r in rows if r['day_pnl']<0]
    }
    return out

if __name__=='__main__':
    mode=sys.argv[1]; year=sys.argv[2]
    rows=load(f'results/{mode}_{year}_*.csv')
    out=summary(f'{mode}_{year}',rows)
    print('SUMMARY '+json.dumps(out,sort_keys=True))
    os.makedirs('merged',exist_ok=True)
    if rows:
        fields=list(rows[0].keys())
        with open(f'merged/{mode}_{year}_daily.csv','w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        with open(f'merged/{mode}_{year}_summary.json','w') as f: json.dump(out,f,indent=2,sort_keys=True)
