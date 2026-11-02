from pathlib import Path
import re

src = Path('ph1_backtest/ph1_remote_backtest.py')
out = Path('/tmp/h1_compression.py')
s = src.read_text()

# Keep the exact old stateful completed-H1 breakout/re-arm engine, but replace
# basket management with the current Compression adaptive grid and 65% guard.
s = s.replace('TARGET = 10.0', 'TARGET = 20.0\nWITHDRAW = 10.0')

configs = '''CONFIGS = [
    ("H1_COMPRESSION_BASELINE", 1, 0, 0, 0, 1, 1),
    ("H1_COMPRESSION_EQ65",     1, 0, 0, 0, 1, 1),
]
'''
s = re.sub(r'CONFIGS = \[.*?\]\n\n', configs + '\n', s, count=1, flags=re.S)

# Never realize a losing basket solely because it is Friday / dataset end.
s = s.replace('if prev_dow == 4:', 'if False and prev_dow == 4:')
s = s.replace('if (last_day + 3) % 7 == 4:', 'if False and (last_day + 3) % 7 == 4:')

# No NEW Friday/weekend baskets, same as the Compression never-loss system.
s = s.replace('if fm == 1 and dow == 4:', 'if fm == 1 and dow >= 4:')

# Daily target is +$20, but withdraw exactly $10 and retain the rest.
s = s.replace('balance[c] -= TARGET\n                        withdrawn[c] += TARGET',
              'balance[c] -= WITHDRAW\n                        withdrawn[c] += WITHDRAW')
s = s.replace('balance[c] -= TARGET; withdrawn[c] += TARGET',
              'balance[c] -= WITHDRAW; withdrawn[c] += WITHDRAW')

# Match the existing 2026 comparison window: through 2026-10-29 UTC only.
needle = "good = t.notna() & df['Bid'].notna() & df['Ask'].notna()\n                        if not bool(good.all()):"
repl = "good = t.notna() & df['Bid'].notna() & df['Ask'].notna()\n                        if year == 2026 and month == 10:\n                            good = good & (t <= pd.Timestamp('2026-10-29 23:59:59.999999999', tz='UTC'))\n                        if not bool(good.all()):"
if needle not in s:
    raise RuntimeError('2026 cutoff insertion needle not found')
s = s.replace(needle, repl, 1)

# Insert Compression spacing and guard helpers before process_chunk.
needle2 = '@njit(cache=True)\ndef process_chunk'
helpers = '''@njit(cache=True)
def compression_gap(switches):
    # 10,30,60,100,150,210... normalized pips => $1,$3,$6,$10,$15,$21... XAU moves.
    n = switches + 1
    return float(n * (n + 1)) / 2.0


@njit(cache=True)
def allow_compression_add(cidx, direction, open_n, buy_n, sell_n, switches, liq, balance):
    # Config 0 is pure H1+Compression baseline.
    # Config 1 adds the exact 65% equity guard: in danger, only orders that
    # reduce absolute BUY/SELL net exposure may be added. No loss is closed.
    if cidx != 1:
        return True
    eq = balance + liq
    if eq >= 0.65 * balance:
        return True
    net = buy_n - sell_n
    new_net = net + (1 if direction > 0 else -1)
    return abs(new_net) < abs(net)


@njit(cache=True)
def process_chunk'''
if needle2 not in s:
    raise RuntimeError('process_chunk needle not found')
s = s.replace(needle2, helpers, 1)

# On first H1 breakout initialize Compression adaptive outer levels.
old_init = '''                            max_pos_lvl[c] = 0; min_neg_lvl[c] = 0
                            danger_on[c] = 0; pos_gap_idx[c] = 0; neg_gap_idx[c] = 0; pos_conf[c] = 0; neg_conf[c] = 0
                            day_activity[c] = 1; armed[c] = 0'''
new_init = '''                            # Repurpose pos_gap_idx as last_side (+1/-1), neg_gap_idx as side-switch count.
                            max_pos_lvl[c] = 0; min_neg_lvl[c] = 0
                            danger_on[c] = 0; pos_conf[c] = 0; neg_conf[c] = 0
                            pos_gap_idx[c] = direction
                            neg_gap_idx[c] = 0
                            g0 = compression_gap(0)
                            next_pos_px[c] = fill + g0
                            next_neg_px[c] = fill - g0
                            day_activity[c] = 1; armed[c] = 0'''
if old_init not in s:
    raise RuntimeError('entry init needle not found')
s = s.replace(old_init, new_init, 1)

start = s.index('            # Grid / whipsaw defence.')
end = s.index('            # Account risk metrics and failure check.', start)
new_grid = '''            # Current Compression adaptive grid, unchanged apart from H1 entry source.
            if open_n[c] > 0 and failed[c] == 0:
                for _ in range(12):
                    acted = 0
                    switches = neg_gap_idx[c]
                    old_g = compression_gap(switches)
                    last_side = pos_gap_idx[c]

                    if bid >= next_pos_px[c]:
                        liq = buy_n[c] * bid - buy_sum[c] + sell_sum[c] - sell_n[c] * ask - open_n[c] * COMMISSION
                        if liq > 0.0:
                            balance[c] += liq; day_realized[c] += liq
                            open_n[c] = 0; buy_n[c] = 0; sell_n[c] = 0; buy_sum[c] = 0.0; sell_sum[c] = 0.0
                            pos_gap_idx[c] = 0; neg_gap_idx[c] = 0; armed[c] = 0
                        else:
                            if not allow_compression_add(c, 1, open_n[c], buy_n[c], sell_n[c], switches, liq, balance[c]):
                                break
                            old_dn_outer = next_neg_px[c] + old_g
                            fill = ask
                            eq = balance[c] + liq
                            margin = open_n[c] * ((bid + ask) * 0.5) / LEVERAGE
                            req = fill / LEVERAGE
                            if eq - margin < req:
                                failed[c] = 1; failure_day[c] = day
                            else:
                                if last_side == -1:
                                    switches += 1
                                pos_gap_idx[c] = 1
                                neg_gap_idx[c] = switches
                                buy_n[c] += 1; buy_sum[c] += fill; open_n[c] += 1
                                new_up_outer = next_pos_px[c]
                                g = compression_gap(switches)
                                next_pos_px[c] = new_up_outer + g
                                next_neg_px[c] = old_dn_outer - g
                        acted = 1

                    elif bid <= next_neg_px[c]:
                        liq = buy_n[c] * bid - buy_sum[c] + sell_sum[c] - sell_n[c] * ask - open_n[c] * COMMISSION
                        if liq > 0.0:
                            balance[c] += liq; day_realized[c] += liq
                            open_n[c] = 0; buy_n[c] = 0; sell_n[c] = 0; buy_sum[c] = 0.0; sell_sum[c] = 0.0
                            pos_gap_idx[c] = 0; neg_gap_idx[c] = 0; armed[c] = 0
                        else:
                            if not allow_compression_add(c, -1, open_n[c], buy_n[c], sell_n[c], switches, liq, balance[c]):
                                break
                            old_up_outer = next_pos_px[c] - old_g
                            fill = bid
                            eq = balance[c] + liq
                            margin = open_n[c] * ((bid + ask) * 0.5) / LEVERAGE
                            req = fill / LEVERAGE
                            if eq - margin < req:
                                failed[c] = 1; failure_day[c] = day
                            else:
                                if last_side == 1:
                                    switches += 1
                                pos_gap_idx[c] = -1
                                neg_gap_idx[c] = switches
                                sell_n[c] += 1; sell_sum[c] += fill; open_n[c] += 1
                                new_dn_outer = next_neg_px[c]
                                g = compression_gap(switches)
                                next_pos_px[c] = old_up_outer + g
                                next_neg_px[c] = new_dn_outer - g
                        acted = 1

                    if acted == 0 or open_n[c] == 0 or failed[c] != 0:
                        break

                # Basket can close positive before +$20; once realized+floating reaches +$20,
                # close all, withdraw exactly $10, retain the rest, and stop for the UTC day.
                if open_n[c] == 0 and stopped_today[c] == 0 and day_realized[c] >= TARGET:
                    day_target[c] = 1; stopped_today[c] = 1; armed[c] = 0
                    if withdraw_mode[c] != 0:
                        balance[c] -= WITHDRAW; withdrawn[c] += WITHDRAW

'''
s = s[:start] + new_grid + s[end:]

# When tick-by-tick daily +$20 target closes an open basket, reset Compression side state too.
old_target_reset = '''                    danger_on[c] = 0; pos_conf[c] = 0; neg_conf[c] = 0; armed[c] = 0
                    day_target[c] = 1'''
new_target_reset = '''                    danger_on[c] = 0; pos_conf[c] = 0; neg_conf[c] = 0; armed[c] = 0
                    pos_gap_idx[c] = 0; neg_gap_idx[c] = 0
                    day_target[c] = 1'''
if old_target_reset not in s:
    raise RuntimeError('target reset needle not found')
s = s.replace(old_target_reset, new_target_reset, 1)

# Make provenance/rules explicit in output log.
s = s.replace("run_period(args.year,months,args.outdir)", "print('RULESET: exact completed-H1 High/Low breakout + Compression 1,3,6,10,15,21... + T20/W10 + never-loss-close + optional 65% equity hedge guard', flush=True)\n    run_period(args.year,months,args.outdir)")

out.write_text(s)
print(out)
