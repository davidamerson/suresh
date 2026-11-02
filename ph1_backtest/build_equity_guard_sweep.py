from pathlib import Path
import re

src = Path('ph1_backtest/entry10_adaptive_sweep.py')
out = Path('/tmp/eqguard.py')
s = src.read_text()

names = [
    'BASELINE',
    'EQ_HEDGE_50',
    'EQ_HEDGE_55',
    'EQ_HEDGE_60',
    'EQ_HEDGE_65',
    'EQ_HEDGE_70',
    'EQ_HEDGE_75',
    'EQ_HEDGE_80',
    'EQ65_NETCAP4',
    'EQ65_NETCAP3',
    'EQ70_NETCAP3',
    'EQ60_NETCAP3',
]

s = re.sub(r'METHODS = \[.*?\]\n\n', 'METHODS = ' + repr(names) + '\n\n', s, count=1, flags=re.S)
s = s.replace('TARGET = 10.0', 'TARGET = 20.0\nWITHDRAW = 10.0')
s = s.replace('balance[cidx] -= TARGET', 'balance[cidx] -= WITHDRAW')
s = s.replace('withdrawn[cidx] += TARGET', 'withdrawn[cidx] += WITHDRAW')
# Never realize loss at Friday/year-end.
s = s.replace('if prev_dow == 4:', 'if False and prev_dow == 4:')
s = s.replace('if (last_day + 3) % 7 == 4:', 'if False and (last_day + 3) % 7 == 4:')

# All configs use exact same Compression Breakout signals (original index 3).
needle = '    times = np.full((len(METHODS), maxn), np.iinfo(np.int64).max, dtype=np.int64)'
replacement = (
    '    base_rows = list(cleaned[3])\n'
    '    cleaned = [list(base_rows) for _ in METHODS]\n'
    '    maxn = max(1, len(base_rows))\n'
    + needle
)
if needle not in s:
    raise RuntimeError('signal array needle not found')
s = s.replace(needle, replacement, 1)

needle2 = '@njit(cache=True)\ndef process_ticks'
funcs = '''@njit(cache=True)
def allow_add(cidx, direction, open_n, buy_n, sell_n, switches, liq, balance):
    if cidx == 0:
        return True
    eq = balance + liq
    net = buy_n - sell_n
    new_net = net + (1 if direction > 0 else -1)
    reducing = abs(new_net) < abs(net)

    # Strict hedge-only guards. When equity falls below X% of ledger balance,
    # only a new order that REDUCES absolute directional exposure may be added.
    if cidx == 1:
        return True if eq >= 0.50 * balance else reducing
    if cidx == 2:
        return True if eq >= 0.55 * balance else reducing
    if cidx == 3:
        return True if eq >= 0.60 * balance else reducing
    if cidx == 4:
        return True if eq >= 0.65 * balance else reducing
    if cidx == 5:
        return True if eq >= 0.70 * balance else reducing
    if cidx == 6:
        return True if eq >= 0.75 * balance else reducing
    if cidx == 7:
        return True if eq >= 0.80 * balance else reducing

    # Conditional exposure caps only activate inside the danger zone.
    if cidx == 8:
        return True if eq >= 0.65 * balance else abs(new_net) <= 4
    if cidx == 9:
        return True if eq >= 0.65 * balance else abs(new_net) <= 3
    if cidx == 10:
        return True if eq >= 0.70 * balance else abs(new_net) <= 3
    if cidx == 11:
        return True if eq >= 0.60 * balance else abs(new_net) <= 3
    return True

@njit(cache=True)
def process_ticks'''
if needle2 not in s:
    raise RuntimeError('process function needle not found')
s = s.replace(needle2, funcs, 1)

# Gate BUY/SELL additions only. Initial Compression entry is unchanged.
buyneedle = """                        else:
                            fill = ask
                            eq = balance[cidx] + liq"""
buyrepl = """                        else:
                            if not allow_add(cidx, 1, open_n[cidx], buy_n[cidx], sell_n[cidx], switches[cidx], liq, balance[cidx]):
                                break
                            fill = ask
                            eq = balance[cidx] + liq"""
sellneedle = """                        else:
                            fill = bid
                            eq = balance[cidx] + liq"""
sellrepl = """                        else:
                            if not allow_add(cidx, -1, open_n[cidx], buy_n[cidx], sell_n[cidx], switches[cidx], liq, balance[cidx]):
                                break
                            fill = bid
                            eq = balance[cidx] + liq"""
if buyneedle not in s:
    raise RuntimeError('buy gate needle not found')
if sellneedle not in s:
    raise RuntimeError('sell gate needle not found')
s = s.replace(buyneedle, buyrepl, 1)
s = s.replace(sellneedle, sellrepl, 1)

out.write_text(s)
print(out)
