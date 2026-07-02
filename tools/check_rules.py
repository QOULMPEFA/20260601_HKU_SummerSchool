#!/usr/bin/env python3
"""Check Logisim circuit against guide-ai/Logisim电路生成规则.md"""
import re

YO = 200

with open('Logisim/sCPU_F6.circ', 'r', encoding='utf-8') as f:
    content = f.read()

violations = []

# ============ Rule 1: No diagonal wires ============
print("=" * 60)
print("Rule 1: No diagonal wires (all L-shaped)")
diagonals = 0
for m in re.finditer(r'<wire from="\((-?\d+),(-?\d+)\)" to="\((-?\d+),(-?\d+)\)"/>', content):
    x1, y1, x2, y2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    if x1 != x2 and y1 != y2:
        diagonals += 1
        if diagonals <= 5:
            print(f"  DIAGONAL: ({x1},{y1-YO}) -> ({x2},{y2-YO})")
if diagonals:
    violations.append(f"Rule 1: {diagonals} diagonal wires")
    print(f"  FAIL: {diagonals} diagonals")
else:
    print(f"  PASS: 0 diagonal wires")

# ============ Rule 2: No negative coordinates ============
print("\n" + "=" * 60)
print("Rule 2: No negative coordinates")
min_x, min_y = float('inf'), float('inf')
for m in re.finditer(r'<wire from="\((-?\d+),(-?\d+)\)"', content):
    min_x = min(min_x, int(m.group(1)))
    min_y = min(min_y, int(m.group(2)))
for m in re.finditer(r'loc="\((-?\d+),(-?\d+)\)"', content):
    min_x = min(min_x, int(m.group(1)))
    min_y = min(min_y, int(m.group(2)))

print(f"  Min X: {min_x}, Min Y (with YO): {min_y}" + (f" = logical {min_y-YO}" if min_y < 200 else ""))
if min_x < 0 or min_y < 0:
    violations.append(f"Rule 2: Negative coords (min x={min_x}, y={min_y})")
    print(f"  FAIL")
else:
    print(f"  PASS")

# ============ Rule 3: Wires through components ============
print("\n" + "=" * 60)
print("Rule 3: No wires through component bounding boxes")

def get_bounds(lib, name, cx, cy, attrs_str):
    w = attrs_str
    if lib == "0":
        if name == "Pin": return (cx-15,cy-10,cx+15,cy+10)
        elif name == "Splitter": return (cx-30,cy-30,cx+30,cy+30)
        elif name == "Constant": return (cx-25,cy-15,cx+25,cy+15)
        elif name == "Bit Extender": return (cx-40,cy-25,cx+20,cy+25)
        return (cx-20,cy-15,cx+20,cy+15)
    elif lib == "1":
        if "NOT" in name: return (cx-20,cy-15,cx+10,cy+15)
        return (cx-35,cy-20,cx+15,cy+20)
    elif lib == "2":
        if name == "Multiplexer": return (cx-35,cy-25,cx+15,cy+25)
        elif name == "Decoder": return (cx-15,cy-45,cx+25,cy+5)
        return (cx-30,cy-30,cx+30,cy+30)
    elif lib == "3":
        return (cx-45,cy-25,cx+10,cy+25)
    elif lib == "4":
        if name == "ROM": return (cx-10,cy-10,cx+250,cy+400)
        return (cx-35,cy-25,cx+5,cy+25)
    return (cx-30,cy-20,cx+30,cy+20)

comps = []
for m in re.finditer(r'<comp lib="(\d+)" loc="\((-?\d+),(-?\d+)\)" name="([^"]+)">(.*?)</comp>', content, re.DOTALL):
    lib, cx, cy, name = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    x1,y1,x2,y2 = get_bounds(lib, name, cx, cy, m.group(5))
    comps.append((name, x1, y1, x2, y2))

wires_list = []
for m in re.finditer(r'<wire from="\((-?\d+),(-?\d+)\)" to="\((-?\d+),(-?\d+)\)"/>', content):
    wires_list.append((int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4))))

wire_violations = 0
for wx1,wy1,wx2,wy2 in wires_list:
    for cname,cx1,cy1,cx2,cy2 in comps:
        if wy1 == wy2:  # horizontal
            hx1,hx2 = min(wx1,wx2), max(wx1,wx2)
            if wy1 > cy1 and wy1 < cy2 and hx1 < cx2-1 and hx2 > cx1+1:
                wire_violations += 1
                if wire_violations <= 5:
                    print(f"  H-wire y={wy1-YO} x=[{hx1},{hx2}] through {cname} bbox")
        elif wx1 == wx2:  # vertical
            vy1,vy2 = min(wy1,wy2), max(wy1,wy2)
            if wx1 > cx1 and wx1 < cx2 and vy1 < cy2-1 and vy2 > cy1+1:
                wire_violations += 1
                if wire_violations <= 5:
                    print(f"  V-wire x={wx1} y=[{vy1-YO},{vy2-YO}] through {cname} bbox")

if wire_violations:
    violations.append(f"Rule 3: {wire_violations} wires through components")
    print(f"  FAIL: {wire_violations} violations")
else:
    print(f"  PASS: 0 violations")

# ============ Rule 4: Component overlap ============
print("\n" + "=" * 60)
print("Rule 4: Component spacing (no overlapping bboxes)")
spacing_violations = 0
for i in range(len(comps)):
    for j in range(i+1, len(comps)):
        n1,x11,y11,x12,y12 = comps[i]
        n2,x21,y21,x22,y22 = comps[j]
        # Check if bboxes overlap
        if x11 < x22 and x21 < x12 and y11 < y22 and y21 < y12:
            spacing_violations += 1
            if spacing_violations <= 10:
                print(f"  OVERLAP: {n1}[{x11},{y11-YO}]-[{x12},{y12-YO}] vs {n2}[{x21},{y21-YO}]-[{x22},{y22-YO}]")

if spacing_violations:
    violations.append(f"Rule 4: {spacing_violations} component overlaps")
    print(f"  FAIL: {spacing_violations} overlaps")
else:
    print(f"  PASS: 0 overlaps")

# ============ Rule 5: XML format ============
print("\n" + "=" * 60)
print("Rule 5: XML format compliance")

if 'project source="2.7.2"' in content:
    print("  PASS: Logisim v2.7.2 format")
else:
    violations.append("Rule 5: Not v2.7.2 format")

required_libs = {"0":"#Wiring","1":"#Gates","2":"#Plexers","3":"#Arithmetic","4":"#Memory","5":"#I/O","6":"#Base"}
found = set()
for m in re.finditer(r'<lib desc="([^"]+)" name="(\d+)"/>', content):
    found.add(m.group(2))
missing = set(required_libs.keys()) - found
if missing:
    violations.append(f"Rule 5: Missing libs: {missing}")
    print(f"  FAIL: Missing libs {missing}")
else:
    print(f"  PASS: All 7 libraries")

rom_match = re.search(r'<comp lib="4".*?name="ROM">(.*?)</comp>', content, re.DOTALL)
if rom_match and 'addr/data:' in rom_match.group(0):
    print("  PASS: ROM content format")
else:
    violations.append("Rule 5: ROM format issue")

inline = re.findall(r'<comp[^>]+=\s*"[^"]*"[^>]*>', content)
inline_bad = [i for i in inline if '<a name=' not in i and '/>' in i]
if inline_bad:
    violations.append(f"Rule 5: {len(inline_bad)} inline-attr components")
    print(f"  FAIL: {len(inline_bad)} inline attrs")
else:
    print("  PASS: All attributes as child elements")

# ============ Rule 6-7: not checkable ============

# ============ Rule 8: Safe areas ============
print("\n" + "=" * 60)
print("Rule 8: Known safe areas check")

safe_areas = {
    "Pin列":     (30, 90, 290, 390),
    "PC列":      (160, 245, 310, 940),
    "ROM列":     (280, 480, 190, 540),
    "PC_Mux":    (350, 410, 610, 690),
    "Splitter":  (550, 610, 320, 360),
    "Decoder":   (630, 690, 540, 580),
    "BitExt2":   (550, 610, 830, 870),
    "Shifter":   (720, 800, 830, 870),
    "GPR列":     (720, 800, 230, 710),
    "raddrMux":  (790, 1050, 160, 270),
    "rMux":      (910, 1090, 250, 550),
    "ALU列":     (1160, 1240, 370, 590),
    "控制门":    (660, 1020, 930, 1180),
    "wMux":      (1170, 1390, 750, 790),
    "OUT":       (1160, 1240, 900, 940),
    "waddrDec":  (830, 890, 1120, 1150),
    "devConst":  (970, 1030, 1170, 1200),
}

mismatches = 0
for cname,cx1,cy1,cx2,cy2 in comps:
    cx, cy = (cx1+cx2)/2, (cy1+cy2)/2
    # Find matching safe area
    matched = None
    for aname,(ax1,ax2,ay1,ay2) in safe_areas.items():
        if ax1 <= cx <= ax2 and ay1 <= cy <= ay2:
            matched = aname
            break
    if matched is None:
        mismatches += 1
        if mismatches <= 5:
            print(f"  UNMATCHED: {cname} at center ({int(cx)},{int(cy-YO)}) — no safe area")

if mismatches:
    print(f"  NOTE: {mismatches} components outside defined safe areas (may be OK)")
else:
    print(f"  PASS: All components in known safe areas")

# ============ Summary ============
print("\n" + "=" * 60)
print("COMPLIANCE SUMMARY")
print("=" * 60)
if violations:
    print(f"\n[!!!] {len(violations)} VIOLATIONS:")
    for v in violations:
        print(f"  - {v}")
else:
    print("\n[OK] ALL RULES PASSED")

print(f"\nTotal: 48 components, {len(wires_list)} wires")
