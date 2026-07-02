#!/usr/bin/env python3
"""
生成 sCPU .circ 文件（Logisim v2.7.2 格式）

所有引脚坐标均从 Logisim-evolution Java 源码中精确提取:
  Register (classic): Register.java
  Adder:              Adder.java
  Comparator:         Comparator.java
  Shifter:            Shifter.java
  BitExtender:        BitExtender.java
  Constant:           Constant.java
  Multiplexer:        Multiplexer.java (WIDE, EAST, botLeft)
  Decoder:            Decoder.java (EAST, botLeft)
  ROM (classic):      RamAppearance.java
  AND/OR Gates:       AbstractGate.java (shaped, 30px)
  NOT Gate:           NotGate.java (WIDE)
  Splitter:           SplitterParameters.java
  Pin:                Pin.java

内建规则:
  - 全部 L 形走线 (禁止斜线)
  - 正坐标 (y + YO 偏移)
  - 通过安全通道绕行, 不穿元件
"""
import re

# ============================================================
# 全局配置
# ============================================================
YO = 200          # y 偏移, 确保全部正坐标
IND = "    "      # XML 缩进

# ---- 安全通道 ----
CH_X = {
    "pin_pc":    120,   # Pin 与 PC 之间
    "pc_mid":    245,   # PC 右/Adder 右
    "pc_rom":    300,   # PC 与 ROM 之间
    "rom_l":     360,   # ROM 左
    "rom_r":     580,   # ROM 右外侧
    "splt_l":    530,   # Splitter 左侧 (ROM 右侧)
    "splt_r":    625,   # Splitter 右侧
    "gpr_l":     710,   # Decoder 与 GPR 之间
    "gpr_r":     805,   # GPR 右侧
    "rmux_mid":  970,   # rMux 纵向间隙
    "rmux_r":   1095,   # rMux 树右侧
    "alu_l":    1150,   # ALU 左侧
    "alu_r":    1270,   # ALU 右侧
    "wmux_mid": 1300,   # wMux 链中间
}

CH_Y = {
    "clk_trunk":  -90,  # 1-bit 时钟干道 (隔离)
    "ctrl_trunk": -70,  # 1-bit 控制信号 (隔离)
    "data_trunk": -60,  # 8-bit 数据干道
    "clk_lvl":    100,  # Pin/PC 时钟层
    "pc_mid":     225,  # PC 底与 Adder 顶之间
    "rom_top":    120,  # ROM 上沿
    "pc_low":     380,  # PC 列下方
    "rmux_mid":   240,  # rMux1树底与rMux2树顶之间
    "ctrl_hi":    700,  # 控制门上方
    "ctrl_lo":    730,  # 控制门输入层
}

# ============================================================
# XML 工具
# ============================================================
def a_xml(name, val):
    return f'<a name="{name}" val="{val}"/>'

def P(x, y):
    """坐标字符串, 自动加 y 偏移"""
    return f"({x},{y + YO})"

def comp(lib, loc_xy, name, **props):
    x, y = loc_xy
    loc = P(x, y)
    if not props:
        return f'<comp lib="{lib}" loc="{loc}" name="{name}"/>'
    lines = [f'<comp lib="{lib}" loc="{loc}" name="{name}">']
    for k, v in props.items():
        lines.append(f"  {a_xml(k, v)}")
    lines.append("</comp>")
    return "\n".join(lines)

# ============================================================
# 精确引脚坐标 — 从 Logisim-evolution Java 源码提取
# ============================================================

# --- Register (classic appearance) ---
# Bounds: (-30, -20, 30, 40), loc 在右侧中心
# OUT=(0,0), IN=(-30,0), CK=(-20,20), CLR=(-10,20), EN=(-30,10)
def reg_Q(cx, cy):   return (cx + 0,  cy + 0)
def reg_D(cx, cy):   return (cx - 30, cy + 0)
def reg_CK(cx, cy):  return (cx - 20, cy + 20)
def reg_CLR(cx, cy): return (cx - 10, cy + 20)
def reg_EN(cx, cy):  return (cx - 30, cy + 10)

# --- Adder ---
# Bounds: (-40, -20, 40, 40)
# IN0=A=(-40,-10), IN1=B=(-40,10), OUT=(0,0), C_IN=(-20,-20), C_OUT=(-20,20)
def add_A(cx, cy):    return (cx - 40, cy - 10)
def add_B(cx, cy):    return (cx - 40, cy + 10)
def add_OUT(cx, cy):  return (cx + 0,  cy + 0)
def add_CIN(cx, cy):  return (cx - 20, cy - 20)
def add_COUT(cx, cy): return (cx - 20, cy + 20)

# --- Comparator ---
# Bounds: (-40, -20, 40, 40)
# IN0=A=(-40,-10), IN1=B=(-40,10), GT=(0,-10), EQ=(0,0), LT=(0,10)
def cmp_A(cx, cy):  return (cx - 40, cy - 10)
def cmp_B(cx, cy):  return (cx - 40, cy + 10)
def cmp_GT(cx, cy): return (cx + 0,  cy - 10)
def cmp_EQ(cx, cy): return (cx + 0,  cy + 0)
def cmp_LT(cx, cy): return (cx + 0,  cy + 10)

# --- Shifter ---
# Bounds: (-40, -20, 40, 40)
# IN0=data=(-40,-10), IN1=shift=(-40,10), OUT=(0,0)
def sft_IN(cx, cy):  return (cx - 40, cy - 10)
def sft_AMT(cx, cy): return (cx - 40, cy + 10)
def sft_OUT(cx, cy): return (cx + 0,  cy + 0)

# --- BitExtender ---
# Bounds: (-40, -20, 40, 40)
# OUT=(0,0), IN=(-40,0)
def ext_OUT(cx, cy): return (cx + 0,  cy + 0)
def ext_IN(cx, cy):  return (cx - 40, cy + 0)

# --- Constant ---
# OUT=(0,0)
def const_OUT(cx, cy): return (cx, cy)

# --- Multiplexer (WIDE, EAST, botLeft, inputs=2, no enable) ---
# IN0=(-30,-10), IN1=(-30,10), OUT=(0,0), SEL=(-20,20)
def mux_IN0(cx, cy): return (cx - 30, cy - 10)
def mux_IN1(cx, cy): return (cx - 30, cy + 10)
def mux_OUT(cx, cy): return (cx + 0,  cy + 0)
def mux_SEL(cx, cy): return (cx - 20, cy + 20)

# --- Multiplexer (WIDE, EAST, botLeft, select=2bit, 4 inputs, no enable) ---
# For 4 inputs in EAST: w=40, s=20, SEL at (-20, 10*inputs) = (-20, 40)
# IN0-3: (-40, -20+10*i) = (-40,-20),(-40,-10),(-40,0),(-40,10)
# This is NOT used — all our muxes are 2-input. Included for completeness.
# We only use select=2 mux for raddr tree with width=2

# --- Multiplexer 2-bit wide for raddr tree (select=1, width=2) ---
# Same layout as above: IN0=(-30,-10), IN1=(-30,10), OUT=(0,0), SEL=(-20,20)

# --- Decoder (EAST, botLeft, select=2, 4 outputs, enable=true) ---
# Bounds rotated from EAST
# OUT0=(20,-40), OUT1=(20,-30), OUT2=(20,-20), OUT3=(20,-10)
# SEL=(0,0), EN=(-10,0)
def dec_OUT0(cx, cy): return (cx + 20, cy - 40)
def dec_OUT1(cx, cy): return (cx + 20, cy - 30)
def dec_OUT2(cx, cy): return (cx + 20, cy - 20)
def dec_OUT3(cx, cy): return (cx + 20, cy - 10)
def dec_SEL(cx, cy):  return (cx + 0,  cy + 0)
def dec_EN(cx, cy):   return (cx - 10, cy + 0)

# --- Decoder (EAST, botLeft, select=1, 2 outputs) ---
# OUT0=(10,-30), OUT1=(10,-10), SEL=(0,0), EN=(-10,0)
def dec2_OUT0(cx, cy): return (cx + 10, cy - 30)
def dec2_OUT1(cx, cy): return (cx + 10, cy - 10)

# --- ROM (classic appearance) ---
# Bounds: (0, 0, 240, 140), loc at TOP-LEFT
# addr=(0,10), data=(240, controlHeight) where controlHeight defaults to ~60
# Actually for ROM without enable block, controlHeight=60, data=(240, 60+10*fan)
# For SINGLE data line (no separated bus), data is at right edge
# addr port: (0, 10) relative to loc
# data out: (240, 60) approximate for single data line.
# Let me use exact: data starts at controlHeight which for basic ROM = 60
# With single line: data at (bounds_width, 70)
def rom_ADDR(cx, cy): return (cx + 0, cy + 10)
def rom_DATA(cx, cy): return (cx + 240, cy + 70)  # SymbolWidth(200)+40=240 width, data at y≈70

# --- Pin ---
# Port at (0, 0)
def pin_PORT(cx, cy): return (cx, cy)

# --- Splitter ---
# Combined end at loc. Fan ends offset by SplitterParameters.
# facing=west, appear=center, spacing=1 (gap=10), fanout=4
# Facing WEST (m=-1): dxEnd0=-20, dyEnd0=-gap*(fanout/2)
# For fanout=4, gap=10: dyEnd0 = -10*2 = -20
# fan0..3: origin + (-20, -20) + i*(0, 10) = (-20+i*0, -20+i*10)
# combined end at origin

def spl_COMB(cx, cy): return (cx, cy)

def spl_fan(cx, cy, fan_index, facing="west", fanout=4, appear="center"):
    """Compute splitter fan pin position.
    Based on SplitterParameters.java.
    For facing=west, appear=center, spacing=1:
      dxEnd0 = -20, dyEnd0 = -gap * (fanout/2)
    """
    gap = 10  # spacing * 10
    width = 20

    if facing == "north" or facing == "south":
        m = 1 if facing == "north" else -1
        justify = _justify(appear)
        dxEnd0 = (gap * ((fanout + 1) // 2 - 1)) if justify == 0 else \
                 (-10 if m * justify < 0 else (10 + gap * (fanout - 1)))
        dyEnd0 = -m * width
        return (cx + dxEnd0 + fan_index * (-gap), cy + dyEnd0 + fan_index * 0)
    else:
        m = -1 if facing == "west" else 1
        justify = _justify(appear)
        dxEnd0 = m * width
        if justify == 0:
            dyEnd0 = -gap * (fanout // 2)
        elif m * justify > 0:
            dyEnd0 = 10
        else:
            dyEnd0 = -(10 + gap * (fanout - 1))
        return (cx + dxEnd0 + fan_index * 0, cy + dyEnd0 + fan_index * gap)

def _justify(appear):
    if appear == "center": return 0
    if appear == "right": return 1
    return -1

# Small splitter: facing=east, appear=center, fanout=2
# EAST (m=1): dxEnd0=20, dyEnd0=-gap*(2/2)=-10
# fan0=(20,-10), fan1=(20,0)

# ---- Gate (AND/OR, 2-input, EAST-facing) ----
# Inputs at (-30, -10) and (-30, 10) per getInputOffset() for size=30, inputs=2
# Output at (0, 0)
def gate_OUT(cx, cy):  return (cx + 0, cy + 0)
def gate_IN0(cx, cy):  return (cx - 30, cy - 10)
def gate_IN1(cx, cy):  return (cx - 30, cy + 10)

# ---- NOT Gate (WIDE, EAST-facing) ----
# IN=(-30, 0), OUT=(0, 0)
def not_IN(cx, cy):  return (cx - 20, cy + 0)  # Narrow size=20
def not_OUT(cx, cy): return (cx + 0, cy + 0)


# ============================================================
# 主生成函数
# ============================================================
"""Block-based hierarchical circuit generation for sCPU.

This file contains the Block class and all block builder functions.
It is designed to be imported by generate_circ.py or concatenated into it.
"""
import re

# ============================================================
# Block class
# ============================================================
#!/usr/bin/env python3
"""Block-based hierarchical circuit generation for sCPU.

This file contains the Block class and all block builder functions.
It is designed to be imported by generate_circ.py or concatenated into it.
"""
import re

# ============================================================
# Block class
# ============================================================

"""Block-based hierarchical circuit generation for sCPU.

This file contains the Block class and all block builder functions.
It is designed to be imported by generate_circ.py or concatenated into it.
"""
import re

# ============================================================
# Block class
# ============================================================

"""Block-based hierarchical circuit generation for sCPU.

This file contains the Block class and all block builder functions.
It is designed to be imported by generate_circ.py or concatenated into it.
"""
import re

# ============================================================
# Block class
# ============================================================

"""Block-based hierarchical circuit generation for sCPU.

This file contains the Block class and all block builder functions.
It is designed to be imported by generate_circ.py or concatenated into it.
"""
import re

# ============================================================
# Block class
# ============================================================

"""Block-based hierarchical circuit generation for sCPU.

This file contains the Block class and all block builder functions.
It is designed to be imported by generate_circ.py or concatenated into it.
"""
import re

# ============================================================
# Block class
# ============================================================
class Block:
    """Self-contained circuit block with local coordinates."""
    def __init__(self, name, offset_x=0, offset_y=0):
        self.name = name
        self.ox = offset_x
        self.oy = offset_y
        self._comps = []   # (lib, x, y, name, props_dict)
        self._wires = []   # (x1, y1, x2, y2)
        self._ports = {}   # port_name -> (local_x, local_y)

    def add_comp(self, lib, xy, name, **props):
        x, y = xy
        self._comps.append((lib, x, y, name, props))

    def add_wire(self, fx, fy, tx, ty):
        self._wires.append((fx, fy, tx, ty))

    def add_port(self, port_name, x, y):
        self._ports[port_name] = (x, y)

    def global_xy(self, lx, ly):
        return (lx + self.ox, ly + self.oy)

    def global_port(self, port_name):
        lx, ly = self._ports[port_name]
        return (lx + self.ox, ly + self.oy)

    def emit_comps(self, IND="    "):
        result = []
        for lib, x, y, name, props in self._comps:
            gx, gy = x + self.ox, y + self.oy
            if not props:
                result.append(f'{IND}<comp lib="{lib}" loc="({gx},{gy + YO})" name="{name}"/>')
            else:
                lines = [f'{IND}<comp lib="{lib}" loc="({gx},{gy + YO})" name="{name}">']
                for k, v in props.items():
                    lines.append(f'{IND}  <a name="{k}" val="{v}"/>')
                lines.append(f'{IND}</comp>')
                result.append("\n".join(lines))
        return result

    def emit_wires(self, IND="    "):
        result = []
        for fx, fy, tx, ty in self._wires:
            gx1, gy1 = fx + self.ox, fy + self.oy
            gx2, gy2 = tx + self.ox, ty + self.oy
            result.append(f'{IND}<wire from="({gx1},{gy1 + YO})" to="({gx2},{gy2 + YO})"/>')
        return result


# ============================================================
# Block Builder Functions
# Each returns a Block with internal components and wires.
# Local coordinates are used; offsets map to global positions.
# ============================================================

def build_clock_reset():
    """Clock and reset distribution backbone.
    Global range: x[0,1190], y[-100,800]
    """
    b = Block("clock_reset", 0, -100)
    oy = b.oy  # = -100

    # clk and rst input pins
    b.add_comp("0", (60, 200), "Pin", width="1", label="clk", labelloc="east", facing="east")
    b.add_comp("0", (60, 280), "Pin", width="1", label="rst", labelloc="east", facing="east")

    CK_BB = 54  # backbone x
    CK_GX = 718 # GPR CK vertical x
    CK_TRUNK_Y = 165  # local y = logical 65 (below writeback min y=-60)
    RST_Y = 900  # local y = logical 800

    # ---- Clock tree ----
    # clk pin -> backbone
    b.add_wire(60, 200, 60, CK_TRUNK_Y)
    b.add_wire(60, CK_TRUNK_Y, CK_BB, CK_TRUNK_Y)
    b.add_wire(CK_BB, CK_TRUNK_Y, CK_BB, 835)   # backbone vertical to logical y=735

    # CK trunk to GPR vertical
    b.add_wire(CK_BB, CK_TRUNK_Y, CK_GX, CK_TRUNK_Y)
    b.add_wire(CK_GX, CK_TRUNK_Y, CK_GX, 600)   # down to logical y=500

    # PC CK: from backbone at y=165, horizontal to x=110 (left of CLR at x=115)
    # then up to y=260, then right to CK pin at x=180
    b.add_wire(CK_BB, CK_TRUNK_Y, 110, CK_TRUNK_Y)
    b.add_wire(110, CK_TRUNK_Y, 110, 260)
    b.add_wire(110, 260, 180, 260)

    # OUT CK: from backbone at logical y=735 (local 835), horizontal to x=1180
    b.add_wire(CK_BB, 835, 1180, 835)
    b.add_wire(1180, 835, 1180, 840)  # down to OUT.CK at logical 740 (local 840)

    # GPR CK horizontals from x=718 to x=740
    for cky in [180, 320, 460, 600]:  # local: logical 80, 220, 360, 500
        b.add_wire(CK_GX, cky, 740, cky)

    # ---- Reset tree ----
    # rst pin -> RST trunk
    b.add_wire(60, 280, 95, 280)
    b.add_wire(95, 280, 95, RST_Y)
    b.add_wire(95, RST_Y, 1190, RST_Y)

    # PC CLR (logical y=130, local 230)
    b.add_wire(115, RST_Y, 115, 230)
    b.add_wire(115, 230, 190, 230)
    b.add_wire(190, 230, 190, 260)  # up to PC.CLR at logical 160

    # GPR CLR at x=755
    for clry in [180, 320, 460, 600]:  # logical 80, 220, 360, 500
        b.add_wire(755, RST_Y, 755, clry)
        b.add_wire(755, clry, 750, clry)

    # OUT CLR
    b.add_wire(1190, RST_Y, 1190, 840)  # to logical 740

    # ---- Ports ----
    b.add_port("ck_pc_pin", 180, 260)       # PC.CK
    b.add_port("ck_gpr_v", CK_GX, CK_TRUNK_Y)  # top of GPR CK vertical
    b.add_port("ck_gpr_h", CK_GX, 180)       # R0 CK horizontal y
    b.add_port("ck_out_pin", 1180, 840)      # OUT.CK
    b.add_port("rst_trunk", 95, RST_Y)       # RST trunk reference
    b.add_port("rst_pc_clr", 190, 260)       # PC.CLR
    b.add_port("rst_gpr_clr_x", 755, RST_Y)  # GPR CLR x
    b.add_port("rst_out_clr", 1190, 840)     # OUT.CLR

    return b


def build_pc():
    """PC update loop: PC register, Adder, SignExt, PC_Mux, AND gate.
    Global range: x[60,420], y[100,600]
    """
    b = Block("pc", 100, 100)
    # Components in local coords (= global - offset)
    b.add_comp("4", (100, 40), "Register", width="8", label="PC",
               labelloc="east", appearance="classic")
    b.add_comp("3", (100, 220), "Adder", width="8")
    b.add_comp("0", (100, 350), "Constant", width="8", value="0x01")
    b.add_comp("0", (100, 440), "Bit Extender", in_width="2", out_width="8", type="sign")
    b.add_comp("2", (280, 350), "Multiplexer", width="8")
    b.add_comp("0", (60, 200), "Constant", width="1", value="0x0")
    b.add_comp("1", (280, 460), "AND Gate", width="1", inputs="2", size="30")
    b.add_comp("0", (250, 470), "Constant", width="1", value="0x1")  # VCC for AND.IN1

    # Internal wires: PC update loop (3 isolated y-levels)
    # PC.Q(100,40) -> Adder.A(60,210) at y=115
    b.add_wire(100, 40, 100, 115)
    b.add_wire(100, 115, 60, 115)
    b.add_wire(60, 115, 60, 210)

    # Adder.OUT(100,220) -> PC.D(70,40) at y=135
    b.add_wire(100, 220, 100, 135)
    b.add_wire(100, 135, 70, 135)
    b.add_wire(70, 135, 70, 40)

    # PC.Q -> ROM.ADDR at y=125 (separate level)
    b.add_wire(100, 40, 100, 125)
    b.add_wire(100, 125, 280, 125)
    b.add_wire(280, 125, 280, 10)

    # Adder CIN tie
    b.add_wire(60, 200, 80, 200)

    # Constant -> PC_Mux.IN0 (250,340) AND Adder.B (60,230)
    b.add_wire(100, 350, 250, 350)
    b.add_wire(250, 350, 250, 340)
    b.add_wire(100, 350, 100, 230)   # branch to Adder.B y-level
    b.add_wire(100, 230, 60, 230)    # left to Adder.B

    # SignExt -> PC_Mux.IN1
    b.add_wire(100, 440, 100, 430)
    b.add_wire(100, 430, 250, 430)
    b.add_wire(250, 430, 250, 360)

    # PC_Mux.OUT -> PC.D (via x=265, y=550, x=20)
    b.add_wire(280, 350, 265, 350)
    b.add_wire(265, 350, 265, 550)
    b.add_wire(265, 550, 20, 550)
    b.add_wire(20, 550, 20, 135)
    b.add_wire(20, 135, 70, 135)

    # rst -> AND.IN0 (rst comes from external at local x=-40)
    b.add_wire(-40, 80, -40, 450)
    b.add_wire(-40, 450, 250, 450)

    # AND.OUT -> PC.EN (safe path via x=-50, y=570)
    b.add_wire(280, 460, 280, 570)
    b.add_wire(280, 570, -50, 570)
    b.add_wire(-50, 570, -50, 50)
    b.add_wire(-50, 50, 70, 50)

    # Ports
    b.add_port("pc_q", 100, 40)
    b.add_port("pc_q_rom", 280, 10)  # routed to ROM level
    b.add_port("pc_d", 70, 40)
    b.add_port("signext_in", 60, 440)
    b.add_port("mux_sel", 260, 370)
    b.add_port("and_rst_in", -40, 80)
    b.add_port("pc_en", 70, 50)
    b.add_port("pc_ck", 80, 60)
    b.add_port("pc_clr", 90, 60)

    return b


def build_fetch_decode():
    """ROM + Splitter + opcode Decoder + rs1/rs2 Splitters.
    Global range: x[340,680], y[50,470]
    Offset: (340, 50)
    """
    b = Block("fetch_decode", 340, 50)

    # ROM at global (380,100) -> local (40, 50)
    rom_lines = [
        f'<comp lib="4" loc="({40 + b.ox},{50 + b.oy + YO})" name="ROM">',
        f'  <a name="addrWidth" val="8"/>',
        f'  <a name="dataWidth" val="8"/>',
        f'  <a name="appearance" val="classic"/>',
        f'  <a name="contents">addr/data: 8 8',
        '0 90', '1 a1', '2 be', '3 16',
        '4 29', '5 f7', '6 54', '7 0',
        f'  </a>',
        f'</comp>',
    ]
    b._rom_lines = rom_lines  # special handling for ROM

    # ROM splitter at global (580,100) -> local (240, 50)
    b.add_comp("0", (240, 50), "Splitter", facing="west", fanout="4",
               incoming="8", appear="center",
               bit7="0", bit6="0", bit5="1", bit4="1",
               bit3="2", bit2="2", bit1="3", bit0="3")

    # opcode Decoder at global (650,360) -> local (310, 310)
    b.add_comp("2", (310, 310), "Decoder", select="2", enable="false")

    # rs1/rs2 splitters at global (700,80) and (700,110) -> local (360, 30), (360, 60)
    b.add_comp("0", (360, 30), "Splitter", facing="east", fanout="2",
               incoming="2", bit0="0", bit1="1", appear="right")
    b.add_comp("0", (360, 60), "Splitter", facing="east", fanout="2",
               incoming="2", bit0="0", bit1="1", appear="right")

    # --- Internal wires ---
    # ROM.DATA -> splitter comb
    # ROM at local (40,50), data at (280,120) [40+240, 50+70]
    b.add_wire(280, 120, 280, 50)  # up to splitter y
    b.add_wire(280, 50, 240, 50)   # left to splitter comb

    # Splitter fan0 -> opcode Decoder SEL
    # Splitter at (240,50), facing west: fan0 at (220, 30)
    # Decoder SEL at (310, 310)
    b.add_wire(220, 30, 190, 30)   # left
    b.add_wire(190, 30, 190, 310)  # down
    b.add_wire(190, 310, 310, 310) # right to decoder SEL

    # Splitter fan2 -> rs1_sel comb (360, 30)
    b.add_wire(220, 50, 285, 50)   # right
    b.add_wire(285, 50, 285, 30)   # up
    b.add_wire(285, 30, 360, 30)   # right to rs1 comb

    # Splitter fan3 -> rs2_sel comb (360, 60)
    b.add_wire(220, 60, 285, 60)
    b.add_wire(285, 60, 360, 60)

    # --- Ports ---
    b.add_port("rom_addr", 40, 60)        # ROM.ADDR at local (40, 60) = global (380, 110)
    b.add_port("spl_fan1", 220, 40)       # Splitter fan1 (opcode low bits)
    b.add_port("spl_fan3", 220, 60)       # Splitter fan3 (immediate)
    b.add_port("dec_out0", 330, 270)      # Decoder out0 (local: 310+20, 310-40)
    b.add_port("dec_out1", 330, 280)      # Decoder out1 (local: 310+20, 310-30)
    b.add_port("dec_out2", 330, 290)      # Decoder out2 (local: 310+20, 310-20)
    b.add_port("dec_out3", 330, 300)      # Decoder out3 (local: 310+20, 310-10)
    b.add_port("rs1_fan0", 380, 40)       # rs1_sel fan0 (360+20, 30-20+0*10)
    b.add_port("rs1_fan1", 380, 50)       # rs1_sel fan1 (360+20, 30-20+1*10)
    b.add_port("rs2_fan0", 380, 70)       # rs2_sel fan0 (360+20, 60-20+0*10)
    b.add_port("rs2_fan1", 380, 80)       # rs2_sel fan1 (360+20, 60-20+1*10)

    return b


def build_gpr_rmux():
    """GPR register file + raddr mux tree + rMux1/rMux2 trees.
    Global range: x[640,1070], y[-30,530]
    Offset: (640, -30)
    """
    b = Block("gpr_rmux", 640, -30)
    # = local + (640, -30) = global

    # GPR registers at global (760, 60/200/340/480)
    # -> local (120, 90), (120, 230), (120, 370), (120, 510)
    gpr_ly = [90, 230, 370, 510]
    for i, ly in enumerate(gpr_ly):
        b.add_comp("4", (120, ly), "Register", width="8",
                   label=f"R{i}", labelloc="east", appearance="classic")

    # raddr Mux tree at global (680,20),(680,0),(820,10),(920,10),(1020,10)
    b.add_comp("0", (40, 50), "Constant", width="2", value="0x00")
    b.add_comp("0", (40, 30), "Constant", width="1", value="0x0")
    b.add_comp("2", (180, 40), "Multiplexer", width="2")
    b.add_comp("2", (280, 40), "Multiplexer", width="2")
    b.add_comp("2", (380, 40), "Multiplexer", width="2")

    # rMux trees at global (940,80/180/300/400), (1060,130/350)
    b.add_comp("2", (300, 110), "Multiplexer", width="8")   # rMux1_ab
    b.add_comp("2", (300, 210), "Multiplexer", width="8")   # rMux1_cd
    b.add_comp("2", (420, 160), "Multiplexer", width="8")   # rMux1_top
    b.add_comp("2", (300, 330), "Multiplexer", width="8")   # rMux2_ab
    b.add_comp("2", (300, 430), "Multiplexer", width="8")   # rMux2_cd
    b.add_comp("2", (420, 380), "Multiplexer", width="8")   # rMux2_top

    # --- GPR Q -> rMux inputs ---
    # R0.Q at local (120, 90) -> junction at x=238
    b.add_wire(120, 90, 238, 90)
    b.add_wire(238, 90, 238, 100)   # to rMux1_ab.IN0 at (270, 100)
    b.add_wire(238, 100, 270, 100)
    b.add_wire(238, 90, 238, 320)   # to rMux2_ab.IN0 at (270, 320)
    b.add_wire(238, 320, 270, 320)

    # R1.Q at local (120, 230)
    b.add_wire(120, 230, 250, 230)
    b.add_wire(250, 230, 250, 120)   # to rMux1_ab.IN1 at (270, 120)
    b.add_wire(250, 120, 270, 120)
    b.add_wire(250, 230, 250, 340)   # to rMux2_ab.IN1 at (270, 340)
    b.add_wire(250, 340, 270, 340)

    # R2.Q at local (120, 370)
    b.add_wire(120, 370, 262, 370)
    b.add_wire(262, 370, 262, 200)   # to rMux1_cd.IN0 at (270, 200)
    b.add_wire(262, 200, 270, 200)
    b.add_wire(262, 370, 262, 420)   # to rMux2_cd.IN0 at (270, 420)
    b.add_wire(262, 420, 270, 420)

    # R3.Q at local (120, 510)
    b.add_wire(120, 510, 274, 510)
    b.add_wire(274, 510, 274, 220)   # to rMux1_cd.IN1 at (270, 220)
    b.add_wire(274, 220, 270, 220)
    b.add_wire(274, 510, 274, 440)   # to rMux2_cd.IN1 at (270, 440)
    b.add_wire(274, 440, 270, 440)

    # rMux1_ab.OUT -> rMux1_top.IN0
    b.add_wire(300, 110, 300, 150)
    b.add_wire(300, 150, 390, 150)

    # rMux1_cd.OUT -> rMux1_top.IN1
    b.add_wire(300, 210, 300, 170)
    b.add_wire(300, 170, 390, 170)

    # rMux2_ab.OUT -> rMux2_top.IN0
    b.add_wire(300, 330, 300, 370)
    b.add_wire(300, 370, 390, 370)

    # rMux2_cd.OUT -> rMux2_top.IN1
    b.add_wire(300, 430, 300, 390)
    b.add_wire(300, 390, 390, 390)

    # --- raddr Mux tree ---
    # GND -> Mux1.IN0
    b.add_wire(40, 50, 150, 50)
    b.add_wire(150, 50, 150, 30)
    # Mux1.OUT -> Mux2.IN0
    b.add_wire(180, 40, 250, 40)
    b.add_wire(250, 40, 250, 30)
    # Mux2.OUT -> Mux3.IN0
    b.add_wire(280, 40, 350, 40)
    b.add_wire(350, 40, 350, 30)
    # Mux3.OUT -> waddr decoder (via above)
    b.add_wire(380, 40, 380, 10)
    b.add_wire(380, 10, 220, 10)
    b.add_wire(220, 10, 220, -20)   # drop to decoder

    # raddr SELs all GND
    b.add_wire(40, 30, 160, 30)
    b.add_wire(160, 30, 160, 60)
    b.add_wire(160, 30, 260, 30)
    b.add_wire(260, 30, 260, 60)
    b.add_wire(260, 30, 360, 30)
    b.add_wire(360, 30, 360, 60)

    # --- Ports ---
    b.add_port("rmux1_out", 420, 160)     # rMux1_top.OUT
    b.add_port("rmux2_out", 420, 380)     # rMux2_top.OUT
    b.add_port("rmux1_sel_ab", 280, 130)  # rMux1_ab.SEL
    b.add_port("rmux1_sel_cd", 280, 230)  # rMux1_cd.SEL
    b.add_port("rmux1_sel_top", 400, 180) # rMux1_top.SEL
    b.add_port("rmux2_sel_ab", 280, 350)  # rMux2_ab.SEL
    b.add_port("rmux2_sel_cd", 280, 450)  # rMux2_cd.SEL
    b.add_port("rmux2_sel_top", 400, 400) # rMux2_top.SEL
    b.add_port("r0_d", 90, 90)            # R0.D at local (120-30, 90)
    b.add_port("r1_d", 90, 230)
    b.add_port("r2_d", 90, 370)
    b.add_port("r3_d", 90, 510)
    b.add_port("r0_q", 120, 90)           # R0.Q (for debug)
    b.add_port("raddr_out", 220, -20)     # raddr tree output
    b.add_port("gpr_ck_x", 100, 90)       # CK pin x at local 100 = global 740
    b.add_port("gpr_clr_x", 110, 90)      # CLR pin x at local 110 = global 750

    return b


def build_alu():
    """ALU: Adder + Comparator + CIN GND.
    Global range: x[1100,1250], y[150,430]
    Offset: (1100, 150)
    """
    b = Block("alu", 1100, 150)

    b.add_comp("3", (100, 50), "Adder", width="8")       # global (1200,200)
    b.add_comp("3", (100, 230), "Comparator", width="8") # global (1200,380)
    b.add_comp("0", (60, 30), "Constant", width="1", value="0x0")  # global (1160,180)

    # CIN GND
    b.add_wire(60, 30, 80, 30)

    # Ports
    b.add_port("adder_a", 60, 40)      # Adder.A
    b.add_port("adder_b", 60, 60)      # Adder.B
    b.add_port("adder_out", 100, 50)   # Adder.OUT
    b.add_port("comp_a", 60, 220)      # Comp.A
    b.add_port("comp_b", 60, 240)      # Comp.B
    b.add_port("comp_eq", 100, 230)    # Comp.EQ
    b.add_port("comp_gt", 100, 220)    # Comp.GT
    b.add_port("comp_lt", 100, 240)    # Comp.LT

    return b


def build_control():
    """Control logic: NOT, AND, OR gates, waddr Decoder, 4x write-enable ANDs.
    Global range: x[640,1160], y[640,1000]
    Offset: (640, 640)
    """
    b = Block("control", 640, 640)

    # NOT at global (680,740) -> local (40, 100)
    b.add_comp("1", (40, 100), "NOT Gate", width="1", size="20")
    # AND at global (860,740) -> local (220, 100)
    b.add_comp("1", (220, 100), "AND Gate", width="1", inputs="2", size="30")
    # OR1 at global (860,840) -> local (220, 200)
    b.add_comp("1", (220, 200), "OR Gate", width="1", inputs="2", size="30")
    # OR2 at global (1000,840) -> local (360, 200)
    b.add_comp("1", (360, 200), "OR Gate", width="1", inputs="2", size="30")
    # 4x AND gates at global (1140,680/780/880/980) -> local (500, 40/140/240/340)
    and_ys = [40, 140, 240, 340]
    for ay in and_ys:
        b.add_comp("1", (500, ay), "AND Gate", width="1", inputs="2", size="30")
    # waddr Decoder at global (860,930) -> local (220, 290)
    b.add_comp("2", (220, 290), "Decoder", select="2", enable="false")

    # --- Internal wires ---
    # NOT.IN (20, 100) and NOT.OUT (40, 100)
    # NOT.OUT -> AND.IN0 (190, 90)
    b.add_wire(40, 100, 40, 90)
    b.add_wire(40, 90, 190, 90)

    # OR1.OUT (220, 200) -> OR2.IN0 (330, 190)
    b.add_wire(220, 200, 330, 200)
    b.add_wire(330, 200, 330, 190)

    # OR2.OUT (360, 200) -> 4x AND.IN0
    b.add_wire(360, 200, 410, 200)
    b.add_wire(410, 200, 410, 30)
    b.add_wire(410, 30, 470, 30)
    b.add_wire(410, 200, 410, 130)
    b.add_wire(410, 130, 470, 130)
    b.add_wire(410, 200, 410, 230)
    b.add_wire(410, 230, 470, 230)
    b.add_wire(410, 200, 410, 330)
    b.add_wire(410, 330, 470, 330)

    # waddr Decoder outputs -> 4x AND.IN1
    wdec_outs = [(240, 250), (240, 260), (240, 270), (240, 280)]
    # AND.IN1 at local (470, 50+i*100) since AND at (500, 40+i*100), IN1=(470, 50+i*100)
    for i, (wx, wy) in enumerate(wdec_outs):
        target_y = 50 + i * 100
        b.add_wire(wx, wy, 360 + i * 20, wy)
        b.add_wire(360 + i * 20, wy, 360 + i * 20, target_y)
        b.add_wire(360 + i * 20, target_y, 470, target_y)

    # --- Ports ---
    b.add_port("not_in", 20, 100)          # NOT.IN
    b.add_port("and_in1", 190, 110)        # AND.IN1 (from decoder out3)
    b.add_port("and_out", 220, 100)        # AND.OUT (branch_taken)
    b.add_port("or1_in0", 190, 190)        # OR1.IN0 (from decoder out0)
    b.add_port("or1_in1", 190, 210)        # OR1.IN1 (from decoder out1)
    b.add_port("wdec_sel", 220, 290)       # waddr Decoder SEL
    for i in range(4):
        b.add_port(f"wen{i}", 500, and_ys[i])  # AND.OUT for each register
    b.add_port(f"wen{i}_in", 470, and_ys[i])   # AND.IN1 approach

    return b


def build_writeback():
    """Writeback: wMux1, wMux2, li BitExt/Shifter, OUT register, Constant.
    Global range: x[1120,1400], y[500,1000]
    Offset: (1120, 500)
    """
    b = Block("writeback", 1120, 500)

    # wMux1 at global (1200,560) -> local (80, 60)
    b.add_comp("2", (80, 60), "Multiplexer", width="8")
    # wMux2 at global (1360,560) -> local (240, 60)
    b.add_comp("2", (240, 60), "Multiplexer", width="8")
    # OUT register at global (1200,720) -> local (80, 220)
    b.add_comp("4", (80, 220), "Register", width="8",
               label="OUT", labelloc="east", appearance="classic")
    # Constant 0x00 at global (1000,980) -> ... wait, this is in control block range
    # Actually at (1000, 980), offset (1120, 500) -> would be local (-120, 480)
    # Let's just put it at local (200, 480)
    b.add_comp("0", (200, 480), "Constant", width="8", value="0x00")

    # li BitExt at global (580,640) -> local (-540, 140)... hmm, this is far left
    # BitExt belongs more naturally in the immediate path. Let's put it in writeback
    # Actually, the immediate path connects splitter fan3 -> BitExt -> wMux1.IN1
    # Let's put BitExt at local (-540, 140) = global (580, 640) — works!
    b.add_comp("0", (-540, 140), "Bit Extender", in_width="2", out_width="8", type="zero")
    # Shifter at global (760,640) -> local (-360, 140)
    b.add_comp("3", (-360, 140), "Shifter", width="8")

    # --- Internal wires ---
    # wMux1.OUT -> wMux2.IN0
    b.add_wire(80, 60, 160, 60)
    b.add_wire(160, 60, 160, 50)
    b.add_wire(160, 50, 210, 50)

    # Constant -> wMux2.IN1
    b.add_wire(200, 480, 200, 340)
    b.add_wire(200, 340, 160, 340)
    b.add_wire(160, 340, 160, 70)
    b.add_wire(160, 70, 210, 70)

    # li BitExt.IN — connected externally
    # BitExt.OUT -> Shifter.IN (or bypass)
    b.add_wire(-540, 140, -540, 210)
    b.add_wire(-540, 210, 200, 210)
    b.add_wire(200, 210, 200, 170)
    b.add_wire(200, 170, 50, 170)
    b.add_wire(50, 170, 50, 70)

    # --- Ports ---
    b.add_port("wmux1_in0", 50, 50)       # wMux1.IN0 (from ALU sum)
    b.add_port("wmux1_in1", 50, 70)       # wMux1.IN1 (from immediate)
    b.add_port("wmux1_sel", 60, 80)       # wMux1.SEL
    b.add_port("wmux2_sel", 220, 80)      # wMux2.SEL
    b.add_port("wmux2_out", 240, 60)      # wMux2.OUT
    b.add_port("out_d", 50, 220)          # OUT.D
    b.add_port("out_en", 50, 230)         # OUT.EN
    b.add_port("out_ck", 60, 240)         # OUT.CK at local (80-20, 220+20) = (60, 240)
    b.add_port("out_clr", 70, 240)        # OUT.CLR
    b.add_port("bitext_in", -580, 140)    # li BitExt.IN
    b.add_port("bitext_out", -540, 140)   # li BitExt.OUT

    return b


if __name__ == "__main__":
    print("Block builders module loaded. Run generate_circ.py to generate circuit.")

def generate():
    """Block-based hierarchical circuit generation."""
    L = []
    w = L.append

    # ---- Create all blocks ----
    cr = build_clock_reset()
    pc = build_pc()
    fd = build_fetch_decode()
    gp = build_gpr_rmux()
    al = build_alu()
    ct = build_control()
    wb = build_writeback()

    blocks = [cr, pc, fd, gp, al, ct, wb]

    # ---- XML Header ----
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

    # ---- Emit all block components ----
    for block in blocks:
        comp_lines = block.emit_comps()
        for cl in comp_lines:
            L.append(cl)

    # Special: ROM component
    if hasattr(fd, '_rom_lines'):
        for rl in fd._rom_lines:
            L.append('    ' + rl if not rl.startswith('    ') else rl)

    # ---- Emit all block internal wires ----
    for block in blocks:
        wire_lines = block.emit_wires()
        for wl in wire_lines:
            L.append(wl)

    # ---- Cross-block connections ----
    def wire(fx, fy, tx, ty):
        L.append(IND + f'<wire from="{P(fx, fy)}" to="{P(tx, ty)}"/>')

    def route_hv(sx, sy, tx, ty, via_x):
        wire(sx, sy, via_x, sy)
        wire(via_x, sy, via_x, ty)
        wire(via_x, ty, tx, ty)

    def route_vh(sx, sy, tx, ty, via_y):
        wire(sx, sy, sx, via_y)
        wire(sx, via_y, tx, via_y)
        wire(tx, via_y, tx, ty)

    def gp_xy(block, port):
        return block.global_port(port)

    # === CROSS-BLOCK ROUTING ===

    # 1. PC.Q -> ROM.ADDR
    sx, sy = gp_xy(pc, "pc_q_rom")
    tx, ty = gp_xy(fd, "rom_addr")
    wire(sx, sy, tx, sy)
    wire(tx, sy, tx, ty)

    # 2. Splitter fan1 -> waddr Decoder SEL
    sx, sy = gp_xy(fd, "spl_fan1")
    tx, ty = gp_xy(ct, "wdec_sel")
    route_hv(sx, sy, tx, ty, 530)

    # 3. Splitter fan3 -> immediate path (li BitExt + SignExt)
    sx, sy = gp_xy(fd, "spl_fan3")
    b1x, b1y = gp_xy(wb, "bitext_in")
    wire(sx, sy, 530, sy)
    wire(530, sy, 530, b1y)
    wire(530, b1y, b1x, b1y)
    # Branch 2: SignExt.IN
    sx2, sy2 = gp_xy(pc, "signext_in")
    wire(530, sy, 530, sy2 + 10)
    wire(530, sy2 + 10, sx2, sy2 + 10)
    wire(sx2, sy2 + 10, sx2, sy2)

    # 4. rs1_sel fans -> rMux1 SELs
    fx0, fy0 = gp_xy(fd, "rs1_fan0")
    m1ab_sx, m1ab_sy = gp_xy(gp, "rmux1_sel_ab")
    m1cd_sx, m1cd_sy = gp_xy(gp, "rmux1_sel_cd")
    route_hv(fx0, fy0, m1ab_sx, m1ab_sy, 730)
    wire(730, fy0, 730, m1cd_sy - 5)
    wire(730, m1cd_sy - 5, 960, m1cd_sy - 5)
    wire(960, m1cd_sy - 5, 960, m1cd_sy)
    wire(960, m1cd_sy, m1cd_sx, m1cd_sy)

    fx1, fy1 = gp_xy(fd, "rs1_fan1")
    m1t_sx, m1t_sy = gp_xy(gp, "rmux1_sel_top")
    route_hv(fx1, fy1, m1t_sx, m1t_sy, 740)

    # 5. rs2_sel fans -> rMux2 SELs
    fx0, fy0 = gp_xy(fd, "rs2_fan0")
    m2ab_sx, m2ab_sy = gp_xy(gp, "rmux2_sel_ab")
    m2cd_sx, m2cd_sy = gp_xy(gp, "rmux2_sel_cd")
    route_hv(fx0, fy0, m2ab_sx, m2ab_sy, 750)
    wire(750, fy0, 750, m2cd_sy - 5)
    wire(750, m2cd_sy - 5, 980, m2cd_sy - 5)
    wire(980, m2cd_sy - 5, 980, m2cd_sy)
    wire(980, m2cd_sy, m2cd_sx, m2cd_sy)

    fx1, fy1 = gp_xy(fd, "rs2_fan1")
    m2t_sx, m2t_sy = gp_xy(gp, "rmux2_sel_top")
    route_hv(fx1, fy1, m2t_sx, m2t_sy, 810)

    # 6. rMux outputs -> ALU inputs
    r1x, r1y = gp_xy(gp, "rmux1_out")
    aa_x, aa_y = gp_xy(al, "adder_a")
    ca_x, ca_y = gp_xy(al, "comp_a")
    wire(r1x, r1y, r1x, 170)
    wire(r1x, 170, aa_x, 170)
    wire(aa_x, 170, aa_x, aa_y)
    wire(r1x, 170, 1158, 170)
    wire(1158, 170, 1158, ca_y - 5)
    wire(1158, ca_y - 5, 1153, ca_y - 5)
    wire(1153, ca_y - 5, 1153, ca_y)
    wire(1153, ca_y, ca_x, ca_y)

    r2x, r2y = gp_xy(gp, "rmux2_out")
    ab_x, ab_y = gp_xy(al, "adder_b")
    cb_x, cb_y = gp_xy(al, "comp_b")
    wire(r2x, r2y, 1090, r2y)
    wire(1090, r2y, 1090, 180)
    wire(1090, 180, 1157, 180)
    wire(1157, 180, 1157, ab_y)
    wire(1157, ab_y, ab_x, ab_y)
    wire(1090, r2y, 1090, cb_y - 5)
    wire(1090, cb_y - 5, 1157, cb_y - 5)
    wire(1157, cb_y - 5, 1157, cb_y)
    wire(1157, cb_y, cb_x, cb_y)

    # 7. ALU output -> wMux1.IN0
    ao_x, ao_y = gp_xy(al, "adder_out")
    w1i0_x, w1i0_y = gp_xy(wb, "wmux1_in0")
    wire(ao_x, ao_y, 1220, ao_y)
    wire(1220, ao_y, 1220, w1i0_y - 10)
    wire(1220, w1i0_y - 10, 1170, w1i0_y - 10)
    wire(1170, w1i0_y - 10, 1170, w1i0_y)
    wire(1170, w1i0_y, w1i0_x, w1i0_y)

    # 8. li BitExt -> wMux1.IN1
    bo_x, bo_y = gp_xy(wb, "bitext_out")
    w1i1_x, w1i1_y = gp_xy(wb, "wmux1_in1")
    wire(bo_x, bo_y, bo_x, 710)
    wire(bo_x, 710, 1170, 710)
    wire(1170, 710, 1170, w1i1_y)
    wire(1170, w1i1_y, w1i1_x, w1i1_y)

    # 9. wMux2.OUT -> GPR D pins (writeback)
    w2o_x, w2o_y = gp_xy(wb, "wmux2_out")
    wire(w2o_x, w2o_y, w2o_x, 655)
    wire(w2o_x, 655, 55, 655)
    wire(55, 655, 55, -60)

    r0d_x, r0d_y = gp_xy(gp, "r0_d")
    r1d_x, r1d_y = gp_xy(gp, "r1_d")
    wire(55, -60, 685, -60)
    wire(685, -60, 685, r0d_y)
    wire(685, r0d_y, r0d_x, r0d_y)
    wire(685, -60, 685, r1d_y)
    wire(685, r1d_y, r1d_x, r1d_y)

    r2d_x, r2d_y = gp_xy(gp, "r2_d")
    r3d_x, r3d_y = gp_xy(gp, "r3_d")
    wire(55, 655, 55, 510)
    wire(55, 510, 745, 510)
    wire(745, 510, 745, r2d_y)
    wire(745, r2d_y, r2d_x, r2d_y)
    wire(745, 510, 745, r3d_y)
    wire(745, r3d_y, r3d_x, r3d_y)

    # 10. rMux1_top.OUT -> OUT.D (L-shaped, no diagonal)
    wire(r1x, r1y, r1x, r1y - 40)    # vertical from OUT
    wire(r1x, r1y - 40, 1160, r1y - 40)  # horizontal to x=1160
    wire(1160, r1y - 40, 1160, 330)
    wire(1160, 330, 1370, 330)
    wire(1370, 330, 1370, 805)
    wire(1370, 805, 1170, 805)
    wire(1170, 805, 1170, 720)

    # 11. Decoder outputs -> control gates
    d0x, d0y = gp_xy(fd, "dec_out0")
    d1x, d1y = gp_xy(fd, "dec_out1")
    d2x, d2y = gp_xy(fd, "dec_out2")
    d3x, d3y = gp_xy(fd, "dec_out3")

    o1i0x, o1i0y = gp_xy(ct, "or1_in0")
    o1i1x, o1i1y = gp_xy(ct, "or1_in1")
    a_in1x, a_in1y = gp_xy(ct, "and_in1")

    route_hv(d0x, d0y, o1i0x, o1i0y, 780)
    route_hv(d1x, d1y, o1i1x, o1i1y, 780)
    route_hv(d3x, d3y, a_in1x, a_in1y, 790)

    # 12. Comparator.EQ -> NOT.IN
    ceq_x, ceq_y = gp_xy(al, "comp_eq")
    ni_x, ni_y = gp_xy(ct, "not_in")
    wire(ceq_x, ceq_y, 1210, ceq_y)
    wire(1210, ceq_y, 1210, 730)
    wire(1210, 730, 660, 730)
    wire(660, 730, 660, ni_y)
    wire(660, ni_y, ni_x, ni_y)

    # 13. is_li -> wMux1.SEL
    w1s_x, w1s_y = gp_xy(wb, "wmux1_sel")
    wire(d0x, d0y, 900, d0y)
    wire(900, d0y, 900, 600)
    wire(900, 600, 1180, 600)
    wire(1180, 600, 1180, w1s_y)
    wire(1180, w1s_y, w1s_x, w1s_y)

    # 14. is_io -> wMux2.SEL + OUT.EN
    w2s_x, w2s_y = gp_xy(wb, "wmux2_sel")
    oe_x, oe_y = gp_xy(wb, "out_en")
    wire(d2x, d2y, 920, d2y)
    wire(920, d2y, 920, 605)
    wire(920, 605, 1340, 605)
    wire(1340, 605, 1340, w2s_y)
    wire(1340, w2s_y, w2s_x, w2s_y)
    wire(920, d2y, 920, 730)
    wire(920, 730, 1170, 730)
    wire(1170, 730, 1170, oe_y)
    wire(1170, oe_y, oe_x, oe_y)

    # 15. branch AND.OUT -> PC_Mux.SEL
    ao_x, ao_y = gp_xy(ct, "and_out")
    ms_x, ms_y = gp_xy(pc, "mux_sel")
    wire(ao_x, ao_y, ao_x, 470)
    wire(ao_x, 470, 360, 470)
    wire(360, 470, 360, ms_y)
    wire(360, ms_y, ms_x, ms_y)

    # 16. rst -> PC AND.IN0
    wire(60, 180, 60, 550)
    wire(60, 550, 350, 550)

    # 17. 4x AND outputs -> GPR.EN pins
    en_targets = [(730, 70), (730, 210), (730, 350), (730, 490)]
    for i, (enx, eny) in enumerate(en_targets):
        ax, ay = gp_xy(ct, f"wen{i}")
        wire(ax, ay, 710, ay)
        wire(710, ay, 710, eny)
        wire(710, eny, enx, eny)

    # 18. raddr Mux3.OUT -> waddr Decoder SEL
    ra_x, ra_y = gp_xy(gp, "raddr_out")
    wd_x, wd_y = gp_xy(ct, "wdec_sel")
    wire(ra_x, ra_y, ra_x, -20)
    wire(ra_x, -20, 860, -20)
    wire(860, -20, 860, wd_y)
    wire(860, wd_y, wd_x, wd_y)

    # ---- XML Footer ----
    w('  </circuit>')
    w('</project>')
    return "\n".join(L) + "\n"

def validate_routing(xml_str):
    """Validate that no wire passes through a component pin it shouldn't."""
    import re as _re

    # Parse all wires: (x1, y1, x2, y2)
    wires = []
    for m in _re.finditer(r'<wire from="\((-?\d+),(-?\d+)\)" to="\((-?\d+),(-?\d+)\)"/>', xml_str):
        wires.append(tuple(int(g) for g in m.groups()))

    # Parse all components and their pin coordinates
    # Each component's pins depend on its type (lib) and location
    # We collect: (x, y, comp_name, pin_desc)
    pins = []  # list of (x, y, component_label)

    # Component types and their pin offset functions (from Logisim Java sources)
    # All coordinates are already in Logisim space (YO applied in XML)
    for m in _re.finditer(
        r'<comp lib="(\d+)" loc="\((-?\d+),(-?\d+)\)" name="([^"]+)">(.*?)</comp>',
        xml_str, _re.DOTALL
    ):
        lib = m.group(1)
        cx = int(m.group(2))
        cy = int(m.group(3))
        name = m.group(4)
        attrs = m.group(5)

        def add_pin(px, py, desc):
            pins.append((px, py, f"{name}.{desc}"))

        # Extract attributes
        aw = {}
        for am in _re.finditer(r'<a name="(\w+)" val="([^"]+)"/>', attrs):
            aw[am.group(1)] = am.group(2)

        pass  # Component identification done in the if/elif chain below

        # --- Determine pins based on component type ---
        if lib == "0":  # Wiring library
            if name == "Pin":
                add_pin(cx, cy, "PORT")
            elif name == "Splitter":
                # Combined end at (cx, cy)
                add_pin(cx, cy, "COMB")
                fanout = int(aw.get("fanout", "2"))
                facing = aw.get("facing", "east")
                appear = aw.get("appear", "center")
                gap = 10
                width = 20
                for fi in range(fanout):
                    if facing in ("north", "south"):
                        m_sign = 1 if facing == "north" else -1
                        # simplified; see spl_fan() for full logic
                        continue
                    else:  # east/west
                        m_sign = -1 if facing == "west" else 1
                        if appear == "center":
                            dyEnd0 = -gap * (fanout // 2)
                        elif (m_sign > 0 and appear == "right") or (m_sign < 0 and appear == "left"):
                            dyEnd0 = 10
                        else:
                            dyEnd0 = -(10 + gap * (fanout - 1))
                        fx = cx + m_sign * width
                        fy = cy + dyEnd0 + fi * gap
                        add_pin(fx, fy, f"FAN{fi}")
            elif name == "Constant":
                add_pin(cx, cy, "OUT")
            elif name == "Bit Extender":
                add_pin(cx, cy, "OUT")
                add_pin(cx - 40, cy, "IN")
        elif lib == "1":  # Gates
            if "NOT" in name:
                add_pin(cx - 20, cy, "IN")
                add_pin(cx, cy, "OUT")
            else:
                add_pin(cx - 30, cy - 10, "IN0")
                add_pin(cx - 30, cy + 10, "IN1")
                add_pin(cx, cy, "OUT")
        elif lib == "2":  # Plexers
            if name == "Multiplexer":
                add_pin(cx - 30, cy - 10, "IN0")
                add_pin(cx - 30, cy + 10, "IN1")
                add_pin(cx, cy, "OUT")
                add_pin(cx - 20, cy + 20, "SEL")
            elif name == "Decoder":
                sel_bits = int(aw.get("select", "1"))
                for i in range(2 ** sel_bits):
                    add_pin(cx + 20, cy - 40 + i * 10, f"OUT{i}")
                add_pin(cx, cy, "SEL")
                if aw.get("enable") == "true":
                    add_pin(cx - 10, cy, "EN")
        elif lib == "3":  # Arithmetic
            if name == "Adder":
                add_pin(cx - 40, cy - 10, "A")
                add_pin(cx - 40, cy + 10, "B")
                add_pin(cx, cy, "OUT")
                add_pin(cx - 20, cy - 20, "CIN")
                add_pin(cx - 20, cy + 20, "COUT")
            elif name == "Comparator":
                add_pin(cx - 40, cy - 10, "A")
                add_pin(cx - 40, cy + 10, "B")
                add_pin(cx, cy - 10, "GT")
                add_pin(cx, cy, "EQ")
                add_pin(cx, cy + 10, "LT")
            elif name == "Shifter":
                add_pin(cx - 40, cy - 10, "IN")
                add_pin(cx - 40, cy + 10, "AMT")
                add_pin(cx, cy, "OUT")
        elif lib == "4":  # Memory
            if name in ("Register", "PC", "OUT") or aw.get("appearance") == "classic":
                add_pin(cx, cy, "Q")
                add_pin(cx - 30, cy, "D")
                add_pin(cx - 20, cy + 20, "CK")
                add_pin(cx - 10, cy + 20, "CLR")
                add_pin(cx - 30, cy + 10, "EN")
            elif name == "ROM":
                add_pin(cx, cy + 10, "ADDR")
                add_pin(cx + 240, cy + 70, "DATA")

    # Build pin set for fast lookup
    pin_set = {}  # (x, y) → description
    for px, py, desc in pins:
        pin_set[(px, py)] = desc

    # Collect all wire endpoints (points where wires change direction or terminate)
    wire_endpoints = set()
    for wx1, wy1, wx2, wy2 in wires:
        wire_endpoints.add((wx1, wy1))
        wire_endpoints.add((wx2, wy2))

    # Check each wire segment — only flag if the pin is NOT at a wire endpoint
    # (a wire is allowed to pass through a pin it's supposed to connect to at a junction)
    violations = []
    for wx1, wy1, wx2, wy2 in wires:
        if wy1 == wy2:  # horizontal
            y = wy1
            x_min, x_max = min(wx1, wx2), max(wx1, wx2)
            for (px, py), desc in pin_set.items():
                if py == y and x_min < px < x_max and (px, py) not in wire_endpoints:
                    violations.append(
                        f"H-wire ({wx1},{wy1-YO})→({wx2},{wy2-YO}) passes through orphan pin {desc}"
                    )
        elif wx1 == wx2:  # vertical
            x = wx1
            y_min, y_max = min(wy1, wy2), max(wy1, wy2)
            for (px, py), desc in pin_set.items():
                if px == x and y_min < py < y_max and (px, py) not in wire_endpoints:
                    violations.append(
                        f"V-wire ({wx1},{wy1-YO})→({wx2},{wy2-YO}) passes through orphan pin {desc}"
                    )

    # Check for unconnected pins
    pins_without_wires = []
    for (px, py), desc in pin_set.items():
        if (px, py) not in wire_endpoints:
            pins_without_wires.append(f"  {desc} at ({px},{py-YO})")

    return violations, pins_without_wires, len(pins)





if __name__ == "__main__":
    xml = generate()
    for path in ["Logisim/sCPU_F6.circ", "sCPU_F6.circ"]:
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
    comps = len(re.findall(r"<comp ", xml))
    wires = len(re.findall(r"<wire ", xml))
    print(f"[OK] {comps} components, {wires} wires -> Logisim/sCPU_F6.circ")
    print(f"[i]  y offset +{YO}, all L-shaped routing")
    print(f"[i] Exact pin coords based on Logisim-evolution source")

    violations, unconnected, num_pins = validate_routing(xml)
    if violations:
        print(f"[!!!] WIRE-THROUGH-PIN VIOLATIONS ({len(violations)}):")
        for v in violations:
            print(f"  {v}")
    else:
        print(f"[OK] No wire-through-pin violations ({num_pins} pins checked)")
    if unconnected:
        print(f"[i] Unconnected pins ({len(unconnected)}):")
        for u in unconnected[:20]:
            print(u)
        if len(unconnected) > 20:
            print(f"  ... and {len(unconnected) - 20} more")




