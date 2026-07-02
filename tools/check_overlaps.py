#!/usr/bin/env python3
"""检查 Logisim .circ 中的非预期线段重叠 (网络间短路)"""
import re
import sys
from collections import defaultdict

def parse_wires(xml_path):
    wires = []
    with open(xml_path, encoding="utf-8") as f:
        content = f.read()
    for m in re.finditer(r'<wire from="\((-?\d+),(-?\d+)\)" to="\((-?\d+),(-?\d+)\)"/>', content):
        x1, y1, x2, y2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        wires.append((x1, y1, x2, y2))
    return wires

def segments_share_point(w1, w2):
    """两个轴对齐线段是否共享至少一个点"""
    x11, y11, x12, y12 = w1
    x21, y21, x22, y22 = w2

    # 水平-水平: 同 y 且 x 区间重叠
    if y11 == y12 and y21 == y22 and y11 == y21:
        x1_min, x1_max = min(x11, x12), max(x11, x12)
        x2_min, x2_max = min(x21, x22), max(x21, x22)
        return max(x1_min, x2_min) <= min(x1_max, x2_max)

    # 垂直-垂直: 同 x 且 y 区间重叠
    if x11 == x12 and x21 == x22 and x11 == x21:
        y1_min, y1_max = min(y11, y12), max(y11, y12)
        y2_min, y2_max = min(y21, y22), max(y21, y22)
        return max(y1_min, y2_min) <= min(y1_max, y2_max)

    # 水平-垂直交叉
    if y11 == y12 and x21 == x22:
        x_min, x_max = min(x11, x12), max(x11, x12)
        y_min, y_max = min(y21, y22), max(y21, y22)
        return x_min <= x21 <= x_max and y_min <= y11 <= y_max

    if x11 == x12 and y21 == y22:
        x_min, x_max = min(x21, x22), max(x21, x22)
        y_min, y_max = min(y11, y12), max(y11, y12)
        return x_min <= x11 <= x_max and y_min <= y21 <= y_max

    return False

def find_overlap_point(w1, w2):
    """返回两个重叠线段的共享点"""
    x11, y11, x12, y12 = w1
    x21, y21, x22, y22 = w2

    if y11 == y12 and y21 == y22 and y11 == y21:
        x1_min, x1_max = min(x11, x12), max(x11, x12)
        x2_min, x2_max = min(x21, x22), max(x21, x22)
        return (max(x1_min, x2_min), y11)

    if x11 == x12 and x21 == x22 and x11 == x21:
        y1_min, y1_max = min(y11, y12), max(y11, y12)
        y2_min, y2_max = min(y21, y22), max(y21, y22)
        return (x11, max(y1_min, y2_min))

    if y11 == y12 and x21 == x22:
        return (x21, y11)
    if x11 == x12 and y21 == y22:
        return (x11, y21)
    return None

def main():
    xml_path = sys.argv[1] if len(sys.argv) > 1 else "Logisim/sCPU_F6.circ"
    wires = parse_wires(xml_path)
    n = len(wires)
    print(f"Total wire segments: {n}")

    # Union-Find: 任意共享点的线段合并为同一网络
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

    # 检查所有线段对: 共享点 → 合并
    for i in range(n):
        for j in range(i + 1, n):
            if segments_share_point(wires[i], wires[j]):
                union(i, j)

    # 按网络分组
    nets_map = defaultdict(list)
    for i in range(n):
        nets_map[find(i)].append(i)

    nets = list(nets_map.values())
    print(f"Logical nets: {len(nets)}")

    # 检查不同网络间是否还有重叠 (这不应发生，如果发生了就是真正的冲突)
    # 实际上如果我们的 union-find 是正确的，不同网络间不可能有重叠
    # 但我们可以检查 "可疑重叠" — 同一 y 上不同网络的水平线靠近但不重叠

    # 更重要: 检查同一网络内是否有宽度不一致的信号
    # 这需要知道每条线段的信号宽度...

    # 让我们换个角度: 检查是否有不该连在一起的端口被连通了
    # 解析所有 comp 的端口位置
    with open(xml_path, encoding="utf-8") as f:
        content = f.read()

    # 提取元件信息 (loc + name)
    comps = []
    for m in re.finditer(r'<comp lib="(\d+)" loc="\((-?\d+),(-?\d+)\)" name="([^"]+)">(.*?)</comp>', content, re.DOTALL):
        lib = m.group(1)
        x = int(m.group(2))
        y = int(m.group(3))
        name = m.group(4)
        attrs_str = m.group(5)
        # 提取关键宽度属性
        widths = {}
        for am in re.finditer(r'<a name="(\w+)" val="([^"]+)"/>', attrs_str):
            widths[am.group(1)] = am.group(2)
        comps.append({'lib': lib, 'x': x, 'y': y, 'name': name, 'attrs': widths})

    # 计算每个网络的覆盖范围
    for net_id, segs in nets_map.items():
        if len(segs) <= 1:
            continue
        # 收集网络中所有唯一点
        points = set()
        for si in segs:
            w = wires[si]
            # 添加线段端点
            points.add((w[0], w[1]))
            points.add((w[2], w[3]))

        # 检查: 该网络中是否有不同 y 层的大量线段 (暗示多个信号通过同一通道)
        ys = set(p[1] for p in points)
        xs = set(p[0] for p in points)

    # 主要检查: 同一 y 坐标上，两个不同网络的水平线是否交叉
    # 按 y 分组
    h_by_y = defaultdict(list)  # y → [(x1,x2,net_id), ...]
    v_by_x = defaultdict(list)  # x → [(y1,y2,net_id), ...]

    for net_id, segs in nets_map.items():
        for si in segs:
            w = wires[si]
            if w[1] == w[3]:  # 水平
                h_by_y[w[1]].append((min(w[0], w[2]), max(w[0], w[2]), net_id))
            else:  # 垂直
                v_by_x[w[0]].append((min(w[1], w[3]), max(w[1], w[3]), net_id))

    problems = []

    # 检查水平线
    for y, segs in h_by_y.items():
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                x1a, x1b, n1 = segs[i]
                x2a, x2b, n2 = segs[j]
                if n1 == n2:
                    continue  # 同一网络内重叠是正常的
                if max(x1a, x2a) <= min(x1b, x2b):
                    # 重叠! 但它们在 union-find 中应该有相同的根...
                    # 如果不同根, 说明它们通过其他线段间接相连??
                    # 检查端点共享
                    problems.append({
                        'type': 'H-H overlap',
                        'y': y,
                        'x_range': (max(x1a, x2a), min(x1b, x2b)),
                        'net1': n1, 'net2': n2,
                        'seg1': (x1a, y, x1b, y),
                        'seg2': (x2a, y, x2b, y),
                    })

    # 检查垂直线
    for x, segs in v_by_x.items():
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                y1a, y1b, n1 = segs[i]
                y2a, y2b, n2 = segs[j]
                if n1 == n2:
                    continue
                if max(y1a, y2a) <= min(y1b, y2b):
                    problems.append({
                        'type': 'V-V overlap',
                        'x': x,
                        'y_range': (max(y1a, y2a), min(y1b, y2b)),
                        'net1': n1, 'net2': n2,
                        'seg1': (x, y1a, x, y1b),
                        'seg2': (x, y2a, x, y2b),
                    })

    # 检查水平-垂直交叉
    for y, h_segs in h_by_y.items():
        for x1a, x1b, n1 in h_segs:
            for x_val, v_segs in v_by_x.items():
                if not (x1a <= x_val <= x1b):
                    continue
                for y2a, y2b, n2 in v_segs:
                    if n1 == n2:
                        continue
                    if y2a <= y <= y2b:
                        problems.append({
                            'type': 'H-V cross',
                            'point': (x_val, y),
                            'net1': n1, 'net2': n2,
                            'seg1': (x1a, y, x1b, y),
                            'seg2': (x_val, y2a, x_val, y2b),
                        })

    YO = 200
    if not problems:
        print("\n[OK] No cross-net overlaps detected!")
        return

    print(f"\n[WARN] Found {len(problems)} cross-net overlap(s):")
    # 按类型分组显示
    by_type = defaultdict(list)
    for p in problems:
        by_type[p['type']].append(p)

    for ptype, plist in by_type.items():
        print(f"\n  --- {ptype} ({len(plist)} instances) ---")
        # 只显示前10个
        for p in plist[:10]:
            sy = p.get('y', p.get('point', (0, 0))[1]) - YO
            if ptype == 'H-H overlap':
                xr = p['x_range']
                print(f"    y={sy}: nets {p['net1']} vs {p['net2']}, x=[{xr[0]}..{xr[1]}]")
            elif ptype == 'V-V overlap':
                yr = p['y_range']
                print(f"    x={p['x']}: nets {p['net1']} vs {p['net2']}, y=[{yr[0]-YO}..{yr[1]-YO}]")
            elif ptype == 'H-V cross':
                pt = p['point']
                print(f"    ({pt[0]}, {pt[1]-YO}): net {p['net1']} (H) × net {p['net2']} (V)")
        if len(plist) > 10:
            print(f"    ... and {len(plist) - 10} more")

    # 输出具体重叠详情
    print("\n\n=== Detailed overlaps ===")
    for p in problems[:30]:
        if p['type'] == 'H-H overlap':
            sy = p['y'] - YO
            print(f"\ny={sy} (source): net{n1} vs net{n2} overlap x=[{p['x_range'][0]}..{p['x_range'][1]}]")
        elif p['type'] == 'H-V cross':
            pt = p['point']
            print(f"\n({pt[0]}, {pt[1]-YO}): net{n1} H × net{n2} V")

if __name__ == "__main__":
    main()
