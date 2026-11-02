import argparse
import fresh_xau_daytrader_fast as fast
import fresh_xau_poc_daytrader as poc

# fresh_xau_daytrader_fast already monkey-patches the shared research module's simulate
# with a NumPy-array implementation using the same execution/accounting rules.
poc.m.simulate = fast.fast_simulate

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); a=ap.parse_args(); poc.main(a.outdir)
