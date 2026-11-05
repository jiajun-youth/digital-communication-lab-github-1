"""Run with python main.py. GUI uses only Tkinter, NumPy and Matplotlib."""
import csv
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from core import (MODES, constellation, transmit, text_bits, bits_text,
                  theoretical_ber, calibrate, choose_mode, sweep)


class App:
    def __init__(self, root):
        self.root = root
        root.title('Digital Communication Lab | 数字通信实验室')
        root.geometry('1180x820')
        self.events = queue.Queue()
        controls = ttk.Frame(root, padding=12)
        controls.pack(fill='x')
        ttk.Label(controls, text='发送文字').grid(row=0, column=0)
        self.message = tk.StringVar(value='你好，通信工程！Hello Communication!')
        ttk.Entry(controls, textvariable=self.message, width=65).grid(row=0, column=1, columnspan=5, sticky='ew')
        self.mode = tk.StringVar(value='QPSK')
        ttk.Combobox(controls, textvariable=self.mode, values=MODES + ('Adaptive',), state='readonly', width=12).grid(row=1, column=0, pady=10)
        ttk.Label(controls, text='Eb/N0 (dB)').grid(row=1, column=1)
        self.db = tk.StringVar(value='6')
        ttk.Entry(controls, textvariable=self.db, width=8).grid(row=1, column=2)
        ttk.Label(controls, text='随机种子').grid(row=1, column=3)
        self.seed = tk.StringVar(value='42')
        ttk.Entry(controls, textvariable=self.seed, width=10).grid(row=1, column=4)
        ttk.Button(controls, text='运行链路', command=self.run_link).grid(row=1, column=5, padx=8)
        self.sweep_button = ttk.Button(controls, text='运行误码率实验并导出', command=self.start_sweep)
        self.sweep_button.grid(row=1, column=6)
        self.status = tk.StringVar()
        ttk.Label(root, textvariable=self.status, padding=10, wraplength=1120).pack(fill='x')
        self.figure = Figure(figsize=(11, 6), dpi=100)
        self.axes = self.figure.subplots(2, 2)
        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        self.root.after(100, self.poll)
        self.run_link()

    def run_link(self):
        try:
            db = float(self.db.get())
            seed = int(self.seed.get())
            if not np.isfinite(db) or not -20 <= db <= 40:
                raise ValueError('Eb/N0 请设置在 -20 到 40 dB 之间')
            if not 0 <= seed < 2 ** 32:
                raise ValueError('随机种子应在 0 到 2^32-1 之间')
            text = self.message.get()
            if not text or len(text.encode('utf-8')) > 10000:
                raise ValueError('请输入 1 到 10000 字节的文字')
            rng = np.random.RandomState(seed)
            mode = self.mode.get()
            note = ''
            if mode == 'Adaptive':
                mode, meets = choose_mode(db, calibrate())
                note = ' | 自适应目标 BER≤0.001：' + ('理论预测满足' if meets else '当前信道无法满足，使用 BPSK')
            bits = text_bits(text)
            result = transmit(bits, mode, db, rng)
            sample = transmit(rng.randint(0, 2, 40000).astype(np.uint8), mode, db, rng)
            self.status.set('{} | 文字误码 {}/{}，BER={:.4g} | 随机数据 BER={:.4g}{}\n接收：{}'.format(mode, result['errors'], len(bits), result['ber'], sample['ber'], note, bits_text(result['bits'])))
            a, b, c, d = self.axes.flat
            a.clear(); b.clear()
            a.scatter(sample['rx'][:2500].real, sample['rx'][:2500].imag, s=3, alpha=.25, label='Received')
            points, _ = constellation(mode)
            a.scatter(points.real, points.imag, c='red', marker='x', s=70, label='Ideal')
            a.set(title=mode + ' constellation', xlabel='In-phase', ylabel='Quadrature', xlim=(-2.5, 2.5), ylim=(-2.5, 2.5))
            a.legend(); a.grid(alpha=.2)
            n = min(60, len(bits))
            b.step(range(n), bits[:n], where='mid', label='Sent')
            b.step(range(n), result['bits'][:n] + .06, where='mid', label='Recovered', alpha=.7)
            b.set(title='First bits (received offset for visibility)', xlabel='Bit index', ylim=(-.2, 1.4)); b.legend()
            if not c.lines:
                x = np.linspace(0, 14, 100)
                for m in MODES:
                    c.semilogy(x, theoretical_ber(m, x), label=m + (' approx.' if m == '16QAM' else ' theory'))
                c.set(title='Reference BER', xlabel='Eb/N0 (dB)', ylabel='BER', ylim=(1e-6, 1)); c.legend(); c.grid(alpha=.3)
            d.clear()
            x = np.linspace(0, 14, 100)
            thresholds = calibrate()
            selected = [choose_mode(v, thresholds) for v in x]
            rates = [{'BPSK': 1, 'QPSK': 2, '16QAM': 4}[m] if ok else 0 for m, ok in selected]
            d.step(x, rates, where='post', label='Adaptive (target BER 0.001)')
            d.axvline(db, color='gray', linestyle=':')
            d.set(title='Theoretical eligible spectral efficiency', xlabel='Eb/N0 (dB)', ylabel='Bits / symbol (0 = target unmet)', ylim=(-.2, 4.5)); d.legend(); d.grid(alpha=.2)
            self.figure.tight_layout(); self.canvas.draw()
        except (ValueError, OverflowError) as exc:
            messagebox.showerror('参数错误', str(exc))

    def start_sweep(self):
        self.sweep_button.configure(state='disabled')
        self.status.set('正在实验：3 种调制 × 8 个 Eb/N0，每点 100000 比特……')
        def worker():
            try:
                self.events.put(('done', sweep()))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            kind, data = self.events.get_nowait()
            self.sweep_button.configure(state='normal')
            if kind == 'error':
                messagebox.showerror('实验失败', data)
            else:
                output = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
                os.makedirs(output, exist_ok=True)
                with open(os.path.join(output, 'ber.csv'), 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f); writer.writerow(['ebn0_db', 'mode', 'errors', 'bits', 'ber']); writer.writerows(data)
                ax = self.axes[1, 0]; ax.clear()
                x = np.linspace(0, 14, 150)
                for mode in MODES:
                    line, = ax.semilogy(x, theoretical_ber(mode, x), label=mode + ' theory' + (' approx.' if mode == '16QAM' else ''))
                    rows = [r for r in data if r[1] == mode]
                    positive = [r for r in rows if r[2] > 0]
                    zero = [r for r in rows if r[2] == 0]
                    ax.semilogy([r[0] for r in positive], [r[4] for r in positive], 'o', color=line.get_color())
                    ax.semilogy([r[0] for r in zero], [3.0 / r[3] for r in zero], 'v', fillstyle='none', color=line.get_color())
                ax.set(title='Monte Carlo BER (v: zero errors, ~95% upper bound)', xlabel='Eb/N0 (dB)', ylabel='BER', ylim=(1e-6, 1)); ax.legend(fontsize=8); ax.grid(alpha=.3)
                self.figure.tight_layout(); self.canvas.draw()
                self.figure.savefig(os.path.join(output, 'experiment.png'), dpi=160)
                self.status.set('实验完成，已导出 results/ber.csv 和 experiment.png。空心倒三角代表零误码点的约 95% 上界 3/N。')
        except queue.Empty:
            pass
        except Exception as exc:
            messagebox.showerror('导出失败', str(exc))
        self.root.after(100, self.poll)


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
