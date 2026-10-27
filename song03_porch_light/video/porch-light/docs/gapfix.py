"""Breath-gap constrained lyric windows (Porch Light, 2026-10-18).
The forced aligner squeezes the next line into a long held note (2:21-2:25 "gone" held, "But I leave" placed
inside it). Rule: a line starts after the first breath gap in the vocal that follows the previous line's
last-word onset. Gaps = 20 ms vocal RMS at least 10 dB under the 1.5 s phrase level for >= 60 ms.
Writes docs/lyrics.txt windows [gap end - 0.08, next line's gap start + 0.1]; run align.py after; iterate.
usage: python docs/gapfix.py  (from the film folder)"""
import json, numpy as np, soundfile as sf
from scipy.ndimage import maximum_filter1d, uniform_filter1d

x, sr = sf.read('audio/stems/vocals.wav', always_2d=True); x = x.mean(1)
hop = int(0.02 * sr); n = len(x) // hop
v = 10 * np.log10(uniform_filter1d((x[:n * hop].reshape(n, hop) ** 2).mean(1), 2) + 1e-12)
lvl = maximum_filter1d(v, int(1.5 / 0.02))
dip = (v < lvl - 10) | (v < -45)
gaps = []; i = 0
while i < n:
    if dip[i]:
        j = i
        while j < n and dip[j]: j += 1
        if j - i >= 3: gaps.append((i * 0.02, j * 0.02))
        i = j
    else: i += 1

L = json.load(open('lyrics.json'))['lines']
sheet = [l for l in open('docs/lyrics.txt', encoding='utf8').read().splitlines() if l and not l.startswith('#')]
secs = [l.split()[3] for l in sheet if l.startswith('@')]; texts = [l for l in sheet if not l.startswith('@')]
assert len(texts) == len(L) == len(secs)

def gap_after(t):
    for a, b in gaps:
        if b > t: return (max(a, t), b)
    return (t, t)

starts = [];
for k, l in enumerate(L):
    if k == 0: starts.append(max(0.0, l['words'][0]['t0'] - 0.4)); continue
    last_on = L[k - 1]['words'][-1]['t0']
    g0, g1 = gap_after(last_on + 0.25)
    starts.append(max(g1 - 0.08, last_on + 0.25))
ends = [starts[k + 1] + 0.1 if k + 1 < len(L) else L[-1]['words'][-1]['t1'] + 1.0 for k in range(len(L))]
out = ['# breath-gap windows (docs/gapfix.py)']
moved = []
for k, l in enumerate(L):
    out.append(f"@ {starts[k]:.2f} {ends[k]:.2f} {secs[k]}"); out.append(texts[k])
    if l['words'][0]['t0'] < starts[k] - 0.05: moved.append((k, l['text'][:32], round(l['words'][0]['t0'], 2), round(starts[k] + 0.08, 2)))
open('docs/lyrics.txt', 'w', encoding='utf8').write('\n'.join(out) + '\n')
print(f"{len(gaps)} breath gaps; lines starting before their breath gap: {len(moved)}")
for m in moved: print('  ', m)
