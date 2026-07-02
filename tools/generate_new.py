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
