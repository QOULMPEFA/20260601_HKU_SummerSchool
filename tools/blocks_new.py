#!/usr/bin/env python3
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
