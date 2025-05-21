#!/bin/bash

# 默认值
output_dir=$(pwd)  # 默认输出目录为当前工作目录
para_times=0        # 默认持续运行

# 使用 getopts 解析命令行参数
while getopts "t:d:" opt; do
    case $opt in
        t)
            para_times=$OPTARG  # 获取 -t 后的值作为运行次数
            ;;
        d)
            output_dir=$OPTARG  # 获取 -d 后的值作为输出目录路径
            ;;
        *)
            echo "用法: $0 [-t 次数] [-d 输出目录]"
            exit 1
            ;;
    esac
done

# 确保输出目录存在，如果不存在则创建它
if [ ! -d "$output_dir" ]; then
    mkdir -p "$output_dir"
    echo "创建输出目录: $output_dir"
fi

output_file=${output_dir}"/ProcessMemoryData.txt"
# 创建临时文件存储数据
temp_file=$(mktemp)

collect_memory_data() {
   # 添加时间戳
  echo "统计时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$output_file"
  echo "" >> "$output_file"

  # 收集数据
  for pidpath in /proc/*/; do
      pid=$(basename "$pidpath")
      # 检查是否为数字（进程ID）
      if [[ "$pid" =~ ^[0-9]+$ ]]; then
          # 使用2>/dev/null忽略错误信息
          name=$(cat "$pidpath/status" 2>/dev/null | grep "Name:" | awk '{print $2}')
          rss=$(cat "$pidpath/status" 2>/dev/null | grep VmRSS | awk '{print $2}')
          pss=$(cat "$pidpath/smaps" 2>/dev/null | grep "^Pss:" | awk '{sum += $2} END {print sum}')
          vss=$(cat "$pidpath/status" 2>/dev/null | grep VmSize | awk '{print $2}')

          # 确保所有值都有数字，没有则设为0
          [[ -z "$rss" ]] && rss=0
          [[ -z "$pss" ]] && pss=0
          [[ -z "$vss" ]] && vss=0

          # 只输出有内存使用的进程
          if [[ $pss -gt 0 || $rss -gt 0 || $vss -gt 0 ]]; then
              # 使用awk进行KB到MB的转换
              echo "$name $pss $rss $vss" | \
              awk '{printf "%s %.1f %.1f %.1f\n",
                   $1,
                   $2/1024,
                   $3/1024,
                   $4/1024}' >> "$temp_file"
          fi
      fi
  done

  # 输出表头
  printf "%-30s %15s %15s %15s\n" "PROCESS" "PSS(MB)" "RSS(MB)" "VSS(MB)" >> "$output_file"
  printf "%s\n" "===============================================================================" >> "$output_file"

  # 使用awk进行排序和格式化输出
  awk '
  {
      line[NR] = $0
      pss[NR] = $2
  }
  END {
      # 冒泡排序
      n = NR
      for (i = 1; i <= n; i++) {
          for (j = 1; j <= n-i; j++) {
              if (pss[j] < pss[j+1]) {
                  # 交换数据
                  temp = line[j]
                  line[j] = line[j+1]
                  line[j+1] = temp

                  temp = pss[j]
                  pss[j] = pss[j+1]
                  pss[j+1] = temp
              }
          }
      }

      # 输出排序后的结果，格式化对齐
      for (i = 1; i <= NR; i++) {
          split(line[i], arr)
          printf "%-30s %15.1f %15.1f %15.1f\n", arr[1], arr[2], arr[3], arr[4]
      }
  }' "$temp_file" >> "$output_file"

  # 计算总和并输出
  awk '
  BEGIN {
      pss_total = 0
      rss_total = 0
      vss_total = 0
  }
  {
      pss_total += $2
      rss_total += $3
      vss_total += $4
  }
  END {
      printf "\n%s\n", "==============================================================================="
      printf "%-30s %15.1f %15.1f %15.1f\n", "TOTAL:", pss_total, rss_total, vss_total
  }' "$temp_file" >> "$output_file"

  # 删除临时文件
  rm -f "$temp_file"

  echo "统计完成，结果已保存到 $output_file"
}

# 执行内存监控
if [ $para_times -eq 0 ]; then
    # 持续运行模式
    echo "开始持续监控进程内存，按 Ctrl+C 终止..."
    while true; do
        collect_memory_data
        sleep 5  # 每隔5秒检查一次状态
    done
else
    # 指定次数运行模式
    echo "开始监控进程内存，将运行 $para_times 次..."
    original_para_times=$para_times
    while [ $para_times -gt 0 ]; do
        echo "第 $((original_para_times - para_times + 1)) 次运行 (共 $original_para_times 次)"
        collect_memory_data
        ((para_times--))

        # 如果不是最后一次运行，则等待5秒
        if [ $para_times -gt 0 ]; then
            sleep 5
        fi
    done
    echo "监控完成，共运行 $original_para_times 次"
fi