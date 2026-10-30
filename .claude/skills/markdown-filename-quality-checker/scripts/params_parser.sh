#!/bin/bash

# 参数解析脚本
# 用法：./params_parser.sh "$@"

input_content=""
rules_list=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --rules)
            rules_list="$2"
            shift 2
            ;;
        *)
            # 如果不是--rules参数，将其作为markdown内容或文件路径
            if [[ -z "$input_content" ]]; then
                input_content="$1"
            else
                input_content="$input_content,$1"
            fi
            shift
            ;;
    esac
done

# 构建参数传递给主处理逻辑
if [[ -n "$rules_list" ]]; then
    echo "{\"input\":\"$input_content\",\"rules\":\"$rules_list\"}"
else
    echo "{\"input\":\"$input_content\",\"rules\":\"\"}"
fi