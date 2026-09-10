"""
生成人体各部位STL文件，用于Qt3D人偶
所有模型以Y轴为长轴，原点在模型中心（关节处）
"""
import numpy as np
from stl import mesh
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(OUT_DIR, exist_ok=True)


def make_capsule(radius, length, segments=24):
    """生成胶囊体（圆柱体+两个半球），Y轴为长轴，原点在中心"""
    vertices = []
    faces = []
    half = length / 2

    # 中间圆柱体
    cyl_start = len(vertices)
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        x = radius * np.cos(angle)
        z = radius * np.sin(angle)
        vertices.append([x, -half, z])
        vertices.append([x, half, z])
    for i in range(segments):
        i0 = cyl_start + i * 2
        i1 = cyl_start + ((i + 1) % segments) * 2
        faces.append([i0, i1, i1 + 1])
        faces.append([i0, i1 + 1, i0 + 1])

    # 上半球
    top_start = len(vertices)
    lat_seg = 8
    for lat in range(1, lat_seg + 1):
        phi = np.pi / 2 * lat / lat_seg
        r = radius * np.cos(phi)
        y = half + radius * np.sin(phi)
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            vertices.append([r * np.cos(angle), y, r * np.sin(angle)])
    # 上半球顶面
    top_pole = len(vertices)
    vertices.append([0, half + radius, 0])
    for i in range(segments):
        ring_start = top_start
        i0 = ring_start + i
        i1 = ring_start + (i + 1) % segments
        faces.append([i0, i1, top_pole])
    # 上半球侧面
    for lat in range(lat_seg - 1):
        ring0 = top_start + lat * segments
        ring1 = top_start + (lat + 1) * segments
        for i in range(segments):
            i0 = ring0 + i
            i1 = ring0 + (i + 1) % segments
            i2 = ring1 + (i + 1) % segments
            i3 = ring1 + i
            faces.append([i0, i1, i2])
            faces.append([i0, i2, i3])
    # 上半球底部和圆柱体连接
    for i in range(segments):
        cyl_i = cyl_start + i * 2 + 1
        cyl_next = cyl_start + ((i + 1) % segments) * 2 + 1
        ring_i = top_start + i
        ring_next = top_start + (i + 1) % segments
        faces.append([cyl_i, cyl_next, ring_next])
        faces.append([cyl_i, ring_next, ring_i])

    # 下半球
    bot_start = len(vertices)
    for lat in range(1, lat_seg + 1):
        phi = np.pi / 2 * lat / lat_seg
        r = radius * np.cos(phi)
        y = -half - radius * np.sin(phi)
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            vertices.append([r * np.cos(angle), y, r * np.sin(angle)])
    bot_pole = len(vertices)
    vertices.append([0, -half - radius, 0])
    for i in range(segments):
        ring_start = bot_start
        i0 = ring_start + i
        i1 = ring_start + (i + 1) % segments
        faces.append([i0, bot_pole, i1])
    for lat in range(lat_seg - 1):
        ring0 = bot_start + lat * segments
        ring1 = bot_start + (lat + 1) * segments
        for i in range(segments):
            i0 = ring0 + i
            i1 = ring0 + (i + 1) % segments
            i2 = ring1 + (i + 1) % segments
            i3 = ring1 + i
            faces.append([i0, i2, i1])
            faces.append([i0, i3, i2])
    for i in range(segments):
        cyl_i = cyl_start + i * 2
        cyl_next = cyl_start + ((i + 1) % segments) * 2
        ring_i = bot_start + i
        ring_next = bot_start + (i + 1) % segments
        faces.append([cyl_i, ring_next, cyl_next])
        faces.append([cyl_i, ring_i, ring_next])

    return mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype)), np.array(vertices), np.array(faces)


def make_sphere(radius, segments=24, lat_seg=16):
    """生成球体，原点在中心"""
    vertices = []
    faces = []
    for lat in range(lat_seg + 1):
        phi = np.pi * lat / lat_seg
        r = radius * np.sin(phi)
        y = radius * np.cos(phi)
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            vertices.append([r * np.cos(angle), y, r * np.sin(angle)])
    for lat in range(lat_seg):
        ring0 = lat * segments
        ring1 = (lat + 1) * segments
        for i in range(segments):
            i0 = ring0 + i
            i1 = ring0 + (i + 1) % segments
            i2 = ring1 + (i + 1) % segments
            i3 = ring1 + i
            faces.append([i0, i1, i2])
            faces.append([i0, i2, i3])
    return mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype)), np.array(vertices), np.array(faces)


def make_box(sx, sy, sz):
    """生成长方体，原点在中心"""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    vertices = [
        [-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
        [-hx, -hy, hz], [hx, -hy, hz], [hx, hy, hz], [-hx, hy, hz],
    ]
    faces = [
        [0, 1, 2], [0, 2, 3],  # back
        [4, 6, 5], [4, 7, 6],  # front
        [0, 4, 5], [0, 5, 1],  # bottom
        [3, 2, 6], [3, 6, 7],  # top
        [0, 3, 7], [0, 7, 4],  # left
        [1, 5, 6], [1, 6, 2],  # right
    ]
    return mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype)), np.array(vertices), np.array(faces)


def save_stl(filename, m, vertices, faces):
    for i, f in enumerate(faces):
        for j in range(3):
            m.vectors[i][j] = vertices[f[j]]
    m.save(os.path.join(OUT_DIR, filename))
    print(f"  {filename}: {len(faces)} triangles")


print("Generating STL models...")

# 四肢胶囊体（半径, 长度）
m, v, f = make_capsule(0.035, 0.22)  # 上臂
save_stl('upper_arm.stl', m, v, f)

m, v, f = make_capsule(0.030, 0.20)  # 前臂
save_stl('forearm.stl', m, v, f)

m, v, f = make_capsule(0.045, 0.32)  # 大腿
save_stl('thigh.stl', m, v, f)

m, v, f = make_capsule(0.035, 0.30)  # 小腿
save_stl('shin.stl', m, v, f)

# 头（球体）
m, v, f = make_sphere(0.06)
save_stl('head.stl', m, v, f)

# 躯干（长方体，稍微圆润）
m, v, f = make_box(0.18, 0.30, 0.10)
save_stl('spine.stl', m, v, f)

# 骨盆
m, v, f = make_box(0.16, 0.08, 0.10)
save_stl('hips.stl', m, v, f)

# 手
m, v, f = make_box(0.04, 0.06, 0.025)
save_stl('hand.stl', m, v, f)

# 脚
m, v, f = make_box(0.05, 0.03, 0.12)
save_stl('foot.stl', m, v, f)

# 滑雪板
m, v, f = make_box(0.06, 0.008, 0.80)
save_stl('ski.stl', m, v, f)

# 雪杖（细圆柱，用胶囊体代替）
m, v, f = make_capsule(0.006, 0.60)
save_stl('pole.stl', m, v, f)

print("Done! All STL files saved to models/")
