#!/usr/bin/env python3
"""用香港天文台数据库仲裁差异日期。"""
import sys, os, sqlite3, datetime
sys.path.insert(0, r"D:\c_wannianli")
from chinese_calendar.api import Calendar
from lunar_python import Lunar as LP

DB_PATH = r"D:\c_metaphysics\chinese-calendar-database\chinese_calendar.db"

def hko_lunar(y, m, d):
    """查询 HKO 数据库的农历日期。"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT lunar_year, lunar_month, lunar_day, is_leap_month FROM days WHERE year=? AND month=? AND day=?",
        (y, m, d)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        ly, lm, ld, leap = row
        return (ly, lm, ld, bool(leap))
    return None

# 1) 1920-11-15 边界
print("="*60)
print("1) 1920-11-15 边界")
print("="*60)
for dy in range(-1, 3):
    dt = datetime.date(1920, 11, 15) + datetime.timedelta(days=dy)
    y, m, d = dt.year, dt.month, dt.day
    our = Calendar.from_solar(y, m, d).lunar
    our_text = f"{our.year}.{our.month:02d}.{our.day:02d}" if our else "None"
    hko = hko_lunar(y, m, d)
    hko_text = f"{hko[0]}.{hko[1]:02d}.{hko[2]:02d}" if hko else "None"
    lp = LP.fromDate(datetime.datetime(y, m, d, 12, 0, 0))
    lp_text = f"{lp.getYear()}.{abs(lp.getMonth()):02d}.{lp.getDay():02d}"
    win = "🏆" if our_text == hko_text else "❌"
    print(f"  {y}-{m:02d}-{d:02d}: 我们={our_text}  HKO={hko_text}  lunar_python={lp_text}  {win}")

# 2) 2015 年 闰月
print()
print("="*60)
print("2) 2015-05-18 闰月差异")
print("="*60)
for dy in range(-10, 15):
    dt = datetime.date(2015, 5, 18) + datetime.timedelta(days=dy)
    y, m, d = dt.year, dt.month, dt.day
    our = Calendar.from_solar(y, m, d).lunar
    our_text = f"{our.year}.{our.month:02d}.{our.day:02d}(闰={our.is_leap})" if our else "None"
    hko = hko_lunar(y, m, d)
    hko_text = f"{hko[0]}.{hko[1]:02d}.{hko[2]:02d}(闰={hko[3]})" if hko else "None"
    lp = LP.fromDate(datetime.datetime(y, m, d, 12, 0, 0))
    lp_text = f"{lp.getYear()}.{abs(lp.getMonth()):02d}.{lp.getDay():02d}(闰={lp.getMonth()<0})"
    # 以 HKO 为基准
    if hko:
        our_ok = (our and our.year==hko[0] and our.month==hko[1] and our.day==hko[2])
        lp_ok = (abs(lp.getMonth())==hko[1] and lp.getDay()==hko[2])
        win = "🏆H" if our_ok else ("🏆L" if lp_ok and not our_ok else "❌")
    else:
        win = ""
    if win != "🏆H":
        print(f"  {y}-{m:02d}-{d:02d}: 我们={our_text}  HKO={hko_text}  lp={lp_text}  {win}")
