#!/usr/bin/env python3
"""Post-hoc temporal robustness only. PRIMARY pre-registered windows unchanged.
Frozen splits BEFORE reading these new holdout comparisons; report ALL splits.
"""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.resolve()))
import astral_global_hypothesis_test as main_study
import astral_market_fred_public_archive as market_study
CUTS={"earthquakes":(2012,2020),"markets":(2019,2022),"conflicts":(2015,2020)}
def run(dataset,cutoff,out):
    if cutoff not in CUTS[dataset]:raise ValueError("Unexpected temporal cutoff")
    study=market_study if dataset=="markets" else main_study
    before=getattr(study,dataset)
    def frozen_cut():
        seq=list(before())
        seq[4]=cutoff
        return tuple(seq)
    setattr(study,dataset,frozen_cut)
    study.report(dataset,out)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",required=True,choices=list(CUTS))
    p.add_argument("--cutoff",type=int,required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    run(a.dataset,a.cutoff,a.out)
