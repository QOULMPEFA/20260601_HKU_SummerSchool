# Logisim 电路封装经验总结

## 一、为什么需要封装

### 问题
平面电路（单层 `main` 电路，所有元件和线在同一坐标空间）存在根本性缺陷：
- **线干涉**：不同信号的线在密集区域共享物理坐标，导致电气短路
- **位宽不匹配**：1-bit 时钟/控制信号与 8-bit 数据总线合并到同一逻辑网
- **维护困难**：修改一根线可能影响整个电路

### 解决方案
Logisim 子电路（`<circuit>` 元素）封装：
- 每个子电路有**独立的局部坐标空间**
- 子电路内部的线**永远不会**与其他子电路的线发生物理碰撞
- main 电路只放置子电路实例 + 跨模块连线

---

## 二、子电路 XML 格式要点

### 2.1 内联子电路（同一 .circ 文件）

**定义：**
```xml
<circuit name="子电路名">
  <a name="circuit" val="子电路名"/>
  <a name="clabel" val=""/>
  <a name="clabelup" val="east"/>
  <!-- 内部元件和线 -->
</circuit>
```

**实例化（在 main 中引用）：**
```xml
<comp loc="(x,y)" name="子电路名"/>
```
不需要 `lib` 属性！Logisim 会在同一文件中查找同名电路。

### 2.2 Pin 组件作为 I/O 端口

**输入引脚**（外部驱动子电路，数据流入）：
```xml
<comp lib="0" loc="(x,y)" name="Pin">
  <a name="width" val="8"/>
  <a name="label" val="端口名"/>
</comp>
```
- `facing` 默认 `east`，端口出现在子电路**西边缘**

**输出引脚**（子电路驱动外部，数据流出）：
```xml
<comp lib="0" loc="(x,y)" name="Pin">
  <a name="facing" val="west"/>
  <a name="output" val="true"/>
  <a name="width" val="8"/>
  <a name="label" val="端口名"/>
  <a name="labelloc" val="east"/>
</comp>
```
- `facing="west"`，端口出现在子电路**东边缘**

### 2.3 端口位置计算

端口在 main 中的全局位置 = **放置偏移 + 局部端口坐标**

```
pg(s, port_name) = placement_offset + s.port_xy(port_name)
```

### 2.4 `<appear>` 块的问题

`<appear>` 块用于自定义子电路外观和端口位置，但：
- `circ-port` 的 `pin` 属性必须**完全匹配** Pin 组件的 `loc`（含 YO=200 偏移）
- `<appear>` 必须在所有 `<wire>` 和 `<comp>` **之后**
- 需要 `<rect>` 定义视觉边框，否则端口无法定位
- **实践中极难自动生成正确格式**，建议不使用，让 Logisim 自动计算

---

## 三、坐标系统

### 3.1 两层坐标

| 层次 | 坐标系 | 说明 |
|------|--------|------|
| 逻辑坐标 | 子电路局部坐标 | 可以为负，子电路内部使用 |
| XML 坐标 | 逻辑 + YO=200 | 必须 ≥ 0（Logisim 画布原点左上角） |

### 3.2 放置偏移计算

```
placement_x = target_global_x - port_local_x
placement_y = target_global_y - port_local_y
```

选择子电路中最关键的端口（如 `clk_in`、`pc_q`），计算放置偏移使其全局位置与原始电路对齐。

### 3.3 切边问题

**原因**：子电路的包围盒（bounding box）扩展到画布边缘之外。

**排查步骤**：
1. 计算子电路所有元件的 min/max 坐标
2. 计算全局坐标 = 放置偏移 + 局部坐标
3. 确保全局 min ≥ 安全边距（如 50px）
4. 如不够，增加放置偏移

**经验值**：子电路包围盒可能比元件坐标范围大（Logisim 会加 padding），建议至少留 **100-200px 安全边距**。

---

## 四、遇到的问题及修复

### 4.1 元件坐标偏移导致切边

**问题**：`pc` 子电路局部 x 范围 [-50, 280]，放置偏移 x=100，全局 x 范围 [50, 380]。局部有负坐标。
**修复**：增加放置偏移补偿局部 min 值：
```python
if min_x + ox < MARGIN:
    ox += MARGIN - (min_x + ox)
```

### 4.2 `<appear>` 块报错 "circ-port not found"

**问题**：多次尝试自定 `<appear>` 块，始终报此错误。
**根因**：`circ-port` 格式极其挑剔——`pin` 必须精确匹配 Pin loc（含 YO），`x,y` 必须在子电路边框上，需要 `circ-anchor` 和 `rect` 配合。
**最终方案**：放弃 `<appear>`，让 Logisim 自动计算端口位置。无 `<appear>` 时电路可正常打开。

### 4.3 放置偏移 Y 为负导致切边

**问题**：`clock_reset` 关键端口 `clk_in` 局部 y=200，目标全局 y=100，偏移 y=-100。子电路顶部超出画布。
**修复**：加 300px 上边距，偏移改为 y=200，XML loc=(0,400)。

### 4.4 放置偏移 X 为 0 被误认为切边

**问题**：`clock_reset` 偏移 x=0（因为 `clk_in` 局部 x=60，目标全局 x=60，60-60=0）。打开后 loc 显示 (0,400)，用户认为 x=0 是切边。
**解释**：x=0 是正确的——子电路内容从 x=54 开始，全局有 54px 左边距。最终给所有模块加 50px x-padding 以消除疑虑。

### 4.5 子电路内部坐标大量为负的处理

**问题**：`writeback` 有 BitExtender 在局部 x=-580。
**修复思路**：最初尝试 `shift_coords()` 把内部坐标全部平移为正，但这破坏了端口对齐。**正确做法**：保留原始坐标，通过增大放置偏移来补偿，让全局坐标为正。

### 4.6 跨模块连线坐标问题

**问题**：子电路端口位置由 Logisim 自动计算（无 `<appear>` 时），无法精确预知。
**当前状态**：跨模块接线尚未完成。需要：
1. 在 Logisim 中打开电路，记录每个端口的实际全局位置
2. 或者使用 `<appear>` 精确定义端口（需攻克格式问题）

---

## 五、代码架构

### 5.1 文件结构

```
generate_circ.py        — 平面版生成器（Block 类 + 7 个 builder，功能可用）
subcircuits.py           — 子电路 builder（Subcircuit 类 + Pin I/O 端口）
gen_subcircuit.py        — 子电路版生成器（装配 + 放置 + 跨模块接线）
log/subcircuit_specs.json — 子电路规格数据（JSON）
log/subcircuit_specs.txt  — 子电路规格数据（文本）
```

### 5.2 Subcircuit 类核心方法

| 方法 | 功能 |
|------|------|
| `add_comp(lib, xy, name, **props)` | 添加元件 |
| `add_wire(fx, fy, tx, ty)` | 添加线（局部坐标） |
| `add_input(name, x, y, width)` | 添加输入 Pin 端口 |
| `add_output(name, x, y, width)` | 添加输出 Pin 端口 |
| `port_xy(name)` | 获取端口局部坐标 |
| `shift_coords(dx, dy)` | 平移所有坐标（谨慎使用！） |
| `emit_circuit()` | 生成 `<circuit>` XML |
| `instantiate(loc_x, loc_y)` | 生成实例化 XML |

### 5.3 生成流程

```
1. subcircuits.py: 构建 7 个 Subcircuit 对象（局部坐标 + Pin 端口）
2. gen_subcircuit.py: 
   a. 计算放置偏移（端口对齐 + 安全边距）
   b. 生成 XML header + main 电路（实例化 + 跨模块线）
   c. 生成子电路定义（emit_circuit）
3. 输出 sCPU_F6_sub.circ
```

---

## 六、调试工具

| 工具 | 功能 |
|------|------|
| `check_overlaps.py` | 检测线重叠（union-find） |
| `check_widths.py` | 检测位宽不匹配 |
| `diagnose_nets.py` | 分析每个逻辑网的引脚组成 |
| `find_bridge.py` | BFS 双向搜索定位桥接点 |
| `check_rules.py` | 检查是否违反生成规则 |
| `validate_routing()` | 检测线穿过非目标引脚 |
| `log/subcircuit_specs.json` | 子电路尺寸和端口坐标数据 |

---

## 七、关键原则

1. **子电路内部坐标保持原始值**——不要随意 `shift_coords`，通过放置偏移补偿
2. **放置偏移计算**：`ox = target_global_x - port_local_x`
3. **安全边距**：全局 y ≥ 50（最好 ≥ 100），x ≥ 50
4. **不用 `<appear>`**：让 Logisim 自动计算端口位置
5. **YO=200 统一偏移**：所有 XML 坐标 = 逻辑坐标 + 200
6. **所有线必须 L 形**：`fx==tx or fy==ty`，禁止斜线
7. **先放模块后接线**：确认模块位置正确后，再加跨模块连线
