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
        self.root.title("内存分析工具 v4.1")
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
        self.process_list = []
        self.all_processes = set()
        self.legend_frame = None
        self.legend_canvas = None
        self.auto_update = tk.BooleanVar(value=True)  # 新增自动更新开关
        self.update_job = None  # 延迟任务ID
        # 创建界面组件
        self.create_widgets()
        self.setup_plots()

    def create_widgets(self):
        """创建界面组件"""
        # 在工具栏添加控件
        toolbar = ttk.Frame(self.root)
        ttk.Button(toolbar, text="打开文件", command=self.load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="导出数据", command=self.export_data).pack(side=tk.LEFT, padx=2)

        # 新增手动更新按钮
        ttk.Button(toolbar, text="更新图表", command=self.safe_update).pack(side=tk.LEFT, padx=10)

        # 新增自动更新开关
        ttk.Checkbutton(
            toolbar,
            text="自动更新",
            variable=self.auto_update,
            command=lambda: messagebox.showinfo("提示", f"自动更新已{'启用' if self.auto_update.get() else '关闭'}")
        ).pack(side=tk.LEFT)

        toolbar.pack(side=tk.TOP, fill=tk.X)

        # 主内容区域
        main_panel = ttk.Frame(self.root)

        # 新增全选按钮
        ttk.Button(toolbar, text="全选", command=self.select_all).pack(side=tk.LEFT, padx=5)

        # 新增全非选按钮
        ttk.Button(toolbar, text="全非选", command=self.select_none).pack(side=tk.LEFT, padx=5)

        # 左侧进程列表
        self.tree_frame = ttk.Frame(main_panel, width=240)
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

        # 中间图表区域
        self.notebook = ttk.Notebook(main_panel)
        self.tab_pss = ttk.Frame(self.notebook)
        self.tab_rss = ttk.Frame(self.notebook)
        self.tab_vss = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_pss, text="PSS图表")
        self.notebook.add(self.tab_rss, text="RSS图表")
        self.notebook.add(self.tab_vss, text="VSS图表")
        self.notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 右侧图例区域（修复后的代码）
        legend_panel = ttk.Frame(main_panel, width=230)
        self.legend_frame = ttk.Frame(legend_panel)

        # 创建Canvas和滚动条
        self.legend_canvas = tk.Canvas(self.legend_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.legend_frame, orient="vertical", command=self.legend_canvas.yview)

        # 创建可滚动框架
        self.scrollable_frame = ttk.Frame(self.legend_canvas)

        # 绑定配置事件
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.legend_canvas.configure(
                scrollregion=self.legend_canvas.bbox("all")
            )
        )

        # 将可滚动框架嵌入Canvas
        self.legend_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="frame")

        # 配置Canvas滚动
        self.legend_canvas.configure(yscrollcommand=scrollbar.set)

        # 绑定鼠标滚轮事件
        self.legend_canvas.bind("<Enter>", lambda _: self.legend_canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.legend_canvas.bind("<Leave>", lambda _: self.legend_canvas.unbind_all("<MouseWheel>"))

        # 打包组件
        scrollbar.pack(side="right", fill="y")
        self.legend_canvas.pack(side="left", fill="both", expand=True)
        self.legend_frame.pack(fill="both", expand=True, padx=5, pady=5)
        legend_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)

        main_panel.pack(fill=tk.BOTH, expand=True)

        # 绑定事件
        self.tree.bind('<Button-1>', self.on_tree_click)

    def _on_mousewheel(self, event):
        """处理鼠标滚轮滚动"""
        self.legend_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def setup_plots(self):
        """初始化图表"""
        self.fig_pss = Figure(figsize=(8, 6), dpi=100)
        self.ax_pss = self.fig_pss.add_subplot(111)
        self.canvas_pss = FigureCanvasTkAgg(self.fig_pss, master=self.tab_pss)
        self.canvas_pss.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.fig_rss = Figure(figsize=(8, 6), dpi=100)
        self.ax_rss = self.fig_rss.add_subplot(111)
        self.canvas_rss = FigureCanvasTkAgg(self.fig_rss, master=self.tab_rss)
        self.canvas_rss.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.fig_vss = Figure(figsize=(8, 6), dpi=100)
        self.ax_vss = self.fig_vss.add_subplot(111)
        self.canvas_vss = FigureCanvasTkAgg(self.fig_vss, master=self.tab_vss)
        self.canvas_vss.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 统一设置图表样式
        for ax in [self.ax_pss, self.ax_rss, self.ax_vss]:
            ax.set_xlabel("时间")
            ax.set_ylabel("内存使用 (MB)")
            ax.grid(True)

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
        """处理复选框点击（优化响应）"""
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        if column == '#1':
            current = self.tree.item(item, 'values')[0]
            new_value = '✓' if current == '' else ''
            self.tree.set(item, column='Visible', value=new_value)

            if self.auto_update.get():
                # 取消之前的延迟任务
                if self.update_job:
                    self.root.after_cancel(self.update_job)
                # 新增500ms延迟更新
                self.update_job = self.root.after(1000, self.safe_update)

    def safe_update(self):
        """安全更新方法（防止重复调用）"""
        if self.update_job:
            self.root.after_cancel(self.update_job)
            self.update_job = None
        self.update_plot()
    def update_plot(self):
        """更新图表和滚动图例"""
        # 在开始前禁用界面交互
        self.root.config(cursor="watch")
        self.root.update()
        try:
            # 清空图表和旧图例
            for ax in [self.ax_pss, self.ax_rss, self.ax_vss]:
                ax.clear()
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            # 获取选中的进程
            selected = [
                self.tree.item(item, 'values')[1]
                for item in self.tree.get_children()
                if self.tree.item(item, 'values')[0] == '✓'
            ]

            # 生成颜色
            colors = plt.cm.tab20(np.linspace(0, 1, len(selected))) if selected else []

            # 绘制图表和生成图例
            for idx, process in enumerate(selected):
                sub_df = self.full_df[self.full_df['process'] == process]
                if not sub_df.empty:
                    times = sub_df['timestamp']
                    color = colors[idx]

                    # 绘制曲线
                    self.ax_pss.plot(times, sub_df['PSS'], color=color, marker='o', linewidth=1,markersize=1)
                    self.ax_rss.plot(times, sub_df['RSS'], color=color, marker='s', linewidth=1,markersize=1)
                    self.ax_vss.plot(times, sub_df['VSS'], color=color, marker='^', linewidth=1,markersize=1)

                    # 生成图例项
                    item_frame = ttk.Frame(self.scrollable_frame)
                    color_block = tk.Label(item_frame,
                                           bg=matplotlib.colors.to_hex(color),
                                           width=4,
                                           height=1,
                                           relief='solid')
                    process_label = ttk.Label(item_frame, text=process[:18], width=20)
                    color_block.pack(side=tk.LEFT, padx=5)
                    process_label.pack(side=tk.LEFT)
                    item_frame.pack(anchor=tk.W, pady=2)

            # 强制更新布局并设置滚动区域
            self.scrollable_frame.update_idletasks()
            self.legend_canvas.configure(scrollregion=self.legend_canvas.bbox("all"))

            # 重置Canvas窗口尺寸
            self.legend_canvas.itemconfig("frame", width=self.legend_canvas.winfo_width())
            # 更新图表格式
            self.ax_pss.set_title("PSS 使用趋势", fontproperties='SimHei', pad=15)
            self.ax_rss.set_title("RSS 使用趋势", fontproperties='SimHei', pad=15)
            self.ax_vss.set_title("VSS 使用趋势", fontproperties='SimHei', pad=15)

            # 调整布局
            for fig in [self.fig_pss, self.fig_rss, self.fig_vss]:
                fig.tight_layout(rect=[0.05, 0.05, 0.95, 0.95])

            self.canvas_pss.draw()
            self.canvas_rss.draw()
            self.canvas_vss.draw()
            self.legend_canvas.configure(scrollregion=self.legend_canvas.bbox("all"))
        finally:
            # 恢复界面交互
            self.root.config(cursor="")
            self.root.update()

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
    
    
    def select_all(self):
        """全选进程"""
    # 将所有进程的显示状态设置为“✓”
        for item in self.tree.get_children():
            self.tree.set(item, column='Visible', value='✓')
    # 检查自动更新是否开启
        if self.auto_update.get():
        # 如果自动更新开启，取消之前的延迟更新任务
            if self.update_job:
                self.root.after_cancel(self.update_job)
        # 设置一个新的延迟更新任务
            self.update_job = self.root.after(500, self.safe_update)

    def select_none(self):
        """全非选进程"""
    # 将所有进程的显示状态设置为空字符串
        for item in self.tree.get_children():
            self.tree.set(item, column='Visible', value='')
    # 检查自动更新是否开启
        if self.auto_update.get():
        # 如果自动更新开启，取消之前的延迟更新任务
            if self.update_job:
                self.root.after_cancel(self.update_job)
        # 设置一个新的延迟更新任务
            self.update_job = self.root.after(500, self.safe_update)


if __name__ == "__main__":
    analyzer = MemoryAnalyzer()
    analyzer.run()