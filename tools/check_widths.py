#!/usr/bin/env python3
"""Find bit-width mismatches in Logisim circuit."""
import re
from collections import defaultdict

with open('Logisim/sCPU_F6.circ', 'r', encoding='utf-8') as f:
    content = f.read()

YO = 200

# Parse pins with widths
pins = {}  # (x,y) -> (width, name, pin_desc)

for m in re.finditer(r'<comp lib="(\d+)" loc="\((-?\d+),(-?\d+)\)" name="([^"]+)">(.*?)</comp>', content, re.DOTALL):
    lib, cx_s, cy_s, name = m.group(1), m.group(2), m.group(3), m.group(4)
    cx, cy = int(cx_s), int(cy_s)
    attrs = m.group(5)

    def getw(default=1):
        w = re.search(r'<a name="width" val="(\d+)"', attrs)
        return int(w.group(1)) if w else default

    if lib == "0":
        if name == "Pin":
            w = getw(1); pins[(cx,cy)] = (w, name, "PORT")
        elif name == "Constant":
            w = getw(1); pins[(cx,cy)] = (w, name, "OUT")
        elif name == "Splitter":
            inc_m = re.search(r'<a name="incoming" val="(\d+)"', attrs)
            inc = int(inc_m.group(1)) if inc_m else 8
            fanout_m = re.search(r'<a name="fanout" val="(\d+)"', attrs)
            fanout = int(fanout_m.group(1)) if fanout_m else 2
            facing_m = re.search(r'<a name="facing" val="(\w+)"', attrs)
            facing = facing_m.group(1) if facing_m else "east"
            appear_m = re.search(r'<a name="appear" val="(\w+)"', attrs)
            appear = appear_m.group(1) if appear_m else "center"
            pins[(cx,cy)] = (inc, name, "COMB")
            gap, sw = 10, 20
            for fi in range(fanout):
                if facing in ("east","west"):
                    ms = -1 if facing=="west" else 1
                    if appear=="center": dy0 = -gap*(fanout//2)
                    elif (ms>0 and appear=="right") or (ms<0 and appear=="left"): dy0 = 10
                    else: dy0 = -(10+gap*(fanout-1))
                    fx, fy = cx+ms*sw, cy+dy0+fi*gap
                    pins[(fx,fy)] = (inc//fanout, name, f"FAN{fi}")
        elif name == "Bit Extender":
            ow = re.search(r'<a name="out_width" val="(\d+)"', attrs)
            iw = re.search(r'<a name="in_width" val="(\d+)"', attrs)
            out_w = int(ow.group(1)) if ow else 8
            in_w = int(iw.group(1)) if iw else 2
            pins[(cx,cy)] = (out_w, name, "OUT")
            pins[(cx-40,cy)] = (in_w, name, "IN")
    elif lib == "1":
        if "NOT" in name:
            pins[(cx,cy)] = (1, name, "OUT")
            pins[(cx-20,cy)] = (1, name, "IN")
        else:
            pins[(cx,cy)] = (1, name, "OUT")
            pins[(cx-30,cy-10)] = (1, name, "IN0")
            pins[(cx-30,cy+10)] = (1, name, "IN1")
    elif lib == "2":
        if name == "Multiplexer":
            bw = getw(8)
            sel_m = re.search(r'<a name="select" val="(\d+)"', attrs)
            sel_w = int(sel_m.group(1)) if sel_m else 1
            pins[(cx,cy)] = (bw, name, "OUT")
            pins[(cx-30,cy-10)] = (bw, name, "IN0")
            pins[(cx-30,cy+10)] = (bw, name, "IN1")
            pins[(cx-20,cy+20)] = (sel_w, name, "SEL")
        elif name == "Decoder":
            sel_m = re.search(r'<a name="select" val="(\d+)"', attrs)
            sw = int(sel_m.group(1)) if sel_m else 2
            for i in range(2**sw):
                pins[(cx+20,cy-40+i*10)] = (1, name, f"OUT{i}")
            pins[(cx,cy)] = (sw, name, "SEL")
            if 'enable="true"' in attrs:
                pins[(cx-10,cy)] = (1, name, "EN")
    elif lib == "3":
        bw = getw(8)
        if name == "Adder":
            pins[(cx-40,cy-10)] = (bw, name, "A")
            pins[(cx-40,cy+10)] = (bw, name, "B")
            pins[(cx,cy)] = (bw, name, "OUT")
            pins[(cx-20,cy-20)] = (1, name, "CIN")
            pins[(cx-20,cy+20)] = (1, name, "COUT")
        elif name == "Comparator":
            pins[(cx-40,cy-10)] = (bw, name, "A")
            pins[(cx-40,cy+10)] = (bw, name, "B")
            pins[(cx,cy-10)] = (1, name, "GT")
            pins[(cx,cy)] = (1, name, "EQ")
            pins[(cx,cy+10)] = (1, name, "LT")
        elif name == "Shifter":
            pins[(cx-40,cy-10)] = (bw, name, "IN")
            pins[(cx-40,cy+10)] = (bw, name, "AMT")
            pins[(cx,cy)] = (bw, name, "OUT")
    elif lib == "4":
        bw = getw(8)
        if name == "ROM":
            aw = int(re.search(r'<a name="addrWidth" val="(\d+)"', attrs).group(1))
            dw = int(re.search(r'<a name="dataWidth" val="(\d+)"', attrs).group(1))
            pins[(cx,cy+10)] = (aw, name, "ADDR")
            pins[(cx+240,cy+70)] = (dw, name, "DATA")
        else:
            pins[(cx,cy)] = (bw, name, "Q")
            pins[(cx-30,cy)] = (bw, name, "D")
            pins[(cx-20,cy+20)] = (1, name, "CK")
            pins[(cx-10,cy+20)] = (1, name, "CLR")
            pins[(cx-30,cy+10)] = (1, name, "EN")

# Parse wires
wires = []
for m in re.finditer(r'<wire from="\((-?\d+),(-?\d+)\)" to="\((-?\d+),(-?\d+)\)"/>', content):
    wires.append((int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4))))

n = len(wires)
parent = list(range(n))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
def union(i, j):
    ri, rj = find(i), find(j)
    if ri != rj: parent[ri] = rj

def share(w1, w2):
    if w1[1]==w1[3] and w2[1]==w2[3] and w1[1]==w2[1]:
        x1=(min(w1[0],w1[2]),max(w1[0],w1[2])); x2=(min(w2[0],w2[2]),max(w2[0],w2[2]))
        return max(x1[0],x2[0])<=min(x1[1],x2[1])
    elif w1[0]==w1[2] and w2[0]==w2[2] and w1[0]==w2[0]:
        y1=(min(w1[1],w1[3]),max(w1[1],w1[3])); y2=(min(w2[1],w2[3]),max(w2[1],w2[3]))
        return max(y1[0],y2[0])<=min(y1[1],y2[1])
    elif w1[1]==w1[3] and w2[0]==w2[2]:
        hx=(min(w1[0],w1[2]),max(w1[0],w1[2])); vy=(min(w2[1],w2[3]),max(w2[1],w2[3]))
        return hx[0]<=w2[0]<=hx[1] and vy[0]<=w1[1]<=vy[1]
    elif w1[0]==w1[2] and w2[1]==w2[3]:
        vy=(min(w1[1],w1[3]),max(w1[1],w1[3])); hx=(min(w2[0],w2[2]),max(w2[0],w2[2]))
        return hx[0]<=w1[0]<=hx[1] and vy[0]<=w2[1]<=vy[1]
    return False

for i in range(n):
    for j in range(i+1, n):
        if share(wires[i], wires[j]):
            union(i, j)

# Map pins to nets
net_pins = defaultdict(list)
for (px, py), (pw, pname, ppin) in pins.items():
    for wi, w in enumerate(wires):
        if (w[0],w[1])==(px,py) or (w[2],w[3])==(px,py):
            net_pins[find(wi)].append((pw, pname, ppin, px, py))
            break

# Also check: pins at same (x,y) on DIFFERENT components (pin overlap)
pin_overlaps = defaultdict(list)
for (px, py), (pw, pname, ppin) in pins.items():
    pin_overlaps[(px,py)].append((pw, pname, ppin))

print("=== PIN OVERLAP WIDTH CHECK ===")
overlap_issues = 0
for pos, plist in pin_overlaps.items():
    widths = set(p[0] for p in plist)
    if len(widths) > 1:
        overlap_issues += 1
        print(f"\nWidth mismatch at ({pos[0]},{pos[1]-YO}):")
        for pw, pname, ppin in plist:
            print(f"  {pname}.{ppin} width={pw}")

print(f"\nTotal pin overlap mismatches: {overlap_issues}")

# Check nets for width mismatches
print("\n=== NET WIDTH CHECK ===")
mismatches = 0
for net_id, plist in sorted(net_pins.items(), key=lambda x: -len(x[1])):
    widths = set(p[0] for p in plist)
    if len(widths) > 1:
        mismatches += 1
        print(f"\nNet (root {net_id}): widths {widths}")
        for pw, pname, ppin, px, py in sorted(plist, key=lambda x: x[0]):
            print(f"  width={pw}: {pname}.{ppin} at ({px},{py-YO})")
        if mismatches >= 8:
            print(f"  ... (stopping after 8)")
            break

print(f"\nTotal nets with width mismatches: {mismatches}")
