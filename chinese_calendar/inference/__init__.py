# inference: 术数推理引擎
#
# 基于 Leap71 Noyron 式方法论构建的确定性推理引擎。
# 上层依赖万年历引擎的干支/节气/排盘系统。
#
# 包含:
#   shishen.py    — 十神关系系统
#   relations.py  — 刑冲合害规则
#   dayun.py      — 大运排盘
#   shensha.py    — 神煞系统
#   geju.py       — 格局判定
#   engine.py     — 约束驱动推演引擎
#
# 所有模块均为纯逻辑，无需 PyMeeus。
