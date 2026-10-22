"""
经典人物人偶生成器 v2 - 完全自定义身体结构
每个人物有独特的身体比例、服装造型、头饰特征
"""
import os
import numpy as np
from stl import mesh
import sys

sys.path.insert(0, r'D:\PyPrjs\SyntrakView')
from generate_models import (
    make_box, make_cylinder, make_capsule, make_sphere, make_torus,
    merge_meshes, save_stl, translate, scale, rotate_y, rotate_x, rotate_z, BASE_DIR
)


def make_cone(radius, height, segments=12):
    vertices = [[0, height/2, 0], [0, -height/2, 0]]
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), -height/2, radius * np.sin(angle)])
    faces = []
    for i in range(segments):
        i0, i1 = 2 + i, 2 + (i + 1) % segments
        faces.append([0, i1, i0])
        faces.append([1, i0, i1])
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)


def make_ellipsoid(rx, ry, rz, segments=16, lat_seg=10):
    """生成椭球体"""
    v, f = make_sphere(1.0, segments=segments, lat_seg=lat_seg)
    v = scale(v, rx, ry, rz)
    return v, f


def center_mesh(v):
    """将模型顶点居中（减去边界框中心），确保原点在模型中心"""
    center = (v.max(axis=0) + v.min(axis=0)) / 2
    return v - center


def save_character(out_dir, name, parts):
    """保存人物所有部位（自动居中，骨骼系统会自动适配模型长度）
    每个人物可以有自己的体型比例，不需要强制匹配骨骼尺寸"""
    char_dir = os.path.join(out_dir, name)
    os.makedirs(char_dir, exist_ok=True)
    print(f"\n=== {name} -> {char_dir} ===")
    total = 0
    for part_name, (v, f) in parts.items():
        if part_name not in ('joint',):
            v = center_mesh(v)
        n = save_stl(os.path.join(char_dir, f'{part_name}.stl'), v, f)
        total += n
        if part_name in ('head', 'spine', 'foot', 'upper_arm', 'forearm', 'thigh', 'shin'):
            y_len = v[:, 1].max() - v[:, 1].min()
            print(f"  {part_name}.stl: {n} triangles, Y-length={y_len:.3f}")
    print(f"  {name} 总计: {total} triangles")
    return total


def make_ski_gear(foot_w=0.07):
    """生成滑雪板和雪杖（通用）"""
    # 滑雪板
    ski_body_v, ski_body_f = make_box(foot_w * 1.3, 0.008, 0.9)
    tip_v, tip_f = make_box(foot_w * 1.3, 0.008, 0.12)
    rot = np.array([[1,0,0],[0,np.cos(np.radians(15)),-np.sin(np.radians(15))],[0,np.sin(np.radians(15)),np.cos(np.radians(15))]]).T
    tip_v = tip_v @ rot
    tip_v = translate(tip_v, 0, 0.015, 0.5)
    tail_v, tail_f = make_box(foot_w * 1.3, 0.008, 0.08)
    tail_v = translate(tail_v, 0, 0, -0.48)
    ski_v, ski_f = merge_meshes([(ski_body_v, ski_body_f), (tip_v, tip_f), (tail_v, tail_f)])

    # 雪杖
    pole_shaft_v, pole_shaft_f = make_cylinder(0.004, 0.65, segments=12)
    pole_shaft_v = translate(pole_shaft_v, 0, -0.05, 0)
    handle_v, handle_f = make_capsule(0.012, 0.05, segments=10, lat_seg=6)
    handle_v = translate(handle_v, 0, 0.3, 0)
    tip_v, tip_f = make_cylinder(0.003, 0.03, segments=8)
    tip_v = translate(tip_v, 0, -0.37, 0)
    basket_v, basket_f = make_torus(0.025, 0.003, major_seg=12, minor_seg=6)
    basket_v = translate(basket_v, 0, -0.32, 0)
    pole_v, pole_f = merge_meshes([(pole_shaft_v, pole_shaft_f), (handle_v, handle_f), (tip_v, tip_f), (basket_v, basket_f)])

    # 关节球
    joint_v, joint_f = make_sphere(0.03, segments=14, lat_seg=10)

    return {'ski': (ski_v, ski_f), 'pole': (pole_v, pole_f), 'joint': (joint_v, joint_f)}


# ==================== 唐老鸭 ====================

def generate_donald_duck(out_dir):
    """唐老鸭：白色圆胖身体、巨大黄色扁嘴、蓝色水手服、翅膀、黄色蹼足、水手帽"""
    parts = {}

    # 头：白色大球 + 巨大黄色扁嘴 + 蓝色水手帽
    head_v, head_f = make_sphere(0.07, segments=20, lat_seg=14)
    # 巨大黄色扁嘴（占据头部前方1/3，扁平宽大）
    beak_v, beak_f = make_ellipsoid(0.055, 0.03, 0.07, segments=16, lat_seg=10)
    beak_v = translate(beak_v, 0, -0.01, 0.09)
    # 嘴上下分界线（扁嘴的上半部分稍大）
    beak_top_v, beak_top_f = make_ellipsoid(0.05, 0.015, 0.06, segments=14, lat_seg=8)
    beak_top_v = translate(beak_top_v, 0, 0.005, 0.085)
    # 蓝色水手帽（宽边+平顶）
    hat_brim_v, hat_brim_f = make_cylinder(0.085, 0.008, segments=20)
    hat_brim_v = translate(hat_brim_v, 0, 0.055, 0)
    hat_top_v, hat_top_f = make_cylinder(0.06, 0.025, segments=16)
    hat_top_v = translate(hat_top_v, 0, 0.07, 0)
    # 帽子上的黑色缎带
    ribbon_v, ribbon_f = make_cylinder(0.062, 0.006, segments=16)
    ribbon_v = translate(ribbon_v, 0, 0.06, 0)

    head_parts = [(head_v, head_f), (beak_v, beak_f), (beak_top_v, beak_top_f),
                  (hat_brim_v, hat_brim_f), (hat_top_v, hat_top_f), (ribbon_v, ribbon_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子：很短（鸭子脖子短）
    neck_v, neck_f = make_cylinder(0.03, 0.02, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：白色身体（椭圆形，前后扁平，前面不要突出）+ 蓝色水手服上半部分
    body_v, body_f = make_ellipsoid(0.12, 0.14, 0.07, segments=20, lat_seg=14)
    body_v = translate(body_v, 0, 0.02, -0.01)
    # 蓝色水手服（覆盖上半身体，V字领）
    shirt_v, shirt_f = make_ellipsoid(0.125, 0.09, 0.075, segments=20, lat_seg=10)
    shirt_v = translate(shirt_v, 0, 0.06, -0.01)
    # （腹部已移除，身体直接用白色椭圆体）
    # 水手领（白色大翻领）
    collar_l_v, collar_l_f = make_box(0.06, 0.005, 0.08)
    collar_l_v = rotate_z(collar_l_v, -20)
    collar_l_v = translate(collar_l_v, -0.04, 0.12, 0.08)
    collar_r_v, collar_r_f = make_box(0.06, 0.005, 0.08)
    collar_r_v = rotate_z(collar_r_v, 20)
    collar_r_v = translate(collar_r_v, 0.04, 0.12, 0.08)
    # 红色领结
    bow_v, bow_f = make_sphere(0.015, segments=10, lat_seg=8)
    bow_v = translate(bow_v, 0, 0.11, 0.10)

    # 鸭子屁股：圆润适中，微微向后翘起（经典唐老鸭造型）
    # 主屁股：圆润的球形，大小适中
    butt_main_v, butt_main_f = make_sphere(0.11, segments=20, lat_seg=14)
    butt_main_v = translate(butt_main_v, 0, -0.01, -0.10)
    # 屁股上半部分：微微向上翘起
    butt_up_v, butt_up_f = make_ellipsoid(0.10, 0.08, 0.09, segments=18, lat_seg=12)
    butt_up_v = rotate_x(butt_up_v, -15)
    butt_up_v = translate(butt_up_v, 0, 0.04, -0.13)
    # 屁股顶部：圆润
    butt_top_v, butt_top_f = make_ellipsoid(0.08, 0.06, 0.07, segments=16, lat_seg=10)
    butt_top_v = rotate_x(butt_top_v, -25)
    butt_top_v = translate(butt_top_v, 0, 0.07, -0.15)
    # 屁股底部：圆润的下沿
    butt_bottom_v, butt_bottom_f = make_ellipsoid(0.09, 0.05, 0.08, segments=16, lat_seg=10)
    butt_bottom_v = translate(butt_bottom_v, 0, -0.05, -0.11)

    spine_parts = [(body_v, body_f), (shirt_v, shirt_f),
                    (collar_l_v, collar_l_f), (collar_r_v, collar_r_f), (bow_v, bow_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆+屁股：大圆球(球心往后移) + 圆锥屁股(大头贴球，尖顶向后斜上方)
    # 大圆球（球心往后移，小肚子靠后）
    big_ball_v, big_ball_f = make_sphere(0.09, segments=22, lat_seg=16)
    big_ball_v = translate(big_ball_v, 0, 0, -0.03)
    # 圆锥屁股：大头（底面）贴在大圆球后方，尖顶向后斜上方
    butt_cone_v, butt_cone_f = make_cone(0.08, 0.16, segments=20)
    butt_cone_v = rotate_x(butt_cone_v, -120)
    # 圆锥底面贴在大圆球后方（大圆球已后移0.03，圆锥也相应后移）
    butt_cone_v = translate(butt_cone_v, 0, -0.02, -0.09)
    hips_parts = [(big_ball_v, big_ball_f), (butt_cone_v, butt_cone_f)]
    parts['hips'] = merge_meshes(hips_parts)

    # 上臂：白色翅膀（扁平宽大椭圆形，不是圆柱）
    wing_v, wing_f = make_ellipsoid(0.04, 0.12, 0.08, segments=16, lat_seg=10)
    wing_v = translate(wing_v, 0, -0.05, 0)
    parts['upper_arm'] = (wing_v, wing_f)

    # 前臂：翅膀末端（稍小）
    wing_tip_v, wing_tip_f = make_ellipsoid(0.03, 0.09, 0.06, segments=14, lat_seg=8)
    wing_tip_v = translate(wing_tip_v, 0, -0.03, 0)
    parts['forearm'] = (wing_tip_v, wing_tip_f)

    # 手：翅膀尖（没有手指，扁平）
    hand_v, hand_f = make_ellipsoid(0.025, 0.04, 0.05, segments=12, lat_seg=8)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：短粗橙色腿
    thigh_v, thigh_f = make_capsule(0.035, 0.12, segments=14, lat_seg=8)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：橙色腿
    shin_v, shin_f = make_capsule(0.03, 0.10, segments=14, lat_seg=8)
    parts['shin'] = (shin_v, shin_f)

    # 脚：大黄色蹼足（扁平宽大，像鸭子脚）
    foot_v, foot_f = make_ellipsoid(0.06, 0.025, 0.10, segments=16, lat_seg=10)
    foot_v = translate(foot_v, 0, 0, 0.03)
    # 脚趾间的蹼（扁平延伸）
    web_v, web_f = make_box(0.10, 0.008, 0.06)
    web_v = translate(web_v, 0, -0.01, 0.06)
    parts['foot'] = merge_meshes([(foot_v, foot_f), (web_v, web_f)])

    # 滑雪板、雪杖、关节
    parts.update(make_ski_gear(foot_w=0.08))

    save_character(out_dir, 'donald_duck', parts)


# ==================== 米老鼠 ====================

def generate_mickey_mouse(out_dir):
    """米老鼠：黑色大圆球头、两个巨大黑色圆耳朵、红色大短裤、白色大手套、巨大黄色鞋子"""
    parts = {}

    # 头：黑色大球
    head_v, head_f = make_sphere(0.065, segments=20, lat_seg=14)
    # 两个巨大黑色圆耳朵（直径约头部的2/3，位于头顶两侧）
    ear_l_v, ear_l_f = make_sphere(0.04, segments=16, lat_seg=12)
    ear_l_v = translate(ear_l_v, -0.055, 0.045, 0)
    ear_r_v, ear_r_f = make_sphere(0.04, segments=16, lat_seg=12)
    ear_r_v = translate(ear_r_v, 0.055, 0.045, 0)
    # 白色脸部（口鼻区域，大椭圆）
    face_v, face_f = make_ellipsoid(0.045, 0.035, 0.035, segments=16, lat_seg=10)
    face_v = translate(face_v, 0, -0.015, 0.05)
    # 黑色鼻子（小圆球）
    nose_v, nose_f = make_sphere(0.012, segments=10, lat_seg=8)
    nose_v = translate(nose_v, 0, -0.005, 0.08)

    head_parts = [(head_v, head_f), (ear_l_v, ear_l_f), (ear_r_v, ear_r_f),
                   (face_v, face_f), (nose_v, nose_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子
    neck_v, neck_f = make_cylinder(0.025, 0.03, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：黑色椭圆形身体
    body_v, body_f = make_ellipsoid(0.09, 0.11, 0.075, segments=18, lat_seg=12)
    body_v = translate(body_v, 0, 0, 0)
    # 白色纽扣（两个白色圆扣在短裤上方）
    btn1_v, btn1_f = make_sphere(0.008, segments=8, lat_seg=6)
    btn1_v = translate(btn1_v, 0, -0.02, 0.07)
    btn2_v, btn2_f = make_sphere(0.008, segments=8, lat_seg=6)
    btn2_v = translate(btn2_v, 0, -0.05, 0.07)
    parts['spine'] = merge_meshes([(body_v, body_f), (btn1_v, btn1_f), (btn2_v, btn2_f)])

    # 骨盆：红色大短裤（明显，比普通裤子大很多，圆形鼓起）
    shorts_v, shorts_f = make_ellipsoid(0.11, 0.07, 0.09, segments=18, lat_seg=12)
    shorts_v = translate(shorts_v, 0, -0.04, 0)
    # 短裤上的白色圆点（两个）
    dot1_v, dot1_f = make_sphere(0.01, segments=8, lat_seg=6)
    dot1_v = translate(dot1_v, -0.04, -0.03, 0.07)
    dot2_v, dot2_f = make_sphere(0.01, segments=8, lat_seg=6)
    dot2_v = translate(dot2_v, 0.04, -0.03, 0.07)
    parts['hips'] = merge_meshes([(shorts_v, shorts_f), (dot1_v, dot1_f), (dot2_v, dot2_f)])

    # 上臂：黑色细长手臂
    upper_arm_v, upper_arm_f = make_capsule(0.022, 0.20, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：黑色细长手臂
    forearm_v, forearm_f = make_capsule(0.020, 0.18, segments=14, lat_seg=8)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：白色大手套（比普通手大很多，圆形鼓起，有拇指）
    palm_v, palm_f = make_ellipsoid(0.04, 0.035, 0.03, segments=14, lat_seg=10)
    palm_v = translate(palm_v, 0, -0.01, 0)
    # 拇指
    thumb_v, thumb_f = make_ellipsoid(0.018, 0.025, 0.015, segments=10, lat_seg=8)
    thumb_v = translate(thumb_v, -0.035, 0, 0.01)
    # 四根手指（合并为一个椭圆）
    fingers_v, fingers_f = make_ellipsoid(0.03, 0.03, 0.025, segments=12, lat_seg=8)
    fingers_v = translate(fingers_v, 0, -0.04, 0)
    parts['hand'] = merge_meshes([(palm_v, palm_f), (thumb_v, thumb_f), (fingers_v, fingers_f)])

    # 大腿：黑色短腿
    thigh_v, thigh_f = make_capsule(0.028, 0.14, segments=14, lat_seg=8)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：黑色腿
    shin_v, shin_f = make_capsule(0.025, 0.12, segments=14, lat_seg=8)
    parts['shin'] = (shin_v, shin_f)

    # 脚：巨大黄色椭圆形鞋子（比普通鞋子大很多，椭圆鼓起）
    foot_v, foot_f = make_ellipsoid(0.05, 0.04, 0.11, segments=16, lat_seg=12)
    foot_v = translate(foot_v, 0, 0, 0.04)
    # 鞋面上的黑色条纹
    stripe_v, stripe_f = make_box(0.08, 0.005, 0.04)
    stripe_v = translate(stripe_v, 0, 0.025, 0.02)
    parts['foot'] = merge_meshes([(foot_v, foot_f), (stripe_v, stripe_f)])

    # 滑雪板、雪杖、关节
    parts.update(make_ski_gear(foot_w=0.07))

    save_character(out_dir, 'mickey_mouse', parts)


# ==================== 巴斯光年 ====================

def generate_buzz_lightyear(out_dir):
    """巴斯光年：白色大头盔、紫色面罩、白色宽太空服、绿色胸前控制面板、背部大翅膀、绿色紫色装饰"""
    parts = {}

    # 头：白色大头盔（比普通头大，透明感用白色表示）+ 紫色面罩
    helmet_v, helmet_f = make_sphere(0.075, segments=20, lat_seg=14)
    # 紫色面罩（头盔前方，大椭圆，透明紫色）
    visor_v, visor_f = make_ellipsoid(0.055, 0.04, 0.04, segments=16, lat_seg=10)
    visor_v = translate(visor_v, 0, 0, 0.055)
    # 头盔顶部的红色通信灯
    light_v, light_f = make_cylinder(0.008, 0.015, segments=8)
    light_v = translate(light_v, 0, 0.07, 0)
    # 头盔侧面的白色耳罩
    ear_l_v, ear_l_f = make_ellipsoid(0.02, 0.025, 0.015, segments=10, lat_seg=8)
    ear_l_v = translate(ear_l_v, -0.065, 0, 0)
    ear_r_v, ear_r_f = make_ellipsoid(0.02, 0.025, 0.015, segments=10, lat_seg=8)
    ear_r_v = translate(ear_r_v, 0.065, 0, 0)

    head_parts = [(helmet_v, helmet_f), (visor_v, visor_f), (light_v, light_f),
                  (ear_l_v, ear_l_f), (ear_r_v, ear_r_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子：白色短粗
    neck_v, neck_f = make_cylinder(0.035, 0.035, segments=14)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：白色宽太空服（宽厚，有棱角）+ 绿色胸前控制面板 + 肩部绿色装饰
    body_v, body_f = make_box(0.22, 0.20, 0.14)
    body_v = translate(body_v, 0, 0.02, 0)
    # 胸前绿色控制面板（大矩形，有按钮）
    panel_v, panel_f = make_box(0.10, 0.08, 0.012)
    panel_v = translate(panel_v, 0, 0.02, 0.075)
    # 面板上的按钮（红、绿、蓝小圆点）
    btn_r_v, btn_r_f = make_cylinder(0.008, 0.005, segments=8)
    btn_r_v = translate(btn_r_v, -0.025, 0.04, 0.082)
    btn_g_v, btn_g_f = make_cylinder(0.008, 0.005, segments=8)
    btn_g_v = translate(btn_g_v, 0, 0.04, 0.082)
    btn_b_v, btn_b_f = make_cylinder(0.008, 0.005, segments=8)
    btn_b_v = translate(btn_b_v, 0.025, 0.04, 0.082)
    # 肩部绿色装饰（大块）
    shoulder_l_v, shoulder_l_f = make_box(0.06, 0.05, 0.10)
    shoulder_l_v = translate(shoulder_l_v, -0.12, 0.08, 0)
    shoulder_r_v, shoulder_r_f = make_box(0.06, 0.05, 0.10)
    shoulder_r_v = translate(shoulder_r_v, 0.12, 0.08, 0)
    # 紫色胸带
    strap_v, strap_f = make_box(0.20, 0.02, 0.015)
    strap_v = translate(strap_v, 0, 0.08, 0.075)

    spine_parts = [(body_v, body_f), (panel_v, panel_f), (btn_r_v, btn_r_f),
                    (btn_g_v, btn_g_f), (btn_b_v, btn_b_f), (shoulder_l_v, shoulder_l_f),
                    (shoulder_r_v, shoulder_r_f), (strap_v, strap_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：白色太空服下半部分
    hips_v, hips_f = make_box(0.18, 0.10, 0.12)
    hips_v = translate(hips_v, 0, -0.02, 0)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：白色粗手臂 + 绿色肘部装饰
    upper_arm_v, upper_arm_f = make_capsule(0.035, 0.22, segments=16, lat_seg=10)
    # 绿色上臂装饰环
    arm_ring_v, arm_ring_f = make_cylinder(0.038, 0.02, segments=14)
    arm_ring_v = translate(arm_ring_v, 0, -0.05, 0)
    parts['upper_arm'] = merge_meshes([(upper_arm_v, upper_arm_f), (arm_ring_v, arm_ring_f)])

    # 前臂：白色 + 紫色装饰
    forearm_v, forearm_f = make_capsule(0.032, 0.20, segments=16, lat_seg=10)
    forearm_ring_v, forearm_ring_f = make_cylinder(0.035, 0.02, segments=14)
    forearm_ring_v = translate(forearm_ring_v, 0, 0.05, 0)
    parts['forearm'] = merge_meshes([(forearm_v, forearm_f), (forearm_ring_v, forearm_ring_f)])

    # 手：白色太空手套（粗大有棱角）
    hand_v, hand_f = make_box(0.05, 0.05, 0.045)
    hand_v = translate(hand_v, 0, -0.015, 0)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：白色粗腿 + 绿色装饰
    thigh_v, thigh_f = make_capsule(0.04, 0.30, segments=16, lat_seg=10)
    thigh_ring_v, thigh_ring_f = make_cylinder(0.043, 0.025, segments=14)
    thigh_ring_v = translate(thigh_ring_v, 0, -0.08, 0)
    parts['thigh'] = merge_meshes([(thigh_v, thigh_f), (thigh_ring_v, thigh_ring_f)])

    # 小腿：白色 + 紫色装饰
    shin_v, shin_f = make_capsule(0.036, 0.28, segments=16, lat_seg=10)
    shin_ring_v, shin_ring_f = make_cylinder(0.039, 0.025, segments=14)
    shin_ring_v = translate(shin_ring_v, 0, 0.08, 0)
    parts['shin'] = merge_meshes([(shin_v, shin_f), (shin_ring_v, shin_ring_f)])

    # 脚：白色大靴子（有棱角，宽大）
    foot_v, foot_f = make_box(0.07, 0.06, 0.12)
    foot_v = translate(foot_v, 0, 0, 0.02)
    # 靴子上的绿色装饰条
    boot_stripe_v, boot_stripe_f = make_box(0.06, 0.008, 0.10)
    boot_stripe_v = translate(boot_stripe_v, 0, 0.025, 0.02)
    parts['foot'] = merge_meshes([(foot_v, foot_f), (boot_stripe_v, boot_stripe_f)])

    # 滑雪板、雪杖、关节
    parts.update(make_ski_gear(foot_w=0.08))

    save_character(out_dir, 'buzz_lightyear', parts)


# ==================== 白雪公主 ====================

def generate_snow_white(out_dir):
    """白雪公主：黑色头发、红色大蝴蝶结、蓝色紧身上衣、黄色大裙摆（A字形）、白色衣领"""
    parts = {}

    # 头：白色皮肤 + 黑色头发（覆盖头部大部分）+ 红色大蝴蝶结
    face_v, face_f = make_sphere(0.06, segments=18, lat_seg=12)
    # 黑色头发（覆盖头顶和后方，大半球）
    hair_v, hair_f = make_sphere(0.065, segments=18, lat_seg=10)
    hair_v = scale(hair_v, 1.05, 0.85, 1.0)
    hair_v = translate(hair_v, 0, 0.025, -0.01)
    # 红色大蝴蝶结（头顶，大而明显）
    bow_l_v, bow_l_f = make_ellipsoid(0.03, 0.02, 0.012, segments=12, lat_seg=8)
    bow_l_v = rotate_z(bow_l_v, -15)
    bow_l_v = translate(bow_l_v, -0.03, 0.065, 0.02)
    bow_r_v, bow_r_f = make_ellipsoid(0.03, 0.02, 0.012, segments=12, lat_seg=8)
    bow_r_v = rotate_z(bow_r_v, 15)
    bow_r_v = translate(bow_r_v, 0.03, 0.065, 0.02)
    bow_center_v, bow_center_f = make_sphere(0.012, segments=8, lat_seg=6)
    bow_center_v = translate(bow_center_v, 0, 0.06, 0.025)

    head_parts = [(face_v, face_f), (hair_v, hair_f), (bow_l_v, bow_l_f),
                  (bow_r_v, bow_r_f), (bow_center_v, bow_center_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子
    neck_v, neck_f = make_cylinder(0.024, 0.04, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：蓝色紧身上衣 + 白色大翻领 + 黄色腰带
    top_v, top_f = make_ellipsoid(0.10, 0.12, 0.075, segments=18, lat_seg=12)
    top_v = translate(top_v, 0, 0.02, 0)
    # 白色大翻领（V字形，明显）
    collar_l_v, collar_l_f = make_box(0.07, 0.006, 0.09)
    collar_l_v = rotate_z(collar_l_v, -25)
    collar_l_v = translate(collar_l_v, -0.04, 0.08, 0.06)
    collar_r_v, collar_r_f = make_box(0.07, 0.006, 0.09)
    collar_r_v = rotate_z(collar_r_v, 25)
    collar_r_v = translate(collar_r_v, 0.04, 0.08, 0.06)
    # 黄色腰带
    belt_v, belt_f = make_cylinder(0.105, 0.02, segments=16)
    belt_v = translate(belt_v, 0, -0.05, 0)

    spine_parts = [(top_v, top_f), (collar_l_v, collar_l_f), (collar_r_v, collar_r_f), (belt_v, belt_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：黄色大裙摆（A字形，宽大，比普通裙子大很多）
    skirt_v, skirt_f = make_cone(0.16, 0.30, segments=24)
    skirt_v = translate(skirt_v, 0, -0.10, 0)
    # 裙摆底部的白色花边
    hem_v, hem_f = make_cylinder(0.165, 0.015, segments=24)
    hem_v = translate(hem_v, 0, -0.24, 0)
    parts['hips'] = merge_meshes([(skirt_v, skirt_f), (hem_v, hem_f)])

    # 上臂：蓝色袖子（紧身）
    upper_arm_v, upper_arm_f = make_capsule(0.026, 0.20, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：白色袖子（泡泡袖，稍大）
    forearm_v, forearm_f = make_capsule(0.03, 0.18, segments=14, lat_seg=8)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：白色皮肤
    hand_v, hand_f = make_ellipsoid(0.025, 0.03, 0.022, segments=12, lat_seg=8)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：被裙子遮住，细
    thigh_v, thigh_f = make_capsule(0.02, 0.10, segments=10, lat_seg=6)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：细
    shin_v, shin_f = make_capsule(0.018, 0.10, segments=10, lat_seg=6)
    parts['shin'] = (shin_v, shin_f)

    # 脚：黑色小鞋子（尖头）
    foot_v, foot_f = make_ellipsoid(0.03, 0.025, 0.07, segments=12, lat_seg=8)
    foot_v = translate(foot_v, 0, 0, 0.02)
    parts['foot'] = (foot_v, foot_f)

    # 滑雪板、雪杖、关节
    parts.update(make_ski_gear(foot_w=0.05))

    save_character(out_dir, 'snow_white', parts)


# ==================== 大力水手 ====================

def generate_popeye(out_dir):
    """大力水手：方脸大下巴、烟斗、水手帽、蓝白条纹水手服、特别粗壮的前臂（标志性特征）"""
    parts = {}

    # 头：方脸（用盒子+球组合）+ 大下巴 + 烟斗 + 水手帽
    head_v, head_f = make_ellipsoid(0.055, 0.06, 0.05, segments=16, lat_seg=10)
    # 方下巴（大盒子，明显）
    jaw_v, jaw_f = make_box(0.07, 0.035, 0.06)
    jaw_v = translate(jaw_v, 0, -0.04, 0.01)
    # 大鼻子（突出）
    nose_v, nose_f = make_ellipsoid(0.015, 0.02, 0.02, segments=10, lat_seg=8)
    nose_v = translate(nose_v, 0, -0.01, 0.055)
    # 烟斗（嘴里叼着，明显，黑色长杆+棕色斗钵）
    pipe_stem_v, pipe_stem_f = make_cylinder(0.004, 0.06, segments=8)
    pipe_stem_v = rotate_z(pipe_stem_v, -30)
    pipe_stem_v = translate(pipe_stem_v, 0.04, -0.03, 0.05)
    pipe_bowl_v, pipe_bowl_f = make_ellipsoid(0.012, 0.015, 0.012, segments=10, lat_seg=8)
    pipe_bowl_v = translate(pipe_bowl_v, 0.065, -0.045, 0.05)
    # 水手帽（黑色，平顶宽边）
    hat_brim_v, hat_brim_f = make_cylinder(0.07, 0.006, segments=16)
    hat_brim_v = translate(hat_brim_v, 0, 0.05, 0)
    hat_top_v, hat_top_f = make_cylinder(0.055, 0.02, segments=14)
    hat_top_v = translate(hat_top_v, 0, 0.06, 0)

    head_parts = [(head_v, head_f), (jaw_v, jaw_f), (nose_v, nose_f),
                  (pipe_stem_v, pipe_stem_f), (pipe_bowl_v, pipe_bowl_f),
                  (hat_brim_v, hat_brim_f), (hat_top_v, hat_top_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子：粗短
    neck_v, neck_f = make_cylinder(0.032, 0.03, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：宽肩 + 蓝白条纹水手服
    body_v, body_f = make_ellipsoid(0.12, 0.13, 0.09, segments=18, lat_seg=12)
    body_v = translate(body_v, 0, 0.01, 0)
    # 蓝白条纹（用多个蓝色环表示）
    for i, y in enumerate([0.06, 0.02, -0.02, -0.06]):
        stripe_v, stripe_f = make_cylinder(0.125, 0.015, segments=16)
        stripe_v = translate(stripe_v, 0, y, 0)
        if i == 0:
            stripe_parts = [(stripe_v, stripe_f)]
        else:
            stripe_parts.append((stripe_v, stripe_f))
    # 白色水手领（大翻领）
    collar_v, collar_f = make_box(0.14, 0.006, 0.10)
    collar_v = translate(collar_v, 0, 0.09, 0.04)
    # 红色领巾
    scarf_v, scarf_f = make_sphere(0.015, segments=10, lat_seg=8)
    scarf_v = translate(scarf_v, 0, 0.07, 0.08)

    spine_parts = [(body_v, body_f)] + stripe_parts + [(collar_v, collar_f), (scarf_v, scarf_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：蓝色裤子
    hips_v, hips_f = make_ellipsoid(0.11, 0.06, 0.08, segments=16, lat_seg=10)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：正常粗细
    upper_arm_v, upper_arm_f = make_capsule(0.032, 0.18, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：特别粗壮（大力水手标志性特征！比上臂粗很多）
    forearm_v, forearm_f = make_capsule(0.055, 0.16, segments=18, lat_seg=10)
    # 前臂上的纹身锚（小三角形表示）
    anchor_v, anchor_f = make_cone(0.015, 0.02, segments=6)
    anchor_v = translate(anchor_v, 0, 0, 0.05)
    parts['forearm'] = merge_meshes([(forearm_v, forearm_f), (anchor_v, anchor_f)])

    # 手：粗大拳头
    hand_v, hand_f = make_ellipsoid(0.04, 0.035, 0.035, segments=12, lat_seg=8)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：短粗
    thigh_v, thigh_f = make_capsule(0.038, 0.20, segments=14, lat_seg=8)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：短粗
    shin_v, shin_f = make_capsule(0.034, 0.18, segments=14, lat_seg=8)
    parts['shin'] = (shin_v, shin_f)

    # 脚：大鞋子（棕色，宽大）
    foot_v, foot_f = make_ellipsoid(0.05, 0.035, 0.09, segments=14, lat_seg=10)
    foot_v = translate(foot_v, 0, 0, 0.02)
    parts['foot'] = (foot_v, foot_f)

    # 滑雪板、雪杖、关节
    parts.update(make_ski_gear(foot_w=0.07))

    save_character(out_dir, 'popeye', parts)


# ==================== 国王 ====================

def generate_king(out_dir):
    """国王：金色大皇冠（高而多尖顶）、大胡子、红色拖地长袍、白色毛边、金色权杖"""
    parts = {}

    # 头：白色皮肤 + 大胡子（覆盖下半张脸，大而明显）+ 金色大皇冠
    face_v, face_f = make_sphere(0.06, segments=18, lat_seg=12)
    # 大胡子（白色，覆盖下巴和胸口上方，大椭圆）
    beard_v, beard_f = make_ellipsoid(0.055, 0.08, 0.05, segments=16, lat_seg=10)
    beard_v = translate(beard_v, 0, -0.06, 0.03)
    # 大胡子的卷曲末端（改为小三角，避免两个圆球）
    beard_tip_l_v, beard_tip_l_f = make_cone(0.012, 0.025, segments=6)
    beard_tip_l_v = rotate_x(beard_tip_l_v, 180)
    beard_tip_l_v = translate(beard_tip_l_v, -0.02, -0.10, 0.04)
    beard_tip_r_v, beard_tip_r_f = make_cone(0.012, 0.025, segments=6)
    beard_tip_r_v = rotate_x(beard_tip_r_v, 180)
    beard_tip_r_v = translate(beard_tip_r_v, 0.02, -0.10, 0.04)
    # 金色大皇冠（高，5个尖顶，每个尖顶有珍珠）
    crown_base_v, crown_base_f = make_cylinder(0.065, 0.04, segments=16)
    crown_base_v = translate(crown_base_v, 0, 0.07, 0)
    # 5个尖顶
    crown_spikes = []
    for i in range(5):
        angle = i * 2 * np.pi / 5
        x = 0.05 * np.cos(angle)
        z = 0.05 * np.sin(angle)
        spike_v, spike_f = make_cone(0.015, 0.04, segments=8)
        spike_v = translate(spike_v, x, 0.10, z)
        crown_spikes.append((spike_v, spike_f))
        # 尖顶珍珠
        pearl_v, pearl_f = make_sphere(0.008, segments=8, lat_seg=6)
        pearl_v = translate(pearl_v, x, 0.125, z)
        crown_spikes.append((pearl_v, pearl_f))
    # 皇冠上的红色宝石
    gem_v, gem_f = make_sphere(0.01, segments=8, lat_seg=6)
    gem_v = translate(gem_v, 0, 0.085, 0.06)

    head_parts = [(face_v, face_f), (beard_v, beard_f), (beard_tip_l_v, beard_tip_l_f),
                  (beard_tip_r_v, beard_tip_r_f), (crown_base_v, crown_base_f),
                  (gem_v, gem_f)] + crown_spikes
    parts['head'] = merge_meshes(head_parts)

    # 脖子：被胡子遮住，短粗
    neck_v, neck_f = make_cylinder(0.03, 0.025, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：红色长袍上半部分（宽大）+ 白色毛边 + 金色装饰
    body_v, body_f = make_ellipsoid(0.14, 0.15, 0.11, segments=20, lat_seg=14)
    body_v = translate(body_v, 0, 0.02, 0)
    # 白色毛边（领口和前襟）
    fur_collar_v, fur_collar_f = make_torus(0.08, 0.015, major_seg=16, minor_seg=8)
    fur_collar_v = rotate_x(fur_collar_v, 90)
    fur_collar_v = translate(fur_collar_v, 0, 0.10, 0)
    # 金色腰带
    belt_v, belt_f = make_cylinder(0.145, 0.025, segments=18)
    belt_v = translate(belt_v, 0, -0.04, 0)
    # 金色腰带扣
    buckle_v, buckle_f = make_box(0.04, 0.03, 0.01)
    buckle_v = translate(buckle_v, 0, -0.04, 0.12)

    spine_parts = [(body_v, body_f), (fur_collar_v, fur_collar_f),
                    (belt_v, belt_f), (buckle_v, buckle_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：红色拖地长袍下半部分（A字形，宽大，覆盖腿部）
    robe_v, robe_f = make_cone(0.18, 0.35, segments=24)
    robe_v = translate(robe_v, 0, -0.12, 0)
    # 长袍底部白色毛边
    robe_hem_v, robe_hem_f = make_cylinder(0.185, 0.02, segments=24)
    robe_hem_v = translate(robe_hem_v, 0, -0.28, 0)
    # 长袍前襟的金色装饰线
    trim_v, trim_f = make_box(0.015, 0.30, 0.01)
    trim_v = translate(trim_v, 0, -0.10, 0.15)
    parts['hips'] = merge_meshes([(robe_v, robe_f), (robe_hem_v, robe_hem_f), (trim_v, trim_f)])

    # 上臂：红色长袍袖子（宽大）
    upper_arm_v, upper_arm_f = make_capsule(0.04, 0.20, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：红色长袍袖子 + 白色袖口
    forearm_v, forearm_f = make_capsule(0.038, 0.18, segments=14, lat_seg=8)
    cuff_v, cuff_f = make_cylinder(0.042, 0.02, segments=14)
    cuff_v = translate(cuff_v, 0, -0.07, 0)
    parts['forearm'] = merge_meshes([(forearm_v, forearm_f), (cuff_v, cuff_f)])

    # 手：白色皮肤（右手拿权杖，但权杖作为手部的一部分）
    hand_v, hand_f = make_ellipsoid(0.03, 0.03, 0.028, segments=12, lat_seg=8)
    # 金色权杖（从手向上延伸，长而有顶部装饰）
    staff_v, staff_f = make_cylinder(0.008, 0.40, segments=10)
    staff_v = translate(staff_v, 0, 0.15, 0)
    # 权杖顶部的金色球
    staff_top_v, staff_top_f = make_sphere(0.025, segments=12, lat_seg=10)
    staff_top_v = translate(staff_top_v, 0, 0.36, 0)
    # 权杖顶部的十字
    cross_v_v, cross_v_f = make_box(0.006, 0.04, 0.006)
    cross_v_v = translate(cross_v_v, 0, 0.39, 0)
    cross_h_v, cross_h_f = make_box(0.025, 0.006, 0.006)
    cross_h_v = translate(cross_h_v, 0, 0.395, 0)
    parts['hand'] = merge_meshes([(hand_v, hand_f), (staff_v, staff_f), (staff_top_v, staff_top_f),
                                    (cross_v_v, cross_v_f), (cross_h_v, cross_h_f)])

    # 大腿：被长袍遮住，细
    thigh_v, thigh_f = make_capsule(0.025, 0.08, segments=10, lat_seg=6)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：被长袍遮住
    shin_v, shin_f = make_capsule(0.022, 0.08, segments=10, lat_seg=6)
    parts['shin'] = (shin_v, shin_f)

    # 脚：金色鞋子（被长袍遮住大部分）
    foot_v, foot_f = make_ellipsoid(0.04, 0.03, 0.07, segments=12, lat_seg=8)
    foot_v = translate(foot_v, 0, 0, 0.02)
    parts['foot'] = (foot_v, foot_f)

    # 滑雪板、雪杖、关节
    parts.update(make_ski_gear(foot_w=0.06))

    save_character(out_dir, 'king', parts)


# ==================== 哈利波特 ====================

def generate_harry_potter(out_dir):
    """哈利波特：黑色乱发、圆框眼镜（大而明显）、额头闪电疤痕、黑色长袍、红色围巾、魔杖"""
    parts = {}

    # 头：白色皮肤 + 黑色乱发（蓬松，覆盖头顶）+ 圆框眼镜（大而明显）+ 闪电疤痕
    face_v, face_f = make_sphere(0.058, segments=18, lat_seg=12)
    # 黑色乱发（蓬松，比头大，不规则）
    hair_v, hair_f = make_sphere(0.065, segments=18, lat_seg=10)
    hair_v = scale(hair_v, 1.1, 0.9, 1.05)
    hair_v = translate(hair_v, 0, 0.03, -0.01)
    # 乱发的翘起（几个小球）
    hair_spike1_v, hair_spike1_f = make_sphere(0.015, segments=8, lat_seg=6)
    hair_spike1_v = translate(hair_spike1_v, -0.03, 0.07, 0.02)
    hair_spike2_v, hair_spike2_f = make_sphere(0.015, segments=8, lat_seg=6)
    hair_spike2_v = translate(hair_spike2_v, 0.02, 0.075, 0.03)
    hair_spike3_v, hair_spike3_f = make_sphere(0.012, segments=8, lat_seg=6)
    hair_spike3_v = translate(hair_spike3_v, 0.04, 0.06, 0.01)
    # 圆框眼镜（大而明显，黑色圆环）
    glass_l_v, glass_l_f = make_torus(0.022, 0.003, major_seg=16, minor_seg=6)
    glass_l_v = rotate_y(glass_l_v, 90)
    glass_l_v = translate(glass_l_v, -0.022, 0.005, 0.052)
    glass_r_v, glass_r_f = make_torus(0.022, 0.003, major_seg=16, minor_seg=6)
    glass_r_v = rotate_y(glass_r_v, 90)
    glass_r_v = translate(glass_r_v, 0.022, 0.005, 0.052)
    # 眼镜鼻梁
    bridge_v, bridge_f = make_box(0.012, 0.004, 0.004)
    bridge_v = translate(bridge_v, 0, 0.005, 0.052)
    # 眼镜腿
    arm_l_v, arm_l_f = make_box(0.004, 0.004, 0.04)
    arm_l_v = translate(arm_l_v, -0.04, 0.005, 0.035)
    arm_r_v, arm_r_f = make_box(0.004, 0.004, 0.04)
    arm_r_v = translate(arm_r_v, 0.04, 0.005, 0.035)
    # 额头闪电疤痕（用小三角形表示）
    scar_v, scar_f = make_box(0.003, 0.015, 0.003)
    scar_v = rotate_z(scar_v, 30)
    scar_v = translate(scar_v, -0.01, 0.035, 0.055)

    head_parts = [(face_v, face_f), (hair_v, hair_f), (hair_spike1_v, hair_spike1_f),
                   (hair_spike2_v, hair_spike2_f), (hair_spike3_v, hair_spike3_f),
                   (glass_l_v, glass_l_f), (glass_r_v, glass_r_f), (bridge_v, bridge_f),
                   (arm_l_v, arm_l_f), (arm_r_v, arm_r_f), (scar_v, scar_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子
    neck_v, neck_f = make_cylinder(0.022, 0.04, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：黑色长袍上半部分（宽松）+ 红色围巾（大而明显，多层缠绕）
    body_v, body_f = make_ellipsoid(0.10, 0.13, 0.08, segments=18, lat_seg=12)
    body_v = translate(body_v, 0, 0.01, 0)
    # 红色围巾（多层缠绕，大而明显）
    for i, y in enumerate([0.08, 0.06, 0.04]):
        scarf_v, scarf_f = make_cylinder(0.105, 0.018, segments=16)
        scarf_v = translate(scarf_v, 0, y, 0)
        if i == 0:
            scarf_parts = [(scarf_v, scarf_f)]
        else:
            scarf_parts.append((scarf_v, scarf_f))
    # 围巾的垂下部分（两条长带）
    scarf_tail1_v, scarf_tail1_f = make_box(0.03, 0.15, 0.012)
    scarf_tail1_v = translate(scarf_tail1_v, -0.025, -0.05, 0.07)
    scarf_tail2_v, scarf_tail2_f = make_box(0.03, 0.12, 0.012)
    scarf_tail2_v = translate(scarf_tail2_v, 0.025, -0.04, 0.07)
    # 长袍的金色/红色内衬（领口露出）
    lining_v, lining_f = make_box(0.06, 0.08, 0.01)
    lining_v = translate(lining_v, 0, 0.02, 0.075)

    spine_parts = [(body_v, body_f)] + scarf_parts + [(scarf_tail1_v, scarf_tail1_f),
                                                          (scarf_tail2_v, scarf_tail2_f), (lining_v, lining_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：黑色长袍下半部分（宽松，长及脚踝）
    robe_v, robe_f = make_cone(0.13, 0.30, segments=20)
    robe_v = translate(robe_v, 0, -0.10, 0)
    parts['hips'] = (robe_v, robe_f)

    # 上臂：黑色长袍袖子（宽松）
    upper_arm_v, upper_arm_f = make_capsule(0.03, 0.20, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：黑色长袍袖子
    forearm_v, forearm_f = make_capsule(0.028, 0.18, segments=14, lat_seg=8)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：白色皮肤（右手拿魔杖）
    hand_v, hand_f = make_ellipsoid(0.025, 0.028, 0.025, segments=12, lat_seg=8)
    # 魔杖（细长，从手向外延伸）
    wand_v, wand_f = make_cylinder(0.004, 0.25, segments=8)
    wand_v = translate(wand_v, 0, -0.08, 0.05)
    # 魔杖手柄（稍粗）
    wand_handle_v, wand_handle_f = make_cylinder(0.006, 0.05, segments=8)
    wand_handle_v = translate(wand_handle_v, 0, 0.02, 0.02)
    parts['hand'] = merge_meshes([(hand_v, hand_f), (wand_v, wand_f), (wand_handle_v, wand_handle_f)])

    # 大腿：被长袍遮住，细
    thigh_v, thigh_f = make_capsule(0.022, 0.10, segments=10, lat_seg=6)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：被长袍遮住
    shin_v, shin_f = make_capsule(0.020, 0.10, segments=10, lat_seg=6)
    parts['shin'] = (shin_v, shin_f)

    # 脚：黑色鞋子（被长袍遮住大部分）
    foot_v, foot_f = make_ellipsoid(0.035, 0.025, 0.07, segments=12, lat_seg=8)
    foot_v = translate(foot_v, 0, 0, 0.02)
    parts['foot'] = (foot_v, foot_f)

    # 滑雪板、雪杖、关节
    parts.update(make_ski_gear(foot_w=0.055))

    save_character(out_dir, 'harry_potter', parts)


# ==================== 主入口 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("经典人物人偶生成器 v2 - 完全自定义身体结构")
    print("=" * 60)

    generate_donald_duck(os.path.join(BASE_DIR, 'donald_duck'))
    generate_mickey_mouse(os.path.join(BASE_DIR, 'mickey_mouse'))
    generate_buzz_lightyear(os.path.join(BASE_DIR, 'buzz_lightyear'))
    generate_snow_white(os.path.join(BASE_DIR, 'snow_white'))
    generate_popeye(os.path.join(BASE_DIR, 'popeye'))
    generate_king(os.path.join(BASE_DIR, 'king'))
    generate_harry_potter(os.path.join(BASE_DIR, 'harry_potter'))

    print("\n" + "=" * 60)
    print("全部经典人物生成完成！")
    print(f"模型目录: {BASE_DIR}")
    print("  donald_duck/    - 唐老鸭（鸭子身体、大扁嘴、翅膀、水手帽）")
    print("  mickey_mouse/   - 米老鼠（大耳朵、大手套、大鞋子、红短裤）")
    print("  buzz_lightyear/ - 巴斯光年（大头盔、太空服、翅膀、绿紫装饰）")
    print("  snow_white/     - 白雪公主（黄裙子、蓝上衣、红蝴蝶结、黑发）")
    print("  popeye/         - 大力水手（烟斗、水手帽、粗壮前臂、条纹衫）")
    print("  king/           - 国王（金皇冠、大胡子、红长袍、权杖）")
    print("  harry_potter/   - 哈利波特（圆框眼镜、乱发、红围巾、魔杖、黑袍）")
    print("=" * 60)
