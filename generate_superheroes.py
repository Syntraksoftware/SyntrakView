"""
超级英雄人偶生成器
钢铁侠、绿巨人、奇异博士、美国队长、超人、蜘蛛侠、闪电侠、毒液
"""
import os
import sys
import numpy as np
from stl import mesh as stl_mesh

# 复用generate_characters_v2.py中的基础函数
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_characters_v2 import (
    make_sphere, make_ellipsoid, make_cylinder, make_capsule, make_box,
    make_torus, make_cone, merge_meshes, translate, rotate_x, rotate_y,
    rotate_z, scale, save_stl, center_mesh, save_character, make_ski_gear
)

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')


# ==================== 钢铁侠 ====================
def generate_iron_man(out_dir):
    """钢铁侠：红金配色，头盔面罩，胸口反应炉，金属盔甲"""
    parts = {}

    # 头：金红头盔（面罩+发光眼睛）
    helmet_v, helmet_f = make_sphere(0.06, segments=20, lat_seg=14)
    # 面罩（金色，脸部区域）
    face_v, face_f = make_ellipsoid(0.045, 0.04, 0.035, segments=16, lat_seg=10)
    face_v = translate(face_v, 0, -0.005, 0.035)
    # 眼睛（发光白色，狭长）
    eye_l_v, eye_l_f = make_box(0.018, 0.006, 0.008)
    eye_l_v = translate(eye_l_v, -0.018, 0.01, 0.058)
    eye_r_v, eye_r_f = make_box(0.018, 0.006, 0.008)
    eye_r_v = translate(eye_r_v, 0.018, 0.01, 0.058)
    # 头顶金色
    top_v, top_f = make_sphere(0.04, segments=14, lat_seg=10)
    top_v = translate(top_v, 0, 0.035, -0.005)

    head_parts = [(helmet_v, helmet_f), (face_v, face_f), (eye_l_v, eye_l_f),
                  (eye_r_v, eye_r_f), (top_v, top_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子
    neck_v, neck_f = make_cylinder(0.025, 0.03, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：红色盔甲主体 + 金色肩部 + 胸口反应炉（圆形发光）
    body_v, body_f = make_ellipsoid(0.11, 0.14, 0.07, segments=20, lat_seg=14)
    body_v = translate(body_v, 0, 0.01, 0)
    # 金色胸甲
    chest_v, chest_f = make_ellipsoid(0.10, 0.08, 0.06, segments=18, lat_seg=10)
    chest_v = translate(chest_v, 0, 0.04, 0.02)
    # 胸口反应炉（圆形发光蓝白）
    reactor_v, reactor_f = make_cylinder(0.025, 0.008, segments=16)
    reactor_v = rotate_x(reactor_v, 90)
    reactor_v = translate(reactor_v, 0, 0.03, 0.075)
    # 金色肩部
    shoulder_l_v, shoulder_l_f = make_sphere(0.04, segments=14, lat_seg=10)
    shoulder_l_v = translate(shoulder_l_v, -0.10, 0.08, 0)
    shoulder_r_v, shoulder_r_f = make_sphere(0.04, segments=14, lat_seg=10)
    shoulder_r_v = translate(shoulder_r_v, 0.10, 0.08, 0)

    spine_parts = [(body_v, body_f), (chest_v, chest_f), (reactor_v, reactor_f),
                    (shoulder_l_v, shoulder_l_f), (shoulder_r_v, shoulder_r_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：红色
    hips_v, hips_f = make_ellipsoid(0.09, 0.06, 0.06, segments=16, lat_seg=10)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：红色盔甲
    upper_arm_v, upper_arm_f = make_capsule(0.03, 0.22, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：金色盔甲
    forearm_v, forearm_f = make_capsule(0.028, 0.20, segments=14, lat_seg=8)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：红色手套 + 掌心反应炉
    hand_v, hand_f = make_sphere(0.025, segments=12, lat_seg=8)
    palm_reactor_v, palm_reactor_f = make_cylinder(0.012, 0.005, segments=10)
    palm_reactor_v = rotate_x(palm_reactor_v, 90)
    palm_reactor_v = translate(palm_reactor_v, 0, 0, 0.025)
    parts['hand'] = merge_meshes([(hand_v, hand_f), (palm_reactor_v, palm_reactor_f)])

    # 大腿：红色
    thigh_v, thigh_f = make_capsule(0.035, 0.28, segments=14, lat_seg=8)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：金色
    shin_v, shin_f = make_capsule(0.032, 0.26, segments=14, lat_seg=8)
    parts['shin'] = (shin_v, shin_f)

    # 脚：红色靴子
    foot_v, foot_f = make_ellipsoid(0.03, 0.04, 0.07, segments=14, lat_seg=10)
    foot_v = translate(foot_v, 0, -0.01, 0.02)
    parts['foot'] = (foot_v, foot_f)

    parts.update(make_ski_gear(foot_w=0.06))
    save_character(out_dir, 'iron_man', parts)


# ==================== 绿巨人 ====================
def generate_hulk(out_dir):
    """绿巨人：绿色皮肤，巨大肌肉，紫色裤子，黑色头发，愤怒表情"""
    parts = {}

    # 头：绿色皮肤 + 黑色短发 + 愤怒眉毛 + 巨大下巴
    face_v, face_f = make_sphere(0.065, segments=20, lat_seg=14)
    # 黑色短发
    hair_v, hair_f = make_sphere(0.06, segments=18, lat_seg=12)
    hair_v = scale(hair_v, 1.05, 0.7, 1.0)
    hair_v = translate(hair_v, 0, 0.035, -0.01)
    # 愤怒眉毛（粗黑，倾斜）
    brow_l_v, brow_l_f = make_box(0.025, 0.006, 0.008)
    brow_l_v = rotate_z(brow_l_v, -15)
    brow_l_v = translate(brow_l_v, -0.02, 0.015, 0.058)
    brow_r_v, brow_r_f = make_box(0.025, 0.006, 0.008)
    brow_r_v = rotate_z(brow_r_v, 15)
    brow_r_v = translate(brow_r_v, 0.02, 0.015, 0.058)
    # 眼睛（绿色，小）
    eye_l_v, eye_l_f = make_sphere(0.008, segments=8, lat_seg=6)
    eye_l_v = translate(eye_l_v, -0.018, 0.005, 0.06)
    eye_r_v, eye_r_f = make_sphere(0.008, segments=8, lat_seg=6)
    eye_r_v = translate(eye_r_v, 0.018, 0.005, 0.06)
    # 巨大下巴
    jaw_v, jaw_f = make_ellipsoid(0.04, 0.03, 0.035, segments=14, lat_seg=10)
    jaw_v = translate(jaw_v, 0, -0.035, 0.02)

    head_parts = [(face_v, face_f), (hair_v, hair_f), (brow_l_v, brow_l_f),
                   (brow_r_v, brow_r_f), (eye_l_v, eye_l_f), (eye_r_v, eye_r_f),
                   (jaw_v, jaw_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子（粗壮）
    neck_v, neck_f = make_cylinder(0.035, 0.04, segments=14)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：巨大绿色肌肉胸肌 + 紫色裤子腰部
    body_v, body_f = make_ellipsoid(0.14, 0.16, 0.09, segments=22, lat_seg=16)
    body_v = translate(body_v, 0, 0.02, 0)
    # 胸肌（两块凸起）
    pec_l_v, pec_l_f = make_ellipsoid(0.06, 0.05, 0.04, segments=14, lat_seg=10)
    pec_l_v = translate(pec_l_v, -0.045, 0.05, 0.06)
    pec_r_v, pec_r_f = make_ellipsoid(0.06, 0.05, 0.04, segments=14, lat_seg=10)
    pec_r_v = translate(pec_r_v, 0.045, 0.05, 0.06)
    # 腹肌（几块凸起）
    for i, y in enumerate([0.0, -0.025, -0.05]):
        ab_l_v, ab_l_f = make_ellipsoid(0.025, 0.018, 0.02, segments=10, lat_seg=8)
        ab_l_v = translate(ab_l_v, -0.02, y, 0.07)
        ab_r_v, ab_r_f = make_ellipsoid(0.025, 0.018, 0.02, segments=10, lat_seg=8)
        ab_r_v = translate(ab_r_v, 0.02, y, 0.07)
        if i == 0:
            ab_parts = [(ab_l_v, ab_l_f), (ab_r_v, ab_r_f)]
        else:
            ab_parts.extend([(ab_l_v, ab_l_f), (ab_r_v, ab_r_f)])

    spine_parts = [(body_v, body_f), (pec_l_v, pec_l_f), (pec_r_v, pec_r_f)] + ab_parts
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：紫色裤子
    hips_v, hips_f = make_ellipsoid(0.12, 0.07, 0.08, segments=18, lat_seg=12)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：巨大绿色肌肉
    upper_arm_v, upper_arm_f = make_capsule(0.05, 0.25, segments=16, lat_seg=10)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：更粗壮
    forearm_v, forearm_f = make_capsule(0.055, 0.22, segments=16, lat_seg=10)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：巨大绿色拳头
    hand_v, hand_f = make_sphere(0.04, segments=14, lat_seg=10)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：紫色裤子 + 巨大肌肉
    thigh_v, thigh_f = make_capsule(0.055, 0.30, segments=16, lat_seg=10)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：绿色
    shin_v, shin_f = make_capsule(0.045, 0.28, segments=16, lat_seg=10)
    parts['shin'] = (shin_v, shin_f)

    # 脚：巨大绿色
    foot_v, foot_f = make_ellipsoid(0.04, 0.05, 0.08, segments=14, lat_seg=10)
    foot_v = translate(foot_v, 0, -0.01, 0.02)
    parts['foot'] = (foot_v, foot_f)

    parts.update(make_ski_gear(foot_w=0.08))
    save_character(out_dir, 'hulk', parts)


# ==================== 奇异博士 ====================
def generate_doctor_strange(out_dir):
    """奇异博士：红色披风，蓝色法袍，阿戈摩托之眼，黑色头发，胡子"""
    parts = {}

    # 头：白色皮肤 + 黑色头发 + 胡子 + 山羊胡
    face_v, face_f = make_sphere(0.058, segments=18, lat_seg=12)
    # 黑色头发（向后梳）
    hair_v, hair_f = make_sphere(0.062, segments=18, lat_seg=12)
    hair_v = scale(hair_v, 1.05, 0.85, 1.0)
    hair_v = translate(hair_v, 0, 0.025, -0.015)
    # 鬓角
    side_l_v, side_l_f = make_box(0.01, 0.03, 0.015)
    side_l_v = translate(side_l_v, -0.05, -0.01, 0.02)
    side_r_v, side_r_f = make_box(0.01, 0.03, 0.015)
    side_r_v = translate(side_r_v, 0.05, -0.01, 0.02)
    # 小胡子
    mustache_v, mustache_f = make_box(0.03, 0.006, 0.01)
    mustache_v = translate(mustache_v, 0, -0.015, 0.055)
    # 山羊胡
    goatee_v, goatee_f = make_ellipsoid(0.015, 0.025, 0.012, segments=10, lat_seg=8)
    goatee_v = translate(goatee_v, 0, -0.04, 0.05)

    head_parts = [(face_v, face_f), (hair_v, hair_f), (side_l_v, side_l_f),
                   (side_r_v, side_r_f), (mustache_v, mustache_f), (goatee_v, goatee_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子
    neck_v, neck_f = make_cylinder(0.022, 0.04, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：蓝色法袍 + 阿戈摩托之眼（胸口绿色宝石）
    body_v, body_f = make_ellipsoid(0.10, 0.14, 0.08, segments=18, lat_seg=12)
    body_v = translate(body_v, 0, 0.01, 0)
    # 法袍V字领
    collar_v, collar_f = make_box(0.06, 0.005, 0.06)
    collar_v = rotate_x(collar_v, -20)
    collar_v = translate(collar_v, 0, 0.08, 0.06)
    # 阿戈摩托之眼（金色底座 + 绿色宝石）
    amulet_base_v, amulet_base_f = make_cylinder(0.025, 0.008, segments=16)
    amulet_base_v = rotate_x(amulet_base_v, 90)
    amulet_base_v = translate(amulet_base_v, 0, 0.02, 0.075)
    amulet_gem_v, amulet_gem_f = make_sphere(0.015, segments=12, lat_seg=8)
    amulet_gem_v = translate(amulet_gem_v, 0, 0.02, 0.082)
    # 红色披风（从肩部向后垂下，大而明显）
    cape_v, cape_f = make_box(0.22, 0.30, 0.015)
    cape_v = translate(cape_v, 0, 0.0, -0.08)
    # 披风肩部隆起
    cape_shoulder_v, cape_shoulder_f = make_ellipsoid(0.12, 0.04, 0.05, segments=14, lat_seg=10)
    cape_shoulder_v = translate(cape_shoulder_v, 0, 0.10, -0.05)

    spine_parts = [(body_v, body_f), (collar_v, collar_f), (amulet_base_v, amulet_base_f),
                    (amulet_gem_v, amulet_gem_f), (cape_v, cape_f), (cape_shoulder_v, cape_shoulder_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：蓝色法袍
    hips_v, hips_f = make_ellipsoid(0.09, 0.06, 0.07, segments=16, lat_seg=10)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：蓝色法袍袖子
    upper_arm_v, upper_arm_f = make_capsule(0.032, 0.22, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：蓝色
    forearm_v, forearm_f = make_capsule(0.03, 0.20, segments=14, lat_seg=8)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：白色手套
    hand_v, hand_f = make_sphere(0.025, segments=12, lat_seg=8)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：蓝色法袍
    thigh_v, thigh_f = make_capsule(0.035, 0.28, segments=14, lat_seg=8)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：蓝色
    shin_v, shin_f = make_capsule(0.032, 0.26, segments=14, lat_seg=8)
    parts['shin'] = (shin_v, shin_f)

    # 脚：红色靴子
    foot_v, foot_f = make_ellipsoid(0.03, 0.04, 0.07, segments=14, lat_seg=10)
    foot_v = translate(foot_v, 0, -0.01, 0.02)
    parts['foot'] = (foot_v, foot_f)

    parts.update(make_ski_gear(foot_w=0.06))
    save_character(out_dir, 'doctor_strange', parts)


# ==================== 美国队长 ====================
def generate_captain_america(out_dir):
    """美国队长：蓝白红配色，星星条纹，头盔A字，盾牌"""
    parts = {}

    # 头：蓝色头盔 + 白色A字 + 白色翅膀装饰
    helmet_v, helmet_f = make_sphere(0.06, segments=20, lat_seg=14)
    # 脸部（肤色，下半部分）
    face_v, face_f = make_ellipsoid(0.05, 0.035, 0.04, segments=16, lat_seg=10)
    face_v = translate(face_v, 0, -0.02, 0.035)
    # 头盔上的A字（用白色小方块拼）
    a_v, a_f = make_box(0.015, 0.02, 0.005)
    a_v = translate(a_v, 0, 0.03, 0.058)
    # 白色翅膀装饰（头盔两侧）
    wing_l_v, wing_l_f = make_ellipsoid(0.025, 0.015, 0.01, segments=10, lat_seg=8)
    wing_l_v = translate(wing_l_v, -0.055, 0.02, 0.02)
    wing_r_v, wing_r_f = make_ellipsoid(0.025, 0.015, 0.01, segments=10, lat_seg=8)
    wing_r_v = translate(wing_r_v, 0.055, 0.02, 0.02)

    head_parts = [(helmet_v, helmet_f), (face_v, face_f), (a_v, a_f),
                  (wing_l_v, wing_l_f), (wing_r_v, wing_r_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子
    neck_v, neck_f = make_cylinder(0.025, 0.035, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：蓝色上衣 + 白色星星 + 红白条纹腹部
    body_v, body_f = make_ellipsoid(0.11, 0.14, 0.07, segments=20, lat_seg=14)
    body_v = translate(body_v, 0, 0.01, 0)
    # 胸口白色星星（用多个小三角形拼，简化为星形）
    star_v, star_f = make_cylinder(0.02, 0.008, segments=5)
    star_v = rotate_x(star_v, 90)
    star_v = translate(star_v, 0, 0.05, 0.072)
    # 腹部红白条纹
    for i, y in enumerate([0.0, -0.02, -0.04, -0.06]):
        stripe_v, stripe_f = make_box(0.10, 0.015, 0.02)
        stripe_v = translate(stripe_v, 0, y, 0.065)
        if i == 0:
            stripe_parts = [(stripe_v, stripe_f)]
        else:
            stripe_parts.append((stripe_v, stripe_f))

    spine_parts = [(body_v, body_f), (star_v, star_f)] + stripe_parts
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：蓝色
    hips_v, hips_f = make_ellipsoid(0.09, 0.06, 0.06, segments=16, lat_seg=10)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：蓝色
    upper_arm_v, upper_arm_f = make_capsule(0.032, 0.22, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：红白条纹
    forearm_v, forearm_f = make_capsule(0.03, 0.20, segments=14, lat_seg=8)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：白色手套
    hand_v, hand_f = make_sphere(0.025, segments=12, lat_seg=8)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：蓝色
    thigh_v, thigh_f = make_capsule(0.035, 0.28, segments=14, lat_seg=8)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：蓝色 + 白色条纹
    shin_v, shin_f = make_capsule(0.032, 0.26, segments=14, lat_seg=8)
    parts['shin'] = (shin_v, shin_f)

    # 脚：红色靴子
    foot_v, foot_f = make_ellipsoid(0.03, 0.04, 0.07, segments=14, lat_seg=10)
    foot_v = translate(foot_v, 0, -0.01, 0.02)
    parts['foot'] = (foot_v, foot_f)

    # 盾牌（左手，圆形，红白蓝同心圆）
    shield_v, shield_f = make_cylinder(0.08, 0.01, segments=24)
    shield_v = rotate_y(shield_v, 90)
    shield_v = translate(shield_v, -0.12, 0.0, 0.0)
    parts['joint'] = (shield_v, shield_f)

    parts.update(make_ski_gear(foot_w=0.06))
    save_character(out_dir, 'captain_america', parts)


# ==================== 超人 ====================
def generate_superman(out_dir):
    """超人：蓝色紧身衣，红色披风，红色靴子，胸口S标志，黑色头发"""
    parts = {}

    # 头：白色皮肤 + 黑色卷发（前额一撮）+ 方下巴
    face_v, face_f = make_sphere(0.06, segments=20, lat_seg=14)
    # 黑色头发
    hair_v, hair_f = make_sphere(0.062, segments=18, lat_seg=12)
    hair_v = scale(hair_v, 1.05, 0.8, 1.0)
    hair_v = translate(hair_v, 0, 0.03, -0.01)
    # 前额标志性卷发
    curl_v, curl_f = make_sphere(0.012, segments=8, lat_seg=6)
    curl_v = translate(curl_v, 0, 0.025, 0.055)
    # 方下巴
    jaw_v, jaw_f = make_box(0.05, 0.025, 0.04)
    jaw_v = translate(jaw_v, 0, -0.04, 0.02)

    head_parts = [(face_v, face_f), (hair_v, hair_f), (curl_v, curl_f), (jaw_v, jaw_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子
    neck_v, neck_f = make_cylinder(0.025, 0.04, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：蓝色紧身衣 + 红色披风 + 胸口S标志（黄色菱形底+红色S）
    body_v, body_f = make_ellipsoid(0.11, 0.15, 0.07, segments=20, lat_seg=14)
    body_v = translate(body_v, 0, 0.01, 0)
    # 胸口黄色菱形
    emblem_v, emblem_f = make_cylinder(0.03, 0.008, segments=4)
    emblem_v = rotate_x(emblem_v, 45)
    emblem_v = rotate_y(emblem_v, 45)
    emblem_v = translate(emblem_v, 0, 0.05, 0.072)
    # 红色披风（大，从肩部向后垂下）
    cape_v, cape_f = make_box(0.20, 0.35, 0.012)
    cape_v = translate(cape_v, 0, -0.02, -0.08)
    # 披风肩部
    cape_shoulder_v, cape_shoulder_f = make_ellipsoid(0.11, 0.035, 0.04, segments=14, lat_seg=10)
    cape_shoulder_v = translate(cape_shoulder_v, 0, 0.10, -0.05)
    # 红色内裤外穿（标志性）
    briefs_v, briefs_f = make_ellipsoid(0.10, 0.04, 0.06, segments=16, lat_seg=10)
    briefs_v = translate(briefs_v, 0, -0.08, 0.01)

    spine_parts = [(body_v, body_f), (emblem_v, emblem_f), (cape_v, cape_f),
                    (cape_shoulder_v, cape_shoulder_f), (briefs_v, briefs_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：蓝色
    hips_v, hips_f = make_ellipsoid(0.09, 0.05, 0.06, segments=16, lat_seg=10)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：蓝色
    upper_arm_v, upper_arm_f = make_capsule(0.032, 0.24, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：蓝色
    forearm_v, forearm_f = make_capsule(0.03, 0.22, segments=14, lat_seg=8)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：红色
    hand_v, hand_f = make_sphere(0.025, segments=12, lat_seg=8)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：蓝色
    thigh_v, thigh_f = make_capsule(0.035, 0.30, segments=14, lat_seg=8)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：蓝色
    shin_v, shin_f = make_capsule(0.032, 0.28, segments=14, lat_seg=8)
    parts['shin'] = (shin_v, shin_f)

    # 脚：红色靴子
    foot_v, foot_f = make_ellipsoid(0.03, 0.045, 0.075, segments=14, lat_seg=10)
    foot_v = translate(foot_v, 0, -0.01, 0.02)
    parts['foot'] = (foot_v, foot_f)

    parts.update(make_ski_gear(foot_w=0.06))
    save_character(out_dir, 'superman', parts)


# ==================== 蜘蛛侠 ====================
def generate_spiderman(out_dir):
    """蜘蛛侠：红蓝配色，蛛网纹理，大眼睛面罩，蜘蛛标志"""
    parts = {}

    # 头：红色面罩 + 巨大白色眼睛（黑边）
    head_v, head_f = make_sphere(0.06, segments=20, lat_seg=14)
    # 巨大眼睛（白色，狭长，黑边）
    eye_l_v, eye_l_f = make_ellipsoid(0.022, 0.015, 0.008, segments=12, lat_seg=8)
    eye_l_v = rotate_z(eye_l_v, -10)
    eye_l_v = translate(eye_l_v, -0.022, 0.008, 0.055)
    eye_r_v, eye_r_f = make_ellipsoid(0.022, 0.015, 0.008, segments=12, lat_seg=8)
    eye_r_v = rotate_z(eye_r_v, 10)
    eye_r_v = translate(eye_r_v, 0.022, 0.008, 0.055)
    # 眼睛黑边
    eye_l_border_v, eye_l_border_f = make_ellipsoid(0.025, 0.018, 0.005, segments=12, lat_seg=8)
    eye_l_border_v = rotate_z(eye_l_border_v, -10)
    eye_l_border_v = translate(eye_l_border_v, -0.022, 0.008, 0.052)
    eye_r_border_v, eye_r_border_f = make_ellipsoid(0.025, 0.018, 0.005, segments=12, lat_seg=8)
    eye_r_border_v = rotate_z(eye_r_border_v, 10)
    eye_r_border_v = translate(eye_r_border_v, 0.022, 0.008, 0.052)

    head_parts = [(head_v, head_f), (eye_l_border_v, eye_l_border_f), (eye_r_border_v, eye_r_border_f),
                   (eye_l_v, eye_l_f), (eye_r_v, eye_r_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子
    neck_v, neck_f = make_cylinder(0.022, 0.035, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：红色上半 + 蓝色下半 + 胸口黑色蜘蛛标志
    body_v, body_f = make_ellipsoid(0.10, 0.14, 0.07, segments=20, lat_seg=14)
    body_v = translate(body_v, 0, 0.01, 0)
    # 红色上半胸
    chest_red_v, chest_red_f = make_ellipsoid(0.095, 0.07, 0.065, segments=18, lat_seg=10)
    chest_red_v = translate(chest_red_v, 0, 0.05, 0.01)
    # 胸口黑色蜘蛛标志（简化为蜘蛛形状）
    spider_body_v, spider_body_f = make_ellipsoid(0.012, 0.02, 0.005, segments=8, lat_seg=6)
    spider_body_v = translate(spider_body_v, 0, 0.04, 0.072)
    spider_head_v, spider_head_f = make_sphere(0.008, segments=8, lat_seg=6)
    spider_head_v = translate(spider_head_v, 0, 0.055, 0.073)
    # 蜘蛛腿（8条细线）
    for i, angle in enumerate([-60, -30, 30, 60]):
        leg_l_v, leg_l_f = make_box(0.003, 0.025, 0.003)
        leg_l_v = rotate_z(leg_l_v, angle)
        leg_l_v = translate(leg_l_v, -0.015, 0.045, 0.072)
        leg_r_v, leg_r_f = make_box(0.003, 0.025, 0.003)
        leg_r_v = rotate_z(leg_r_v, -angle)
        leg_r_v = translate(leg_r_v, 0.015, 0.045, 0.072)
        if i == 0:
            leg_parts = [(leg_l_v, leg_l_f), (leg_r_v, leg_r_f)]
        else:
            leg_parts.extend([(leg_l_v, leg_l_f), (leg_r_v, leg_r_f)])

    spine_parts = [(body_v, body_f), (chest_red_v, chest_red_f), (spider_body_v, spider_body_f),
                    (spider_head_v, spider_head_f)] + leg_parts
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：蓝色
    hips_v, hips_f = make_ellipsoid(0.085, 0.055, 0.06, segments=16, lat_seg=10)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：红色
    upper_arm_v, upper_arm_f = make_capsule(0.03, 0.22, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：蓝色
    forearm_v, forearm_f = make_capsule(0.028, 0.20, segments=14, lat_seg=8)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：红色
    hand_v, hand_f = make_sphere(0.022, segments=12, lat_seg=8)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：蓝色
    thigh_v, thigh_f = make_capsule(0.032, 0.28, segments=14, lat_seg=8)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：红色
    shin_v, shin_f = make_capsule(0.03, 0.26, segments=14, lat_seg=8)
    parts['shin'] = (shin_v, shin_f)

    # 脚：红色
    foot_v, foot_f = make_ellipsoid(0.028, 0.04, 0.07, segments=14, lat_seg=10)
    foot_v = translate(foot_v, 0, -0.01, 0.02)
    parts['foot'] = (foot_v, foot_f)

    parts.update(make_ski_gear(foot_w=0.055))
    save_character(out_dir, 'spiderman', parts)


# ==================== 闪电侠 ====================
def generate_flash(out_dir):
    """闪电侠：红色紧身衣，黄色闪电标志，黄色靴子，黄色面罩翅膀"""
    parts = {}

    # 头：红色面罩 + 黄色翅膀装饰（两侧）+ 白色眼睛
    head_v, head_f = make_sphere(0.058, segments=20, lat_seg=14)
    # 黄色翅膀装饰（面罩两侧，向后伸展）
    wing_l_v, wing_l_f = make_ellipsoid(0.04, 0.02, 0.015, segments=12, lat_seg=8)
    wing_l_v = rotate_z(wing_l_v, -20)
    wing_l_v = translate(wing_l_v, -0.06, 0.015, 0)
    wing_r_v, wing_r_f = make_ellipsoid(0.04, 0.02, 0.015, segments=12, lat_seg=8)
    wing_r_v = rotate_z(wing_r_v, 20)
    wing_r_v = translate(wing_r_v, 0.06, 0.015, 0)
    # 白色眼睛
    eye_l_v, eye_l_f = make_ellipsoid(0.015, 0.01, 0.006, segments=10, lat_seg=6)
    eye_l_v = translate(eye_l_v, -0.018, 0.005, 0.055)
    eye_r_v, eye_r_f = make_ellipsoid(0.015, 0.01, 0.006, segments=10, lat_seg=6)
    eye_r_v = translate(eye_r_v, 0.018, 0.005, 0.055)

    head_parts = [(head_v, head_f), (wing_l_v, wing_l_f), (wing_r_v, wing_r_f),
                   (eye_l_v, eye_l_f), (eye_r_v, eye_r_f)]
    parts['head'] = merge_meshes(head_parts)

    # 脖子
    neck_v, neck_f = make_cylinder(0.022, 0.035, segments=12)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：红色紧身衣 + 黄色闪电标志（胸口）
    body_v, body_f = make_ellipsoid(0.10, 0.14, 0.07, segments=20, lat_seg=14)
    body_v = translate(body_v, 0, 0.01, 0)
    # 黄色闪电标志（Z字形，用几个方块拼）
    bolt1_v, bolt1_f = make_box(0.015, 0.03, 0.008)
    bolt1_v = rotate_z(bolt1_v, -20)
    bolt1_v = translate(bolt1_v, -0.01, 0.05, 0.072)
    bolt2_v, bolt2_f = make_box(0.015, 0.03, 0.008)
    bolt2_v = rotate_z(bolt2_v, 20)
    bolt2_v = translate(bolt2_v, 0.01, 0.025, 0.072)
    bolt3_v, bolt3_f = make_box(0.012, 0.02, 0.008)
    bolt3_v = rotate_z(bolt3_v, -20)
    bolt3_v = translate(bolt3_v, 0.005, 0.005, 0.072)

    spine_parts = [(body_v, body_f), (bolt1_v, bolt1_f), (bolt2_v, bolt2_f), (bolt3_v, bolt3_f)]
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：红色
    hips_v, hips_f = make_ellipsoid(0.085, 0.055, 0.06, segments=16, lat_seg=10)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：红色
    upper_arm_v, upper_arm_f = make_capsule(0.03, 0.22, segments=14, lat_seg=8)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：黄色
    forearm_v, forearm_f = make_capsule(0.028, 0.20, segments=14, lat_seg=8)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：红色
    hand_v, hand_f = make_sphere(0.022, segments=12, lat_seg=8)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：红色
    thigh_v, thigh_f = make_capsule(0.032, 0.28, segments=14, lat_seg=8)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：黄色
    shin_v, shin_f = make_capsule(0.03, 0.26, segments=14, lat_seg=8)
    parts['shin'] = (shin_v, shin_f)

    # 脚：黄色靴子
    foot_v, foot_f = make_ellipsoid(0.028, 0.04, 0.07, segments=14, lat_seg=10)
    foot_v = translate(foot_v, 0, -0.01, 0.02)
    parts['foot'] = (foot_v, foot_f)

    parts.update(make_ski_gear(foot_w=0.055))
    save_character(out_dir, 'flash', parts)


# ==================== 毒液 ====================
def generate_venom(out_dir):
    """毒液：黑色共生体，白色蜘蛛标志，白色眼睛，巨大舌头，尖牙"""
    parts = {}

    # 头：黑色共生体 + 巨大白色眼睛（狭长倾斜）+ 尖牙 + 长舌头
    head_v, head_f = make_sphere(0.065, segments=20, lat_seg=14)
    # 巨大白色眼睛（狭长，倾斜，邪恶）
    eye_l_v, eye_l_f = make_ellipsoid(0.025, 0.012, 0.008, segments=12, lat_seg=8)
    eye_l_v = rotate_z(eye_l_v, -25)
    eye_l_v = translate(eye_l_v, -0.022, 0.01, 0.058)
    eye_r_v, eye_r_f = make_ellipsoid(0.025, 0.012, 0.008, segments=12, lat_seg=8)
    eye_r_v = rotate_z(eye_r_v, 25)
    eye_r_v = translate(eye_r_v, 0.022, 0.01, 0.058)
    # 尖牙（上排几颗）
    for i, x in enumerate([-0.02, -0.01, 0, 0.01, 0.02]):
        fang_v, fang_f = make_cone(0.004, 0.012, segments=6)
        fang_v = translate(fang_v, x, -0.02, 0.06)
        if i == 0:
            fang_parts = [(fang_v, fang_f)]
        else:
            fang_parts.append((fang_v, fang_f))
    # 长舌头（从嘴中伸出，粉红色，长而卷曲）
    tongue_v, tongue_f = make_capsule(0.008, 0.06, segments=10, lat_seg=6)
    tongue_v = rotate_x(tongue_v, 30)
    tongue_v = translate(tongue_v, 0, -0.04, 0.08)

    head_parts = [(head_v, head_f), (eye_l_v, eye_l_f), (eye_r_v, eye_r_f),
                   (tongue_v, tongue_f)] + fang_parts
    parts['head'] = merge_meshes(head_parts)

    # 脖子（粗壮黑色）
    neck_v, neck_f = make_cylinder(0.03, 0.04, segments=14)
    parts['neck'] = (neck_v, neck_f)

    # 躯干：黑色共生体肌肉 + 白色蜘蛛标志（大，覆盖胸口）
    body_v, body_f = make_ellipsoid(0.12, 0.16, 0.08, segments=22, lat_seg=16)
    body_v = translate(body_v, 0, 0.01, 0)
    # 胸肌（黑色凸起）
    pec_l_v, pec_l_f = make_ellipsoid(0.055, 0.045, 0.035, segments=14, lat_seg=10)
    pec_l_v = translate(pec_l_v, -0.04, 0.05, 0.06)
    pec_r_v, pec_r_f = make_ellipsoid(0.055, 0.045, 0.035, segments=14, lat_seg=10)
    pec_r_v = translate(pec_r_v, 0.04, 0.05, 0.06)
    # 白色蜘蛛标志（大，覆盖胸口腹部）
    spider_body_v, spider_body_f = make_ellipsoid(0.02, 0.035, 0.006, segments=10, lat_seg=8)
    spider_body_v = translate(spider_body_v, 0, 0.02, 0.075)
    spider_head_v, spider_head_f = make_sphere(0.012, segments=10, lat_seg=8)
    spider_head_v = translate(spider_head_v, 0, 0.05, 0.076)
    # 蜘蛛腿（8条，长而弯曲）
    for i, angle in enumerate([-70, -45, -20, 20, 45, 70]):
        leg_v, leg_f = make_box(0.004, 0.04, 0.004)
        leg_v = rotate_z(leg_v, angle)
        x_offset = -0.02 if angle < 0 else 0.02
        leg_v = translate(leg_v, x_offset, 0.03, 0.075)
        if i == 0:
            leg_parts = [(leg_v, leg_f)]
        else:
            leg_parts.append((leg_v, leg_f))

    spine_parts = [(body_v, body_f), (pec_l_v, pec_l_f), (pec_r_v, pec_r_f),
                    (spider_body_v, spider_body_f), (spider_head_v, spider_head_f)] + leg_parts
    parts['spine'] = merge_meshes(spine_parts)

    # 骨盆：黑色
    hips_v, hips_f = make_ellipsoid(0.10, 0.06, 0.07, segments=16, lat_seg=10)
    parts['hips'] = (hips_v, hips_f)

    # 上臂：黑色粗壮
    upper_arm_v, upper_arm_f = make_capsule(0.04, 0.25, segments=16, lat_seg=10)
    parts['upper_arm'] = (upper_arm_v, upper_arm_f)

    # 前臂：更粗壮
    forearm_v, forearm_f = make_capsule(0.045, 0.22, segments=16, lat_seg=10)
    parts['forearm'] = (forearm_v, forearm_f)

    # 手：巨大黑色爪子
    hand_v, hand_f = make_sphere(0.035, segments=14, lat_seg=10)
    parts['hand'] = (hand_v, hand_f)

    # 大腿：黑色粗壮
    thigh_v, thigh_f = make_capsule(0.045, 0.30, segments=16, lat_seg=10)
    parts['thigh'] = (thigh_v, thigh_f)

    # 小腿：黑色
    shin_v, shin_f = make_capsule(0.04, 0.28, segments=16, lat_seg=10)
    parts['shin'] = (shin_v, shin_f)

    # 脚：巨大黑色
    foot_v, foot_f = make_ellipsoid(0.035, 0.05, 0.08, segments=14, lat_seg=10)
    foot_v = translate(foot_v, 0, -0.01, 0.02)
    parts['foot'] = (foot_v, foot_f)

    parts.update(make_ski_gear(foot_w=0.07))
    save_character(out_dir, 'venom', parts)


# ==================== 主函数 ====================
def main():
    print("=" * 60)
    print("超级英雄人偶生成器")
    print("=" * 60)

    generate_iron_man(os.path.join(BASE_DIR, 'iron_man'))
    generate_hulk(os.path.join(BASE_DIR, 'hulk'))
    generate_doctor_strange(os.path.join(BASE_DIR, 'doctor_strange'))
    generate_captain_america(os.path.join(BASE_DIR, 'captain_america'))
    generate_superman(os.path.join(BASE_DIR, 'superman'))
    generate_spiderman(os.path.join(BASE_DIR, 'spiderman'))
    generate_flash(os.path.join(BASE_DIR, 'flash'))
    generate_venom(os.path.join(BASE_DIR, 'venom'))

    print("\n" + "=" * 60)
    print("全部超级英雄生成完成！")
    print(f"模型目录: {BASE_DIR}")
    print("  iron_man/          - 钢铁侠（红金盔甲，反应炉）")
    print("  hulk/               - 绿巨人（绿色肌肉，紫色裤子）")
    print("  doctor_strange/     - 奇异博士（红色披风，阿戈摩托之眼）")
    print("  captain_america/    - 美国队长（蓝白红，盾牌，A字头盔）")
    print("  superman/           - 超人（蓝色紧身衣，红色披风，S标志）")
    print("  spiderman/          - 蜘蛛侠（红蓝配色，大眼睛，蜘蛛标志）")
    print("  flash/              - 闪电侠（红色，黄色闪电，翅膀面罩）")
    print("  venom/              - 毒液（黑色共生体，白色蜘蛛，长舌头）")
    print("=" * 60)


if __name__ == '__main__':
    main()
