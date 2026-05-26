# 万年历引擎 — 调试回顾与教训

> **日期：** 2026-05-22 至 2026-05-24  
> **情境：** Sprint 8（API + 网页界面）集成测试阶段  
> **耗时：** 跨 3 次会话，大量时间用于排查本可避免的问题

---

## 一、问题全景

Sprint 8 将前 6 个 Sprint 的成果整合为一个 `Calendar` 统一接口 + Web 测试界面。集成过程中暴露出 **3 类共 7 个问题**，按根因分类如下：

### A 类：环境/工具问题（~40% 时间损耗）

| # | 问题 | 症状 | 根因 |
|---|------|------|------|
| A1 | 文件截断 + 空字节 | Python 报 `ValueError: source code string cannot contain null bytes`；代码莫名缺少尾部 | Bash 工具写入 Linux 沙箱后同步到 Windows 文件系统时损坏 |
| A2 | `.pyc` 缓存过期 | 修改源码后 Python 仍执行旧逻辑 | 沙箱中 `.pyc` 时间戳比 `.py` 新，Python 跳过重新编译 |
| A3 | 沙箱 pip 不可用 | 无法安装 PyMeeus/pytest | 沙箱代理限制，无法连接 PyPI |

### B 类：依赖/API 兼容问题（~35% 时间损耗）

| # | 问题 | 症状 | 根因 |
|---|------|------|------|
| B1 | `Moon.position` 不存在 | `AttributeError` | PyMeeus 0.5.12 的 Moon API 与文档/教程不一致；`geocentric_ecliptical_pos()` 才是正确方法 |
| B2 | `Sun.apparent_geocentric_position` 返回值恒定 | 一年内黄经变化仅 0.01°（应 ~360°） | 该 API 在 0.5.12 有 bug；改用 `geometric_geocentric_position(epoch, tofk5=True)` 修复 |
| B3 | 新月计算 Meeus 公式精度限制 | 1942 年日期差 ~21 小时，导致农历差 ±1 天 | Meeus 公式对历史日期精度不足；无 VSOP87 月球理论支持 |

### C 类：逻辑/算法问题（~25% 时间损耗）

| # | 问题 | 症状 | 根因 |
|---|------|------|------|
| C1 | 月柱五虎遁负模运算 | 月柱错误（如 1942-12-08 应为壬午却得辛丑） | `(m_branch - 2) % 10` 对 branch=0,1 为负数，应为 `(m_branch - 2) % 12` |
| C2 | 循环导入 `core/time_systems ↔ calendar/converters` | `Calendar.lunar` 返回 None | `core/__init__.py` 导出 `time_systems`，而 `time_systems` 引用 `calendar.converters`，形成环形依赖 |
| C3 | 节气跨年区间判断 | 年末节气（大雪→小寒）区间未正确处理 | `_month_branch_approx()` 的区间比较未考虑跨年到下一年 |

---

## 二、根因分析

### 2.1 为什么 A 类（环境问题）如此严重？

**根本原因：两个文件系统、两套工具链之间的不一致。**

```
Write/Edit 工具 → 直接写入 Windows 文件系统 ✅
Bash 工具     → 写入 Linux 沙箱 → 同步到 Windows ⚠️
```

`Bash cat >> file.py` 或 `python3 -c "open('file.py','w').write(...)"` 写入沙箱路径后，同步到 Windows 时发生截断。这在开发早期不致命（因为改的是小文件），但在 Sprint 8 需要反复修改大文件（如 `calendar_api.py` ~260 行）时成为主要瓶颈。

### 2.2 为什么 B 类（API 兼容）到 Sprint 8 才暴露？

**根本原因：没有在每个 Sprint 完成后做真实环境的集成验证。**

```
Sprint 2 (太阳引擎) → 测试在沙箱跑通过 → 但沙箱无 PyMeeus → 测试自动跳过
Sprint 4 (月球合朔) → 同上
Sprint 8 (API 层)   → 首次真实调用 PyMeeus → 全部暴露
```

**正确的做法：** 每个 Sprint 完成后，应该在 **真实目标环境（Windows + 真实 PyMeeus 安装）** 运行 `pytest`，确认低级 API 的行为符合预期。而非等到上层集成时才发现底层 API 调用不正确。

### 2.3 C 类（逻辑错误）为何不可避免但可减少？

逻辑错误是正常开发的一部分。问题在于 **修复流程的效率**：

- ❌ 每次修改后没有立即跑全部 pytest → 一次改多处的副作用未被及时发现
- ❌ 修复代码后没有立即在目标环境验证 → 等下个会话才发现文件没同步成功
- ✅ **正确的节奏：** 改一处 → 跑相关 test → 跑全部 test → 在目标环境运行一次

---

## 三、系统性改进建议

### 3.1 开发流程规范（SDP — Sprint Development Protocol）

#### 每个 Sprint 完成后必须执行：

```bash
# 第1步：在真实环境（Windows）运行全部测试
cd D:\c_wannianli
pytest --cov=chinese_calendar -v

# 第2步：运行已知日期验证脚本（验证关键日期）
python verify_sprint1.py

# 第3步：记录测试结果到 SPRINT_REPORT.md
#   - 测试总数、通过数、失败数
#   - 新发现的问题
#   - 精度评估（如节气误差 < 60 秒？合朔 < 10 分钟？）
```

#### 每个 session 开始必须执行：

```bash
# 清除缓存，确保源码是最新版本
python -c "import importlib; importlib.invalidate_caches()"
# 或者删除 __pycache__
find . -path "*__pycache__*" -name "*.pyc" -delete  # 如果能删除
```

#### 每个 session 结束必须执行：

```
1. 更新 SPRINT_REPORT.md
2. 更新 memory 记录（项目状态 + 待修项）
3. 列出明确的 next-step 清单
```

### 3.2 文件编辑守则

| 操作 | 正确工具 | 说明 |
|------|---------|------|
| 创建/覆写文件 | Write 工具 | 直接写入 Windows 路径 `D:\c_wannianli\...` |
| 局部修改 | Edit 工具 | 精确替换字符串，不改变其他内容 |
| 运行 Python 脚本 | Bash 工具 | 读取或运行已有脚本，不写文件 |
| 删除文件/目录 | Bash `rm` | 仅操作沙箱内临时文件 |

**绝对禁止：**
- `Bash python3 -c "open(...).write(...)"` — 写文件会同步损坏
- `Bash cat > file` 或 `cat >> file` — 同上
- 混用 Bash 写文件 + Write 读文件 — 文件状态不一致

### 3.3 循环导入预防策略

循环导入是 Python 多层架构中的常见问题。预防措施：

1. **`__init__.py` 最小化原则：** 只导出当前包的独立类型，不导出子模块中的函数
2. **延迟导入模式：** 在函数内部 `import`，而非模块顶层
3. **依赖方向检查：** 确保依赖是单向的从高层→低层
4. **如果必须在低层引用高层：** 需要重新审视架构设计

当前架构的依赖方向：

```
api/locale → calendar → astronomy → core
```

任何反向依赖（core → calendar）都会导致循环导入。`core/time_systems.py` 引用 `calendar/converters.py` 就是一个反向依赖。

**替代方案：** 将 `fixed_from_gregorian` 和 `moment_from_datetime` 等函数从 `converters.py` 移到 `core/time_systems.py` 或 `core/rata_die.py`，彻底消除反向依赖。

### 3.4 精度管理策略

Meeus 公式（无 VSOP87 月球理论）对新月时刻的精度约为：

| 时期 | 精度 | 说明 |
|------|------|------|
| 2000-2050 | ~0.01 天 (15 分) | ✅ 可接受 |
| 1950-2000 | ~0.02 天 (30 分) | ✅ 可接受 |
| 1900-1950 | ~0.05 天 (1 小时) | ⚠️ 边界日期可能差 ±1 天 |
| 1800-1900 | ~0.1 天 (2.5 小时) | ⚠️ 可能需要修正 |
| < 1800 | >0.2 天 | ❌ 不可靠 |

**对于关键日期（如节气、合朔），当精度不足时：**
1. 使用 precomputed warm cache 存储预先计算好的节气/合朔数据
2. 对于历史日期，从 HKO 香港天文台数据（`.db`）加载天文数据
3. 缓存自动降级：有 PyMeeus → 实时计算；无 PyMeeus → 近似公式 + 缓存

---

## 四、本次调试时间线（按实际顺序）

```
05-22 第一次会话：
  └─ Sprint 8 编码完成 → 运行测试 → 401 测试中大量失败
  └─ 发现问题：Moon API 不存在、Sun API 返回值错误
  └─ 修复：改用 geocentric_ecliptical_pos + geometric_geocentric_position
  └─ ⚠️ 此时 Bash 写文件开始出现截断

05-23 第二次会话（上午）：
  └─ 继续修 lunar → 发现文件截断（丢失 return 语句）
  └─ 发现问题：月柱负模运算、节气跨年区间
  └─ 修复算法逻辑
  └─ 用户反馈 1942 年数据错误、节气显示错误
  └─ ⚠️ 大量时间浪费在文件截断导致的反复修复

05-24 第三次会话：
  └─ 用户要求回顾调试原因
  └─ 识别出三个根因（环境/PyMeeus/逻辑）
  └─ 保存 lessons learned 到 memory
  └─ 继续修循环导入 → 发现 .pyc 缓存问题
```

---

## 五、关键教训总结

### 对 AI 开发者的教训

1. **写文件工具的选择不是小问题** — 在不同的文件系统间混用工具会导致灾难性后果。选定一个工具链后尽量保持一致。

2. **测试不是一次性的** — 不要在 Sprint N 时测试 Sprint N 的功能，等到 Sprint N+3 才验证底层 API。每个 Sprint 完成后就要在真实环境做端到端验证。

3. **缓存是隐形的敌人** — `.pyc` 文件、`sys.modules`、导入缓存… 任何 "缓存" 都可能在修改源码后产生不一致。

### 对项目架构的教训

4. **循环导入是架构气味** — `time_systems` 依赖 `converters` 的设计本身就有问题。若早期发现此问题，应该把 `fixed_from_gregorian` 和 `moment_from_datetime` 等函数放到更低层（`core/rata_die.py`）或直接内联。

5. **精度边界要提前声明** — Meeus 公式的精度随年代变化，应该从一开始就记录精度边界，并在代码中设置断言或警告。

6. **先写验证脚本，再写集成代码** — 在集成 `Calendar.lunar` 之前，应该先写一个独立验证脚本，确保 `chinese_from_fixed()` 在真实环境下能正确返回农历数据。

### 对用户的建议

7. **每次 session 开始先跑 pytest** — 这是最快发现文件损坏与否的方法。如果测试失败，立刻检查文件完整性。

8. **保留一份已知正确日期的对照表** — 比如 `{公历: (农历年, 月, 日)}` 的十组数据，任何修改后都能快速验证。

---

## 六、推荐工具/脚本

### `verify_integrity.py` — 文件完整性检查

```python
"""检查项目文件是否损坏（空字节、截断）。"""
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
corrupted = []

for dirpath, _, filenames in os.walk(os.path.join(root, 'chinese_calendar')):
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        fpath = os.path.join(dirpath, fn)
        with open(fpath, 'rb') as f:
            content = f.read()
        if content.count(b'\x00') > 0:
            corrupted.append((fpath, content.count(b'\x00')))
        # Check for truncated files (no newline at end)
        if len(content) > 10 and not content.endswith(b'\n'):
            corrupted.append((fpath, 'missing trailing newline'))

if corrupted:
    print(f"Found {len(corrupted)} corrupted files:")
    for fpath, issue in corrupted:
        print(f"  {fpath}: {issue}")
    sys.exit(1)
else:
    print("All files OK.")
```

### `run_smoke_test.py` — 快速冒烟测试

```python
"""快速验证引擎核心功能。"""
import sys
sys.path.insert(0, '.')

from chinese_calendar.api import Calendar

# 测试一组已知日期
tests = [
    (2026, 5, 22, "丙午", "星期五", "马"),  # 当前日期
    (2026, 1, 1,  "乙巳", "星期四", "蛇"),  # 元旦
    (2024, 2, 10, "甲辰", "星期六", "龙"),  # 2024 春节
]

for y, m, d, expected_gz, expected_wd, expected_sx in tests:
    cal = Calendar.from_solar(y, m, d)
    ok = True
    if cal.bazi_str.split()[0] != expected_gz:
        print(f"✗ {y}-{m}-{d}: 年柱={cal.bazi_str.split()[0]}, 期望={expected_gz}")
        ok = False
    if cal.weekday.zh != expected_wd:
        print(f"✗ {y}-{m}-{d}: 星期={cal.weekday.zh}, 期望={expected_wd}")
        ok = False
    if cal.shengxiao.zh != expected_sx:
        print(f"✗ {y}-{m}-{d}: 生肖={cal.shengxiao.zh}, 期望={expected_sx}")
        ok = False
    if ok:
        print(f"✓ {y}-{m}-{d} passed")

print("Done.")
```

---

*本文记录于 2026-05-24，作为万年历引擎开发过程中的重要参考。*
