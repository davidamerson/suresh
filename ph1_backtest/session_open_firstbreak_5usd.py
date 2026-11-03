import argparse, json
from pathlib import Path
import session_open_independent_groups as base

# Corrected user rules:
# - first break direction only for each session group
# - no opposite-side trade inside that group
# - close the entire group only at +$5 net
base.EPS_PROFIT = 5.0


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
    print('SESSION EVENTS', len(sched), flush=True)

    result = base.simulate(bars, sched, 'FIRST_BREAK')
    report = {
        'system': 'Four Session Opening-H1 First-Break Only + $5 Group Target',
        'year': args.year,
        'session_definition': {
            'AUSTRALIAN': '08:00 Australia/Sydney',
            'ASIAN': '09:00 Asia/Tokyo',
            'LONDON': '08:00 Europe/London',
            'NEW_YORK': '08:00 America/New_York',
            'DST': 'zoneinfo historical'
        },
        'result': result,
        'clarification': 'Once the first side breaks, that session group keeps only that direction; a later opposite-side break does not add an opposite trade.'
    }
    with open(out / f'report_{args.year}.json', 'w') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
