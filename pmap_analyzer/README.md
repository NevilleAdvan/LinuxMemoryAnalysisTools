# PMAP内存分析工具

这是一个用于解析和分析pmap命令输出的Python工具。它可以帮助你统计不同内存映射类型的内存使用情况，并以表格形式展示或导出到Excel文件中。


## 功能特点
- 解析pmap命令输出，按内存映射类型和模式统计内存使用
- 支持从文件或标准输入读取pmap数据
- 自动对齐并格式化控制台输出
- 支持将结果导出到Excel文件，便于进一步分析
- 按内存使用量降序排列结果，便于快速识别内存占用大户


## 安装依赖
该工具需要以下Python库：
- `openpyxl`：用于创建和操作Excel文件

你可以使用pip安装这些依赖：
```bash
pip install openpyxl
```
## 使用方法
从标准输入读取 pmap 数据：
```bash
python pmap_analyzer.py
```
执行后，你可以粘贴 pmap 命令的输出，然后按 Ctrl+D(Linux/Mac) 或 Ctrl+Z(Windows) 结束输入。

## 从文件读取
```bash
python pmap_analyzer.py -i pmap_output.txt
```
##导出到 Excel
```bash
python pmap_analyzer.py -i pmap_output.txt -o memory_analysis.xlsx
```

## 完整参数说明
```plaintext
usage: pmap_analyzer.py [-h] [-i INPUT] [-o OUTPUT]

分析pmap输出并统计内存使用情况

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        pmap输入文件
  -o OUTPUT, --output OUTPUT
                        Excel输出文件 (例如: result.xlsx)

```

# 输出格式
## 控制台输出
格式化后的表格会显示在终端中，包含以下字段：

* Mode：内存映射的访问模式（如r-xp, rw-p）
* Mapping：内存映射的名称或路径
* Kbytes：占用的总内存大小（KB）
* PSS：比例集大小（KB）
* Dirty：脏页内存大小（KB）

示例：
```plaintext
Mode    Mapping                      Kbytes   PSS  Dirty
----------------------------------------------------------
rw-p    libc-2.27.so                18432  5220  5220
r--p    libc-2.27.so                 2368   780   780
r-xp    libc-2.27.so                16896   560   560
rw-p    [heap]                       8192  3240  3240

```

# Excel 输出
Excel 文件包含相同的数据，并具有以下特点：

* 表头加粗并居中对齐
* 自动调整列宽以适应最长内容
* 工作表名称为 "内存映射统计"

# 注意事项
* 如果指定的 Excel 输出文件扩展名不是 .xlsx 或 .xlsm，程序会自动添加 .xlsx 扩展名
* 对于大型 pmap 输出，Excel 文件可能更适合查看和分析
* 程序会自动处理内存映射名称中的方括号（例如 [heap] 会被处理为 heap）
* 结果按 Kbytes 字段降序排列，便于快速识别最大的内存占用项

