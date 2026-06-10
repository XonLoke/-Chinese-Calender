#!/usr/bin/env python3
"""从 HKO 数据库预计算 1901-2100 农历缓存（JSON），保证 100% 准确率。"""
import sqlite3, json, os

DB_PATH = r"D:\c_metaphysics\chinese-calendar-database\chinese_calendar.db"
OUTPUT = os.path.join(os.path.dirname(__file__), "chinese_calendar", "data", "hko_cache.json")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 从 HKO 读取全部 1901-2100 农历数据
cur.execute("SELECT COUNT(*) FROM days")
total = cur.fetchone()[0]
print(f"HKO 数据总量: {total} 行")

cur.execute("SELECT MIN(year), MAX(year) FROM days")
min_y, max_y = cur.fetchone()
print(f"年份范围: {min_y} - {max_y}")

# 读取所有数据并转换为 RD→(year,month,day,leap) 映射
from chinese_calendar.calendar.converters import fixed_from_gregorian

cache = {}
cur.execute("SELECT year, month, day, lunar_year, lunar_month, lunar_day, is_leap_month FROM days ORDER BY year, month, day")
count = 0
for row in cur:
    y, m, d, ly, lm, ld, leap = row
    rd = fixed_from_gregorian(y, m, d).day
    cache[str(rd)] = [ly, lm, ld, bool(leap)]
    count += 1
    if count % 10000 == 0:
        print(f"  处理 {count}/{total}...")

conn.close()

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, separators=(",",":"))

print(f"\n✅ 缓存写入: {OUTPUT}")
print(f"  RD 条目: {len(cache)}")
print(f"  JSON 大小: {os.path.getsize(OUTPUT) / 1024:.1f} KB")
