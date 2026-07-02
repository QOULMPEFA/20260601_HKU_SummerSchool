#!/usr/bin/env python3
"""
引脚校准电路生成器
对每种元器件, 在多个候选偏移位置放置测试线,
打开后观察哪些线真正连接到了引脚, 由此反推精确偏移量。
"""
YO = 200
IND = "    "

def a_xml(name, val):
    return f'<a name="{name}" val="{val}"/>'

def P(x, y):
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

def wire(fx, fy, tx, ty):
    return f'<wire from="{P(fx,fy)}" to="{P(tx,ty)}"/>'

def generate():
    L = []
    w = L.append

    w('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
    w('<project source="2.7.2" version="1.0">')
    w('This file is intended to be loaded by Logisim (http://www.cburch.com/logisim/).')
    for num, desc in [("0","#Wiring"),("1","#Gates"),("2","#Plexers"),
                       ("3","#Arithmetic"),("4","#Memory"),("5","#I/O"),("6","#Base")]:
        w(f'  <lib desc="{desc}" name="{num}"/>')
    w('  <main name="main"/>')
    w('  <options>')
    w(f'    {a_xml("gateUndefined","ignore")}')
    w(f'    {a_xml("simlimit","1000")}')
    w(f'    {a_xml("simrand","0")}')
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

    def add_comp(lib, xy, name, **props):
        L.append(IND + comp(lib, xy, name, **props))

    def add_wire(fx, fy, tx, ty):
        L.append(IND + wire(fx, fy, tx, ty))

    # ============================================================
    # 1. Register (width=8)
    # ============================================================
    add_comp("4", (200, 100), "Register", width="8", label="REG8")
    # D input (west) candidates:
    for i, dx in enumerate([-45, -40, -35]):
        add_wire(200+dx, 100, 200, 100-20-i*10)  # approach from west
    # Q output (east) candidates:
    for i, dx in enumerate([35, 40, 45]):
        add_wire(200+dx, 100+20+i*10, 270, 100+20+i*10)  # approach from east
    # clk (north) candidates:
    for i, dy in enumerate([-35, -30, -25]):
        add_wire(200-10, 100+dy, 200+10, 100+dy)
    # en (north) candidates:
    for i, dy in enumerate([-40, -35, -30, -25]):
        add_wire(200+10-i*5, 100+dy, 200+20-i*5, 100+dy)

    # ============================================================
    # 2. Mux (width=8)
    # ============================================================
    add_comp("2", (400, 100), "Multiplexer", width="8")
    # in0 (west upper) candidates:
    for i, (dx, dy) in enumerate([(-35,-10), (-30,-8), (-30,-10), (-25,-8)]):
        add_wire(400+dx, 400+dy, 400, 100+15+i*5)
    # in1 (west lower) candidates:
    for i, (dx, dy) in enumerate([(-35,8), (-30,8), (-30,10), (-25,10)]):
        add_wire(400+dx, 400+dy, 400, 100+25+i*5)
    # sel (south) candidates:
    for i, dy in enumerate([35, 40, 45]):
        add_wire(400-10, 100+dy, 400+10, 100+dy)
    # out (east) candidates:
    for i, dx in enumerate([25, 30, 35]):
        add_wire(400+dx, 100, 470+i*10, 100)

    # ============================================================
    # 3. Mux (width=2)
    # ============================================================
    add_comp("2", (400, 250), "Multiplexer", width="2")
    # in0/in1 (west) candidates - smaller mux
    for i, (dx, dy) in enumerate([(-25,-5), (-25,-3), (-20,-5), (-20,-3)]):
        add_wire(400+dx, 250+dy, 400, 250+15+i*5)
    for i, (dx, dy) in enumerate([(-25,3), (-25,5), (-20,3), (-20,5)]):
        add_wire(400+dx, 250+dy, 400, 250+25+i*5)
    # sel (south) candidates:
    for i, dy in enumerate([20, 25, 30, 35]):
        add_wire(400-10, 250+dy, 400+10, 250+dy)
    # out (east) candidates:
    for i, dx in enumerate([20, 25, 30]):
        add_wire(400+dx, 250, 470+i*10, 250)

    # ============================================================
    # 4. Adder (width=8)
    # ============================================================
    add_comp("3", (200, 300), "Adder", width="8")
    # A (west upper) candidates:
    for i, (dx, dy) in enumerate([(-45,-10), (-40,-10), (-35,-10)]):
        add_wire(200+dx, 300+dy, 200, 300-15+i*5)
    # B (west lower) candidates:
    for i, (dx, dy) in enumerate([(-45,10), (-40,10), (-35,10)]):
        add_wire(200+dx, 300+dy, 200, 300+15+i*5)
    # out (east) candidates:
    for i, dx in enumerate([35, 40, 45]):
        add_wire(200+dx, 300, 270+i*10, 300)

    # ============================================================
    # 5. Comparator (width=8)
    # ============================================================
    add_comp("3", (200, 460), "Comparator", width="8")
    # A (west upper), B (west lower):
    for i, (dx, dy) in enumerate([(-45,-10), (-40,-10), (-35,-10)]):
        add_wire(200+dx, 460+dy, 200, 460-15+i*5)
    for i, (dx, dy) in enumerate([(-45,10), (-40,10), (-35,10)]):
        add_wire(200+dx, 460+dy, 200, 460+15+i*5)
    # a≠b out (east)
    for i, dx in enumerate([35, 40, 45]):
        add_wire(200+dx, 460, 270+i*10, 460)

    # ============================================================
    # 6. Decoder (width=2)
    # ============================================================
    add_comp("2", (600, 100), "Decoder", width="2")
    # sel (south) candidates:
    for i, dy in enumerate([20, 25, 30]):
        add_wire(600-10, 100+dy, 600+10, 100+dy)
    # out0-out3 (east) candidates:
    for i, (dx, dy) in enumerate([(25,-15),(30,-15),(25,-10),(30,-10)]):
        add_wire(600+dx, 100+dy, 600, 100-20+i*5)

    # ============================================================
    # 7. Splitter (fanout=4, incoming=8, facing=west)
    # ============================================================
    add_comp("0", (600, 300), "Splitter", facing="west", fanout="4",
             incoming="8", appear="center", bit0="6", bit1="4",
             bit2="2", bit3="0")
    # input (east side since facing=west)
    for i, dx in enumerate([20, 25, 30]):
        add_wire(600+dx, 300, 670+i*10, 300)

    # ============================================================
    # 8. Shifter (width=8)
    # ============================================================
    add_comp("3", (600, 460), "Shifter", width="8")
    # data_in (west)
    for i, dx in enumerate([-45, -40, -35]):
        add_wire(600+dx, 460, 600, 460-15+i*5)
    # out (east)
    for i, dx in enumerate([35, 40, 45]):
        add_wire(600+dx, 460, 670+i*10, 460)

    # ============================================================
    # 9. Bit Extender
    # ============================================================
    add_comp("0", (800, 100), "Bit Extender", in_width="2",
             out_width="8", type="zero")
    # in (west), out (east)
    for i, dx in enumerate([-35, -30, -25]):
        add_wire(800+dx, 100, 800, 100-15+i*5)
    for i, dx in enumerate([25, 30, 35]):
        add_wire(800+dx, 100, 870+i*10, 100)

    # ============================================================
    # 10. Gates (AND, OR, NOT)
    # ============================================================
    add_comp("1", (800, 250), "AND Gate", width="1", inputs="2")
    for i, dy in enumerate([-5, -3, 3, 5]):
        add_wire(800-25, 250+dy, 800-5, 250+dy)
    for i, dx in enumerate([15, 20, 25]):
        add_wire(800+dx, 250, 870+i*10, 250)

    add_comp("1", (800, 350), "OR Gate", width="1", inputs="2")
    for i, dy in enumerate([-5, -3, 3, 5]):
        add_wire(800-25, 350+dy, 800-5, 350+dy)
    for i, dx in enumerate([15, 20, 25]):
        add_wire(800+dx, 350, 870+i*10, 350)

    add_comp("1", (800, 450), "NOT Gate", width="1")
    for i, dy in enumerate([-3, 0, 3]):
        add_wire(800-25, 450+dy, 800-5, 450+dy)
    for i, dx in enumerate([15, 20, 25]):
        add_wire(800+dx, 450, 870+i*10, 450)

    # ============================================================
    # 11. ROM
    # ============================================================
    add_comp("4", (200, 620), "ROM", addrWidth="3", dataWidth="8")
    # A (west), D (east)
    for i, (dx, dy) in enumerate([(-55,-20),(-50,-20),(-45,-20)]):
        add_wire(200+dx, 620+dy, 200, 620-20+i*5)

    # ============================================================
    # 12. Constant
    # ============================================================
    add_comp("0", (600, 620), "Constant", width="2", value="0x00")
    for i, dx in enumerate([20, 25, 30]):
        add_wire(600+dx, 620, 670+i*10, 620)

    add_comp("0", (700, 620), "Constant", width="8", value="0x01")
    for i, dx in enumerate([25, 30, 35]):
        add_wire(700+dx, 620, 770+i*10, 620)

    # ============================================================
    # 13. Pin
    # ============================================================
    add_comp("0", (200, 750), "Pin", width="1", label="test",
             labelloc="east", facing="east")
    for i, dx in enumerate([15, 20, 25]):
        add_wire(200+dx, 750, 270+i*10, 750)

    w('  </circuit>')
    w('</project>')
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    xml = generate()
    with open("Logisim/calibrate_pins.circ", "w", encoding="utf-8") as f:
        f.write(xml)
    print("[OK] calibrate_pins.circ generated")
    print("[i] Open in Logisim and check which test wires touch pins")
