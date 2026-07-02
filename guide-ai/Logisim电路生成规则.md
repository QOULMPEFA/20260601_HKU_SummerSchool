# Logisim .circ 文件自动生成规则

> 基于 sCPU 项目实战踩坑总结。违反任一条都会导致文件打不开或元件重叠。

---

## 规则 1：禁止对角线 — 只允许 L 形走线

**所有 `<wire>` 必须是水平或垂直的。** 禁止斜线（from 和 to 的 x 和 y 都不同）。

```
# 错误 ❌
<wire from="(230,650)" to="(350,642)"/>   # 斜线，触发 WireRepair 卡死

# 正确 ✅ — 拆成 L 形
<wire from="(230,650)" to="(300,650)"/>   # 水平段
<wire from="(300,650)" to="(300,642)"/>   # 垂直段
<wire from="(300,642)" to="(350,642)"/>   # 水平段
```

**规则**：每根逻辑连线至少拆成 2-3 段（水平→垂直→水平），拐点放在安全通道内。

---

## 规则 2：禁止负坐标 — 全部 y ≥ 0

Logisim 画布原点在左上角，**负坐标会导致不可预期的行为**。

```python
# 代码中统一 +200（或更大）偏移所有 y 坐标
YO = 200
def shift_y(m):
    return f"{int(m.group(1)) + YO}"
xml = re.sub(r'(?<=,)(-?\d+)(?=\))', shift_y, xml)
```

参考最小 y 值：组件 ≥ 200，线 ≥ 100。

---

## 规则 3：禁止走线穿过任何元件边界框

**每根线段的两端点间不能有其他元件。** 必须为走线预留「安全通道」。

### 安全通道定义

**水平通道（y 值）**：
- `y = 路由用`：选在两组元件之间的空隙，如 `y=140`（在 raddr Mux 上方 20px）
- `y = 源端 y`：直接复用源/目标引脚所在的 y，通常也在安全区

**垂直通道（x 值）**：
- `x = 120`：Pin 与 PC 列之间
- `x = 300`：PC 列与 ROM/Mux 列之间
- `x = 530`：ROM 与 Splitter 之间
- `x = 620`：Splitter 右侧
- `x = 710`：Decoder 与 GPR 之间
- `x = 800`：GPR 与 rMux 之间（但需检查 y 高度避免穿过 raddr Mux）
- `x = 970`：rMux1_ab 与 rMux2_ab 之间的纵向间隙
- `x = 1050`：rMux 树右侧

### 判断线段是否安全

对每条线段 `(x1,y1)→(x2,y2)`：
1. 若是水平线（y1=y2），检查该 y 值在 `[min(x1,x2), max(x1,x2)]` 范围内是否穿过任何元件
2. 若是垂直线（x1=x2），检查该 x 值在 `[min(y1,y2), max(y1,y2)]` 范围内是否穿过任何元件

---

## 规则 4：元件必须充分留间距

### 元件大致尺寸（保守估计）

| 元件类型 | 宽度 | 高度 | 备注 |
|---------|------|------|------|
| Pin (width=1) | 30 | 20 | 很小 |
| Register (width=8) | 80 | 60 | |
| ROM (含内容显示) | 150-200 | 250-400 | **巨大！** 内容行数越多越高 |
| RAM | 150 | 200+ | |
| Mux (width=2) | 50 | 80 | |
| Mux (width=8) | 60 | 80 | |
| Decoder | 60 | 50 | |
| Adder/Comparator | 80 | 60 | |
| Shifter | 80 | 80 | |
| Splitter (fanout=4) | 60 | 60 | |
| AND/OR/NOT Gate | 40 | 40 | |
| Bit Extender | 60 | 50 | |
| Constant | 50 | 30 | |

**间距规则**：两个元件中心至少相距 **宽度/2 + 宽度/2 + 20px**。例如两个 Register（各 80 宽）至少相距 80/2+80/2+20 = 100px（从中心到中心）。

---

## 规则 5：XML 格式规范

### 必须是 Logisim v2.7.2 格式
```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<project source="2.7.2" version="1.0">
```

### 库编号对照
| 编号 | 库名 |
|------|------|
| 0 | Wiring (Pin, Splitter, Constant, Bit Extender, Tunnel) |
| 1 | Gates (AND, OR, NOT, XOR, NAND, NOR) |
| 2 | Plexers (Mux, Decoder, Priority Encoder) |
| 3 | Arithmetic (Adder, Subtractor, Comparator, Shifter) |
| 4 | Memory (Register, ROM, RAM, D Flip-Flop) |
| 5 | I/O |
| 6 | Base |

### 属性必须用子元素，不能内联
```xml
<!-- 正确 ✅ -->
<comp lib="4" loc="(200,340)" name="Register">
  <a name="width" val="8"/>
  <a name="label" val="PC"/>
</comp>

<!-- 错误 ❌ -->
<comp lib="4" loc="(200,340)" name="Register" width="8"/>
```

### ROM 内容格式
```xml
<a name="contents">addr/data: 8 8
0 90
1 a1
...
</a>
```
- 分隔符是 **`/`** 不是 `\`
- 内容作为**文本节点**，不是 `val` 属性
- 十六进制值，每行一个地址

### 关键属性名
- Bit Extender: `in_width`, `out_width`, `type` (值: `"sign"` 或 `"zero"`)
- ROM: `addrWidth`, `dataWidth`
- Splitter: `fanout`, `incoming`, `bit0`-`bitN`, `appear`, `facing`
- Decoder: `width` (=选择位宽，输出 2^width 路)

---

## 规则 6：生成流程

1. **先布元件**，确认无重叠（用规则 4 的尺寸表检查）
2. **定义安全通道**（规则 3）
3. **逐根连线**，全部 L 形（规则 1），检查不穿过元件（规则 3）
4. **统一 +Y 偏移**（规则 2），后处理到全部正坐标
5. **输出 Logisim v2.7.2 格式**（规则 5）

---

## 规则 7：调试方法

遇到打不开的文件时：
1. 先降到 **0 根线**，验证元件布局无问题
2. 加 **1 根线**（最简单的一根），验证能打开
3. 逐组加线（2-3 根一组），二分定位问题线
4. 找到问题线后，改用 L 形走安全通道

**最简文件模板**（用于验证格式）：
```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<project source="2.7.2" version="1.0">
This file is intended to be loaded by Logisim (http://www.cburch.com/logisim/).
  <circuit name="main">
    <comp lib="0" loc="(100,300)" name="Pin">
      <a name="facing" val="east"/>
      <a name="width" val="1"/>
      <a name="label" val="clk"/>
    </comp>
    <comp lib="4" loc="(300,300)" name="Register">
      <a name="width" val="8"/>
      <a name="label" val="PC"/>
    </comp>
    <wire from="(130,300)" to="(270,300)"/>
  </circuit>
</project>
```

---

## 规则 8：本次项目的已知安全区

基于 `sCPU_F6.circ` 当前布局（y 已 +200 偏移）：

| 区域 | x 范围 | y 范围 | 元件 |
|------|--------|--------|------|
| Pin 列 | 30-90 | 290-390 | clk, rst |
| PC 列 | 160-245 | 310-940 | PC, Adder, Const, BitExt |
| ROM 列 | 280-480 | 190-540 | ROM (巨大!) |
| PC_Mux | 350-410 | 610-690 | Mux, AND |
| Splitter | 550-610 | 320-360 | Splitter |
| Decoder | 630-690 | 540-580 | opcode Decoder |
| BitExt2 | 550-610 | 830-870 | |
| Shifter | 720-800 | 830-870 | |
| GPR 列 | 720-800 | 230-710 | R0-R3 |
| raddr Mux 列 | 790-1050 | 160-270 | Const + 3×Mux |
| rMux 列 | 910-1090 | 250-550 | 6×Mux |
| ALU 列 | 1160-1240 | 370-590 | Adder, Comparator |
| 控制门 | 660-1020 | 930-1180 | NOT, AND, OR |
| wMux | 1170-1390 | 750-790 | 2×Mux |
| OUT | 1160-1240 | 900-940 | Register |
| waddr Dec | 830-890 | 1120-1150 | Decoder |
| dev Const | 970-1030 | 1170-1200 | |

**安全水平通道**：y=50-150（raddr Mux 上方）, y=300-310（Pin/PC 之间）  
**安全垂直通道**：x=120, x=300, x=530, x=620, x=710, x=970  
