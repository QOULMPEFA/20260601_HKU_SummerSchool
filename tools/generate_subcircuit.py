def generate():
    """Generate circuit using Logisim subcircuit encapsulation."""
    L = []
    w = L.append

    # ---- Create all subcircuits ----
    cr = build_clock_reset()
    pc = build_pc()
    fd = build_fetch_decode()
    gp = build_gpr_rmux()
    al = build_alu()
    ct = build_control()
    wb = build_writeback()

    subcircuits = [cr, pc, fd, gp, al, ct, wb]

    # Placement offsets in main circuit (to position ports conveniently)
    # These are chosen so that port positions in main match the original global coords
    placements = {
        "clock_reset": (0, -100),
        "pc": (100, 100),
        "fetch_decode": (340, 50),
        "gpr_rmux": (640, -30),
        "alu": (1100, 150),
        "control": (640, 640),
        "writeback": (1120, 500),
    }

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

    # ============ MAIN CIRCUIT ============
    w('  <circuit name="main">')
    w(f'    <a name="circuit" val="main"/>')
    w(f'    <a name="clabel" val=""/>')
    w(f'    <a name="clabelup" val="east"/>')

    # ---- Instantiate all subcircuits ----
    for s in subcircuits:
        ox, oy = placements[s.name]
        w(s.instantiate(ox, oy))

    # ---- Cross-block wiring (main circuit only has inter-block connections) ----
    def wire(fx, fy, tx, ty):
        w(f'    <wire from="{P(fx, fy)}" to="{P(tx, ty)}"/>')

    def port_g(s, pname):
        """Get global position of a subcircuit port in the main circuit."""
        ox, oy = placements[s.name]
        lx, ly = s.port_xy(pname)
        return (ox + lx, oy + ly)

    def Pg(s, pname):
        """Port global as tuple."""
        return port_g(s, pname)

    # --- Clock & Reset distribution ---
    # cr outputs connect to individual block inputs
    # PC
    ck_pc = Pg(cr, "ck_pc"); clr_pc = Pg(cr, "rst_pc")
    wire(ck_pc[0], ck_pc[1], *Pg(pc, "ck"))
    wire(clr_pc[0], clr_pc[1], *Pg(pc, "clr"))

    # GPR
    for i, r in enumerate(["r0", "r1", "r2", "r3"]):
        wire(*Pg(cr, f"ck_{r}"), *Pg(gp, f"ck_{r}"))
        wire(*Pg(cr, f"rst_{r}"), *Pg(gp, f"clr_{r}"))

    # OUT
    wire(*Pg(cr, "ck_out"), *Pg(wb, "ck"))
    wire(*Pg(cr, "rst_out"), *Pg(wb, "clr"))

    # --- PC -> ROM fetch ---
    wire(*Pg(pc, "pc_q_fetch"), *Pg(fd, "pc_addr"))

    # --- rst -> PC AND gate ---
    # rst signal: from clock_reset rst_in port to pc.rst_and
    # The rst_in is at cr port (60, 200+oy)
    wire(60, 180, 60, 550)
    wire(60, 550, 350, 550)  # to AND.IN0 at global (350+100, 550+100)

    # --- Decoder outputs -> control ---
    wire(*Pg(fd, "dec_out0"), *Pg(ct, "dec0"))
    wire(*Pg(fd, "dec_out1"), *Pg(ct, "dec1"))
    wire(*Pg(fd, "dec_out3"), *Pg(ct, "dec3"))

    # --- Splitter fan0/fan1 -> waddr/control ---
    wire(*Pg(fd, "opcode_lo"), *Pg(ct, "waddr"))

    # --- rs1/rs2 fans -> rMux SELs ---
    # rs1.fan0 -> rMux1_ab.SEL + rMux1_cd.SEL
    fx0, fy0 = Pg(fd, "rs1_fan0")
    route_hv(fx0, fy0, *Pg(gp, "rmux1_sel_ab"), 730)
    wire(730, fy0, 730, Pg(gp, "rmux1_sel_cd")[1] - 5)
    wire(730, Pg(gp, "rmux1_sel_cd")[1] - 5, 960, Pg(gp, "rmux1_sel_cd")[1] - 5)
    wire(960, Pg(gp, "rmux1_sel_cd")[1] - 5, 960, Pg(gp, "rmux1_sel_cd")[1])
    wire(960, Pg(gp, "rmux1_sel_cd")[1], *Pg(gp, "rmux1_sel_cd"))

    # rs1.fan1 -> rMux1_top.SEL
    route_hv(*Pg(fd, "rs1_fan1"), *Pg(gp, "rmux1_sel_top"), 740)

    # rs2.fan0 -> rMux2_ab.SEL + rMux2_cd.SEL
    fx0, fy0 = Pg(fd, "rs2_fan0")
    route_hv(fx0, fy0, *Pg(gp, "rmux2_sel_ab"), 750)
    wire(750, fy0, 750, Pg(gp, "rmux2_sel_cd")[1] - 5)
    wire(750, Pg(gp, "rmux2_sel_cd")[1] - 5, 980, Pg(gp, "rmux2_sel_cd")[1] - 5)
    wire(980, Pg(gp, "rmux2_sel_cd")[1] - 5, 980, Pg(gp, "rmux2_sel_cd")[1])
    wire(980, Pg(gp, "rmux2_sel_cd")[1], *Pg(gp, "rmux2_sel_cd"))

    # rs2.fan1 -> rMux2_top.SEL
    route_hv(*Pg(fd, "rs2_fan1"), *Pg(gp, "rmux2_sel_top"), 810)

    # --- rMux outputs -> ALU ---
    r1x, r1y = Pg(gp, "rmux1_out")
    wire(r1x, r1y, r1x, 170)
    wire(r1x, 170, *Pg(al, "a"))
    wire(r1x, 170, 1158, 170)
    wire(1158, 170, 1158, Pg(al, "a")[1] + 180)
    wire(1158, Pg(al, "a")[1] + 180, 1153, Pg(al, "a")[1] + 180)
    wire(1153, Pg(al, "a")[1] + 180, 1153, Pg(al, "a")[1] + 180)
    wire(1153, Pg(al, "a")[1] + 180, *Pg(al, "a"))

    r2x, r2y = Pg(gp, "rmux2_out")
    wire(r2x, r2y, 1090, r2y)
    wire(1090, r2y, 1090, 180)
    wire(1090, 180, 1157, 180)
    wire(1157, 180, 1157, Pg(al, "b")[1])
    wire(1157, Pg(al, "b")[1], *Pg(al, "b"))
    wire(1090, r2y, 1090, Pg(al, "b")[1] + 180)
    wire(1090, Pg(al, "b")[1] + 180, 1157, Pg(al, "b")[1] + 180)
    wire(1157, Pg(al, "b")[1] + 180, 1157, Pg(al, "b")[1] + 180)
    wire(1157, Pg(al, "b")[1] + 180, *Pg(al, "b"))

    # --- ALU -> writeback ---
    wire(*Pg(al, "sum"), *Pg(wb, "alu_result"))

    # --- Comparator EQ -> control ---
    ceqx, ceqy = Pg(al, "eq")
    wire(ceqx, ceqy, 1210, ceqy)
    wire(1210, ceqy, 1210, 730)
    wire(1210, 730, 660, 730)
    wire(660, 730, 660, Pg(ct, "comp_eq")[1])
    wire(660, Pg(ct, "comp_eq")[1], *Pg(ct, "comp_eq"))

    # --- Immediate path ---
    wire(*Pg(fd, "rs2_imm"), *Pg(wb, "imm_in"))
    # Also route to SignExt (in PC block) via the splitter
    sx, sy = Pg(fd, "rs2_imm")
    wire(sx, sy, 530, sy)
    wire(530, sy, 530, 550)
    wire(530, 550, *Pg(pc, "branch_offset"))

    # --- wMux2 output -> GPR D pins ---
    w2x, w2y = Pg(wb, "wdata")
    wire(w2x, w2y, w2x, 655)
    wire(w2x, 655, 55, 655)
    wire(55, 655, 55, -60)

    for r in ["r0", "r1"]:
        wire(55, -60, 685, -60)
        wire(685, -60, 685, Pg(gp, f"d_{r}")[1])
        wire(685, Pg(gp, f"d_{r}")[1], *Pg(gp, f"d_{r}"))

    for r in ["r2", "r3"]:
        wire(55, 655, 55, 510)
        wire(55, 510, 745, 510)
        wire(745, 510, 745, Pg(gp, f"d_{r}")[1])
        wire(745, Pg(gp, f"d_{r}")[1], *Pg(gp, f"d_{r}"))

    # --- rMux1 -> OUT.D ---
    wire(r1x, r1y, r1x, r1y - 40)
    wire(r1x, r1y - 40, 1160, r1y - 40)
    wire(1160, r1y - 40, 1160, 330)
    wire(1160, 330, 1370, 330)
    wire(1370, 330, 1370, 805)
    wire(1370, 805, 1170, 805)
    wire(1170, 805, 1170, Pg(wb, "out_d")[1])
    wire(1170, Pg(wb, "out_d")[1], *Pg(wb, "out_d"))

    # --- Control -> PC_Mux.SEL ---
    ao_x, ao_y = Pg(ct, "branch_taken")
    wire(ao_x, ao_y, ao_x, 470)
    wire(ao_x, 470, 360, 470)
    wire(360, 470, 360, Pg(pc, "mux_sel")[1])
    wire(360, Pg(pc, "mux_sel")[1], *Pg(pc, "mux_sel"))

    # --- is_li / is_io ---
    wire(*Pg(fd, "dec_out0"), *Pg(wb, "is_li"))  # need route_hv
    wire(*Pg(fd, "dec_out2"), *Pg(wb, "is_io"))

    # --- Control -> GPR.EN ---
    for i in range(4):
        r = f"r{i}"
        wx, wy = Pg(ct, f"wen{i}")
        wire(wx, wy, 710, wy)
        wire(710, wy, 710, Pg(gp, f"en_{r}")[1])
        wire(710, Pg(gp, f"en_{r}")[1], *Pg(gp, f"en_{r}"))

    # --- raddr -> waddr Decoder ---
    rax, ray = Pg(gp, "raddr_out")
    wire(rax, ray, rax, -20)
    wire(rax, -20, 860, -20)
    wire(860, -20, 860, Pg(ct, "waddr")[1])
    wire(860, Pg(ct, "waddr")[1], *Pg(ct, "waddr"))

    # --- li BitExt -> wMux1.IN1 ---
    bix, biy = Pg(wb, "imm_out_to_mux")
    wire(bix, biy, bix, 710)
    wire(bix, 710, 1170, 710)
    wire(1170, 710, 1170, Pg(wb, "alu_result")[1] + 20)
    wire(1170, Pg(wb, "alu_result")[1] + 20, Pg(wb, "alu_result")[0], Pg(wb, "alu_result")[1] + 20)

    # --- is_li to wMux1.SEL ---
    d0x, d0y = Pg(fd, "dec_out0")
    wire(d0x, d0y, 900, d0y)
    wire(900, d0y, 900, 600)
    wire(900, 600, 1180, 600)
    wire(1180, 600, 1180, Pg(wb, "is_li")[1])
    wire(1180, Pg(wb, "is_li")[1], *Pg(wb, "is_li"))

    # --- is_io to wMux2.SEL + OUT.EN ---
    d2x, d2y = Pg(fd, "dec_out2")
    wire(d2x, d2y, 920, d2y)
    wire(920, d2y, 920, 605)
    wire(920, 605, 1340, 605)
    wire(1340, 605, 1340, Pg(wb, "is_io")[1])
    wire(1340, Pg(wb, "is_io")[1], *Pg(wb, "is_io"))
    wire(920, d2y, 920, 730)
    wire(920, 730, 1170, 730)
    wire(1170, 730, 1170, Pg(wb, "out_d")[1] + 10)
    wire(1170, Pg(wb, "out_d")[1] + 10, *Pg(wb, "out_d"))

    w('  </circuit>')

    # ============ SUBCIRCUIT DEFINITIONS ============
    for s in subcircuits:
        lines = s.emit_circuit()
        # Handle ROM special case
        if hasattr(s, '_rom_lines'):
            # Insert ROM lines before the last </circuit>
            for rl in s._rom_lines:
                lines.insert(-1, rl)
        for line in lines:
            w(line)

    # ---- XML Footer ----
    w('</project>')
    return "\n".join(L) + "\n"


# Need these from the main module
def route_hv(sx, sy, tx, ty, via_x):
    """Route: horizontal to via_x, then vertical."""
    # Will be defined in the function scope when called
    pass
