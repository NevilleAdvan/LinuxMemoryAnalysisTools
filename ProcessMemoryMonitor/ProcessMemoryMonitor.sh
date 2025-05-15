#!/bin/bash

# 确保输出目录存在
output_dir=${1:-$(pwd)}
para_times=${2:-0}

output_file=${output_dir}"/ProcessMemoryData.txt"
# 创建临时文件存储数据
temp_file=$(mktemp)

while [[ $para_times -ne 0 || "$2" == "" ]];do
  if [ $para_times -ne 0 ]; then
     ((para_times--))
     echo "剩余 times: $para_times"
  fi
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

  sleep 5  # 每隔5秒检查一次状态
done