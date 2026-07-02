#!/usr/bin/env python3
"""Find the FIRST bridge wire pair connecting CK to RST, using alternating BFS."""
import re
from collections import deque

with open('Logisim/sCPU_F6.circ', encoding='utf-8') as f:
    content = f.read()

wires = []
for m in re.finditer(r'<wire from="\((-?\d+),(-?\d+)\)" to="\((-?\d+),(-?\d+)\)"/>', content):
    wires.append(tuple(int(g) for g in m.groups()))
n = len(wires)

# Precompute adjacency: wire[i] touches wire[j]
adj = {i: set() for i in range(n)}
for i in range(n):
    for j in range(i+1, n):
        w1, w2 = wires[i], wires[j]
        shared = False
        if w1[1] == w1[3] and w2[1] == w2[3] and w1[1] == w2[1]:
            x1 = (min(w1[0],w1[2]), max(w1[0],w1[2]))
            x2 = (min(w2[0],w2[2]), max(w2[0],w2[2]))
            shared = max(x1[0],x2[0]) <= min(x1[1],x2[1])
        elif w1[0] == w1[2] and w2[0] == w2[2] and w1[0] == w2[0]:
            y1 = (min(w1[1],w1[3]), max(w1[1],w1[3]))
            y2 = (min(w2[1],w2[3]), max(w2[1],w2[3]))
            shared = max(y1[0],y2[0]) <= min(y1[1],y2[1])
        elif w1[1] == w1[3] and w2[0] == w2[2]:
            hx = (min(w1[0],w1[2]), max(w1[0],w1[2]))
            vy = (min(w2[1],w2[3]), max(w2[1],w2[3]))
            shared = hx[0] <= w2[0] <= hx[1] and vy[0] <= w1[1] <= vy[1]
        elif w1[0] == w1[2] and w2[1] == w2[3]:
            vy = (min(w1[1],w1[3]), max(w1[1],w1[3]))
            hx = (min(w2[0],w2[2]), max(w2[0],w2[2]))
            shared = hx[0] <= w1[0] <= hx[1] and vy[0] <= w2[1] <= vy[1]
        if shared:
            adj[i].add(j)
            adj[j].add(i)

# Find seed wire indices
ck_start = set()
rst_start = set()

for m in re.finditer(r'<comp lib="(\d+)" loc="\((-?\d+),(-?\d+)\)" name="([^"]+)">(.*?)</comp>', content, re.DOTALL):
    lib, cx, cy, name = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    attrs = m.group(5)
    if name in ('Register', 'PC', 'OUT') or ('classic' in attrs and name != 'ROM'):
        if name != 'ROM':
            ck_seed_pt = (cx - 20, cy + 20)
            rst_seed_pt = (cx - 10, cy + 20)
            for i, w in enumerate(wires):
                if (w[0],w[1]) == ck_seed_pt or (w[2],w[3]) == ck_seed_pt:
                    ck_start.add(i)
                if (w[0],w[1]) == rst_seed_pt or (w[2],w[3]) == rst_seed_pt:
                    rst_start.add(i)
    if name == 'Pin':
        label_m = re.search(r'<a name="label" val="([^"]+)"/>', attrs)
        if label_m:
            label = label_m.group(1)
            pt = (cx, cy)
            for i, w in enumerate(wires):
                if (w[0],w[1]) == pt or (w[2],w[3]) == pt:
                    if label == 'clk':
                        ck_start.add(i)
                    elif label == 'rst':
                        rst_start.add(i)

# Alternating BFS: expand CK and RST frontiers alternately, check for bridges
ck_visited = set(ck_start)
rst_visited = set(rst_start)
ck_frontier = deque(ck_start)
rst_frontier = deque(rst_start)

iteration = 0
while ck_frontier and rst_frontier:
    iteration += 1
    # Expand CK
    new_ck = deque()
    while ck_frontier:
        wi = ck_frontier.popleft()
        for nj in adj[wi]:
            if nj not in ck_visited:
                if nj in rst_visited:
                    # BRIDGE FOUND! Wire 'wi' (CK side) touches wire 'nj' (RST side)
                    w1, w2 = wires[wi], wires[nj]
                    print(f"BRIDGE at iteration {iteration}:")
                    print(f"  CK wire ({w1[0]},{w1[1]-200})->({w1[2]},{w1[3]-200})")
                    print(f"  RST wire ({w2[0]},{w2[1]-200})->({w2[2]},{w2[3]-200})")

                    # Find shared point
                    sp = None
                    if w1[1] == w1[3] and w2[1] == w2[3] and w1[1] == w2[1]:
                        x1 = (min(w1[0],w1[2]), max(w1[0],w1[2]))
                        x2 = (min(w2[0],w2[2]), max(w2[0],w2[2]))
                        sp = (max(x1[0],x2[0]), w1[1])
                    elif w1[0] == w1[2] and w2[0] == w2[2] and w1[0] == w2[0]:
                        y1 = (min(w1[1],w1[3]), max(w1[1],w1[3]))
                        y2 = (min(w2[1],w2[3]), max(w2[1],w2[3]))
                        sp = (w1[0], max(y1[0],y2[0]))
                    elif w1[1] == w1[3] and w2[0] == w2[2]:
                        sp = (w2[0], w1[1])
                    elif w1[0] == w1[2] and w2[1] == w2[3]:
                        sp = (w1[0], w2[1])
                    if sp:
                        print(f"  Shared point: ({sp[0]},{sp[1]-200})")
                    import sys; sys.exit(0)
                ck_visited.add(nj)
                new_ck.append(nj)
    ck_frontier = new_ck

    # Expand RST
    new_rst = deque()
    while rst_frontier:
        wi = rst_frontier.popleft()
        for nj in adj[wi]:
            if nj not in rst_visited:
                if nj in ck_visited:
                    w2, w1 = wires[wi], wires[nj]  # wi is rst side, nj is ck side
                    print(f"BRIDGE at iteration {iteration}:")
                    print(f"  RST wire ({w2[0]},{w2[1]-200})->({w2[2]},{w2[3]-200})")
                    print(f"  CK wire ({w1[0]},{w1[1]-200})->({w1[2]},{w1[3]-200})")
                    sp = None
                    if w1[1] == w1[3] and w2[1] == w2[3] and w1[1] == w2[1]:
                        x1 = (min(w1[0],w1[2]), max(w1[0],w1[2]))
                        x2 = (min(w2[0],w2[2]), max(w2[0],w2[2]))
                        sp = (max(x1[0],x2[0]), w1[1])
                    elif w1[0] == w1[2] and w2[0] == w2[2] and w1[0] == w2[0]:
                        y1 = (min(w1[1],w1[3]), max(w1[1],w1[3]))
                        y2 = (min(w2[1],w2[3]), max(w2[1],w2[3]))
                        sp = (w1[0], max(y1[0],y2[0]))
                    elif w1[1] == w1[3] and w2[0] == w2[2]:
                        sp = (w2[0], w1[1])
                    elif w1[0] == w1[2] and w2[1] == w2[3]:
                        sp = (w1[0], w2[1])
                    if sp:
                        print(f"  Shared point: ({sp[0]},{sp[1]-200})")
                    import sys; sys.exit(0)
                rst_visited.add(nj)
                new_rst.append(nj)
    rst_frontier = new_rst

print(f"No bridge found after {iteration} iterations.")
print(f"CK visited: {len(ck_visited)}, RST visited: {len(rst_visited)}")
