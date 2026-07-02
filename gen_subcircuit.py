#!/usr/bin/env python3
"""Generate Logisim subcircuit circuit with <appear> blocks for explicit port positions."""
import sys, re
sys.path.insert(0, '.')
import xml.etree.ElementTree as ET

with open('subcircuits.py', 'r', encoding='utf-8') as f:
    exec(f.read())

YO = 200
def P(x, y):
    return f"({x},{y + YO})"
def a_xml(name, val):
    return f'<a name="{name}" val="{val}"/>'

# Build all subcircuits
cr = build_clock_reset()
pc = build_pc()
fd = build_fetch_decode()
gp = build_gpr_rmux()
al = build_alu()
ct = build_control()
wb = build_writeback()
all_sc = [cr, pc, fd, gp, al, ct, wb]

# Placements from log/subcircuit_specs.json (all global y >= 150)
placements = {
    "clock_reset": (50, 200),
    "pc": (150, 400),
    "fetch_decode": (390, 350),
    "gpr_rmux": (690, 370),
    "alu": (1150, 450),
    "control": (690, 940),
    "writeback": (1170, 800),
}

IND = "    "
L = []

def pg(s, pname):
    ox, oy = placements[s.name]
    lx, ly = s.port_xy(pname)
    return (ox + lx, oy + ly)

# XML header
L.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
L.append('<project source="2.7.2" version="1.0">')
L.append('This file is intended to be loaded by Logisim (http://www.cburch.com/logisim/).')
for num, desc in [("0","#Wiring"),("1","#Gates"),("2","#Plexers"),("3","#Arithmetic"),("4","#Memory"),("5","#I/O"),("6","#Base")]:
    L.append(f'  <lib desc="{desc}" name="{num}"/>')
L.append('  <main name="main"/>')
L.append('  <options>')
L.append(f'    {a_xml("gateUndefined", "ignore")}')
L.append(f'    {a_xml("simlimit", "1000")}')
L.append(f'    {a_xml("simrand", "0")}')
L.append('  </options>')
L.append('  <mappings>')
L.append('    <tool lib="6" map="Button2" name="Poke Tool"/>')
L.append('    <tool lib="6" map="Button3" name="Menu Tool"/>')
L.append('    <tool lib="6" map="Ctrl Button1" name="Menu Tool"/>')
L.append('  </mappings>')
L.append('  <toolbar>')
L.append('    <tool lib="6" name="Poke Tool"/>')
L.append('    <tool lib="6" name="Edit Tool"/>')
L.append('  </toolbar>')

# MAIN circuit — just instantiate blocks, NO wiring yet
L.append('  <circuit name="main">')
L.append(f'    <a name="circuit" val="main"/>')
L.append(f'    <a name="clabel" val=""/>')
L.append(f'    <a name="clabelup" val="east"/>')
for s in all_sc:
    ox, oy = placements[s.name]
    L.append(f'{IND}<comp loc="{P(ox, oy)}" name="{s.name}"/>')
L.append('  </circuit>')

# SUBCIRCUIT definitions with <appear> blocks
for s in all_sc:
    L.append(f'  <circuit name="{s.name}">')
    L.append(f'    <a name="circuit" val="{s.name}"/>')
    L.append(f'    <a name="clabel" val=""/>')
    L.append(f'    <a name="clabelup" val="east"/>')

    # Wires (XML coords with YO)
    for fx, fy, tx, ty in s._wires:
        L.append(f'    <wire from="{P(fx, fy)}" to="{P(tx, ty)}"/>')

    # Components (Pins are I/O ports) — MUST come before <appear>
    for lib, x, y, name, props in s._comps:
        L.append(f'    {comp(lib, (x, y), name, **props)}')

    # ROM special
    if hasattr(s, '_rom_lines'):
        for rl in s._rom_lines:
            L.append(rl)

    # ---- NO <appear> block — let Logisim auto-compute port positions ----
    # Pins with facing="west"/"east" will appear on EAST/WEST edges automatically

    L.append(f'  </circuit>')

L.append('</project>')
xml = "\n".join(L) + "\n"

with open('Logisim/sCPU_F6_sub.circ', 'w', encoding='utf-8') as f:
    f.write(xml)
with open('d:/sCPU/sCPU_F6_sub.circ', 'w', encoding='utf-8') as f:
    f.write(xml)

# Quick verify
try:
    ET.parse('Logisim/sCPU_F6_sub.circ')
    print("XML valid.")
except Exception as e:
    print(f"Error: {e}")

# Check a circ-port example
m = re.search(r'<circ-port height="10" pin="([^"]+)" width="10" x="([^"]+)" y="([^"]+)"', xml)
if m:
    print(f"Example circ-port: pin={m.group(1)} x={m.group(2)} y={m.group(3)}")
    # Check matching Pin loc
    pin_loc = f'loc="({m.group(1)})"'
    if pin_loc in xml:
        print(f"  Matching Pin loc found: {pin_loc}")
    else:
        print(f"  WARNING: No Pin with loc={pin_loc}")
