"""Physical invariants and independent analytical BER validation."""
import csv
import os
import unittest
import numpy as np
from core import *


class ModemTests(unittest.TestCase):
    def test_all_symbols_and_padding(self):
        for mode in MODES:
            points, labels = constellation(mode)
            self.assertAlmostEqual(float(np.mean(abs(points) ** 2)), 1)
            for length in (1, 7, 64, 101):
                bits = np.random.RandomState(length).randint(0, 2, length).astype(np.uint8)
                np.testing.assert_array_equal(demodulate(modulate(bits, mode), mode)[:length], bits)
            np.testing.assert_array_equal(demodulate(points, mode), labels.reshape(-1))

    def test_utf8(self):
        text = '你好，通信工程！Hello 🌍'
        self.assertEqual(bits_text(text_bits(text)), text)

    def test_against_theory(self):
        rng = np.random.RandomState(123)
        bits = rng.randint(0, 2, 400000).astype(np.uint8)
        for mode in MODES:
            for db in (2, 6):
                observed = transmit(bits, mode, db, rng)['ber']
                expected = float(theoretical_ber(mode, db))
                tolerance = 6 * np.sqrt(expected * (1 - expected) / len(bits)) + (0.002 if mode == '16QAM' else 0)
                self.assertLess(abs(observed - expected), tolerance)

    def test_adaptive(self):
        thresholds = calibrate()
        self.assertEqual(choose_mode(-5, thresholds), ('BPSK', False))
        self.assertEqual(choose_mode(20, thresholds), ('16QAM', True))
        self.assertEqual(choose_mode(8, thresholds), ('QPSK', True))


def export():
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(output, exist_ok=True)
    rows = sweep()
    with open(os.path.join(output, 'ber.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ebn0_db', 'mode', 'errors', 'bits', 'ber'])
        writer.writerows(rows)
    fig, ax = plt.subplots(figsize=(9, 5))
    grid = np.linspace(0, 14, 200)
    for mode in MODES:
        line, = ax.semilogy(grid, theoretical_ber(mode, grid), label=mode + (' approximate theory' if mode == '16QAM' else ' theory'))
        selected = [r for r in rows if r[1] == mode]
        for zero, marker in ((False, 'o'), (True, 'v')):
            subset = [r for r in selected if (r[2] == 0) == zero]
            ax.semilogy([r[0] for r in subset], [3 / r[3] if zero else r[4] for r in subset], marker, color=line.get_color(), fillstyle='none' if zero else 'full')
    ax.set(xlabel='Eb/N0 (dB)', ylabel='Bit error rate', ylim=(1e-6, 1), title='AWGN simulation | 100,000 bits/point | seed 42\nv: zero errors, approximate 95% upper bound 3/N')
    ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
    fig.savefig(os.path.join(output, 'ber_curve.png'), dpi=160)
    print('Exported results/ber.csv and results/ber_curve.png')


if __name__ == '__main__':
    import sys
    if '--export' in sys.argv:
        export()
    else:
        unittest.main()
