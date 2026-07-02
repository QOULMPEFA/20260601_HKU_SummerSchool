#!/usr/bin/env python3
"""Diagnose which component pins are in each logical net."""
import re
import sys
from collections import defaultdict

YO = 200

def parse_wires(xml_path):
    wires = []
    with open(xml_path, encoding="utf-8") as f:
        content = f.read()
    for m in re.finditer(r'<wire from="\((-?\d+),(-?\d+)\)" to="\((-?\d+),(-?\d+)\)"/>', content):
        x1, y1, x2, y2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        wires.append((x1, y1, x2, y2))
    return wires, content

def parse_comps(content):
    """Parse components and their pin locations."""
    comps = []
    for m in re.finditer(
        r'<comp lib="(\d+)" loc="\((-?\d+),(-?\d+)\)" name="([^"]+)">(.*?)</comp>',
        content, re.DOTALL
    ):
        lib = m.group(1)
        cx = int(m.group(2))
        cy = int(m.group(3))
        name = m.group(4)
        attrs = m.group(5)
        aw = {}
        for am in re.finditer(r'<a name="(\w+)" val="([^"]+)"/>', attrs):
            aw[am.group(1)] = am.group(2)
        comps.append({'lib': lib, 'cx': cx, 'cy': cy, 'name': name, 'attrs': aw})
    return comps

def get_pins(comp):
    """Return list of (x, y, pin_name) for a component."""
    cx, cy, name, lib = comp['cx'], comp['cy'], comp['name'], comp['lib']
    aw = comp['attrs']
    pins = []

    if lib == "0":
        if name == "Pin":
            pins.append((cx, cy, "PORT"))
        elif name == "Splitter":
            pins.append((cx, cy, "COMB"))
            fanout = int(aw.get("fanout", "2"))
            facing = aw.get("facing", "east")
            appear = aw.get("appear", "center")
            gap = 10
            width = 20
            for fi in range(fanout):
                if facing in ("north", "south"):
                    continue  # simplified
                else:
                    m_sign = -1 if facing == "west" else 1
                    if appear == "center":
                        dyEnd0 = -gap * (fanout // 2)
                    elif (m_sign > 0 and appear == "right") or (m_sign < 0 and appear == "left"):
                        dyEnd0 = 10
                    else:
                        dyEnd0 = -(10 + gap * (fanout - 1))
                    fx = cx + m_sign * width
                    fy = cy + dyEnd0 + fi * gap
                    pins.append((fx, fy, f"FAN{fi}"))
        elif name == "Constant":
            pins.append((cx, cy, "OUT"))
        elif name == "Bit Extender":
            pins.append((cx, cy, "OUT"))
            pins.append((cx - 40, cy, "IN"))
    elif lib == "1":
        if "NOT" in name:
            pins.append((cx - 20, cy, "IN"))
            pins.append((cx, cy, "OUT"))
        else:
            pins.append((cx - 30, cy - 10, "IN0"))
            pins.append((cx - 30, cy + 10, "IN1"))
            pins.append((cx, cy, "OUT"))
    elif lib == "2":
        if name == "Multiplexer":
            pins.append((cx - 30, cy - 10, "IN0"))
            pins.append((cx - 30, cy + 10, "IN1"))
            pins.append((cx, cy, "OUT"))
            pins.append((cx - 20, cy + 20, "SEL"))
        elif name == "Decoder":
            sel_bits = int(aw.get("select", "1"))
            for i in range(2 ** sel_bits):
                pins.append((cx + 20, cy - 40 + i * 10, f"OUT{i}"))
            pins.append((cx, cy, "SEL"))
            if aw.get("enable") == "true":
                pins.append((cx - 10, cy, "EN"))
    elif lib == "3":
        if name == "Adder":
            pins.append((cx - 40, cy - 10, "A"))
            pins.append((cx - 40, cy + 10, "B"))
            pins.append((cx, cy, "OUT"))
            pins.append((cx - 20, cy - 20, "CIN"))
            pins.append((cx - 20, cy + 20, "COUT"))
        elif name == "Comparator":
            pins.append((cx - 40, cy - 10, "A"))
            pins.append((cx - 40, cy + 10, "B"))
            pins.append((cx, cy - 10, "GT"))
            pins.append((cx, cy, "EQ"))
            pins.append((cx, cy + 10, "LT"))
        elif name == "Shifter":
            pins.append((cx - 40, cy - 10, "IN"))
            pins.append((cx - 40, cy + 10, "AMT"))
            pins.append((cx, cy, "OUT"))
    elif lib == "4":
        if name in ("Register", "PC", "OUT") or aw.get("appearance") == "classic":
            if name != "ROM":
                pins.append((cx, cy, "Q"))
                pins.append((cx - 30, cy, "D"))
                pins.append((cx - 20, cy + 20, "CK"))
                pins.append((cx - 10, cy + 20, "CLR"))
                pins.append((cx - 30, cy + 10, "EN"))
        if name == "ROM":
            pins.append((cx, cy + 10, "ADDR"))
            pins.append((cx + 240, cy + 70, "DATA"))

    return [(px, py - YO, f"{name}.{pn}") for px, py, pn in pins]


def main():
    xml_path = sys.argv[1] if len(sys.argv) > 1 else "Logisim/sCPU_F6.circ"
    wires, content = parse_wires(xml_path)
    comps = parse_comps(content)

    # Build all pins
    all_pins = []
    for c in comps:
        all_pins.extend(get_pins(c))

    # Union-find on wires
    n = len(wires)
    parent = list(range(n))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(i, j):
        root_i, root_j = find(i), find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    for i in range(n):
        for j in range(i + 1, n):
            w1, w2 = wires[i], wires[j]
            # Check if segments share any point
            if w1[1] == w1[3] and w2[1] == w2[3] and w1[1] == w2[1]:  # H-H
                x1_min, x1_max = min(w1[0], w1[2]), max(w1[0], w1[2])
                x2_min, x2_max = min(w2[0], w2[2]), max(w2[0], w2[2])
                if max(x1_min, x2_min) <= min(x1_max, x2_max):
                    union(i, j)
            elif w1[0] == w1[2] and w2[0] == w2[2] and w1[0] == w2[0]:  # V-V
                y1_min, y1_max = min(w1[1], w1[3]), max(w1[1], w1[3])
                y2_min, y2_max = min(w2[1], w2[3]), max(w2[1], w2[3])
                if max(y1_min, y2_min) <= min(y1_max, y2_max):
                    union(i, j)
            elif w1[1] == w1[3] and w2[0] == w2[2]:  # H-V
                x_min, x_max = min(w1[0], w1[2]), max(w1[0], w1[2])
                y_min, y_max = min(w2[1], w2[3]), max(w2[1], w2[3])
                if x_min <= w2[0] <= x_max and y_min <= w1[1] <= y_max:
                    union(i, j)
            elif w1[0] == w1[2] and w2[1] == w2[3]:  # V-H
                x_min, x_max = min(w2[0], w2[2]), max(w2[0], w2[2])
                y_min, y_max = min(w1[1], w1[3]), max(w1[1], w1[3])
                if x_min <= w1[0] <= x_max and y_min <= w2[1] <= y_max:
                    union(i, j)

    # Map wires to nets
    net_wires = defaultdict(list)
    for i in range(n):
        net_wires[find(i)].append(i)

    # Find which pins are on each net
    nets = list(net_wires.values())
    print(f"Total logical nets: {len(nets)}")

    # For each net, find which pins touch it
    for net_idx, segs in enumerate(sorted(nets, key=len, reverse=True)):
        # Collect all points in this net
        net_points = set()
        for si in segs:
            w = wires[si]
            net_points.add((w[0], w[1]))
            net_points.add((w[2], w[3]))

        # Find pins that match points in this net
        net_pins = []
        for px, py, pdesc in all_pins:
            xml_x, xml_y = px, py + YO
            if (xml_x, xml_y) in net_points:
                net_pins.append(pdesc)

        # Group pins by type
        pin_types = defaultdict(list)
        for p in net_pins:
            comp = p.split(".")[0]
            pin = p.split(".")[1]
            pin_types[pin].append(comp)

        print(f"\n--- Net {net_idx + 1} ({len(segs)} wires, {len(net_pins)} pins) ---")
        for ptype, comps in sorted(pin_types.items()):
            print(f"  {ptype}: {', '.join(sorted(set(comps)))}")

if __name__ == "__main__":
    main()
