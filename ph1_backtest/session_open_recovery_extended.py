import argparse, json
from pathlib import Path
import session_open_independent_groups as base
import session_open_recovery_sweep as core

CONFIGS = {
    'MILD4_REF': {'lots':[0.01,0.01,0.02,0.02], 'levels':[0.0,10.0,20.0,30.0]},
    'EQ6_TIGHT': {'lots':[0.01,0.01,0.01,0.01,0.01,0.01], 'levels':[0.0,10.0,20.0,30.0,40.0,50.0]},
    'EQ6_WIDE': {'lots':[0.01,0.01,0.01,0.01,0.01,0.01], 'levels':[0.0,15.0,30.0,50.0,75.0,105.0]},
    'CAP2_6': {'lots':[0.01,0.01,0.02,0.02,0.02,0.02], 'levels':[0.0,10.0,20.0,35.0,55.0,80.0]},
    'CAP2_6_WIDE': {'lots':[0.01,0.01,0.02,0.02,0.02,0.02], 'levels':[0.0,10.0,25.0,45.0,70.0,100.0]},
    'EQ8_WIDE': {'lots':[0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01], 'levels':[0.0,10.0,20.0,35.0,55.0,80.0,110.0,145.0]},
    'CAP2_8_WIDE': {'lots':[0.01,0.01,0.02,0.02,0.02,0.02,0.02,0.02], 'levels':[0.0,10.0,20.0,35.0,55.0,80.0,110.0,145.0]},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    work = out / 'work'
    work.mkdir(exist_ok=True)

    bars = base.load_year(args.year, work)
    sched = base.session_schedule(args.year, bars)

    results = []
    for name, cfg in CONFIGS.items():
        print('RUN', name, flush=True)
        r = core.simulate(bars, sched, name, cfg)
        results.append(r)
        print(json.dumps(r, indent=2), flush=True)

    report = {
        'system': 'Four Session First-Break $5 Group Extended Small-Cap Recovery Sweep',
        'year': args.year,
        'results': results,
    }
    with open(out / f'extended_recovery_{args.year}.json', 'w') as f:
        json.dump(report, f, indent=2)
    print('FINAL', json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
