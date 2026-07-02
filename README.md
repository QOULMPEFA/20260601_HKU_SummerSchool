# 一生一芯 — sCPU F6 电路生成器

## 项目结构

```
一生一芯/
├── generate_circ.py          ← 平面版生成器（可直接运行，生成完整电路）
├── gen_subcircuit.py          ← 子电路封装版生成器
├── subcircuits.py             ← 子电路 builder 库（7个模块定义）
├── tools/                     ← 检查/诊断工具
│   ├── check_overlaps.py      — 线重叠检测（union-find）
│   ├── check_rules.py         — 规范合规检查
│   ├── check_widths.py        — 位宽不匹配检测
│   ├── diagnose_nets.py       — 逻辑网分析
│   ├── find_bridge.py         — 桥接点定位
│   └── calibrate_pins.py      — 引脚校准
├── Logisim/
│   ├── sCPU_F6.circ           — 当前平面版输出
│   ├── sCPU_F6_sub.circ       — 当前子电路版输出
│   ├── output/                — 最终输出副本
│   ├── archive/               — 历史迭代版本
│   └── reference/             — 参考电路（MIPS CPU）
├── log/                       — 日志和数据
│   ├── lessons_learned.md     — 经验总结
│   ├── subcircuit_specs.json  — 子电路规格
│   └── *.log                  — 生成/检查日志
├── guide-ai/                  — AI 生成指南
├── guide/                     — 项目学习指南
└── logisim_github/            — Logisim 源码（参考）
```

## 快速开始

```bash
# 生成平面版电路
python generate_circ.py

# 生成子电路封装版
python gen_subcircuit.py

# 检查重叠
python tools/check_overlaps.py Logisim/sCPU_F6.circ

# 诊断网络
python tools/diagnose_nets.py Logisim/sCPU_F6.circ

# 查看子电路规格
cat log/subcircuit_specs.txt
```

## 输出文件

- `Logisim/sCPU_F6.circ` — 平面版，可直接在 Logisim 中打开
- `Logisim/sCPU_F6_sub.circ` — 子电路封装版（7模块，无 `<appear>` 块）
- `d:/sCPU/sCPU_F6.circ` — ASCII 路径副本（避免中文路径问题）

## 当前状态

| 指标 | 平面版 | 子电路版 |
|------|--------|---------|
| 元件数 | 48 | 129（分布在7个子电路中） |
| 线数 | 276 | 156（子电路内部）+ 待接线 |
| 可打开 | ✅ | ✅ |
| 0 斜线 | ✅ | ✅ |
| 0 引脚穿通 | ✅ | - |
| 跨模块接线 | N/A（平面） | 待完成 |
