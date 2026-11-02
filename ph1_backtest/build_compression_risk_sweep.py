from pathlib import Path
import re

src = Path('ph1_backtest/entry10_adaptive_sweep.py')
out = Path('/tmp/risk.py')
s = src.read_text()

names = [
    'BASELINE',
    'POSCAP_12',
    'POSCAP_16',
    'NET_EXPOSURE_CAP_2',
    'HEDGE_ONLY_AFTER_8',
    'HEDGE_ONLY_AFTER_SWITCH2',
    'EQUITY_HEDGE_BELOW_65PCT',
    'GAP_X2_AFTER_SWITCH2',
    'GAP_X3_AFTER_SWITCH3',
    'NETCAP2_GAPX2',
    'DANGER_HEDGE_GAPX3',
    'BALANCED_COMBO',
]

s = re.sub(r'METHODS = \[.*?\]\n\n', 'METHODS = ' + repr(names) + '\n\n', s, count=1, flags=re.S)
s = s.replace('TARGET = 10.0', 'TARGET = 20.0\nWITHDRAW = 10.0')
s = s.replace('balance[cidx] -= TARGET', 'balance[cidx] -= WITHDRAW')
s = s.replace('withdrawn[cidx] += TARGET', 'withdrawn[cidx] += WITHDRAW')

# Never realize a losing basket on Friday or at the final Friday boundary.
s = s.replace('if prev_dow == 4:', 'if False and prev_dow == 4:')
s = s.replace('if (last_day + 3) % 7 == 4:', 'if False and (last_day + 3) % 7 == 4:')

# All configs receive the exact same Compression Breakout signals (original index 3).
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
def gap_for_config(cidx, switches):
    g = gap_from_switches(switches)
    if cidx == 7 and switches >= 2:
        return g * 2.0
    if cidx == 8 and switches >= 3:
        return g * 3.0
    if cidx == 9 and switches >= 2:
        return g * 2.0
    if cidx == 10 and switches >= 2:
        return g * 3.0
    if cidx == 11 and switches >= 3:
        return g * 2.0
    return g

@njit(cache=True)
def allow_add(cidx, direction, open_n, buy_n, sell_n, switches, liq, balance):
    net = buy_n - sell_n
    new_net = net + (1 if direction > 0 else -1)
    reducing = abs(new_net) < abs(net)
    eq = balance + liq

    if cidx == 1:
        return open_n < 12
    if cidx == 2:
        return open_n < 16
    if cidx == 3:
        return abs(new_net) <= 2
    if cidx == 4 and open_n >= 8:
        return reducing
    if cidx == 5 and switches >= 2:
        return reducing
    if cidx == 6 and eq < 0.65 * balance:
        return reducing
    if cidx == 9:
        return abs(new_net) <= 2
    if cidx == 10 and (open_n >= 8 or switches >= 2 or eq < 0.75 * balance):
        return reducing
    if cidx == 11:
        if open_n >= 16:
            return False
        if abs(new_net) > 3:
            return False
        if eq < 0.60 * balance and not reducing:
            return False
    return True

@njit(cache=True)
def process_ticks'''
if needle2 not in s:
    raise RuntimeError('process function needle not found')
s = s.replace(needle2, funcs, 1)

s = s.replace('g = gap_from_switches(switches[cidx])', 'g = gap_for_config(cidx, switches[cidx])')

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
