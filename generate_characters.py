"""
经典人物人偶生成器
在基础滑雪者人偶上添加特色装饰部件（皇冠、蝴蝶结、翅膀、眼镜等）
生成白雪公主、唐老鸭、巴斯光年、米老鼠、大力水手、国王、哈利波特
"""
import os
import numpy as np
from stl import mesh
import sys

# 导入generate_models.py中的基础几何体函数
sys.path.insert(0, r'D:\PyPrjs\SyntrakView')
from generate_models import (
    make_box, make_cylinder, make_capsule, make_sphere, make_torus,
    merge_meshes, save_stl, translate, scale, rotate_y, BASE_DIR
)


def generate_character(out_dir, name, body_params, extras_func=None):
    """
    生成经典人物人偶
    body_params: 基础体型参数（同generate_models.py中的参数字典）
    extras_func: 额外装饰部件生成函数，返回额外的几何体列表 [(vertices, faces, stl_name), ...]
                 或者返回一个字典，覆盖某些部位的STL
    """
    os.makedirs(out_dir, exist_ok=True)
    print(f"\n=== 生成 {name} -> {out_dir} ===")

    # 生成基础部位
    parts = {}

    # 头
    head_r = body_params['head_r']
    face_v, face_f = make_sphere(head_r, segments=20, lat_seg=14)
    helmet_v, helmet_f = make_sphere(head_r * 1.1, segments=20, lat_seg=10)
    helmet_v = scale(helmet_v, 1.05, 0.72, 1.05)
    helmet_v = translate(helmet_v, 0, head_r * 0.45, 0)
    head_parts = [(face_v, face_f), (helmet_v, helmet_f)]

    # 如果有额外的头部装饰
    if extras_func:
        extra_head = extras_func('head', body_params)
        if extra_head:
            head_parts.extend(extra_head)

    head_v, head_f = merge_meshes(head_parts)
    parts['head'] = (head_v, head_f)
    print(f"  head.stl: {len(head_f)} triangles")

    # 脖子
    v, f = make_cylinder(body_params['neck_r'], body_params['neck_h'], segments=16)
    parts['neck'] = (v, f)

    # 躯干
    chest_v, chest_f = make_box(body_params['chest_w'], body_params['chest_h'], body_params['chest_d'])
    chest_v = translate(chest_v, 0, body_params['chest_h'] * 0.4 + body_params.get('hunch', 0), 0)
    sh_l_v, sh_l_f = make_sphere(body_params['shoulder_w'] * 0.22, segments=14, lat_seg=10)
    sh_l_v = translate(sh_l_v, -body_params['chest_w'] * 0.52, body_params['chest_h'] * 0.7 + body_params.get('hunch', 0), 0)
    sh_r_v, sh_r_f = make_sphere(body_params['shoulder_w'] * 0.22, segments=14, lat_seg=10)
    sh_r_v = translate(sh_r_v, body_params['chest_w'] * 0.52, body_params['chest_h'] * 0.7 + body_params.get('hunch', 0), 0)
    waist_v, waist_f = make_box(body_params['waist_w'], body_params['waist_h'], body_params['waist_d'])
    waist_v = translate(waist_v, 0, -body_params['waist_h'] * 0.5, 0)

    spine_parts = [(chest_v, chest_f), (sh_l_v, sh_l_f), (sh_r_v, sh_r_f), (waist_v, waist_f)]

    # 女性特征
    if body_params.get('female', False):
        bust_l_v, bust_l_f = make_sphere(body_params['chest_w'] * 0.16, segments=14, lat_seg=10)
        bust_l_v = translate(bust_l_v, -body_params['chest_w'] * 0.2, body_params['chest_h'] * 0.25, body_params['chest_d'] * 0.45)
        bust_r_v, bust_r_f = make_sphere(body_params['chest_w'] * 0.16, segments=14, lat_seg=10)
        bust_r_v = translate(bust_r_v, body_params['chest_w'] * 0.2, body_params['chest_h'] * 0.25, body_params['chest_d'] * 0.45)
        spine_parts.extend([(bust_l_v, bust_l_f), (bust_r_v, bust_r_f)])

    # 额外的躯干装饰
    if extras_func:
        extra_spine = extras_func('spine', body_params)
        if extra_spine:
            spine_parts.extend(extra_spine)

    spine_v, spine_f = merge_meshes(spine_parts)
    parts['spine'] = (spine_v, spine_f)
    print(f"  spine.stl: {len(spine_f)} triangles")

    # 骨盆
    v, f = make_box(body_params['hip_w'], body_params['hip_h'], body_params['hip_d'])
    parts['hips'] = (v, f)

    # 上臂
    v, f = make_capsule(body_params['upper_arm_r'], body_params['upper_arm_l'], segments=18, lat_seg=10)
    parts['upper_arm'] = (v, f)

    # 前臂
    v, f = make_capsule(body_params['forearm_r'], body_params['forearm_l'], segments=18, lat_seg=10)
    parts['forearm'] = (v, f)

    # 手
    palm_v, palm_f = make_box(body_params['hand_w'], body_params['hand_h'], body_params['hand_d'])
    palm_v = translate(palm_v, 0, -body_params['hand_h'] * 0.2, 0)
    thumb_v, thumb_f = make_capsule(body_params['hand_w'] * 0.24, body_params['hand_h'] * 0.8, segments=10, lat_seg=6)
    thumb_v = rotate_y(thumb_v, -30)
    thumb_v = translate(thumb_v, -body_params['hand_w'] * 0.6, -body_params['hand_h'] * 0.4, body_params['hand_d'] * 0.2)
    fingers_v, fingers_f = make_box(body_params['hand_w'] * 0.8, body_params['hand_h'] * 0.7, body_params['hand_d'] * 0.9)
    fingers_v = translate(fingers_v, 0, -body_params['hand_h'] * 0.9, 0)
    hand_parts = [(palm_v, palm_f), (thumb_v, thumb_f), (fingers_v, fingers_f)]

    if extras_func:
        extra_hand = extras_func('hand', body_params)
        if extra_hand:
            hand_parts.extend(extra_hand)

    hand_v, hand_f = merge_meshes(hand_parts)
    parts['hand'] = (hand_v, hand_f)

    # 大腿
    v, f = make_capsule(body_params['thigh_r'], body_params['thigh_l'], segments=18, lat_seg=10)
    parts['thigh'] = (v, f)

    # 小腿
    v, f = make_capsule(body_params['shin_r'], body_params['shin_l'], segments=18, lat_seg=10)
    parts['shin'] = (v, f)

    # 脚
    boot_v, boot_f = make_box(body_params['foot_w'], body_params['foot_h'], body_params['foot_d'])
    boot_v = translate(boot_v, 0, 0, body_params['foot_d'] * 0.18)
    toe_v, toe_f = make_box(body_params['foot_w'] * 0.9, body_params['foot_h'] * 0.55, body_params['foot_d'] * 0.45)
    toe_v = translate(toe_v, 0, -body_params['foot_h'] * 0.24, body_params['foot_d'] * 0.65)
    heel_v, heel_f = make_box(body_params['foot_w'] * 0.85, body_params['foot_h'] * 0.55, body_params['foot_d'] * 0.4)
    heel_v = translate(heel_v, 0, -body_params['foot_h'] * 0.24, -body_params['foot_d'] * 0.35)
    foot_parts = [(boot_v, boot_f), (toe_v, toe_f), (heel_v, heel_f)]

    if extras_func:
        extra_foot = extras_func('foot', body_params)
        if extra_foot:
            foot_parts.extend(extra_foot)

    foot_v, foot_f = merge_meshes(foot_parts)
    parts['foot'] = (foot_v, foot_f)
    print(f"  foot.stl: {len(foot_f)} triangles")

    # 滑雪板
    ski_body_v, ski_body_f = make_box(body_params['foot_w'] * 1.2, 0.008, 0.9)
    tip_v, tip_f = make_box(body_params['foot_w'] * 1.2, 0.008, 0.12)
    tip_v = tip_v @ np.array([[1,0,0],[0,np.cos(np.radians(15)),-np.sin(np.radians(15))],[0,np.sin(np.radians(15)),np.cos(np.radians(15))]]).T
    tip_v = translate(tip_v, 0, 0.015, 0.5)
    tail_v, tail_f = make_box(body_params['foot_w'] * 1.2, 0.008, 0.08)
    tail_v = translate(tail_v, 0, 0, -0.48)
    ski_v, ski_f = merge_meshes([(ski_body_v, ski_body_f), (tip_v, tip_f), (tail_v, tail_f)])
    parts['ski'] = (ski_v, ski_f)

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
    parts['pole'] = (pole_v, pole_f)

    # 关节球
    v, f = make_sphere(0.03, segments=14, lat_seg=10)
    parts['joint'] = (v, f)

    # 保存所有部位
    total = 0
    for part_name, (v, f) in parts.items():
        n = save_stl(os.path.join(out_dir, f'{part_name}.stl'), v, f)
        total += n

    print(f"  {name} 总计: {total} triangles")
    return total


# ==================== 经典人物定义 ====================

# 白雪公主：蓝色上衣、黄色裙子、红色蝴蝶结、黑色头发
def snow_white_extras(part, params):
    if part == 'head':
        extras = []
        # 黑色头发（覆盖头盔，改为黑色球体）
        hair_v, hair_f = make_sphere(params['head_r'] * 1.08, segments=18, lat_seg=12)
        hair_v = scale(hair_v, 1.02, 0.85, 1.02)
        hair_v = translate(hair_v, 0, params['head_r'] * 0.3, 0)
        extras.append((hair_v, hair_f))
        # 红色蝴蝶结
        bow_l_v, bow_l_f = make_sphere(0.02, segments=10, lat_seg=8)
        bow_l_v = scale(bow_l_v, 1.5, 0.8, 0.5)
        bow_l_v = translate(bow_l_v, -0.025, params['head_r'] * 0.85, 0)
        bow_r_v, bow_r_f = make_sphere(0.02, segments=10, lat_seg=8)
        bow_r_v = scale(bow_r_v, 1.5, 0.8, 0.5)
        bow_r_v = translate(bow_r_v, 0.025, params['head_r'] * 0.85, 0)
        bow_center_v, bow_center_f = make_sphere(0.012, segments=8, lat_seg=6)
        bow_center_v = translate(bow_center_v, 0, params['head_r'] * 0.85, 0)
        extras.extend([(bow_l_v, bow_l_f), (bow_r_v, bow_r_f), (bow_center_v, bow_center_f)])
        return extras
    elif part == 'spine':
        extras = []
        # 黄色裙子（腰部以下加宽，类似裙摆）
        skirt_v, skirt_f = make_cylinder(params['hip_w'] * 0.75, 0.25, segments=20)
        skirt_v = scale(skirt_v, 1.0, 1.0, 1.3)
        skirt_v = translate(skirt_v, 0, -0.18, 0)
        extras.append((skirt_v, skirt_f))
        return extras
    return None

SNOW_WHITE = {
    'name': 'snow_white',
    'head_r': 0.06, 'neck_r': 0.024, 'neck_h': 0.045,
    'chest_w': 0.20, 'chest_h': 0.18, 'chest_d': 0.12, 'shoulder_w': 0.20,
    'waist_w': 0.15, 'waist_h': 0.11, 'waist_d': 0.10,
    'hip_w': 0.19, 'hip_h': 0.09, 'hip_d': 0.12,
    'upper_arm_r': 0.027, 'upper_arm_l': 0.25,
    'forearm_r': 0.024, 'forearm_l': 0.23,
    'hand_w': 0.044, 'hand_h': 0.046, 'hand_d': 0.040,
    'thigh_r': 0.033, 'thigh_l': 0.37,
    'shin_r': 0.028, 'shin_l': 0.35,
    'foot_w': 0.065, 'foot_h': 0.070, 'foot_d': 0.105,
    'hunch': 0, 'female': True, 'kid': False,
}

# 唐老鸭：白色大头、黄色大嘴、蓝色水手服
def donald_duck_extras(part, params):
    if part == 'head':
        extras = []
        # 黄色大嘴
        beak_v, beak_f = make_box(0.05, 0.035, 0.06)
        beak_v = translate(beak_v, 0, -0.005, params['head_r'] * 0.9)
        extras.append((beak_v, beak_f))
        # 水手帽
        hat_v, hat_f = make_cylinder(params['head_r'] * 0.85, 0.025, segments=16)
        hat_v = translate(hat_v, 0, params['head_r'] * 0.75, 0)
        hat_brim_v, hat_brim_f = make_cylinder(params['head_r'] * 1.1, 0.008, segments=16)
        hat_brim_v = translate(hat_brim_v, 0, params['head_r'] * 0.65, 0)
        extras.extend([(hat_v, hat_f), (hat_brim_v, hat_brim_f)])
        return extras
    elif part == 'spine':
        extras = []
        # 白色腹部（胸前白色椭圆）
        belly_v, belly_f = make_sphere(0.05, segments=14, lat_seg=10)
        belly_v = scale(belly_v, 1.2, 1.5, 0.5)
        belly_v = translate(belly_v, 0, 0, params['chest_d'] * 0.55)
        extras.append((belly_v, belly_f))
        return extras
    elif part == 'foot':
        extras = []
        # 黄色大脚（脚放大）
        return extras
    return None

DONALD_DUCK = {
    'name': 'donald_duck',
    'head_r': 0.07, 'neck_r': 0.026, 'neck_h': 0.04,
    'chest_w': 0.22, 'chest_h': 0.19, 'chest_d': 0.15, 'shoulder_w': 0.22,
    'waist_w': 0.20, 'waist_h': 0.12, 'waist_d': 0.14,
    'hip_w': 0.20, 'hip_h': 0.09, 'hip_d': 0.14,
    'upper_arm_r': 0.030, 'upper_arm_l': 0.24,
    'forearm_r': 0.027, 'forearm_l': 0.22,
    'hand_w': 0.050, 'hand_h': 0.050, 'hand_d': 0.045,
    'thigh_r': 0.036, 'thigh_l': 0.34,
    'shin_r': 0.031, 'shin_l': 0.32,
    'foot_w': 0.085, 'foot_h': 0.075, 'foot_d': 0.13,
    'hunch': 0, 'female': False, 'kid': False,
}

# 巴斯光年：白色太空服、绿色紫色装饰、头盔、翅膀
def buzz_lightyear_extras(part, params):
    if part == 'head':
        extras = []
        # 透明头盔（白色大球体）
        helmet_v, helmet_f = make_sphere(params['head_r'] * 1.25, segments=18, lat_seg=12)
        helmet_v = translate(helmet_v, 0, 0.01, 0)
        extras.append((helmet_v, helmet_f))
        return extras
    elif part == 'spine':
        extras = []
        # 胸前控制面板
        panel_v, panel_f = make_box(0.08, 0.06, 0.01)
        panel_v = translate(panel_v, 0, 0.02, params['chest_d'] * 0.55)
        extras.append((panel_v, panel_f))
        # 翅膀（背部）
        wing_l_v, wing_l_f = make_box(0.02, 0.25, 0.12)
        wing_l_v = translate(wing_l_v, -0.12, 0.05, -params['chest_d'] * 0.4)
        wing_r_v, wing_r_f = make_box(0.02, 0.25, 0.12)
        wing_r_v = translate(wing_r_v, 0.12, 0.05, -params['chest_d'] * 0.4)
        extras.extend([(wing_l_v, wing_l_f), (wing_r_v, wing_r_f)])
        return extras
    return None

BUZZ_LIGHTYEAR = {
    'name': 'buzz_lightyear',
    'head_r': 0.06, 'neck_r': 0.028, 'neck_h': 0.04,
    'chest_w': 0.24, 'chest_h': 0.21, 'chest_d': 0.15, 'shoulder_w': 0.26,
    'waist_w': 0.20, 'waist_h': 0.13, 'waist_d': 0.13,
    'hip_w': 0.21, 'hip_h': 0.10, 'hip_d': 0.14,
    'upper_arm_r': 0.035, 'upper_arm_l': 0.27,
    'forearm_r': 0.032, 'forearm_l': 0.25,
    'hand_w': 0.052, 'hand_h': 0.052, 'hand_d': 0.047,
    'thigh_r': 0.040, 'thigh_l': 0.38,
    'shin_r': 0.034, 'shin_l': 0.36,
    'foot_w': 0.078, 'foot_h': 0.080, 'foot_d': 0.12,
    'hunch': 0, 'female': False, 'kid': False,
}

# 米老鼠：黑色大圆耳朵、红色短裤、黄色鞋子、白色手套
def mickey_mouse_extras(part, params):
    if part == 'head':
        extras = []
        # 两个大圆耳朵
        ear_l_v, ear_l_f = make_sphere(0.035, segments=14, lat_seg=10)
        ear_l_v = translate(ear_l_v, -params['head_r'] * 0.85, params['head_r'] * 0.6, 0)
        ear_r_v, ear_r_f = make_sphere(0.035, segments=14, lat_seg=10)
        ear_r_v = translate(ear_r_v, params['head_r'] * 0.85, params['head_r'] * 0.6, 0)
        extras.extend([(ear_l_v, ear_l_f), (ear_r_v, ear_r_f)])
        return extras
    elif part == 'spine':
        extras = []
        # 红色短裤（腰部红色）
        shorts_v, shorts_f = make_box(params['hip_w'] * 0.95, 0.10, params['hip_d'] * 1.05)
        shorts_v = translate(shorts_v, 0, -0.08, 0)
        extras.append((shorts_v, shorts_f))
        return extras
    elif part == 'hand':
        extras = []
        # 白色大手套（手放大）
        return extras
    return None

MICKEY_MOUSE = {
    'name': 'mickey_mouse',
    'head_r': 0.06, 'neck_r': 0.024, 'neck_h': 0.035,
    'chest_w': 0.20, 'chest_h': 0.17, 'chest_d': 0.13, 'shoulder_w': 0.21,
    'waist_w': 0.17, 'waist_h': 0.10, 'waist_d': 0.11,
    'hip_w': 0.18, 'hip_h': 0.08, 'hip_d': 0.12,
    'upper_arm_r': 0.028, 'upper_arm_l': 0.23,
    'forearm_r': 0.025, 'forearm_l': 0.21,
    'hand_w': 0.056, 'hand_h': 0.054, 'hand_d': 0.050,
    'thigh_r': 0.032, 'thigh_l': 0.32,
    'shin_r': 0.027, 'shin_l': 0.30,
    'foot_w': 0.080, 'foot_h': 0.072, 'foot_d': 0.125,
    'hunch': 0, 'female': False, 'kid': False,
}

# 大力水手：水手服、烟斗、强壮前臂、水手帽
def popeye_extras(part, params):
    if part == 'head':
        extras = []
        # 烟斗（嘴边）
        pipe_v, pipe_f = make_cylinder(0.006, 0.04, segments=8)
        pipe_v = rotate_y(pipe_v, 90)
        pipe_v = translate(pipe_v, params['head_r'] * 0.7, -0.01, params['head_r'] * 0.6)
        extras.append((pipe_v, pipe_f))
        # 水手帽
        hat_v, hat_f = make_cylinder(params['head_r'] * 0.9, 0.03, segments=16)
        hat_v = translate(hat_v, 0, params['head_r'] * 0.7, 0)
        hat_brim_v, hat_brim_f = make_cylinder(params['head_r'] * 1.15, 0.008, segments=16)
        hat_brim_v = translate(hat_brim_v, 0, params['head_r'] * 0.6, 0)
        extras.extend([(hat_v, hat_f), (hat_brim_v, hat_brim_f)])
        return extras
    return None

POPEYE = {
    'name': 'popeye',
    'head_r': 0.058, 'neck_r': 0.030, 'neck_h': 0.04,
    'chest_w': 0.25, 'chest_h': 0.20, 'chest_d': 0.15, 'shoulder_w': 0.26,
    'waist_w': 0.21, 'waist_h': 0.12, 'waist_d': 0.13,
    'hip_w': 0.21, 'hip_h': 0.09, 'hip_d': 0.13,
    'upper_arm_r': 0.040, 'upper_arm_l': 0.26,
    'forearm_r': 0.045, 'forearm_l': 0.24,  # 强壮前臂
    'hand_w': 0.058, 'hand_h': 0.056, 'hand_d': 0.052,
    'thigh_r': 0.038, 'thigh_l': 0.36,
    'shin_r': 0.033, 'shin_l': 0.34,
    'foot_w': 0.075, 'foot_h': 0.075, 'foot_d': 0.115,
    'hunch': 0, 'female': False, 'kid': False,
}

# 国王：皇冠、长袍、权杖、胡子
def king_extras(part, params):
    if part == 'head':
        extras = []
        # 皇冠
        crown_v, crown_f = make_cylinder(params['head_r'] * 0.85, 0.05, segments=8)
        crown_v = translate(crown_v, 0, params['head_r'] * 0.8, 0)
        # 皇冠尖顶
        for i in range(4):
            angle = i * np.pi / 2
            tip_v, tip_f = make_cone(0.012, 0.025)
            x = params['head_r'] * 0.6 * np.cos(angle)
            z = params['head_r'] * 0.6 * np.sin(angle)
            tip_v = translate(tip_v, x, params['head_r'] * 1.05, z)
            extras.append((tip_v, tip_f))
        extras.append((crown_v, crown_f))
        # 大胡子
        beard_v, beard_f = make_sphere(0.04, segments=14, lat_seg=10)
        beard_v = scale(beard_v, 1.2, 1.5, 0.8)
        beard_v = translate(beard_v, 0, -params['head_r'] * 0.5, params['head_r'] * 0.5)
        extras.append((beard_v, beard_f))
        return extras
    elif part == 'spine':
        extras = []
        # 长袍（身体加宽加长）
        robe_v, robe_f = make_cylinder(params['hip_w'] * 0.8, 0.4, segments=20)
        robe_v = scale(robe_v, 1.1, 1.0, 1.2)
        robe_v = translate(robe_v, 0, -0.15, 0)
        extras.append((robe_v, robe_f))
        return extras
    elif part == 'hand':
        extras = []
        # 权杖（右手）
        staff_v, staff_f = make_cylinder(0.008, 0.5, segments=10)
        staff_v = translate(staff_v, 0, 0.1, 0)
        staff_top_v, staff_top_f = make_sphere(0.02, segments=12, lat_seg=8)
        staff_top_v = translate(staff_top_v, 0, 0.35, 0)
        extras.extend([(staff_v, staff_f), (staff_top_v, staff_top_f)])
        return extras
    return None

def make_cone(radius, height, segments=12):
    """生成圆锥体"""
    vertices = []
    faces = []
    h = height / 2
    vertices.append([0, h, 0])  # 顶点
    vertices.append([0, -h, 0])  # 底中心
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), -h, radius * np.sin(angle)])
    for i in range(segments):
        i0, i1 = 2 + i, 2 + (i + 1) % segments
        faces.append([0, i1, i0])  # 侧面
        faces.append([1, i0, i1])  # 底面
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)

KING = {
    'name': 'king',
    'head_r': 0.062, 'neck_r': 0.028, 'neck_h': 0.04,
    'chest_w': 0.26, 'chest_h': 0.22, 'chest_d': 0.17, 'shoulder_w': 0.26,
    'waist_w': 0.24, 'waist_h': 0.14, 'waist_d': 0.16,
    'hip_w': 0.24, 'hip_h': 0.10, 'hip_d': 0.16,
    'upper_arm_r': 0.034, 'upper_arm_l': 0.26,
    'forearm_r': 0.030, 'forearm_l': 0.24,
    'hand_w': 0.054, 'hand_h': 0.054, 'hand_d': 0.050,
    'thigh_r': 0.042, 'thigh_l': 0.38,
    'shin_r': 0.036, 'shin_l': 0.36,
    'foot_w': 0.080, 'foot_h': 0.080, 'foot_d': 0.12,
    'hunch': 0.01, 'female': False, 'kid': False,
}

# 哈利波特：圆框眼镜、黑色长袍、红色围巾、魔杖
def harry_potter_extras(part, params):
    if part == 'head':
        extras = []
        # 圆框眼镜（两个圆环）
        glass_l_v, glass_l_f = make_torus(0.018, 0.003, major_seg=16, minor_seg=6)
        glass_l_v = rotate_y(glass_l_v, 90)
        glass_l_v = translate(glass_l_v, -0.02, 0.005, params['head_r'] * 0.85)
        glass_r_v, glass_r_f = make_torus(0.018, 0.003, major_seg=16, minor_seg=6)
        glass_r_v = rotate_y(glass_r_v, 90)
        glass_r_v = translate(glass_r_v, 0.02, 0.005, params['head_r'] * 0.85)
        # 眼镜鼻梁
        bridge_v, bridge_f = make_box(0.012, 0.004, 0.004)
        bridge_v = translate(bridge_v, 0, 0.005, params['head_r'] * 0.85)
        extras.extend([(glass_l_v, glass_l_f), (glass_r_v, glass_r_f), (bridge_v, bridge_f)])
        # 黑色乱发（头顶不规则球体）
        hair_v, hair_f = make_sphere(params['head_r'] * 1.05, segments=16, lat_seg=10)
        hair_v = scale(hair_v, 1.0, 0.7, 1.0)
        hair_v = translate(hair_v, 0, params['head_r'] * 0.4, 0)
        extras.append((hair_v, hair_f))
        return extras
    elif part == 'spine':
        extras = []
        # 红色围巾
        scarf_v, scarf_f = make_box(params['chest_w'] * 0.7, 0.04, params['chest_d'] * 0.9)
        scarf_v = translate(scarf_v, 0, params['chest_h'] * 0.45, 0)
        extras.append((scarf_v, scarf_f))
        return extras
    elif part == 'hand':
        extras = []
        # 魔杖（右手）
        wand_v, wand_f = make_cylinder(0.004, 0.28, segments=8)
        wand_v = translate(wand_v, 0, -0.05, 0)
        extras.append((wand_v, wand_f))
        return extras
    return None

HARRY_POTTER = {
    'name': 'harry_potter',
    'head_r': 0.058, 'neck_r': 0.022, 'neck_h': 0.045,
    'chest_w': 0.19, 'chest_h': 0.18, 'chest_d': 0.12, 'shoulder_w': 0.20,
    'waist_w': 0.16, 'waist_h': 0.11, 'waist_d': 0.10,
    'hip_w': 0.17, 'hip_h': 0.085, 'hip_d': 0.11,
    'upper_arm_r': 0.025, 'upper_arm_l': 0.25,
    'forearm_r': 0.022, 'forearm_l': 0.23,
    'hand_w': 0.042, 'hand_h': 0.046, 'hand_d': 0.038,
    'thigh_r': 0.030, 'thigh_l': 0.36,
    'shin_r': 0.026, 'shin_l': 0.34,
    'foot_w': 0.062, 'foot_h': 0.066, 'foot_d': 0.10,
    'hunch': 0, 'female': False, 'kid': True,
}


# ==================== 主入口 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("经典人物人偶生成器")
    print("=" * 60)

    characters = [
        (SNOW_WHITE, snow_white_extras),
        (DONALD_DUCK, donald_duck_extras),
        (BUZZ_LIGHTYEAR, buzz_lightyear_extras),
        (MICKEY_MOUSE, mickey_mouse_extras),
        (POPEYE, popeye_extras),
        (KING, king_extras),
        (HARRY_POTTER, harry_potter_extras),
    ]

    for params, extras_func in characters:
        generate_character(
            os.path.join(BASE_DIR, params['name']),
            params['name'],
            params,
            extras_func
        )

    print("\n" + "=" * 60)
    print("全部经典人物生成完成！")
    print(f"模型目录: {BASE_DIR}")
    for params, _ in characters:
        print(f"  {params['name']}/")
    print("=" * 60)
