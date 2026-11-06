"""
Adversarial controls AFTER observing the original 6-domain outputs.
Explicitly exploratory: not a preregistered confirmation or p-value.
Checks "Maya 260/365" against ordinary forecasting lags, secular trends
and arbitrary pairs of almost-identical calendar periods.
"""
from pathlib import Path
import importlib, json, csv, math, io, contextlib
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from scipy.stats import binomtest

# Prior runner already archives sources, runs six tests; use it to obtain
# verified source bytes and outcomes in this separate standalone job.
import study_global_domains as source
OUT=Path("../results/astrology_calendar_robustness")
OUT.mkdir(parents=True,exist_ok=True)
RNG=np.random.default_rng(20261106)
pairs=[(259,365),(260,364),(260,366),(261,365),(261,366),(250,350),(265,375)]
pairs+= [(int(a),int(b)) for a,b in RNG.integers([220,345],[310,385],size=(143,2))]
results=[];details=[]
def wave(jdn,p):return np.column_stack([np.sin(2*np.pi*jdn/p),np.cos(2*np.pi*jdn/p)])
def evalseries(name,data):
    years=np.array(sorted(data),dtype=int)
    if any((np.diff(years)!=1)):return
    y=np.array([data[int(q)] for q in years],dtype=float)
    eligible=np.arange(2,len(years))
    hold=eligible[years[eligible]>=2015]
    if len(hold)!=11:return
    time=(years-years[0])/100.
    lag=np.column_stack([y[eligible-1],y[eligible-2],time[eligible]])
    jdn=np.array([int(source.swe.julday(int(yr),1,1,0)+.5) for yr in years])
    actual=np.column_stack([wave(jdn-584283,260),wave(jdn-584283,365)])
    calendar_candidates=[np.column_stack([wave(jdn-584283,a),wave(jdn-584283,b)]) for a,b in pairs]
    all_pred={"MAYA_PERIODS":[],"BASE_LAG_TREND":[],"BASE_CONST":[],"BASE_LAST_3":[],"BASE_LAST_5":[],"BASE_LAST_10":[],"BASE_LOCAL_TREND10":[],"BASE_SMOOTH":[],"BASE_QUADRATIC_RIDGE":[]}
    per_controls=[[] for _ in pairs]
    for j in hold:
        tr=eligible[eligible<j]
        trpos=np.where(np.isin(eligible,tr))[0]
        tpos=int(np.where(eligible==j)[0][0])
        def fit(extra):
            if extra is None:X=lag
            else:X=np.column_stack([lag,extra[eligible]])
            sc=StandardScaler().fit(X[trpos])
            f=Ridge(alpha=80.).fit(sc.transform(X[trpos]),y[tr])
            return float(f.predict(sc.transform(X[tpos:tpos+1]))[0])
        all_pred["MAYA_PERIODS"].append(fit(actual))
        all_pred["BASE_LAG_TREND"].append(fit(None))
        all_pred["BASE_CONST"].append(float(np.mean(y[tr])))
        all_pred["BASE_LAST_3"].append(float(np.mean(y[j-3:j])))
        all_pred["BASE_LAST_5"].append(float(np.mean(y[j-5:j])))
        all_pred["BASE_LAST_10"].append(float(np.mean(y[j-10:j])))
        # a causal local linear extrapolation with last 10 completed years
        xx=np.arange(10,dtype=float)
        slope,intercept=np.polyfit(xx,y[j-10:j],1)
        all_pred["BASE_LOCAL_TREND10"].append(float(intercept+10*slope))
        all_pred["BASE_SMOOTH"].append(float(sum(y[j-t]*0.65**(t-1) for t in range(1,11))/sum(0.65**(t-1) for t in range(1,11))))
        qtime=np.column_stack([time,time*time])
        all_pred["BASE_QUADRATIC_RIDGE"].append(fit(qtime))
        for k,arr in enumerate(calendar_candidates):
            per_controls[k].append(fit(arr))
    truth=y[hold]
    m=lambda v:float(np.mean(abs(truth-np.array(v))))
    maya=m(all_pred["MAYA_PERIODS"])
    control_errors=[m(z) for z in per_controls]
    actual_vs_baselines=sorted([(k,m(v)) for k,v in all_pred.items()],key=lambda x:x[1])
    better=int(np.sum(np.array(control_errors)<maya))
    report={"domain":name,"year_start":2015,"year_end":2025,"holdout_n":11,"MAYA_MAE":round(maya,5),
            "baseline_MAEs":{k:round(v,5) for k,v in actual_vs_baselines},
            "best_nonastrology_baseline":min((v,k) for k,v in actual_vs_baselines if k!="MAYA_PERIODS"),
            "random_arbitrary_calendar_pairs":len(pairs),
            "arbitrary_pairs_better_than_Maya":better,
            "fraction_controls_better_than_Maya":round(better/len(pairs),5),
            "best_arbitrary_pair":pairs[int(np.argmin(control_errors))],
            "best_arbitrary_MAE":round(float(min(control_errors)),5),
            "notes":"Period pairs selected only for adversarial sensitivity, not new astrology systems. Selection follows viewing original results; no prospective replication."}
    print("ADVERSARIAL_RESULT",json.dumps(report,default=str),flush=True)
    results.append(report)
    for i,j in enumerate(hold):
        rec={"domain":name,"year":int(years[j]),"actual":float(truth[i])}
        rec.update({k:float(v[i]) for k,v in all_pred.items()})
        details.append(rec)
for label,fn in source.data_sources:
    try:
        ans=fn()
        datasets=ans if isinstance(ans,list) else [ans]
        for name,data,info in datasets:
            evalseries(name,data)
    except Exception as e:
        print("DIAGNOSTIC_MISSING",label,repr(e),flush=True)
if len(results)<6:raise RuntimeError("Not all six diagnostics completed")
(OUT/"adversarial_calendar_control_summary.json").write_text(json.dumps(results,indent=2))
with open(OUT/"adversarial_calendar_control_details.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=details[0].keys());w.writeheader();w.writerows(details)
(OUT/"period_pairs_seed_20261106.json").write_text(json.dumps({"periods":[list(p) for p in pairs],"seed":20261106,"purpose":"Diagnostic arbitrary periods are NOT astrological rules"},indent=2))
print("ADVERSARIAL_COMPLETE",len(results),flush=True)
