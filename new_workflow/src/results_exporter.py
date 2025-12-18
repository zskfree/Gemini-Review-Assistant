# new_workflow/src/results_exporter.py
"""
文献综述助手 - 结果导出器
负责将总结结果排序并导出为CSV文件
"""
import csv
import json
import os
import re
from typing import Any, Dict, List, Tuple

try:
    from pypinyin import lazy_pinyin  # optional
    _HAS_PYPINYIN = True
except Exception:
    _HAS_PYPINYIN = False

def _contains_cjk(text: str) -> bool:
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

def _english_key(text: str) -> str:
    s = text.strip()
    s = re.sub(r'[^0-9A-Za-z]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.lower()

def _chinese_key(text: str) -> str:
    s = text.strip()
    if _HAS_PYPINYIN:
        try:
            return ''.join(lazy_pinyin(s)).lower()
        except Exception:
            pass
    return s.lower()

def _ref_sort_key(reference: str) -> Tuple[int, str]:
    if _contains_cjk(reference):
        return (0, _chinese_key(reference))
    return (1, _english_key(reference))

def _sorted_results(summary_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = [r for r in summary_results if isinstance(r, dict)]
    items = [r for r in items if 'reference' in r]
    return sorted(items, key=lambda r: _ref_sort_key(str(r.get('reference', ''))))

def sort_and_export(summary_results: List[Dict[str, Any]], output_csv_path: str) -> int:
    sorted_items = _sorted_results(summary_results)
    os.makedirs(os.path.dirname(output_csv_path) or '.', exist_ok=True)
    with open(output_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['reference', 'summary'])
        for r in sorted_items:
            ref = str(r.get('reference', '')).strip()
            summ = '' if r.get('summary') is None else str(r.get('summary'))
            writer.writerow([ref, summ])
    return len(sorted_items)

def export_from_json(input_json_path: str, output_csv_path: str) -> int:
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError('Input JSON must be a list of objects.')
    return sort_and_export(data, output_csv_path)

if __name__ == "__main__":
    # 测试代码
    test_json_path = 'new_workflow/txts_zsk/literature_summary.json'
    test_csv_path = 'new_workflow/txts_zsk/summary_sorted.csv'
    count = export_from_json(test_json_path, test_csv_path)
    print(f"导出完成，共 {count} 条记录到 {test_csv_path}")