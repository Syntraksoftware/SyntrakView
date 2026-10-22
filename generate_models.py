"""
多套人偶STL模型生成器 v4
参数化生成男女老少多款滑雪者人偶，每套输出到 models/<名称>/ 子目录
所有几何体均为封闭实体（圆柱体有顶底、胶囊体两端封闭、立方体六面封闭）
"""
import numpy as np
from stl import mesh
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), 'models')


# ==================== 基础几何体（全部封闭） ====================

def make_box(sx, sy, sz):
    """封闭立方体（6面12三角形）"""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    vertices = [
        [-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
        [-hx, -hy, hz], [hx, -hy, hz], [hx, hy, hz], [-hx, hy, hz],
    ]
    faces = [
        [0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6],
        [0, 4, 5], [0, 5, 1], [3, 2, 6], [3, 6, 7],
        [0, 3, 7], [0, 7, 4], [1, 5, 6], [1, 6, 2],
    ]
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)


def make_cylinder(radius, height, segments=24):
    """封闭圆柱体（顶面+底面+侧面）"""
    vertices = []
    faces = []
    h = height / 2
    vertices.append([0, h, 0])  # 0: top center
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), h, radius * np.sin(angle)])
    vertices.append([0, -h, 0])  # segments+1: bot center
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), -h, radius * np.sin(angle)])
    for i in range(segments):
        i0, i1 = 1 + i, 1 + (i + 1) % segments
        faces.append([0, i1, i0])
    for i in range(segments):
        i0 = segments + 2 + i
        i1 = segments + 2 + (i + 1) % segments
        faces.append([segments + 1, i0, i1])
    for i in range(segments):
        t0, t1 = 1 + i, 1 + (i + 1) % segments
        b0 = segments + 2 + i
        b1 = segments + 2 + (i + 1) % segments
        faces.append([t0, b0, b1])
        faces.append([t0, b1, t1])
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)


def make_capsule(radius, height, segments=24, lat_seg=12):
    """封闭胶囊体（圆柱+两个半球，两端完全封闭）"""
    vertices, faces = [], []
    cyl_h = max(height - 2 * radius, 0)
    # 中间圆柱侧面
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), cyl_h / 2, radius * np.sin(angle)])
        vertices.append([radius * np.cos(angle), -cyl_h / 2, radius * np.sin(angle)])
    for i in range(segments):
        t0, t1 = i * 2, ((i + 1) % segments) * 2
        b0, b1 = i * 2 + 1, ((i + 1) % segments) * 2 + 1
        faces.append([t0, b0, b1])
        faces.append([t0, b1, t1])
    # 上半球（封闭顶端）
    top_off = len(vertices)
    for lat in range(1, lat_seg + 1):
        phi = np.pi * lat / (2 * lat_seg)
        r, y = radius * np.sin(phi), cyl_h / 2 + radius * np.cos(phi)
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            vertices.append([r * np.cos(angle), y, r * np.sin(angle)])
    top_vtx = len(vertices)
    vertices.append([0, cyl_h / 2 + radius, 0])
    for lat in range(lat_seg):
        r0 = top_off + lat * segments
        r1 = top_off + (lat + 1) * segments if lat < lat_seg - 1 else None
        for i in range(segments):
            i0, i1 = r0 + i, r0 + (i + 1) % segments
            if r1 is not None:
                i2, i3 = r1 + (i + 1) % segments, r1 + i
                faces.append([i0, i1, i2])
                faces.append([i0, i2, i3])
            else:
                faces.append([i0, i1, top_vtx])
    for i in range(segments):
        t0, t1 = i * 2, ((i + 1) % segments) * 2
        r0, r1 = top_off + i, top_off + (i + 1) % segments
        faces.append([t0, r0, r1])
        faces.append([t0, r1, t1])
    # 下半球（封闭底端）
    bot_off = len(vertices)
    for lat in range(1, lat_seg + 1):
        phi = np.pi * lat / (2 * lat_seg)
        r, y = radius * np.sin(phi), -cyl_h / 2 - radius * np.cos(phi)
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            vertices.append([r * np.cos(angle), y, r * np.sin(angle)])
    bot_vtx = len(vertices)
    vertices.append([0, -cyl_h / 2 - radius, 0])
    for lat in range(lat_seg):
        r0 = bot_off + lat * segments
        r1 = bot_off + (lat + 1) * segments if lat < lat_seg - 1 else None
        for i in range(segments):
            i0, i1 = r0 + i, r0 + (i + 1) % segments
            if r1 is not None:
                i2, i3 = r1 + (i + 1) % segments, r1 + i
                faces.append([i0, i2, i1])
                faces.append([i0, i3, i2])
            else:
                faces.append([i0, bot_vtx, i1])
    for i in range(segments):
        b0, b1 = i * 2 + 1, ((i + 1) % segments) * 2 + 1
        r0, r1 = bot_off + i, bot_off + (i + 1) % segments
        faces.append([b0, r1, r0])
        faces.append([b0, b1, r1])
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)


def make_sphere(radius, segments=24, lat_seg=16):
    """封闭球体"""
    vertices, faces = [], []
    for lat in range(lat_seg + 1):
        phi = np.pi * lat / lat_seg
        r, y = radius * np.sin(phi), radius * np.cos(phi)
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            vertices.append([r * np.cos(angle), y, r * np.sin(angle)])
    for lat in range(lat_seg):
        r0, r1 = lat * segments, (lat + 1) * segments
        for i in range(segments):
            i0, i1 = r0 + i, r0 + (i + 1) % segments
            i2, i3 = r1 + (i + 1) % segments, r1 + i
            faces.append([i0, i1, i2])
            faces.append([i0, i2, i3])
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)


def make_torus(major_r, minor_r, major_seg=24, minor_seg=12):
    """封闭圆环体"""
    vertices, faces = [], []
    for i in range(major_seg):
        theta = 2 * np.pi * i / major_seg
        for j in range(minor_seg):
            phi = 2 * np.pi * j / minor_seg
            x = (major_r + minor_r * np.cos(phi)) * np.cos(theta)
            y = minor_r * np.sin(phi)
            z = (major_r + minor_r * np.cos(phi)) * np.sin(theta)
            vertices.append([x, y, z])
    for i in range(major_seg):
        for j in range(minor_seg):
            i0 = i * minor_seg + j
            i1 = i * minor_seg + (j + 1) % minor_seg
            i2 = ((i + 1) % major_seg) * minor_seg + (j + 1) % minor_seg
            i3 = ((i + 1) % major_seg) * minor_seg + j
            faces.append([i0, i1, i2])
            faces.append([i0, i2, i3])
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)


def merge_meshes(mesh_list):
    all_v, all_f, offset = [], [], 0
    for v, f in mesh_list:
        all_v.extend(v.tolist())
        for face in f:
            all_f.append([face[0] + offset, face[1] + offset, face[2] + offset])
        offset += len(v)
    return np.array(all_v, dtype=float), np.array(all_f, dtype=int)


def save_stl(filepath, vertices, faces):
    """保存STL，自动为每个三角形添加反向副本，实现双面网格（从任何角度看都是封闭实心）"""
    import os
    # 先删除旧文件，避免numpy-stl覆盖大文件时的写入bug
    if os.path.exists(filepath):
        os.remove(filepath)
    # 为每个面添加反向面，禁用背面剔除效果
    doubled_faces = []
    for face in faces:
        doubled_faces.append([face[0], face[1], face[2]])
        doubled_faces.append([face[0], face[2], face[1]])  # 反向
    faces = np.array(doubled_faces, dtype=int)

    m = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
    for i, f in enumerate(faces):
        for j in range(3):
            m.vectors[i][j] = vertices[f[j]]
    m.save(filepath)
    return len(faces)


def translate(v, dx, dy, dz):
    return v + np.array([dx, dy, dz])


def scale(v, sx, sy, sz):
    return v * np.array([sx, sy, sz])


def rotate_y(v, angle_deg):
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return v @ np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]).T


def rotate_x(v, angle_deg):
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return v @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]]).T


def rotate_z(v, angle_deg):
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return v @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]).T


# ==================== 参数化人偶生成器 ====================

def generate_avatar(out_dir, params):
    """
    根据参数字典生成一款滑雪者人偶
    params 包含：
      name, head_r, neck_r, neck_h,
      chest_w, chest_h, chest_d, shoulder_w,
      waist_w, waist_h, waist_d, hip_w, hip_h, hip_d,
      upper_arm_r, upper_arm_l, forearm_r, forearm_l,
      hand_w, hand_h, hand_d,
      thigh_r, thigh_l, shin_r, shin_l,
      foot_w, foot_h, foot_d,
      helmet_color, suit_color, accent_color,
      hunch (驼背程度, 0~0.1),
      female (是否女性特征),
      kid (是否儿童大头比例)
    """
    os.makedirs(out_dir, exist_ok=True)
    name = params.get('name', 'avatar')
    print(f"\n=== 生成 {name} -> {out_dir} ===")
    total = 0
    hunch = params.get('hunch', 0)

    # ----- 头：脸 + 头盔 + 护目镜 + 帽檐 -----
    head_r = params['head_r']
    face_v, face_f = make_sphere(head_r, segments=20, lat_seg=14)
    helmet_v, helmet_f = make_sphere(head_r * 1.1, segments=20, lat_seg=10)
    helmet_v = scale(helmet_v, 1.05, 0.72, 1.05)
    helmet_v = translate(helmet_v, 0, head_r * 0.45, 0)
    # 护目镜
    goggle_ring_v, goggle_ring_f = make_torus(head_r * 0.72, 0.008, major_seg=20, minor_seg=8)
    goggle_ring_v = rotate_y(goggle_ring_v, 90)
    goggle_ring_v = translate(goggle_ring_v, 0, head_r * 0.08, head_r * 0.93)
    goggle_lens_v, goggle_lens_f = make_box(head_r * 1.35, head_r * 0.48, 0.006)
    goggle_lens_v = translate(goggle_lens_v, 0, head_r * 0.08, head_r * 0.93)
    brim_v, brim_f = make_box(head_r * 1.45, 0.006, head_r * 0.65)
    brim_v = translate(brim_v, 0, head_r * 0.2, head_r * 0.88)

    head_parts = [(face_v, face_f), (helmet_v, helmet_f),
                   (goggle_ring_v, goggle_ring_f), (goggle_lens_v, goggle_lens_f),
                   (brim_v, brim_f)]
    # 女性特征：马尾（头盔后加长发）
    if params.get('female', False):
        ponytail_v, ponytail_f = make_capsule(0.018, 0.18, segments=12, lat_seg=8)
        ponytail_v = translate(ponytail_v, 0, head_r * 0.1, -head_r * 0.9)
        head_parts.append((ponytail_v, ponytail_f))
    # 儿童：更大的头盔比例（已经通过head_r体现）

    head_v, head_f = merge_meshes(head_parts)
    n = save_stl(os.path.join(out_dir, 'head.stl'), head_v, head_f)
    total += n
    print(f"  head.stl: {n} triangles")

    # ----- 脖子 -----
    v, f = make_cylinder(params['neck_r'], params['neck_h'], segments=16)
    n = save_stl(os.path.join(out_dir, 'neck.stl'), v, f)
    total += n

    # ----- 躯干：胸 + 肩 + 腰 + 拉链 + 口袋 -----
    chest_v, chest_f = make_box(params['chest_w'], params['chest_h'], params['chest_d'])
    chest_v = translate(chest_v, 0, params['chest_h'] * 0.4 + hunch, 0)
    # 肩膀圆润化
    sh_l_v, sh_l_f = make_sphere(params['shoulder_w'] * 0.22, segments=14, lat_seg=10)
    sh_l_v = translate(sh_l_v, -params['chest_w'] * 0.52, params['chest_h'] * 0.7 + hunch, 0)
    sh_r_v, sh_r_f = make_sphere(params['shoulder_w'] * 0.22, segments=14, lat_seg=10)
    sh_r_v = translate(sh_r_v, params['chest_w'] * 0.52, params['chest_h'] * 0.7 + hunch, 0)

    waist_v, waist_f = make_box(params['waist_w'], params['waist_h'], params['waist_d'])
    waist_v = translate(waist_v, 0, -params['waist_h'] * 0.5, 0)

    zipper_v, zipper_f = make_box(0.012, params['chest_h'] + params['waist_h'], 0.006)
    zipper_v = translate(zipper_v, 0, 0, params['chest_d'] * 0.52)

    pocket_l_v, pocket_l_f = make_box(params['chest_w'] * 0.22, params['chest_h'] * 0.2, 0.006)
    pocket_l_v = translate(pocket_l_v, -params['chest_w'] * 0.26, params['chest_h'] * 0.3, params['chest_d'] * 0.52)
    pocket_r_v, pocket_r_f = make_box(params['chest_w'] * 0.22, params['chest_h'] * 0.2, 0.006)
    pocket_r_v = translate(pocket_r_v, params['chest_w'] * 0.26, params['chest_h'] * 0.3, params['chest_d'] * 0.52)

    spine_parts = [(chest_v, chest_f), (sh_l_v, sh_l_f), (sh_r_v, sh_r_f),
                    (waist_v, waist_f), (zipper_v, zipper_f),
                    (pocket_l_v, pocket_l_f), (pocket_r_v, pocket_r_f)]
    # 女性特征：胸部轮廓
    if params.get('female', False):
        bust_l_v, bust_l_f = make_sphere(params['chest_w'] * 0.16, segments=14, lat_seg=10)
        bust_l_v = translate(bust_l_v, -params['chest_w'] * 0.2, params['chest_h'] * 0.25, params['chest_d'] * 0.45)
        bust_r_v, bust_r_f = make_sphere(params['chest_w'] * 0.16, segments=14, lat_seg=10)
        bust_r_v = translate(bust_r_v, params['chest_w'] * 0.2, params['chest_h'] * 0.25, params['chest_d'] * 0.45)
        spine_parts.extend([(bust_l_v, bust_l_f), (bust_r_v, bust_r_f)])

    spine_v, spine_f = merge_meshes(spine_parts)
    n = save_stl(os.path.join(out_dir, 'spine.stl'), spine_v, spine_f)
    total += n
    print(f"  spine.stl: {n} triangles")

    # ----- 骨盆 -----
    v, f = make_box(params['hip_w'], params['hip_h'], params['hip_d'])
    n = save_stl(os.path.join(out_dir, 'hips.stl'), v, f)
    total += n

    # ----- 上臂（封闭胶囊体）-----
    v, f = make_capsule(params['upper_arm_r'], params['upper_arm_l'], segments=18, lat_seg=10)
    n = save_stl(os.path.join(out_dir, 'upper_arm.stl'), v, f)
    total += n

    # ----- 前臂（封闭胶囊体）-----
    v, f = make_capsule(params['forearm_r'], params['forearm_l'], segments=18, lat_seg=10)
    n = save_stl(os.path.join(out_dir, 'forearm.stl'), v, f)
    total += n

    # ----- 手（封闭：手掌+拇指+四指）-----
    palm_v, palm_f = make_box(params['hand_w'], params['hand_h'], params['hand_d'])
    palm_v = translate(palm_v, 0, -params['hand_h'] * 0.2, 0)
    thumb_v, thumb_f = make_capsule(params['hand_w'] * 0.24, params['hand_h'] * 0.8, segments=10, lat_seg=6)
    thumb_v = rotate_y(thumb_v, -30)
    thumb_v = translate(thumb_v, -params['hand_w'] * 0.6, -params['hand_h'] * 0.4, params['hand_d'] * 0.2)
    fingers_v, fingers_f = make_box(params['hand_w'] * 0.8, params['hand_h'] * 0.7, params['hand_d'] * 0.9)
    fingers_v = translate(fingers_v, 0, -params['hand_h'] * 0.9, 0)
    hand_v, hand_f = merge_meshes([(palm_v, palm_f), (thumb_v, thumb_f), (fingers_v, fingers_f)])
    n = save_stl(os.path.join(out_dir, 'hand.stl'), hand_v, hand_f)
    total += n

    # ----- 大腿（封闭胶囊体，粗壮滑雪裤）-----
    v, f = make_capsule(params['thigh_r'], params['thigh_l'], segments=18, lat_seg=10)
    n = save_stl(os.path.join(out_dir, 'thigh.stl'), v, f)
    total += n

    # ----- 小腿（封闭胶囊体）-----
    v, f = make_capsule(params['shin_r'], params['shin_l'], segments=18, lat_seg=10)
    n = save_stl(os.path.join(out_dir, 'shin.stl'), v, f)
    total += n

    # ----- 脚（封闭滑雪靴：靴筒+鞋头+鞋跟+绑定）-----
    boot_v, boot_f = make_box(params['foot_w'], params['foot_h'], params['foot_d'])
    boot_v = translate(boot_v, 0, 0, params['foot_d'] * 0.18)
    toe_v, toe_f = make_box(params['foot_w'] * 0.9, params['foot_h'] * 0.55, params['foot_d'] * 0.45)
    toe_v = translate(toe_v, 0, -params['foot_h'] * 0.24, params['foot_d'] * 0.65)
    heel_v, heel_f = make_box(params['foot_w'] * 0.85, params['foot_h'] * 0.55, params['foot_d'] * 0.4)
    heel_v = translate(heel_v, 0, -params['foot_h'] * 0.24, -params['foot_d'] * 0.35)
    binding_v, binding_f = make_box(params['foot_w'] * 1.05, params['foot_h'] * 0.28, 0.008)
    binding_v = translate(binding_v, 0, params['foot_h'] * 0.14, params['foot_d'] * 0.52)
    foot_v, foot_f = merge_meshes([(boot_v, boot_f), (toe_v, toe_f), (heel_v, heel_f), (binding_v, binding_f)])
    n = save_stl(os.path.join(out_dir, 'foot.stl'), foot_v, foot_f)
    total += n
    print(f"  foot.stl: {n} triangles (封闭滑雪靴)")

    # ----- 滑雪板（封闭：板身+板头+板尾）-----
    ski_body_v, ski_body_f = make_box(params['foot_w'] * 1.2, 0.008, 0.9)
    tip_v, tip_f = make_box(params['foot_w'] * 1.2, 0.008, 0.12)
    tip_v = tip_v @ np.array([[1,0,0],[0,np.cos(np.radians(15)),-np.sin(np.radians(15))],[0,np.sin(np.radians(15)),np.cos(np.radians(15))]]).T
    tip_v = translate(tip_v, 0, 0.015, 0.5)
    tail_v, tail_f = make_box(params['foot_w'] * 1.2, 0.008, 0.08)
    tail_v = translate(tail_v, 0, 0, -0.48)
    ski_v, ski_f = merge_meshes([(ski_body_v, ski_body_f), (tip_v, tip_f), (tail_v, tail_f)])
    n = save_stl(os.path.join(out_dir, 'ski.stl'), ski_v, ski_f)
    total += n

    # ----- 雪杖（封闭：杖身+握把+杖尖+雪轮）-----
    pole_shaft_v, pole_shaft_f = make_cylinder(0.004, 0.65, segments=12)
    pole_shaft_v = translate(pole_shaft_v, 0, -0.05, 0)
    handle_v, handle_f = make_capsule(0.012, 0.05, segments=10, lat_seg=6)
    handle_v = translate(handle_v, 0, 0.3, 0)
    tip_v, tip_f = make_cylinder(0.003, 0.03, segments=8)
    tip_v = translate(tip_v, 0, -0.37, 0)
    basket_v, basket_f = make_torus(0.025, 0.003, major_seg=12, minor_seg=6)
    basket_v = translate(basket_v, 0, -0.32, 0)
    pole_v, pole_f = merge_meshes([(pole_shaft_v, pole_shaft_f), (handle_v, handle_f), (tip_v, tip_f), (basket_v, basket_f)])
    n = save_stl(os.path.join(out_dir, 'pole.stl'), pole_v, pole_f)
    total += n

    # ----- 关节球（封闭球体）-----
    v, f = make_sphere(0.03, segments=14, lat_seg=10)
    n = save_stl(os.path.join(out_dir, 'joint.stl'), v, f)
    total += n

    print(f"  {name} 总计: {total} triangles (全部封闭实体)")
    return total


# ==================== 各款人偶参数 ====================

# 成年男性滑雪者：健壮、宽肩、窄腰
MALE_SKIER = {
    'name': 'male_skier',
    'head_r': 0.062, 'neck_r': 0.026, 'neck_h': 0.045,
    'chest_w': 0.24, 'chest_h': 0.20, 'chest_d': 0.14, 'shoulder_w': 0.24,
    'waist_w': 0.18, 'waist_h': 0.12, 'waist_d': 0.115,
    'hip_w': 0.19, 'hip_h': 0.085, 'hip_d': 0.125,
    'upper_arm_r': 0.034, 'upper_arm_l': 0.27,
    'forearm_r': 0.030, 'forearm_l': 0.25,
    'hand_w': 0.052, 'hand_h': 0.052, 'hand_d': 0.047,
    'thigh_r': 0.040, 'thigh_l': 0.39,
    'shin_r': 0.034, 'shin_l': 0.37,
    'foot_w': 0.075, 'foot_h': 0.078, 'foot_d': 0.12,
    'hunch': 0, 'female': False, 'kid': False,
}

# 成年女性滑雪者：纤细、窄肩、宽髋、有胸部和马尾
FEMALE_SKIER = {
    'name': 'female_skier',
    'head_r': 0.058, 'neck_r': 0.023, 'neck_h': 0.05,
    'chest_w': 0.21, 'chest_h': 0.19, 'chest_d': 0.13, 'shoulder_w': 0.21,
    'waist_w': 0.16, 'waist_h': 0.12, 'waist_d': 0.105,
    'hip_w': 0.20, 'hip_h': 0.09, 'hip_d': 0.13,
    'upper_arm_r': 0.029, 'upper_arm_l': 0.26,
    'forearm_r': 0.026, 'forearm_l': 0.24,
    'hand_w': 0.046, 'hand_h': 0.048, 'hand_d': 0.042,
    'thigh_r': 0.036, 'thigh_l': 0.38,
    'shin_r': 0.030, 'shin_l': 0.36,
    'foot_w': 0.068, 'foot_h': 0.072, 'foot_d': 0.11,
    'hunch': 0, 'female': True, 'kid': False,
}

# 老年滑雪者：略驼背、稍胖、四肢略短
ELDER_SKIER = {
    'name': 'elder_skier',
    'head_r': 0.060, 'neck_r': 0.025, 'neck_h': 0.04,
    'chest_w': 0.23, 'chest_h': 0.19, 'chest_d': 0.15, 'shoulder_w': 0.23,
    'waist_w': 0.21, 'waist_h': 0.13, 'waist_d': 0.13,
    'hip_w': 0.21, 'hip_h': 0.09, 'hip_d': 0.135,
    'upper_arm_r': 0.032, 'upper_arm_l': 0.25,
    'forearm_r': 0.028, 'forearm_l': 0.23,
    'hand_w': 0.050, 'hand_h': 0.050, 'hand_d': 0.045,
    'thigh_r': 0.038, 'thigh_l': 0.36,
    'shin_r': 0.032, 'shin_l': 0.34,
    'foot_w': 0.072, 'foot_h': 0.075, 'foot_d': 0.115,
    'hunch': 0.025, 'female': False, 'kid': False,
}

# 少年滑雪者：矮小、大头、短四肢
KID_SKIER = {
    'name': 'kid_skier',
    'head_r': 0.065, 'neck_r': 0.022, 'neck_h': 0.035,
    'chest_w': 0.19, 'chest_h': 0.16, 'chest_d': 0.12, 'shoulder_w': 0.19,
    'waist_w': 0.16, 'waist_h': 0.10, 'waist_d': 0.10,
    'hip_w': 0.17, 'hip_h': 0.075, 'hip_d': 0.11,
    'upper_arm_r': 0.027, 'upper_arm_l': 0.21,
    'forearm_r': 0.024, 'forearm_l': 0.19,
    'hand_w': 0.042, 'hand_h': 0.044, 'hand_d': 0.038,
    'thigh_r': 0.033, 'thigh_l': 0.30,
    'shin_r': 0.028, 'shin_l': 0.28,
    'foot_w': 0.062, 'foot_h': 0.065, 'foot_d': 0.10,
    'hunch': 0, 'female': False, 'kid': True,
}


# 胖滑雪者：宽体、大肚子、粗四肢
FAT_SKIER = {
    'name': 'fat_skier',
    'head_r': 0.062, 'neck_r': 0.030, 'neck_h': 0.04,
    'chest_w': 0.30, 'chest_h': 0.22, 'chest_d': 0.20, 'shoulder_w': 0.28,
    'waist_w': 0.28, 'waist_h': 0.15, 'waist_d': 0.19,
    'hip_w': 0.26, 'hip_h': 0.10, 'hip_d': 0.17,
    'upper_arm_r': 0.040, 'upper_arm_l': 0.25,
    'forearm_r': 0.036, 'forearm_l': 0.23,
    'hand_w': 0.058, 'hand_h': 0.055, 'hand_d': 0.050,
    'thigh_r': 0.048, 'thigh_l': 0.36,
    'shin_r': 0.040, 'shin_l': 0.34,
    'foot_w': 0.085, 'foot_h': 0.082, 'foot_d': 0.13,
    'hunch': 0.01, 'female': False, 'kid': False,
}

# 高个子滑雪者：长四肢、窄身、小头
TALL_SKIER = {
    'name': 'tall_skier',
    'head_r': 0.055, 'neck_r': 0.024, 'neck_h': 0.06,
    'chest_w': 0.20, 'chest_h': 0.22, 'chest_d': 0.12, 'shoulder_w': 0.22,
    'waist_w': 0.16, 'waist_h': 0.14, 'waist_d': 0.10,
    'hip_w': 0.18, 'hip_h': 0.10, 'hip_d': 0.12,
    'upper_arm_r': 0.028, 'upper_arm_l': 0.32,
    'forearm_r': 0.025, 'forearm_l': 0.30,
    'hand_w': 0.048, 'hand_h': 0.050, 'hand_d': 0.042,
    'thigh_r': 0.034, 'thigh_l': 0.45,
    'shin_r': 0.029, 'shin_l': 0.43,
    'foot_w': 0.070, 'foot_h': 0.072, 'foot_d': 0.12,
    'hunch': 0, 'female': False, 'kid': False,
}

# 肌肉男滑雪者：宽肩、粗四肢、健壮
MUSCLE_SKIER = {
    'name': 'muscle_skier',
    'head_r': 0.060, 'neck_r': 0.032, 'neck_h': 0.045,
    'chest_w': 0.28, 'chest_h': 0.24, 'chest_d': 0.17, 'shoulder_w': 0.30,
    'waist_w': 0.20, 'waist_h': 0.13, 'waist_d': 0.13,
    'hip_w': 0.22, 'hip_h': 0.10, 'hip_d': 0.14,
    'upper_arm_r': 0.042, 'upper_arm_l': 0.28,
    'forearm_r': 0.038, 'forearm_l': 0.26,
    'hand_w': 0.060, 'hand_h': 0.056, 'hand_d': 0.052,
    'thigh_r': 0.046, 'thigh_l': 0.40,
    'shin_r': 0.038, 'shin_l': 0.38,
    'foot_w': 0.080, 'foot_h': 0.080, 'foot_d': 0.125,
    'hunch': 0, 'female': False, 'kid': False,
}

# 瘦高滑雪者：纤细、长四肢、窄肩
SLIM_SKIER = {
    'name': 'slim_skier',
    'head_r': 0.056, 'neck_r': 0.022, 'neck_h': 0.055,
    'chest_w': 0.18, 'chest_h': 0.20, 'chest_d': 0.11, 'shoulder_w': 0.19,
    'waist_w': 0.14, 'waist_h': 0.12, 'waist_d': 0.09,
    'hip_w': 0.16, 'hip_h': 0.09, 'hip_d': 0.11,
    'upper_arm_r': 0.024, 'upper_arm_l': 0.29,
    'forearm_r': 0.021, 'forearm_l': 0.27,
    'hand_w': 0.042, 'hand_h': 0.046, 'hand_d': 0.038,
    'thigh_r': 0.029, 'thigh_l': 0.42,
    'shin_r': 0.025, 'shin_l': 0.40,
    'foot_w': 0.064, 'foot_h': 0.068, 'foot_d': 0.11,
    'hunch': 0, 'female': False, 'kid': False,
}

# 动漫风格男孩：大头、尖下巴、彩色头发（通过大头比例模拟）
ANIME_BOY = {
    'name': 'anime_boy',
    'head_r': 0.075, 'neck_r': 0.020, 'neck_h': 0.04,
    'chest_w': 0.18, 'chest_h': 0.17, 'chest_d': 0.11, 'shoulder_w': 0.19,
    'waist_w': 0.15, 'waist_h': 0.10, 'waist_d': 0.095,
    'hip_w': 0.16, 'hip_h': 0.08, 'hip_d': 0.105,
    'upper_arm_r': 0.024, 'upper_arm_l': 0.24,
    'forearm_r': 0.021, 'forearm_l': 0.22,
    'hand_w': 0.040, 'hand_h': 0.044, 'hand_d': 0.036,
    'thigh_r': 0.029, 'thigh_l': 0.34,
    'shin_r': 0.025, 'shin_l': 0.32,
    'foot_w': 0.060, 'foot_h': 0.064, 'foot_d': 0.10,
    'hunch': 0, 'female': False, 'kid': True,
}

# 动漫风格女孩：大头、双马尾、纤细
ANIME_GIRL = {
    'name': 'anime_girl',
    'head_r': 0.075, 'neck_r': 0.019, 'neck_h': 0.045,
    'chest_w': 0.17, 'chest_h': 0.17, 'chest_d': 0.105, 'shoulder_w': 0.18,
    'waist_w': 0.13, 'waist_h': 0.11, 'waist_d': 0.085,
    'hip_w': 0.17, 'hip_h': 0.09, 'hip_d': 0.11,
    'upper_arm_r': 0.022, 'upper_arm_l': 0.24,
    'forearm_r': 0.020, 'forearm_l': 0.22,
    'hand_w': 0.038, 'hand_h': 0.042, 'hand_d': 0.034,
    'thigh_r': 0.028, 'thigh_l': 0.35,
    'shin_r': 0.024, 'shin_l': 0.33,
    'foot_w': 0.058, 'foot_h': 0.062, 'foot_d': 0.095,
    'hunch': 0, 'female': True, 'kid': True,
}


# ==================== 主入口 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("多套人偶STL模型生成器 v4 - 参数化男女老少")
    print("所有几何体均为封闭实体")
    print("=" * 60)

    avatars = [MALE_SKIER, FEMALE_SKIER, ELDER_SKIER, KID_SKIER, FAT_SKIER, TALL_SKIER, MUSCLE_SKIER, SLIM_SKIER, ANIME_BOY, ANIME_GIRL]
    for params in avatars:
        generate_avatar(os.path.join(BASE_DIR, params['name']), params)

    print("\n" + "=" * 60)
    print("全部生成完成！")
    print(f"模型目录: {BASE_DIR}")
    print("  male_skier/    - 成年男性（健壮宽肩）")
    print("  female_skier/  - 成年女性（纤细马尾）")
    print("  elder_skier/   - 老年人（略驼背稍胖）")
    print("  kid_skier/     - 少年（矮小大头）")
    print("  fat_skier/     - 胖滑雪者（宽体大肚子）")
    print("  tall_skier/    - 高个子（长四肢窄身）")
    print("  muscle_skier/  - 肌肉男（宽肩粗四肢）")
    print("  slim_skier/    - 瘦高（纤细长四肢）")
    print("  anime_boy/     - 动漫男孩（大头尖下巴）")
    print("  anime_girl/    - 动漫女孩（大头双马尾）")
    print("=" * 60)
