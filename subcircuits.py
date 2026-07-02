#!/usr/bin/env python3
"""Logisim subcircuit-based hierarchical circuit generation.

Each functional block becomes a <circuit> with Pin I/O ports.
The main circuit instantiates blocks and routes cross-block connections.
Internal wires are ISOLATED within each subcircuit's coordinate space.
"""
import re

YO = 200
IND = "    "

def P(x, y):
    return f"({x},{y + YO})"

def a_xml(name, val):
    return f'<a name="{name}" val="{val}"/>'

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
# Subcircuit Block class
# ============================================================
class Subcircuit:
    """A Logisim subcircuit with local coordinates and Pin-based I/O ports."""
    def __init__(self, name):
        self.name = name
        self._comps = []   # (lib, x, y, name, props_dict)
        self._wires = []   # (x1, y1, x2, y2)
        self._ports = {}   # port_name -> (local_x, local_y, width, is_output)

    def add_comp(self, lib, xy, name, **props):
        x, y = xy
        self._comps.append((lib, x, y, name, props))

    def add_wire(self, fx, fy, tx, ty):
        self._wires.append((fx, fy, tx, ty))

    def add_input(self, port_name, x, y, width=1):
        """Add an input pin (parent drives this, data flows INTO subcircuit)."""
        self._ports[port_name] = (x, y, width, False)
        # Input pin: no 'output' attribute, facing east by default
        props = {"width": str(width), "label": port_name}
        self._comps.append(("0", x, y, "Pin", props))

    def add_output(self, port_name, x, y, width=1):
        """Add an output pin (subcircuit drives this, data flows OUT to parent)."""
        self._ports[port_name] = (x, y, width, True)
        # Output pin: output="true", facing west, label on east
        props = {"facing": "west", "output": "true", "width": str(width),
                 "label": port_name, "labelloc": "east"}
        self._comps.append(("0", x, y, "Pin", props))

    def port_xy(self, port_name):
        """Return (x, y) of a port in this subcircuit's local coords."""
        return (self._ports[port_name][0], self._ports[port_name][1])

    def shift_coords(self, dx, dy):
        """Shift all internal coordinates by (dx, dy) — ensures non-negative coords."""
        if dx == 0 and dy == 0:
            return
        self._comps = [(lib, x + dx, y + dy, name, props) for lib, x, y, name, props in self._comps]
        self._wires = [(fx + dx, fy + dy, tx + dx, ty + dy) for fx, fy, tx, ty in self._wires]
        self._ports = {k: (px + dx, py + dy, w, o) for k, (px, py, w, o) in self._ports.items()}

    def emit_circuit(self):
        """Emit the <circuit> XML element."""
        lines = [f'  <circuit name="{self.name}">']
        lines.append(f'    <a name="circuit" val="{self.name}"/>')
        lines.append(f'    <a name="clabel" val=""/>')
        lines.append(f'    <a name="clabelup" val="east"/>')

        # Emit wires first (Logisim convention)
        for fx, fy, tx, ty in self._wires:
            lines.append(f'    <wire from="{P(fx, fy)}" to="{P(tx, ty)}"/>')

        # Emit components (including Pin I/O ports)
        for lib, x, y, name, props in self._comps:
            lines.append(f'    {comp(lib, (x, y), name, **props)}')

        lines.append(f'  </circuit>')
        return lines

    def instantiate(self, loc_x, loc_y):
        """Return the XML for instantiating this subcircuit in the main circuit."""
        # Inline subcircuit: just <comp loc="(x,y)" name="SubName"/>
        return f'{IND}<comp loc="{P(loc_x, loc_y)}" name="{self.name}"/>'


# ============================================================
# Block Builders (same logic, now using Subcircuit + Pin I/O)
# ============================================================

def build_clock_reset():
    """Clock and reset distribution backbone as a subcircuit."""
    s = Subcircuit("clock_reset")

    # ---- Input pins (from outside world) ----
    s.add_input("clk_in", 60, 200, 1)
    s.add_input("rst_in", 60, 280, 1)

    # ---- Output pins (to other blocks) ----
    s.add_output("ck_pc", 180, 260, 1)        # to PC.CK
    s.add_output("ck_r0", 740, 180, 1)        # to R0.CK (logical y=80)
    s.add_output("ck_r1", 740, 320, 1)        # to R1.CK
    s.add_output("ck_r2", 740, 465, 1)        # to R2.CK (via y=365)
    s.add_output("ck_r3", 740, 600, 1)        # to R3.CK
    s.add_output("ck_out", 1180, 840, 1)      # to OUT.CK
    s.add_output("rst_pc", 190, 260, 1)       # to PC.CLR
    s.add_output("rst_r0", 750, 180, 1)       # to R0.CLR
    s.add_output("rst_r1", 750, 320, 1)
    s.add_output("rst_r2", 750, 460, 1)
    s.add_output("rst_r3", 750, 600, 1)
    s.add_output("rst_out", 1190, 840, 1)     # to OUT.CLR

    # ---- Internal wires ----
    CK_BB = 54
    CK_GX = 718
    CK_TRUNK_Y = 165  # logical y=65

    # clk pin -> backbone
    s.add_wire(60, 200, 60, CK_TRUNK_Y)
    s.add_wire(60, CK_TRUNK_Y, CK_BB, CK_TRUNK_Y)
    s.add_wire(CK_BB, CK_TRUNK_Y, CK_BB, 835)  # backbone to y=735

    # CK trunk to GPR vertical
    s.add_wire(CK_BB, CK_TRUNK_Y, CK_GX, CK_TRUNK_Y)
    s.add_wire(CK_GX, CK_TRUNK_Y, CK_GX, 600)  # down to y=500

    # PC CK
    s.add_wire(CK_BB, CK_TRUNK_Y, 110, CK_TRUNK_Y)
    s.add_wire(110, CK_TRUNK_Y, 110, 260)
    s.add_wire(110, 260, 180, 260)

    # GPR CK horizontals
    s.add_wire(CK_GX, 180, 740, 180)   # R0 CK
    s.add_wire(CK_GX, 320, 740, 320)   # R1 CK
    s.add_wire(CK_GX, 465, 740, 465)   # R2 CK
    s.add_wire(740, 465, 740, 460)
    s.add_wire(CK_GX, 600, 740, 600)   # R3 CK

    # OUT CK
    s.add_wire(CK_BB, 835, 1180, 835)
    s.add_wire(1180, 835, 1180, 840)

    # ---- Reset tree ----
    RST_Y = 900  # logical y=800
    s.add_wire(60, 280, 95, 280)
    s.add_wire(95, 280, 95, RST_Y)
    s.add_wire(95, RST_Y, 1190, RST_Y)

    # PC CLR
    s.add_wire(115, RST_Y, 115, 230)
    s.add_wire(115, 230, 190, 230)
    s.add_wire(190, 230, 190, 260)

    # GPR CLR
    for clry in [180, 320, 460, 600]:
        s.add_wire(755, RST_Y, 755, clry)
        s.add_wire(755, clry, 750, clry)

    # OUT CLR
    s.add_wire(1190, RST_Y, 1190, 840)

    return s


def build_pc():
    """PC update loop as a subcircuit."""
    s = Subcircuit("pc")

    # Internal components (local coords)
    s.add_comp("4", (100, 40), "Register", width="8", label="PC",
               labelloc="east", appearance="classic")
    s.add_comp("3", (100, 220), "Adder", width="8")
    s.add_comp("0", (100, 350), "Constant", width="8", value="0x01")
    s.add_comp("0", (100, 440), "Bit Extender", in_width="2", out_width="8", type="sign")
    s.add_comp("2", (280, 350), "Multiplexer", width="8")
    s.add_comp("0", (60, 200), "Constant", width="1", value="0x0")
    s.add_comp("1", (280, 460), "AND Gate", width="1", inputs="2", size="30")
    # VCC for AND.IN1
    s.add_comp("0", (250, 470), "Constant", width="1", value="0x1")

    # ---- I/O Ports ----
    # Inputs (driven from outside)
    s.add_input("ck", 80, 60, 1)           # PC.CK
    s.add_input("clr", 90, 60, 1)          # PC.CLR
    s.add_input("rst_and", -40, 80, 1)     # rst for AND gate
    s.add_input("branch_offset", 60, 440, 2)  # SignExt.IN (2-bit)
    s.add_input("mux_sel", 260, 370, 1)    # PC_Mux.SEL

    # Outputs (driven to outside)
    s.add_output("pc_q", 100, 40, 8)       # PC.Q
    s.add_output("pc_q_fetch", 280, 10, 8)  # PC.Q routed for ROM addr

    # ---- Internal wires ----
    # PC.Q -> Adder.A
    s.add_wire(100, 40, 100, 115)
    s.add_wire(100, 115, 60, 115)
    s.add_wire(60, 115, 60, 210)

    # Adder.OUT -> PC.D
    s.add_wire(100, 220, 100, 135)
    s.add_wire(100, 135, 70, 135)
    s.add_wire(70, 135, 70, 40)

    # PC.Q -> ROM fetch
    s.add_wire(100, 40, 100, 125)
    s.add_wire(100, 125, 280, 125)
    s.add_wire(280, 125, 280, 10)

    # Adder CIN GND
    s.add_wire(60, 200, 80, 200)

    # Constant -> Adder.B + PC_Mux.IN0
    s.add_wire(100, 350, 250, 350)
    s.add_wire(250, 350, 250, 340)
    s.add_wire(100, 350, 100, 230)
    s.add_wire(100, 230, 60, 230)

    # SignExt -> PC_Mux.IN1
    s.add_wire(100, 440, 100, 430)
    s.add_wire(100, 430, 250, 430)
    s.add_wire(250, 430, 250, 360)

    # PC_Mux.OUT -> PC.D (via safe path)
    s.add_wire(280, 350, 265, 350)
    s.add_wire(265, 350, 265, 550)
    s.add_wire(265, 550, 20, 550)
    s.add_wire(20, 550, 20, 135)
    s.add_wire(20, 135, 70, 135)

    # rst -> AND.IN0
    s.add_wire(-40, 80, -40, 450)
    s.add_wire(-40, 450, 250, 450)

    # AND.OUT -> PC.EN
    s.add_wire(280, 460, 280, 570)
    s.add_wire(280, 570, -50, 570)
    s.add_wire(-50, 570, -50, 50)
    s.add_wire(-50, 50, 70, 50)

    return s


def build_fetch_decode():
    """ROM + Splitter + Decoder as a subcircuit."""
    s = Subcircuit("fetch_decode")

    # Inputs
    s.add_input("pc_addr", 40, 60, 8)       # ROM.ADDR

    # Outputs
    s.add_output("opcode_hi", 220, 30, 2)   # Splitter fan0
    s.add_output("opcode_lo", 220, 40, 2)   # Splitter fan1
    s.add_output("rs1_addr", 220, 50, 2)    # Splitter fan2
    s.add_output("rs2_imm", 220, 60, 2)     # Splitter fan3
    s.add_output("dec_out0", 330, 270, 1)   # Decoder out0
    s.add_output("dec_out1", 330, 280, 1)
    s.add_output("dec_out2", 330, 290, 1)
    s.add_output("dec_out3", 330, 300, 1)
    s.add_output("rs1_fan0", 380, 40, 1)    # rs1_sel fan0
    s.add_output("rs1_fan1", 380, 50, 1)
    s.add_output("rs2_fan0", 380, 70, 1)
    s.add_output("rs2_fan1", 380, 80, 1)

    # ROM (needs special handling)
    s._rom_lines = [
        f'    <comp lib="4" loc="{P(40, 60)}" name="ROM">',
        f'      <a name="addrWidth" val="8"/>',
        f'      <a name="dataWidth" val="8"/>',
        f'      <a name="appearance" val="classic"/>',
        f'      <a name="contents">addr/data: 8 8',
        '0 90', '1 a1', '2 be', '3 16',
        '4 29', '5 f7', '6 54', '7 0',
        f'      </a>',
        f'    </comp>',
    ]

    # Internal components
    s.add_comp("0", (240, 50), "Splitter", facing="west", fanout="4",
               incoming="8", appear="center",
               bit7="0", bit6="0", bit5="1", bit4="1",
               bit3="2", bit2="2", bit1="3", bit0="3")
    s.add_comp("2", (310, 310), "Decoder", select="2", enable="false")
    s.add_comp("0", (360, 30), "Splitter", facing="east", fanout="2",
               incoming="2", bit0="0", bit1="1", appear="right")
    s.add_comp("0", (360, 60), "Splitter", facing="east", fanout="2",
               incoming="2", bit0="0", bit1="1", appear="right")

    # Internal wires
    s.add_wire(280, 120, 280, 50)
    s.add_wire(280, 50, 240, 50)
    # fan0 -> decoder SEL
    s.add_wire(220, 30, 190, 30)
    s.add_wire(190, 30, 190, 310)
    s.add_wire(190, 310, 310, 310)
    # fan2 -> rs1_sel
    s.add_wire(220, 50, 285, 50)
    s.add_wire(285, 50, 285, 30)
    s.add_wire(285, 30, 360, 30)
    # fan3 -> rs2_sel
    s.add_wire(220, 60, 285, 60)
    s.add_wire(285, 60, 360, 60)

    return s


def build_gpr_rmux():
    """GPR register file + rMux trees as a subcircuit."""
    s = Subcircuit("gpr_rmux")

    # Inputs
    s.add_input("ck_r0", 100, 90, 1)
    s.add_input("ck_r1", 100, 230, 1)
    s.add_input("ck_r2", 100, 370, 1)
    s.add_input("ck_r3", 100, 510, 1)
    s.add_input("clr_r0", 110, 90, 1)
    s.add_input("clr_r1", 110, 230, 1)
    s.add_input("clr_r2", 110, 370, 1)
    s.add_input("clr_r3", 110, 510, 1)
    s.add_input("en_r0", 90, 70, 1)
    s.add_input("en_r1", 90, 210, 1)
    s.add_input("en_r2", 90, 350, 1)
    s.add_input("en_r3", 90, 490, 1)
    s.add_input("d_r0", 90, 90, 8)
    s.add_input("d_r1", 90, 230, 8)
    s.add_input("d_r2", 90, 370, 8)
    s.add_input("d_r3", 90, 510, 8)
    s.add_input("rmux1_sel_ab", 280, 130, 1)
    s.add_input("rmux1_sel_cd", 280, 230, 1)
    s.add_input("rmux1_sel_top", 400, 180, 1)
    s.add_input("rmux2_sel_ab", 280, 350, 1)
    s.add_input("rmux2_sel_cd", 280, 450, 1)
    s.add_input("rmux2_sel_top", 400, 400, 1)

    # Outputs
    s.add_output("rmux1_out", 420, 160, 8)
    s.add_output("rmux2_out", 420, 380, 8)
    s.add_output("raddr_out", 220, -20, 2)

    # GPR Registers
    for i, ly in enumerate([90, 230, 370, 510]):
        s.add_comp("4", (120, ly), "Register", width="8",
                   label=f"R{i}", labelloc="east", appearance="classic")

    # raddr Mux tree
    s.add_comp("0", (40, 50), "Constant", width="2", value="0x00")
    s.add_comp("0", (40, 30), "Constant", width="1", value="0x0")
    s.add_comp("2", (180, 40), "Multiplexer", width="2")
    s.add_comp("2", (280, 40), "Multiplexer", width="2")
    s.add_comp("2", (380, 40), "Multiplexer", width="2")

    # rMux trees
    s.add_comp("2", (300, 110), "Multiplexer", width="8")   # rMux1_ab
    s.add_comp("2", (300, 210), "Multiplexer", width="8")   # rMux1_cd
    s.add_comp("2", (420, 160), "Multiplexer", width="8")   # rMux1_top
    s.add_comp("2", (300, 330), "Multiplexer", width="8")   # rMux2_ab
    s.add_comp("2", (300, 430), "Multiplexer", width="8")   # rMux2_cd
    s.add_comp("2", (420, 380), "Multiplexer", width="8")   # rMux2_top

    # ---- Internal wires ----
    # GPR Q -> rMux
    d = [238, 250, 262, 274]
    m1_ys = [100, 120, 200, 220]
    m2_ys = [320, 340, 420, 440]
    for i in range(4):
        ly = [90, 230, 370, 510][i]
        s.add_wire(120, ly, d[i], ly)
        s.add_wire(d[i], ly, d[i], m1_ys[i])
        s.add_wire(d[i], m1_ys[i], 270, m1_ys[i])
        s.add_wire(d[i], ly, d[i], m2_ys[i])
        s.add_wire(d[i], m2_ys[i], 270, m2_ys[i])

    # rMux internal
    s.add_wire(300, 110, 300, 150); s.add_wire(300, 150, 390, 150)
    s.add_wire(300, 210, 300, 170); s.add_wire(300, 170, 390, 170)
    s.add_wire(300, 330, 300, 370); s.add_wire(300, 370, 390, 370)
    s.add_wire(300, 430, 300, 390); s.add_wire(300, 390, 390, 390)

    # raddr tree
    s.add_wire(40, 50, 150, 50); s.add_wire(150, 50, 150, 30)
    s.add_wire(180, 40, 250, 40); s.add_wire(250, 40, 250, 30)
    s.add_wire(280, 40, 350, 40); s.add_wire(350, 40, 350, 30)
    s.add_wire(380, 40, 380, 10); s.add_wire(380, 10, 220, 10)
    s.add_wire(220, 10, 220, -20)

    # raddr SELs GND
    s.add_wire(40, 30, 160, 30); s.add_wire(160, 30, 160, 60)
    s.add_wire(160, 30, 260, 30); s.add_wire(260, 30, 260, 60)
    s.add_wire(260, 30, 360, 30); s.add_wire(360, 30, 360, 60)

    return s


def build_alu():
    """ALU: Adder + Comparator as a subcircuit."""
    s = Subcircuit("alu")

    s.add_input("a", 60, 40, 8)
    s.add_input("b", 60, 60, 8)
    s.add_output("sum", 100, 50, 8)
    s.add_output("eq", 100, 230, 1)

    s.add_comp("3", (100, 50), "Adder", width="8")
    s.add_comp("3", (100, 230), "Comparator", width="8")
    s.add_comp("0", (60, 30), "Constant", width="1", value="0x0")

    s.add_wire(60, 30, 80, 30)
    s.add_wire(60, 40, 60, 40)   # input 'a' to Adder.A is via pin location
    s.add_wire(60, 60, 60, 60)   # input 'b' to Adder.B via pin location
    s.add_wire(60, 40, 60, 220)  # 'a' also to Comp.A
    s.add_wire(60, 60, 60, 240)  # 'b' also to Comp.B

    return s


def build_control():
    """Control logic as a subcircuit."""
    s = Subcircuit("control")

    # Inputs
    s.add_input("dec0", 190, 190, 1)
    s.add_input("dec1", 190, 210, 1)
    s.add_input("dec3", 190, 110, 1)
    s.add_input("comp_eq", 20, 100, 1)
    s.add_input("waddr", 220, 290, 2)

    # Outputs
    s.add_output("branch_taken", 220, 100, 1)
    s.add_output("is_gpr_write", 360, 200, 1)
    s.add_output("wen0", 500, 40, 1)
    s.add_output("wen1", 500, 140, 1)
    s.add_output("wen2", 500, 240, 1)
    s.add_output("wen3", 500, 340, 1)

    # Components
    s.add_comp("1", (40, 100), "NOT Gate", width="1", size="20")
    s.add_comp("1", (220, 100), "AND Gate", width="1", inputs="2", size="30")
    s.add_comp("1", (220, 200), "OR Gate", width="1", inputs="2", size="30")
    s.add_comp("1", (360, 200), "OR Gate", width="1", inputs="2", size="30")
    and_ys = [40, 140, 240, 340]
    for ay in and_ys:
        s.add_comp("1", (500, ay), "AND Gate", width="1", inputs="2", size="30")
    s.add_comp("2", (220, 290), "Decoder", select="2", enable="false")

    # Internal wires
    s.add_wire(40, 100, 40, 90)
    s.add_wire(40, 90, 190, 90)
    s.add_wire(220, 200, 330, 200)
    s.add_wire(330, 200, 330, 190)

    # OR2 -> AND.IN0
    for i, ay in enumerate([30, 130, 230, 330]):
        s.add_wire(360, 200, 410, 200)
        s.add_wire(410, 200, 410, ay)
        s.add_wire(410, ay, 470, ay)

    # wdec -> AND.IN1
    wdec_outs = [(240, 250), (240, 260), (240, 270), (240, 280)]
    for i, (wx, wy) in enumerate(wdec_outs):
        target_y = 50 + i * 100
        s.add_wire(wx, wy, 360 + i * 20, wy)
        s.add_wire(360 + i * 20, wy, 360 + i * 20, target_y)
        s.add_wire(360 + i * 20, target_y, 470, target_y)

    return s


def build_writeback():
    """Writeback muxes + OUT register + immediate path as a subcircuit."""
    s = Subcircuit("writeback")

    # Inputs
    s.add_input("alu_result", 50, 50, 8)
    s.add_input("imm_in", -580, 140, 2)
    s.add_input("is_li", 60, 80, 1)
    s.add_input("is_io", 220, 80, 1)
    s.add_input("ck", 60, 240, 1)
    s.add_input("clr", 70, 240, 1)
    s.add_input("out_d", 50, 220, 8)

    # Outputs
    s.add_output("wdata", 240, 60, 8)
    s.add_output("imm_out_to_mux", -540, 210, 8)

    # Components
    s.add_comp("2", (80, 60), "Multiplexer", width="8")
    s.add_comp("2", (240, 60), "Multiplexer", width="8")
    s.add_comp("4", (80, 220), "Register", width="8",
               label="OUT", labelloc="east", appearance="classic")
    s.add_comp("0", (200, 480), "Constant", width="8", value="0x00")
    s.add_comp("0", (-540, 140), "Bit Extender", in_width="2", out_width="8", type="zero")
    s.add_comp("3", (-360, 140), "Shifter", width="8")

    # Internal wires
    s.add_wire(80, 60, 160, 60)
    s.add_wire(160, 60, 160, 50)
    s.add_wire(160, 50, 210, 50)
    s.add_wire(200, 480, 200, 340)
    s.add_wire(200, 340, 160, 340)
    s.add_wire(160, 340, 160, 70)
    s.add_wire(160, 70, 210, 70)
    # BitExt -> wMux1.IN1
    s.add_wire(-540, 140, -540, 210)
    s.add_wire(-540, 210, 200, 210)
    s.add_wire(200, 210, 200, 170)
    s.add_wire(200, 170, 50, 170)
    s.add_wire(50, 170, 50, 70)

    return s


if __name__ == "__main__":
    print("Subcircuit builders module loaded.")
