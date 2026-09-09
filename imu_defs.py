# imu_defs.py
import numpy as np

# 13个IMU传感器定义：ID、名称、3D初始坐标(人体基准坐标系)
# 顺序对应你手绘X标记点位
IMU_LIST = [
    {"id":0, "name":"左肩",     "pos":np.array([-0.30, 0.00, 1.40])},
    {"id":1, "name":"右肩",     "pos":np.array([ 0.30, 0.00, 1.40])},
    {"id":2, "name":"胸口",     "pos":np.array([ 0.00, 0.00, 1.20])},
    {"id":3, "name":"左上臂",   "pos":np.array([-0.45, 0.00, 1.10])},
    {"id":4, "name":"右上臂",   "pos":np.array([ 0.45, 0.00, 1.10])},
    {"id":5, "name":"左前臂",   "pos":np.array([-0.50, 0.00, 0.80])},
    {"id":6, "name":"右前臂",   "pos":np.array([ 0.50, 0.00, 0.80])},
    {"id":7, "name":"左大腿",   "pos":np.array([-0.25, 0.00, 0.40])},
    {"id":8, "name":"右大腿",   "pos":np.array([ 0.25, 0.00, 0.40])},
    {"id":9, "name":"左小腿",   "pos":np.array([-0.23, 0.00, 0.05])},
    {"id":10,"name":"右小腿",   "pos":np.array([ 0.23, 0.00, 0.05])},
    {"id":11,"name":"左髋",     "pos":np.array([-0.22, 0.00, 0.65])},
    {"id":12,"name":"右髋",     "pos":np.array([ 0.22, 0.00, 0.65])},
]
TOTAL_IMU_COUNT = 13
