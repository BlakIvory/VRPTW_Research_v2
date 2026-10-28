"""Desktop launcher and visual comparison UI for the VRPTW experiment."""
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

import experiment


ROOT = Path(__file__).resolve().parents[1]


class VRPTWLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('VRPTW Research | Experiment Launcher')
        self.geometry('1180x780')
        self.minsize(820, 560)
        self.configure(bg='#f3f6fb')
        self.data_path = tk.StringVar(value=str(ROOT / 'data' / 'sample.csv'))
        self.vehicles = tk.StringVar(value='6')
        self.capacity = tk.StringVar(value='80')
        self.travel_scale = tk.StringVar(value='3')
        self.seconds = tk.StringVar(value='10')
        self.status = tk.StringVar(value='Chọn dữ liệu và nhấn “Chạy so sánh”.')
        self.progress = None
        self._build_ui()

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background='#f3f6fb')
        style.configure('Card.TFrame', background='white')
        style.configure('TLabel', background='#f3f6fb', foreground='#25324b', font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 21, 'bold'), foreground='#172554')
        style.configure('Sub.TLabel', font=('Segoe UI', 10), foreground='#64748b')
        style.configure('CardTitle.TLabel', background='white', font=('Segoe UI', 11, 'bold'), foreground='#334155')
        style.configure('Treeview', rowheight=30, font=('Segoe UI', 10))
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'), padding=(14, 9))

        # Put the whole dashboard in a vertical scroll area so smaller screens
        # can still reach the route details and chart.
        outer = ttk.Frame(self)
        outer.pack(fill='both', expand=True)
        scroll_canvas = tk.Canvas(outer, bg='#f3f6fb', highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient='vertical', command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        scroll_canvas.pack(side='left', fill='both', expand=True)
        shell = ttk.Frame(scroll_canvas, padding=16)
        shell_window = scroll_canvas.create_window((0, 0), window=shell, anchor='nw')
        shell.bind('<Configure>', lambda _event: scroll_canvas.configure(scrollregion=scroll_canvas.bbox('all')))
        scroll_canvas.bind('<Configure>', lambda event: scroll_canvas.itemconfigure(shell_window, width=event.width))
        scroll_canvas.bind_all('<MouseWheel>', lambda event: scroll_canvas.yview_scroll(int(-event.delta / 120), 'units'))
        header = ttk.Frame(shell)
        header.pack(fill='x', pady=(0, 16))
        ttk.Label(header, text='VRPTW Experiment Launcher', style='Title.TLabel').pack(anchor='w')
        ttk.Label(header, text='Chạy thuật toán và so sánh kết quả trên cùng một bộ dữ liệu.', style='Sub.TLabel').pack(anchor='w', pady=(4, 0))

        config = ttk.Frame(shell, style='Card.TFrame', padding=11)
        config.pack(fill='x', pady=(0, 10))
        ttk.Label(config, text='THIẾT LẬP THÍ NGHIỆM', style='CardTitle.TLabel').grid(row=0, column=0, columnspan=6, sticky='w', pady=(0, 7))
        ttk.Label(config, text='Tệp dữ liệu').grid(row=1, column=0, sticky='w')
        ttk.Entry(config, textvariable=self.data_path).grid(row=2, column=0, columnspan=4, sticky='ew', padx=(0, 8))
        ttk.Button(config, text='Chọn tệp…', command=self._browse).grid(row=2, column=4, sticky='ew')
        labels = [('Số xe (CSV)', self.vehicles), ('Tải trọng', self.capacity), ('Phút / đơn vị', self.travel_scale), ('Giới hạn (giây)', self.seconds)]
        for col, (label, var) in enumerate(labels):
            ttk.Label(config, text=label).grid(row=3, column=col, sticky='w', pady=(7, 2))
            ttk.Entry(config, textvariable=var, width=18).grid(row=4, column=col, sticky='ew', padx=(0, 10))
        self.run_button = ttk.Button(config, text='▶  Chạy so sánh', style='Accent.TButton', command=self._run)
        self.run_button.grid(row=4, column=4, sticky='e', padx=(8, 0))
        self.progress = ttk.Progressbar(config, mode='indeterminate', length=150)
        self.progress.grid(row=5, column=0, columnspan=5, sticky='ew', pady=(8, 0))
        self.progress.grid_remove()
        for col in range(4): config.columnconfigure(col, weight=1)

        metrics = ttk.Frame(shell)
        metrics.pack(fill='x', pady=(0, 14))
        self.metric_distance = self._metric(metrics, 'KHOẢNG CÁCH TỐT NHẤT', '—', 0)
        self.metric_vehicles = self._metric(metrics, 'SỐ XE', '—', 1)
        self.metric_runtime = self._metric(metrics, 'THỜI GIAN CHẠY', '—', 2)
        self.metric_status = self._metric(metrics, 'TRẠNG THÁI', 'Chưa chạy', 3)
        for col in range(4): metrics.columnconfigure(col, weight=1)

        body = ttk.Frame(shell)
        body.pack(fill='both', expand=True)
        left = ttk.Frame(body, style='Card.TFrame', padding=14)
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))
        right = ttk.Frame(body, style='Card.TFrame', padding=14)
        right.pack(side='left', fill='both', expand=True, padx=(8, 0))
        ttk.Label(left, text='SO SÁNH THUẬT TOÁN', style='CardTitle.TLabel').pack(anchor='w', pady=(0, 10))
        cols = ('algorithm', 'status', 'vehicles', 'distance', 'runtime')
        self.table = ttk.Treeview(left, columns=cols, show='headings', height=7)
        for key, title, width in [('algorithm','Thuật toán',125),('status','Trạng thái',100),('vehicles','Số xe',65),('distance','Khoảng cách',105),('runtime','Thời gian (s)',105)]:
            self.table.heading(key, text=title)
            self.table.column(key, width=width, anchor='center' if key != 'algorithm' else 'w')
        self.table.pack(fill='x')
        ttk.Label(left, text='CÁC TUYẾN ĐƯỜNG', style='CardTitle.TLabel').pack(anchor='w', pady=(18, 8))
        self.routes = tk.Text(left, height=1, wrap='word', font=('Consolas', 10), bg='#f8fafc', relief='flat', padx=10, pady=8)
        self.routes.pack(fill='x', expand=False)
        ttk.Label(right, text='SƠ ĐỒ TUYẾN ĐƯỜNG', style='CardTitle.TLabel').pack(anchor='w')
        self.canvas = tk.Canvas(right, bg='#f8fafc', highlightthickness=0, height=390)
        self.canvas.pack(fill='both', expand=True, pady=(10, 8))
        ttk.Label(right, text='Mỗi màu biểu diễn một xe; depot là hình vuông.', style='Sub.TLabel').pack(anchor='w')
        ttk.Label(shell, textvariable=self.status, style='Sub.TLabel').pack(anchor='w', pady=(12, 0))

    def _metric(self, parent, title, value, col):
        card = ttk.Frame(parent, style='Card.TFrame', padding=(14, 11))
        card.grid(row=0, column=col, sticky='ew', padx=(0 if col == 0 else 6, 6 if col < 3 else 0))
        ttk.Label(card, text=title, style='Sub.TLabel').pack(anchor='w')
        label = ttk.Label(card, text=value, style='CardTitle.TLabel')
        label.pack(anchor='w', pady=(5, 0))
        return label

    def _browse(self):
        path = filedialog.askopenfilename(title='Chọn dữ liệu VRPTW', initialdir=str(ROOT / 'data'), filetypes=[('Dữ liệu VRPTW', '*.csv *.txt'), ('Tất cả tệp', '*.*')])
        if path: self.data_path.set(path)

    def _run(self):
        try:
            values = (int(self.vehicles.get()), int(self.capacity.get()), float(self.travel_scale.get()), int(self.seconds.get()))
            if values[0] < 1 or values[1] < 1 or values[2] <= 0 or values[3] < 1: raise ValueError
            if not Path(self.data_path.get()).is_file(): raise FileNotFoundError('Không tìm thấy tệp dữ liệu.')
        except FileNotFoundError as exc:
            messagebox.showerror('Không tìm thấy dữ liệu', str(exc)); return
        except ValueError:
            messagebox.showerror('Thông số không hợp lệ', 'Vui lòng nhập số xe, tải trọng, thời gian dương và hệ số di chuyển lớn hơn 0.'); return
        self.run_button.configure(state='disabled')
        self.status.set('Đang chạy Greedy, Clarke–Wright và OR-Tools…')
        self.run_button.configure(text='⏳ Đang chạy…')
        self.progress.grid()
        self.progress.start(12)
        threading.Thread(target=self._solve, args=values, daemon=True).start()

    def _solve(self, fleet, capacity, travel_scale, seconds):
        try:
            path = Path(self.data_path.get())
            rows, file_fleet, file_capacity = experiment.load(path)
            if path.suffix.lower() != '.csv':
                fleet = file_fleet
                capacity = file_capacity
            distance, travel = experiment.matrices(rows, travel_scale=travel_scale)
            results = {}
            import time
            methods = [('greedy', 'Greedy gần nhất', lambda: experiment.greedy(rows, distance, travel, capacity, fleet)),
                       ('clarke_wright', 'Clarke–Wright Savings', lambda: experiment.clarke_wright(rows, distance, travel, capacity, fleet)),
                       ('ortools', 'OR-Tools Guided Local Search', lambda: experiment.ortools_solver(rows, distance, travel, capacity, fleet, seconds, 42))]
            for name, label, fn in methods:
                self.after(0, self.status.set, f'Đang chạy {label}…')
                start = time.perf_counter()
                try: result = fn()
                except Exception as exc: result = {'status':'error', 'reason':str(exc)}
                result['runtime_seconds'] = round(time.perf_counter()-start, 5)
                results[name] = result
            report = {'dataset':path.name, 'customers':len(rows)-1, 'vehicles_available':fleet, 'capacity':capacity,
                      'travel_scale':travel_scale, 'distance_metric':'Euclidean', 'results':results}
            output = ROOT / 'outputs' / 'launcher' / f'{path.stem}_result.json'
            output.parent.mkdir(parents=True, exist_ok=True)
            import json
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            self.after(0, self._show_results, rows, results, output)
        except Exception as exc:
            self.after(0, self._failed, str(exc))

    def _failed(self, error):
        self._stop_loading()
        self.run_button.configure(state='normal')
        self.run_button.configure(text='▶  Chạy so sánh')
        self.status.set('Không thể chạy thí nghiệm.')
        messagebox.showerror('Lỗi dữ liệu hoặc solver', error)

    def _show_results(self, rows, results, output):
        self._stop_loading()
        self.run_button.configure(state='normal')
        self.run_button.configure(text='▶  Chạy so sánh')
        for item in self.table.get_children(): self.table.delete(item)
        feasible = []
        self.routes.delete('1.0', 'end')
        for name, label in [('greedy','Greedy gần nhất'),('clarke_wright','Clarke–Wright'),('ortools','OR-Tools GLS')]:
            result = results[name]
            dist = result.get('total_distance')
            if result.get('status') == 'feasible': feasible.append((dist, result, name))
            self.table.insert('', 'end', values=(label, self._status_name(result.get('status')), result.get('vehicles_used','—'), f'{dist:.3f}' if dist is not None else '—', f"{result['runtime_seconds']:.4f}"))
            self.routes.insert('end', f"{label}\n")
            for i, route in enumerate(result.get('routes', []), 1):
                self.routes.insert('end', f"  Xe {i}: {' → '.join(map(str, route['route']))}  |  tải {route['load']}  |  {route['distance']:.3f}\n")
            if not result.get('routes'): self.routes.insert('end', f"  {result.get('reason', 'Không có tuyến khả thi')}\n")
            self.routes.insert('end', '\n')
        self.routes.update_idletasks()
        line_count = int(self.routes.index('end-1c').split('.')[0])
        self.routes.configure(height=max(3, line_count))
        if feasible:
            best_dist, best, best_name = min(feasible, key=lambda x:x[0])
            self.metric_distance.configure(text=f'{best_dist:.3f}  ({best_name})')
            self.metric_vehicles.configure(text=str(best.get('vehicles_used','—')))
            self.metric_runtime.configure(text=f"{best['runtime_seconds']:.4f} s")
            self.metric_status.configure(text='Có lời giải khả thi')
            self._draw(rows, best)
        else:
            self.metric_distance.configure(text='—'); self.metric_vehicles.configure(text='—')
            self.metric_runtime.configure(text='—'); self.metric_status.configure(text='Chưa có lời giải')
            self.canvas.delete('all')
        self.status.set(f'Đã lưu kết quả: {output}')

    def _stop_loading(self):
        self.progress.stop()
        self.progress.grid_remove()

    @staticmethod
    def _status_name(status):
        return {'feasible':'Khả thi','not_found':'Không tìm thấy','dependency_missing':'Thiếu OR-Tools','error':'Lỗi'}.get(status, status)

    def _draw(self, rows, result):
        self.canvas.delete('all')
        w, h = max(self.canvas.winfo_width(), 300), max(self.canvas.winfo_height(), 390)
        xs = [r['x'] for r in rows]; ys = [r['y'] for r in rows]
        span_x = max(max(xs)-min(xs), 1); span_y = max(max(ys)-min(ys), 1)
        pad = 36
        points = [(pad+(r['x']-min(xs))/span_x*(w-2*pad), h-pad-(r['y']-min(ys))/span_y*(h-2*pad)) for r in rows]
        colors = ['#2563eb','#e11d48','#16a34a','#9333ea','#ea580c','#0891b2','#ca8a04']
        for idx, route in enumerate(result.get('routes', [])):
            ids = route['route']
            # IDs in the route are customer IDs, map back to row positions.
            lookup = {r['id']:i for i,r in enumerate(rows)}
            coords = [points[lookup[node]] for node in ids if node in lookup]
            color = colors[idx % len(colors)]
            for a, b in zip(coords, coords[1:]):
                self.canvas.create_line(*a, *b, fill=color, width=2, arrow='last')
        for i, (x, y) in enumerate(points):
            depot = rows[i]['id'] == 0
            if depot: self.canvas.create_rectangle(x-6,y-6,x+6,y+6,fill='#0f172a',outline='white')
            else: self.canvas.create_oval(x-4,y-4,x+4,y+4,fill='#475569',outline='white')
            self.canvas.create_text(x+8,y-8,text=str(rows[i]['id']),anchor='w',fill='#334155',font=('Segoe UI',8))


if __name__ == '__main__':
    VRPTWLauncher().mainloop()
