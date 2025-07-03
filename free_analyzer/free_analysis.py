import re
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
import pandas as pd
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

# 配置中文字体（需要系统支持）
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


class FreeMemoryAnalyzer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Free 内存分析工具 v1.0")
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        init_width = min(int(screen_width * 0.9), 1400)  # 最大不超过1400
        init_height = min(int(screen_height * 0.8), 900)  # 最大不超过900
        # 计算窗口左上角位置，使其居中显示
        x_position = (screen_width - init_width) // 2
        y_position = (screen_height - init_height) // 2

        # 设置窗口大小和位置
        self.root.geometry(f"{init_width}x{init_height}+{x_position}+{y_position}")
        # 设置最小窗口尺寸
        self.root.minsize(800, 600)

        # 初始化数据结构
        self.df = pd.DataFrame()
        self.auto_update = tk.BooleanVar(value=True)  # 自动更新开关
        self.update_job = None  # 延迟任务ID
        # 创建界面组件
        self.create_widgets()
        self.setup_plots()

    def create_widgets(self):
        """创建界面组件"""
        # 工具栏
        toolbar = ttk.Frame(self.root)
        ttk.Button(toolbar, text="打开文件", command=self.load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="导出数据", command=self.export_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="更新图表", command=self.safe_update).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(
            toolbar,
            text="自动更新",
            variable=self.auto_update,
            command=lambda: messagebox.showinfo("提示", f"自动更新已{'启用' if self.auto_update.get() else '关闭'}")
        ).pack(side=tk.LEFT)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # 主内容区域
        main_panel = ttk.Frame(self.root)

        # 标签页
        self.notebook = ttk.Notebook(main_panel)
        self.tab_mem = ttk.Frame(self.notebook)
        self.tab_swap = ttk.Frame(self.notebook)
        self.tab_combined = ttk.Frame(self.notebook)  # 新增整合图表标签页

        self.notebook.add(self.tab_mem, text="内存图表")
        self.notebook.add(self.tab_swap, text="交换空间图表")
        self.notebook.add(self.tab_combined, text="整合图表")  # 添加新标签页
        self.notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main_panel.pack(fill=tk.BOTH, expand=True)

    def setup_plots(self):
        """初始化图表"""
        # 内存图表
        self.fig_mem = Figure(figsize=(8, 6), dpi=100)
        self.ax_mem = self.fig_mem.add_subplot(111)
        self.canvas_mem = FigureCanvasTkAgg(self.fig_mem, master=self.tab_mem)
        self.canvas_mem.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 交换空间图表
        self.fig_swap = Figure(figsize=(8, 6), dpi=100)
        self.ax_swap = self.fig_swap.add_subplot(111)
        self.canvas_swap = FigureCanvasTkAgg(self.fig_swap, master=self.tab_swap)
        self.canvas_swap.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 整合图表
        self.fig_combined = Figure(figsize=(8, 6), dpi=100)
        self.ax_combined = self.fig_combined.add_subplot(111)
        self.canvas_combined = FigureCanvasTkAgg(self.fig_combined, master=self.tab_combined)
        self.canvas_combined.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 统一设置图表样式
        for ax in [self.ax_mem, self.ax_swap, self.ax_combined]:
            ax.set_xlabel("时间")
            ax.set_ylabel("内存使用 (KB)")
            ax.grid(True)

    def parse_data(self, data):
        """解析 free 内存数据"""
        records = []
        time_pattern = re.compile(r"统计时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
        mem_pattern = re.compile(r"Mem:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)")
        swap_pattern = re.compile(r"Swap:\s+(\d+)\s+(\d+)\s+(\d+)")

        # 记录文件读取时间作为默认时间戳
        read_time = datetime.now()
        current_time = None
        data_block = 0  # 数据块计数器
        has_explicit_time = False  # 是否有显式时间戳

        for line in data.split('\n'):
            # 匹配时间戳
            if time_match := time_pattern.match(line):
                current_time = datetime.strptime(time_match.group(1), "%Y-%m-%d %H:%M:%S")
                has_explicit_time = True
                continue

            # 匹配内存数据
            if mem_match := mem_pattern.match(line):
                # 如果没有显式时间戳，则使用读取时间并递增数据块计数
                if not current_time:
                    data_block += 1
                    # 使用读取时间加上一个小的增量（秒级）作为相对时间
                    current_time = read_time + timedelta(seconds=data_block)

                records.append({
                    'timestamp': current_time,
                    'type': 'Mem',
                    'total': int(mem_match.group(1)),
                    'used': int(mem_match.group(2)),
                    'free': int(mem_match.group(3)),
                    'shared': int(mem_match.group(4)),
                    'buff/cache': int(mem_match.group(5)),
                    'available': int(mem_match.group(6))
                })
                # 重置时间戳，以便为下一个数据块生成新的相对时间
                if not has_explicit_time:
                    current_time = None

            # 匹配交换空间数据
            if swap_match := swap_pattern.match(line):
                # 如果没有显式时间戳，则使用读取时间并递增数据块计数
                if not current_time:
                    data_block += 1
                    # 使用读取时间加上一个小的增量（秒级）作为相对时间
                    current_time = read_time + timedelta(seconds=data_block)

                records.append({
                    'timestamp': current_time,
                    'type': 'Swap',
                    'total': int(swap_match.group(1)),
                    'used': int(swap_match.group(2)),
                    'free': int(swap_match.group(3))
                })
                # 重置时间戳，以便为下一个数据块生成新的相对时间
                if not has_explicit_time:
                    current_time = None

        # 为所有记录添加索引列，用于显示相对位置
        for i, record in enumerate(records):
            record['index'] = i

        return pd.DataFrame(records)

    def load_file(self):
        """加载数据文件"""
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not filepath:
            return

        try:
            print(f"正在加载文件: {filepath}")
            with open(filepath, 'r', encoding='utf-8') as f:
                data = f.read()
                print(f"文件内容长度: {len(data)} 字节")

            self.df = self.parse_data(data)
            print(f"解析后的数据行数: {len(self.df)}")
            if not self.df.empty:
                print("数据示例:")
                for i, record in enumerate(self.df.head().to_dict(orient='records')):
                    print(
                        f"记录 {i + 1}: 时间={record['timestamp']}, 类型={record['type']}, 已使用={record.get('used', 'N/A')}")

            if self.df.empty:
                messagebox.showerror("错误", "无法解析文件内容")
                return

            self.update_plot()

        except Exception as e:
            messagebox.showerror("错误", f"文件读取失败: {str(e)}")

    def safe_update(self):
        """安全更新方法（防止重复调用）"""
        if self.update_job:
            self.root.after_cancel(self.update_job)
            self.update_job = None
        self.update_plot()

    def update_plot(self):
        """更新图表"""
        print("开始更新图表...")
        self.root.config(cursor="watch")
        self.root.update()
        try:
            # 清空图表
            self.ax_mem.clear()
            self.ax_swap.clear()
            self.ax_combined.clear()

            # 绘制内存图表（保持原有样式）
            mem_df = self.df[self.df['type'] == 'Mem']
            print(f"内存数据行数: {len(mem_df)}")
            if not mem_df.empty:
                times = mem_df['timestamp']
                print(f"时间范围: {times.min()} 到 {times.max()}")

                # 如果时间都是相同的（可能是没有时间戳），则使用数据索引作为x轴
                if len(times.unique()) <= 1:
                    print("警告：检测到时间戳相同或缺失，将使用数据索引作为x轴")
                    self.ax_mem.plot(mem_df['index'], mem_df['used'], label='已使用', marker='o', linewidth=1,
                                     markersize=1)
                    self.ax_mem.plot(mem_df['index'], mem_df['free'], label='空闲', marker='s', linewidth=1,
                                     markersize=1)
                    self.ax_mem.plot(mem_df['index'], mem_df['available'], label='可用', marker='^', linewidth=1,
                                     markersize=1)
                    self.ax_mem.set_xlabel("数据索引")
                else:
                    self.ax_mem.plot(times, mem_df['used'], label='已使用', marker='o', linewidth=1, markersize=1)
                    self.ax_mem.plot(times, mem_df['free'], label='空闲', marker='s', linewidth=1, markersize=1)
                    self.ax_mem.plot(times, mem_df['available'], label='可用', marker='^', linewidth=1, markersize=1)
                    self.ax_mem.set_xlabel("时间")

                self.ax_mem.set_title("内存使用趋势", fontproperties='SimHei', pad=15)
                self.ax_mem.legend()
                print("内存图表绘制完成")

            # 绘制交换空间图表（保持原有样式）
            swap_df = self.df[self.df['type'] == 'Swap']
            print(f"交换空间数据行数: {len(swap_df)}")
            if not swap_df.empty:
                times = swap_df['timestamp']

                # 如果时间都是相同的（可能是没有时间戳），则使用数据索引作为x轴
                if len(times.unique()) <= 1:
                    self.ax_swap.plot(swap_df['index'], swap_df['used'], label='已使用', marker='o', linewidth=1,
                                      markersize=1)
                    self.ax_swap.plot(swap_df['index'], swap_df['free'], label='空闲', marker='s', linewidth=1,
                                      markersize=1)
                    self.ax_swap.set_xlabel("数据索引")
                else:
                    self.ax_swap.plot(times, swap_df['used'], label='已使用', marker='o', linewidth=1, markersize=1)
                    self.ax_swap.plot(times, swap_df['free'], label='空闲', marker='s', linewidth=1, markersize=1)
                    self.ax_swap.set_xlabel("时间")

                self.ax_swap.set_title("交换空间使用趋势", fontproperties='SimHei', pad=15)
                self.ax_swap.legend()
                print("交换空间图表绘制完成")

            # 绘制整合图表（修改为使用同一个坐标轴）
            if not mem_df.empty and not swap_df.empty:
                times = mem_df['timestamp'] if len(times.unique()) > 1 else mem_df['index']

                # 使用同一个坐标轴绘制所有数据
                # 内存使用情况 - 使用蓝色系
                self.ax_combined.plot(times, mem_df['used'], 'b-', label='内存已使用', linewidth=1.5)
                self.ax_combined.plot(times, mem_df['free'], 'c-', label='内存空闲', linewidth=1.5)

                # 交换空间使用情况 - 使用红色系

                self.ax_combined.plot(times, swap_df['used'], 'r-', label='交换空间已使用',
                                      linewidth=1.5)
                self.ax_combined.plot(times, swap_df['free'], 'm-', label='交换空间空闲',
                                      linewidth=1.5)

                # 设置标题和标签
                self.ax_combined.set_title("内存与交换空间使用趋势对比", fontproperties='SimHei', pad=15)
                self.ax_combined.set_xlabel("时间" if len(times.unique()) > 1 else "数据索引")
                self.ax_combined.set_ylabel("内存使用 (KB)")

                # 添加图例
                self.ax_combined.legend(loc='upper right')

                print("整合图表绘制完成")

            # 调整布局
            for fig in [self.fig_mem, self.fig_swap, self.fig_combined]:
                fig.tight_layout(rect=[0.05, 0.05, 0.95, 0.95])

            self.canvas_mem.draw()
            self.canvas_swap.draw()
            self.canvas_combined.draw()
            print("图表渲染完成")

        finally:
            self.root.config(cursor="")
            self.root.update()

    def export_data(self):
        """导出数据"""
        if self.df.empty:
            messagebox.showwarning("警告", "没有可导出的数据")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")]
        )

        if not filepath:
            return

        try:
            if filepath.endswith('.xlsx'):
                self.df.to_excel(filepath, index=False)
            else:
                self.df.to_csv(filepath, index=False)

            messagebox.showinfo("成功", f"数据已导出到：\n{filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    analyzer = FreeMemoryAnalyzer()
    analyzer.run()