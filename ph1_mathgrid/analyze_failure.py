import csv, glob, json, math, os, statistics

episodes=[]
states=[]
for p in glob.glob('analysis/*_episodes.csv'):
    year=os.path.basename(p).split('_')[0]
    with open(p,newline='') as f:
        for r in csv.DictReader(f):
            r['year']=int(year)
            for k in ['basket_id','start_date','start_sec','end_date','end_sec','start_side','orders','max_pos_depth','max_neg_depth','max_two_depth','max_span','switches']:
                r[k]=int(r[k])
            for k in ['start_h1_range','start_boundary','zero','final_pnl','duration_hours','worst_liq']:
                r[k]=float(r[k])
            episodes.append(r)
for p in glob.glob('analysis/*_states.csv'):
    year=os.path.basename(p).split('_')[0]
    with open(p,newline='') as f:
        for r in csv.DictReader(f):
            r['year']=int(year)
            for k in ['basket_id','event_index','date','sec','next_side','would_switch','orders','pos_depth','neg_depth','two_depth','span','switches']:
                r[k]=int(r[k])
            for k in ['current_liq','worst_liq','elapsed_hours','start_h1_range','daily_realized_before','final_pnl']:
                r[k]=float(r[k])
            states.append(r)

# key basket uniquely by year + id
by_state={}
for r in states:
    by_state.setdefault((r['year'],r['basket_id']),[]).append(r)

cats=[e for e in episodes if e['final_pnl']<=-50]
losses=[e for e in episodes if e['final_pnl']<0]
wins=[e for e in episodes if e['final_pnl']>0]

def q(vals,p):
    if not vals:return None
    vals=sorted(vals)
    i=(len(vals)-1)*p
    lo=int(math.floor(i)); hi=int(math.ceil(i))
    if lo==hi:return vals[lo]
    return vals[lo]*(hi-i)+vals[hi]*(i-lo)

def desc(group,field):
    vals=[x[field] for x in group]
    if not vals:return {}
    return {'min':min(vals),'q25':q(vals,.25),'median':q(vals,.5),'q75':q(vals,.75),'max':max(vals),'mean':sum(vals)/len(vals)}

summary={
 'episodes':len(episodes),'wins':len(wins),'losses':len(losses),'catastrophic_le_-50':len(cats),
 'worst_episodes':sorted([{k:e[k] for k in ['year','basket_id','start_date','end_date','final_pnl','close_reason','orders','max_two_depth','max_span','switches','worst_liq','duration_hours','start_h1_range']} for e in episodes],key=lambda x:x['final_pnl'])[:20],
 'cat_features':{f:desc(cats,f) for f in ['orders','max_two_depth','max_span','switches','worst_liq','duration_hours','start_h1_range']},
 'win_features':{f:desc(wins,f) for f in ['orders','max_two_depth','max_span','switches','worst_liq','duration_hours','start_h1_range']},
 'loss_features':{f:desc(losses,f) for f in ['orders','max_two_depth','max_span','switches','worst_liq','duration_hours','start_h1_range']},
}

# Aggregate observable pre-add features per basket.
agg={}
for e in episodes:
    key=(e['year'],e['basket_id']); ss=by_state.get(key,[])
    if ss:
        agg[key]={
          'max_two':max(x['two_depth'] for x in ss),
          'max_switch':max(x['switches'] for x in ss),
          'max_orders':max(x['orders'] for x in ss),
          'max_span':max(x['span'] for x in ss),
          'min_liq':min(x['current_liq'] for x in ss),
          'max_elapsed':max(x['elapsed_hours'] for x in ss),
          'final_pnl':e['final_pnl'],
        }
    else:
        agg[key]={'max_two':0,'max_switch':0,'max_orders':1,'max_span':0,'min_liq':e['worst_liq'],'max_elapsed':e['duration_hours'],'final_pnl':e['final_pnl']}

catkeys={k for k,v in agg.items() if v['final_pnl']<=-50}
winkeys={k for k,v in agg.items() if v['final_pnl']>0}
losskeys={k for k,v in agg.items() if v['final_pnl']<0}

# Evaluate a trigger on aggregated observable maxima/minima.
def eval_rule(name,fn):
    trig={k for k,v in agg.items() if fn(v)}
    return {
      'rule':name,
      'cat_covered':len(trig & catkeys),'cat_total':len(catkeys),
      'loss_covered':len(trig & losskeys),'loss_total':len(losskeys),
      'win_triggered':len(trig & winkeys),'wins_total':len(winkeys),
      'total_triggered':len(trig),
      'precision_cat_pct':round(100*len(trig&catkeys)/len(trig),3) if trig else 0,
      'win_trigger_pct':round(100*len(trig&winkeys)/len(winkeys),3) if winkeys else 0,
    }

candidates=[]
# Single thresholds
for a in range(1,16): candidates.append(eval_rule(f'two_depth>={a}',lambda v,a=a:v['max_two']>=a))
for b in range(1,16): candidates.append(eval_rule(f'switches>={b}',lambda v,b=b:v['max_switch']>=b))
for c in range(4,61,2): candidates.append(eval_rule(f'orders>={c}',lambda v,c=c:v['max_orders']>=c))
for L in range(10,201,10): candidates.append(eval_rule(f'liq<=-{L}',lambda v,L=L:v['min_liq']<=-L))
# 2-factor rules
for a in range(1,11):
  for b in range(1,11):
    candidates.append(eval_rule(f'two_depth>={a} AND switches>={b}',lambda v,a=a,b=b:v['max_two']>=a and v['max_switch']>=b))
for a in range(1,11):
  for L in range(20,161,10):
    candidates.append(eval_rule(f'two_depth>={a} AND liq<=-{L}',lambda v,a=a,L=L:v['max_two']>=a and v['min_liq']<=-L))
for b in range(1,11):
  for L in range(20,161,10):
    candidates.append(eval_rule(f'switches>={b} AND liq<=-{L}',lambda v,b=b,L=L:v['max_switch']>=b and v['min_liq']<=-L))
for a in range(1,11):
  for s in range(6,31,2):
    candidates.append(eval_rule(f'two_depth>={a} AND span>={s}',lambda v,a=a,s=s:v['max_two']>=a and v['max_span']>=s))

full=[r for r in candidates if r['cat_covered']==r['cat_total'] and r['cat_total']>0]
full=sorted(full,key=lambda r:(r['win_triggered'],r['total_triggered'], -r['loss_covered']))
summary['best_rules_covering_all_catastrophes']=full[:25]
summary['best_rules_any_coverage']=sorted(candidates,key=lambda r:(-r['cat_covered'],r['win_triggered'],r['total_triggered']))[:25]

# For each catastrophic episode, find first observable state where selected broad danger features emerge.
cat_detail=[]
for e in sorted(cats,key=lambda x:x['final_pnl']):
    ss=by_state.get((e['year'],e['basket_id']),[])
    cat_detail.append({
      'year':e['year'],'basket_id':e['basket_id'],'start_date':e['start_date'],'end_date':e['end_date'],'final_pnl':e['final_pnl'],
      'orders':e['orders'],'max_two_depth':e['max_two_depth'],'max_span':e['max_span'],'switches':e['switches'],'worst_liq':e['worst_liq'],'duration_hours':e['duration_hours'],'start_h1_range':e['start_h1_range'],
      'first_two3':next(({'date':x['date'],'sec':x['sec'],'orders':x['orders'],'liq':x['current_liq'],'switches':x['switches'],'span':x['span']} for x in ss if x['two_depth']>=3),None),
      'first_two5':next(({'date':x['date'],'sec':x['sec'],'orders':x['orders'],'liq':x['current_liq'],'switches':x['switches'],'span':x['span']} for x in ss if x['two_depth']>=5),None),
      'first_liq50':next(({'date':x['date'],'sec':x['sec'],'orders':x['orders'],'two_depth':x['two_depth'],'switches':x['switches'],'span':x['span']} for x in ss if x['current_liq']<=-50),None),
    })
summary['catastrophic_details']=cat_detail

os.makedirs('analysis',exist_ok=True)
json.dump(summary,open('analysis/failure_summary.json','w'),indent=2,sort_keys=True)
print(json.dumps(summary,indent=2,sort_keys=True))
