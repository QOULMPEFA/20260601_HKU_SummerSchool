#!/usr/bin/env python3
"""生成 sCPU+I/O .circ（宽松布局，无重叠）"""
import re


def generate():
    L = []
    w = L.append
    IND = "    "

    def a_xml(name, val):
        return f'<a name="{name}" val="{val}"/>'

    def comp(lib, loc, name, **props):
        if not props:
            return f'<comp lib="{lib}" loc="{loc}" name="{name}"/>'
        lines = [f'<comp lib="{lib}" loc="{loc}" name="{name}">']
        for k, v in props.items():
            lines.append(f"  {a_xml(k, v)}")
        lines.append("</comp>")
        return "\n".join(lines)

    def add(lines):
        for line in (lines if isinstance(lines, list) else lines.split("\n")):
            L.append(IND + line)

    # ====== XML 头部 ======
    w('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
    w('<project source="2.7.2" version="1.0">')
    w('This file is intended to be loaded by Logisim (http://www.cburch.com/logisim/).')
    for num, desc in [("0", "#Wiring"), ("1", "#Gates"), ("2", "#Plexers"),
                       ("3", "#Arithmetic"), ("4", "#Memory"), ("5", "#I/O"),
                       ("6", "#Base")]:
        w(f'  <lib desc="{desc}" name="{num}"/>')
    w('  <main name="main"/>')
    w('  <options>')
    w(f'    {a_xml("gateUndefined", "ignore")}')
    w(f'    {a_xml("simlimit", "1000")}')
    w(f'    {a_xml("simrand", "0")}')
    w('  </options>')
    w('  <mappings>')
    w('    <tool lib="6" map="Button2" name="Poke Tool"/>')
    w('    <tool lib="6" map="Button3" name="Menu Tool"/>')
    w('    <tool lib="6" map="Ctrl Button1" name="Menu Tool"/>')
    w('  </mappings>')
    w('  <toolbar>')
    w('    <tool lib="6" name="Poke Tool"/>')
    w('    <tool lib="6" name="Edit Tool"/>')
    w('  </toolbar>')
    w('  <circuit name="main">')

    # ============================================================
    # 元件 — 充足间距，避免重叠（门电路尺寸约 60×60）
    # ============================================================

    # --- 第1列: 时钟 & 复位 ---
    add(comp("0", "(60,100)", "Pin", width="1", label="clk",
             labelloc="east", facing="east"))
    add(comp("0", "(60,180)", "Pin", width="1", label="rst",
             labelloc="east", facing="east"))

    # --- 第2列: PC + 更新电路 (y=100~650) ---
    add(comp("4", "(200,140)", "Register", width="8", label="PC",
             labelloc="east"))
    add(comp("3", "(200,320)", "Adder", width="8"))
    add(comp("0", "(200,450)", "Constant", width="8", value="0x01"))
    add(comp("0", "(200,540)", "Bit Extender", in_width="4",
             out_width="8", type="sign"))
    add(comp("2", "(380,450)", "Multiplexer", width="8"))
    add(comp("1", "(380,560)", "AND Gate", width="1", inputs="2"))

    # --- 第3列: ROM + 译码 (y=100~500) ---
    L.append(f'{IND}<comp lib="4" loc="(380,140)" name="ROM">')
    L.append(f'{IND}  {a_xml("addrWidth", "3")}')
    L.append(f'{IND}  {a_xml("dataWidth", "8")}')
    L.append(f'{IND}  <a name="contents">addr/data: 8 8')
    L.append('0 90')
    L.append('1 a1')
    L.append('2 be')
    L.append('3 16')
    L.append('4 29')
    L.append('5 f7')
    L.append('6 54')
    L.append('7 0')
    L.append(f'{IND}  </a>')
    L.append(f'{IND}</comp>')

    # Splitter
    L.append(f'{IND}<comp lib="0" loc="(580,140)" name="Splitter">')
    L.append(f'{IND}  {a_xml("facing", "west")}')
    L.append(f'{IND}  {a_xml("fanout", "4")}')
    L.append(f'{IND}  {a_xml("incoming", "8")}')
    L.append(f'{IND}  {a_xml("appear", "center")}')
    for i, b in enumerate([6, 4, 2, 0]):
        L.append(f'{IND}  {a_xml(f"bit{i}", str(b))}')
    L.append(f'{IND}</comp>')

    add(comp("2", "(660,360)", "Decoder", width="2"))

    # --- 第4列: li 立即数生成 (x=880, 避免和R3重叠) ---
    add(comp("0", "(580,640)", "Bit Extender", in_width="2",
             out_width="8", type="zero"))
    add(comp("3", "(760,640)", "Shifter", width="8"))

    # --- 第5列: GPR R0-R3 (x=760, y=60~620, 间距140) ---
    gpr_x = 760
    gpr_y = [60, 200, 340, 480]
    for i, y in enumerate(gpr_y):
        add(comp("4", f"({gpr_x},{y})", "Register", width="8",
                 label=f"R{i}", labelloc="east"))

    # --- 第5.5列: raddr1 Mux 树 (x=760, y=680) ---
    add(comp("0", "(680,20)", "Constant", width="2", value="0x00"))
    add(comp("2", "(820,10)", "Multiplexer", width="2"))
    add(comp("2", "(920,10)", "Multiplexer", width="2"))
    add(comp("2", "(1020,10)", "Multiplexer", width="2"))

    # --- 第6列: GPR 读口 Mux 树 (x=940~1080) ---
    # rMux1: ab=(940,100), cd=(940,200), top=(1040,150)
    # rMux2: ab=(940,320), cd=(940,420), top=(1040,370)
    add(comp("2", "(940,80)", "Multiplexer", width="8"))
    add(comp("2", "(940,180)", "Multiplexer", width="8"))
    add(comp("2", "(1060,130)", "Multiplexer", width="8"))
    add(comp("2", "(940,300)", "Multiplexer", width="8"))
    add(comp("2", "(940,400)", "Multiplexer", width="8"))
    add(comp("2", "(1060,350)", "Multiplexer", width="8"))

    # --- 第7列: ALU + 比较器 (x=1200) ---
    add(comp("3", "(1200,200)", "Adder", width="8"))
    add(comp("3", "(1200,380)", "Comparator", width="8"))

    # --- 第8列: 控制逻辑门 (拉开间距, 避开Shifter的x=720~840区域) ---
    add(comp("1", "(680,740)", "NOT Gate", width="1"))
    add(comp("1", "(860,740)", "AND Gate", width="1", inputs="2"))
    add(comp("1", "(860,840)", "OR Gate", width="1", inputs="2"))
    add(comp("1", "(1000,840)", "OR Gate", width="1", inputs="2"))
    # wen AND per register
    add(comp("1", "(1140,680)", "AND Gate", width="1", inputs="2"))
    add(comp("1", "(1140,780)", "AND Gate", width="1", inputs="2"))
    add(comp("1", "(1140,880)", "AND Gate", width="1", inputs="2"))
    add(comp("1", "(1140,980)", "AND Gate", width="1", inputs="2"))

    # --- 第9列: GPR wdata Mux 链 (x=1200, y=560~640) ---
    add(comp("2", "(1200,560)", "Multiplexer", width="8"))
    add(comp("2", "(1360,560)", "Multiplexer", width="8"))

    # --- 第10列: 输出锁存器 (x=1200, y=720) ---
    add(comp("4", "(1200,720)", "Register", width="8", label="OUT",
             labelloc="east"))

    # --- 写地址译码器 (x=860, y=850) ---
    add(comp("2", "(860,930)", "Decoder", width="2"))

    # --- 设备输入 (x=1000, y=980) ---
    add(comp("0", "(1000,980)", "Constant", width="8", value="0x00"))

    # LED Bar 请在 Logisim 中手动添加: Input/Output -> LED Bar (Segments=8, One Wire)
    # 放置在 OUT 寄存器右侧约 (1400,720) 处

    # ==============================================
    # 渐进测试连线 (按组添加，方便定位问题)
    # ==============================================
    def wire(fx, fy, tx, ty):
        L.append(IND + f'<wire from="({fx},{fy})" to="({tx},{ty})"/>')

    # --- 第1组: clk (1 wire, 已验证) ---
    wire(80, 100, 190, 115)     # clk → PC

    # --- 第2组: GPR 读口 (2 wires, 远离 ROM 区域) ---
    wire(800, 60, 910, 74)      # R0.Q → rMux1_ab.in0
    wire(970, 80, 1030, 124)    # rMux1_ab.out → rMux1_top.in0

    if _max_group < 3: return '
'.join(L) + '
'  # CUT
    # --- 第3组: PC 更新环路 (2 wires, PC 列内部) ---
    wire(245, 140, 160, 310)    # PC.Q → PC_Adder.A
    wire(245, 320, 160, 140)    # PC_Adder.out → PC.D

    if _max_group < 4: return '
'.join(L) + '
'  # CUT
    # --- 第4组: PC_Mux 数据 (2 wires) ---
    wire(230, 450, 350, 442)    # Const(1) → PC_Mux.in0
    wire(230, 540, 350, 458)    # SignExt.out → PC_Mux.in1

    if _max_group < 5: return '
'.join(L) + '
'  # CUT
    # --- 第5组: 取指译码 (3 wires, 经过 ROM 附近) ---
    wire(245, 140, 335, 120)    # PC.Q → ROM.A
    wire(435, 120, 605, 140)    # ROM.D → Splitter.in
    wire(550, 132, 630, 355)    # Splitter.fan0 → opcode Decoder.sel

    w('  </circuit>')
    w('</project>')
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    xml = generate()
    for path in ["Logisim/sCPU_F6.circ", "sCPU_F6.circ"]:
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
    comps = len(re.findall(r'<comp ', xml))
    wires = len(re.findall(r'<wire ', xml))
    print(f"[OK] {comps} components, {wires} wires -> Logisim/sCPU_F6.circ")
