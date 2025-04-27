import re
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
# 在文件最顶部的导入区域添加
import numpy as np

# 配置中文字体（需要系统支持）
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False   # 解决负号显示问题


class MemoryAnalyzer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("内存分析工具 v4.0")
        self.root.geometry("1400x900")

        # 初始化数据结构
        self.df = pd.DataFrame()
        self.process_list = []
        self.all_processes = set()

        # 创建界面组件
        self.create_widgets()
        self.setup_plots()

    def create_widgets(self):
        """创建界面组件"""
        # 工具栏
        toolbar = ttk.Frame(self.root)
        ttk.Button(toolbar, text="打开文件", command=self.load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="导出数据", command=self.export_data).pack(side=tk.LEFT, padx=2)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # 主内容区域
        self.notebook = ttk.Notebook(self.root)

        # 创建三个标签页
        self.tab_pss = ttk.Frame(self.notebook)
        self.tab_rss = ttk.Frame(self.notebook)
        self.tab_vss = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_pss, text="PSS图表")
        self.notebook.add(self.tab_rss, text="RSS图表")
        self.notebook.add(self.tab_vss, text="VSS图表")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 进程选择列表
        self.tree_frame = ttk.Frame(self.root, width=250)
        self.tree = ttk.Treeview(self.tree_frame, columns=('Visible', 'Process'), show='headings', height=30)
        self.tree.heading('Visible', text='显示')
        self.tree.heading('Process', text='进程名称')
        self.tree.column('Visible', width=60, anchor=tk.CENTER)
        self.tree.column('Process', width=180)

        vsb = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        # 绑定事件
        self.tree.bind('<Button-1>', self.on_tree_click)

    def setup_plots(self):
        """初始化图表（改进图例位置）"""
        # 创建三个独立的图表
        self.fig_pss = Figure(figsize=(10, 6), dpi=100)
        self.ax_pss = self.fig_pss.add_subplot(111)
        self.canvas_pss = FigureCanvasTkAgg(self.fig_pss, master=self.tab_pss)
        self.canvas_pss.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.fig_rss = Figure(figsize=(10, 6), dpi=100)
        self.ax_rss = self.fig_rss.add_subplot(111)
        self.canvas_rss = FigureCanvasTkAgg(self.fig_rss, master=self.tab_rss)
        self.canvas_rss.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.fig_vss = Figure(figsize=(10, 6), dpi=100)
        self.ax_vss = self.fig_vss.add_subplot(111)
        self.canvas_vss = FigureCanvasTkAgg(self.fig_vss, master=self.tab_vss)
        self.canvas_vss.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 统一设置图表样式
        for ax in [self.ax_pss, self.ax_rss, self.ax_vss]:
            ax.set_xlabel("时间", fontproperties='SimHei')
            ax.set_ylabel("内存使用 (MB)", fontproperties='SimHei')
            ax.grid(True)
            # 设置图例框样式
            ax.legend(
                loc='center left',
                bbox_to_anchor=(1.02, 0.5),  # 精确控制右侧位置
                prop={'family': 'SimHei', 'size': 10},
                frameon=False,
                title='进程列表',
                title_fontproperties='SimHei'
            )

    def parse_data(self, data):
        """解析内存数据"""
        records = []
        time_pattern = re.compile(r"统计时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
        table_start_pattern = re.compile(r"PROCESS\s+PSS\(MB\)\s+RSS\(MB\)\s+VSS\(MB\)")
        process_pattern = re.compile(r"^(\S+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)")

        current_time = None
        in_table = False

        for line in data.split('\n'):
            # 匹配时间戳
            if time_match := time_pattern.match(line):
                current_time = datetime.strptime(time_match.group(1), "%Y-%m-%d %H:%M:%S")
                in_table = False
                continue

            # 匹配表格开始
            if table_start_pattern.search(line):
                in_table = True
                continue

            if in_table and current_time:
                # 结束表格的条件
                if line.startswith('---') or 'TOTAL' in line:
                    in_table = False
                    continue

                # 处理进程数据
                if process_match := process_pattern.match(line.strip()):
                    process = process_match.group(1).strip()
                    records.append({
                        'timestamp': current_time,
                        'process': process,
                        'PSS': float(process_match.group(2)),
                        'RSS': float(process_match.group(3)),
                        'VSS': float(process_match.group(4))
                    })
                    self.all_processes.add(process)

        return pd.DataFrame(records)

    def prepare_data(self):
        """预处理数据"""
        # 合并重复项
        self.df = self.df.groupby(['timestamp', 'process']).last().reset_index()

        # 创建完整的时间-进程矩阵
        time_list = self.df['timestamp'].unique()
        all_processes = self.df['process'].unique().tolist()

        index = pd.MultiIndex.from_product(
            [time_list, all_processes],
            names=['timestamp', 'process']
        )

        self.full_df = (
            self.df.set_index(['timestamp', 'process'])
            .reindex(index, fill_value=0)
            .reset_index()
        )

    def load_file(self):
        """加载数据文件"""
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = f.read()

            self.df = self.parse_data(data)
            if self.df.empty:
                messagebox.showerror("错误", "无法解析文件内容")
                return

            self.prepare_data()
            self.update_process_list()
            self.update_plot()

        except Exception as e:
            messagebox.showerror("错误", f"文件读取失败: {str(e)}")

    def update_process_list(self):
        """更新进程列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.process_list = sorted(self.all_processes)
        for process in self.process_list:
            self.tree.insert('', 'end', values=('✓', process), tags=('visible',))

    def on_tree_click(self, event):
        """处理复选框点击"""
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        if column == '#1':
            current = self.tree.item(item, 'values')[0]
            new_value = '✓' if current == '' else ''
            self.tree.set(item, column='Visible', value=new_value)
            self.update_plot()

    def update_plot(self):
        """更新图表（改进图例生成方式）"""
        # 清空所有图表
        for ax in [self.ax_pss, self.ax_rss, self.ax_vss]:
            ax.clear()

        # 获取选中的进程
        selected = [
            self.tree.item(item, 'values')[1]
            for item in self.tree.get_children()
            if self.tree.item(item, 'values')[0] == '✓'
        ]

        # 为每个进程生成唯一颜色
        colors = plt.cm.tab20(np.linspace(0, 1, len(selected)))

        # 绘制新数据
        for idx, process in enumerate(selected):
            sub_df = self.full_df[self.full_df['process'] == process]
            if not sub_df.empty:
                times = sub_df['timestamp']
                # PSS图表
                self.ax_pss.plot(
                    times, sub_df['PSS'],
                    label=process,
                    color=colors[idx],
                    marker='o',
                    linewidth=2
                )
                # RSS图表
                self.ax_rss.plot(
                    times, sub_df['RSS'],
                    label=process,
                    color=colors[idx],
                    marker='s',
                    linewidth=2
                )
                # VSS图表
                self.ax_vss.plot(
                    times, sub_df['VSS'],
                    label=process,
                    color=colors[idx],
                    marker='^',
                    linewidth=2
                )

        # 设置图表标题（添加字体配置）
        self.ax_pss.set_title("PSS 使用趋势", fontproperties='SimHei', pad=20)
        self.ax_rss.set_title("RSS 使用趋势", fontproperties='SimHei', pad=20)
        self.ax_vss.set_title("VSS 使用趋势", fontproperties='SimHei', pad=20)

        # 强制生成图例
        for ax in [self.ax_pss, self.ax_rss, self.ax_vss]:
            ax.legend(
                loc='center left',
                bbox_to_anchor=(1.02, 0.5),
                prop={'family': 'SimHei', 'size': 10},
                frameon=False,
                title='进程列表',
                title_fontproperties='SimHei'
            )

        # 调整布局
        for fig in [self.fig_pss, self.fig_rss, self.fig_vss]:
            fig.subplots_adjust(
                right=0.78,  # 为右侧图例留出空间
                top=0.92  # 为标题留出空间
            )

        self.canvas_pss.draw()
        self.canvas_rss.draw()
        self.canvas_vss.draw()

    def export_data(self):
        """导出数据"""
        if self.full_df.empty:
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
                self.full_df.to_excel(filepath, index=False)
            else:
                self.full_df.to_csv(filepath, index=False)

            messagebox.showinfo("成功", f"数据已导出到：\n{filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    analyzer = MemoryAnalyzer()
    analyzer.run()