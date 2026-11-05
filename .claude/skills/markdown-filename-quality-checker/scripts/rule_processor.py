#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则分类处理脚本
根据规则序号或规则项名称对规则进行分类并生成JSON文件
"""

import json
import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Rule:
    """规则数据实体类"""
    rule_no: str
    rule_item_name: str
    rule_name: str
    rule_type: str
    rule_desc: str
    rule_level: str
    description_format: str
    reference_doc_path: Optional[str] = None


class RuleProcessor:
    def __init__(self, rules_file_path: str, output_dir_path: str, rule_numbers_str: Optional[str] = None):
        """
        初始化规则处理器
        
        Args:
            rules_file_path: rules.json配置文件路径
            output_dir_path: 输出目录路径
            rule_numbers_str: 规则序号字符串，多个以逗号分隔
        """
        self.rules_file_path = rules_file_path
        self.output_dir_path = output_dir_path
        self.rule_numbers_str = rule_numbers_str
        self.rules: List[Rule] = []
        self.filtered_rules: List[Rule] = []
        
    def load_rules(self) -> None:
        """
        从JSON文件加载规则数据
        """
        # 尝试多种编码格式
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
        
        file_content = None
        used_encoding = None
        for encoding in encodings:
            try:
                with open(self.rules_file_path, 'r', encoding=encoding) as f:
                    file_content = f.read()
                    used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if file_content is None:
            raise ValueError(f"无法解码文件，请检查文件编码格式: {self.rules_file_path}")
                
        try:
            json_data = json.loads(file_content)
                
            # 解析JSON数据为Rule对象列表
            for item in json_data:
                rule = Rule(
                    rule_no=item['rule_no'],
                    rule_item_name=item['rule_item_name'],
                    rule_name=item['rule_name'],
                    rule_type=item['rule_type'],
                    rule_desc=item['rule_desc'],
                    rule_level=item['rule_level'],
                    reference_doc_path=item.get('reference_doc_path'),
                    description_format=item['description_format']
                )
                self.rules.append(rule)
                
        except FileNotFoundError:
            raise FileNotFoundError(f"规则文件不存在: {self.rules_file_path}")
        except json.JSONDecodeError:
            raise ValueError(f"JSON文件格式错误: {self.rules_file_path}")
        except KeyError as e:
            raise KeyError(f"规则数据缺少必要字段: {e}")
    
    def filter_rules_by_numbers(self) -> None:
        """
        根据规则序号筛选规则
        """
        if not self.rule_numbers_str:
            self.filtered_rules = self.rules
            return
            
        # 处理规则序号字符串
        rule_numbers = [num.strip() for num in self.rule_numbers_str.split(',') if num.strip()]
        
        # 筛选指定序号的规则
        self.filtered_rules = []
        for rule in self.rules:
            if rule.rule_no in rule_numbers:
                self.filtered_rules.append(rule)
    
    def group_rules_by_item_name(self) -> Dict[str, List[Dict]]:
        """
        按规则项名称分组规则
        
        Returns:
            分组后的字典，键为规则项名称，值为规则字典列表
        """
        grouped = {}
        
        for rule in self.filtered_rules:
            item_name = rule.rule_item_name
            if item_name not in grouped:
                grouped[item_name] = []
            
            # 将Rule对象转换为字典
            rule_dict = {
                'rule_no': rule.rule_no,
                'rule_item_name': rule.rule_item_name,
                'rule_name': rule.rule_name,
                'rule_type': rule.rule_type,
                'rule_desc': rule.rule_desc,
                'rule_level': rule.rule_level,
                'reference_doc_path': rule.reference_doc_path,
                'description_format': rule.description_format
            }
            grouped[item_name].append(rule_dict)
        
        return grouped
    
    def create_output_files(self) -> None:
        """
        创建输出文件
        """
        # 确保输出目录存在
        os.makedirs(self.output_dir_path, exist_ok=True)
        
        # 按规则项名称分组
        grouped_rules = self.group_rules_by_item_name()
        
        # 为每个规则项创建JSON文件
        for item_name, rules in grouped_rules.items():
            # 清理文件名，去除非法字符
            filename = self._sanitize_filename(item_name)
            output_path = os.path.join(self.output_dir_path, f"{filename}.json")
            
            # 写入JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(rules, f, ensure_ascii=False, indent=2)
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 移除或替换非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 确保文件名不为空
        return filename.strip() or 'unnamed_rule'
    
    def process(self) -> None:
        """
        执行完整的处理流程
        """
        print("开始处理规则数据...")
        
        # 加载规则数据
        self.load_rules()
        print(f"成功加载 {len(self.rules)} 条规则")
        
        # 筛选规则
        self.filter_rules_by_numbers()
        print(f"筛选后剩余 {len(self.filtered_rules)} 条规则")
        
        # 创建输出文件
        self.create_output_files()
        print(f"分类完成，输出文件保存在: {self.output_dir_path}")


def main():
    """
    主函数，处理命令行参数并执行规则处理
    """
    if len(sys.argv) < 3:
        print("用法:")
        print("  py rule_processor.py <rules.json路径> <输出目录路径> [规则序号]")
        print("  py rule_processor.py <rules.json路径> <输出目录路径> [规则序号1,规则序号2,规则序号3]")
        sys.exit(1)
    
    rules_file_path = sys.argv[1]
    output_dir_path = sys.argv[2]
    rule_numbers_str = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        processor = RuleProcessor(rules_file_path, output_dir_path, rule_numbers_str)
        processor.process()
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()