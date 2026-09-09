"""
sensor_data_parser.py
解析主控通过 BLE chr_imu 特征转发的传感器四元数数据，
维护13个传感器的最新状态，供传感器查看窗口使用。
"""
from PyQt6.QtCore import QObject, pyqtSignal
import struct
import time

# 传感器ID→名称映射（与传感器端固件一致，ID=1~13）
SENSOR_NAMES = {
    1: "腰",
    2: "左髋",
    3: "右髋",
    4: "左大腿",
    5: "右大腿",
    6: "左小腿",
    7: "右小腿",
    8: "左肩",
    9: "右肩",
    10: "左上臂",
    11: "右上臂",
    12: "左前臂",
    13: "右前臂",
}

SENSOR_ID_MIN = 1
SENSOR_ID_MAX = 13

# 状态字节位定义（与传感器端 config.h 一致）
STATUS_RUNNING    = 0x01  # bit0: 运行
STATUS_QW_NEG     = 0x02  # bit1: qw符号
STATUS_CAL_VALID  = 0x04  # bit2: 校准有效
STATUS_BLE_CONN   = 0x08  # bit3: BLE连接
STATUS_STATIONARY = 0x10  # bit4: 静止


class SensorData:
    """单个传感器的最新数据"""
    def __init__(self, sensor_id):
        self.sensor_id = sensor_id
        self.name = SENSOR_NAMES.get(sensor_id, f"未知{sensor_id}")
        self.qw = 1.0
        self.qx = 0.0
        self.qy = 0.0
        self.qz = 0.0
        self.status = 0
        self.last_update = 0.0  # time.time()
        self.valid = False

    def update(self, qw, qx, qy, qz, status):
        self.qw = qw
        self.qx = qx
        self.qy = qy
        self.qz = qz
        self.status = status
        self.last_update = time.time()
        self.valid = True

    @property
    def is_stationary(self):
        return bool(self.status & STATUS_STATIONARY)

    @property
    def is_cal_valid(self):
        return bool(self.status & STATUS_CAL_VALID)

    @property
    def is_running(self):
        return bool(self.status & STATUS_RUNNING)

    @property
    def is_fresh(self, timeout_ms=500):
        """数据是否新鲜（最近timeout_ms毫秒内有更新）"""
        if not self.valid:
            return False
        return (time.time() - self.last_update) * 1000 < timeout_ms


class SensorDataParser(QObject):
    """
    解析主控转发的 ble_imu_pkt_t 数据包，维护13个传感器的最新数据。

    数据包格式（与主控 ble_imu_pkt_t 一致）：
      byte0:     pkg_type (1=PKG_TYPE_IMU_RAW)
      byte1-2:   pkg_len (uint16 little-endian)
      byte3:     sensor_id (uint8)
      byte4-19:  q[4] (4个float little-endian)
    """
    sig_sensor_updated = pyqtSignal(int)  # 参数: sensor_id

    def __init__(self):
        super().__init__()
        self.sensors = {}
        for sid in range(SENSOR_ID_MIN, SENSOR_ID_MAX + 1):
            self.sensors[sid] = SensorData(sid)

    def parse_packet(self, data: bytes):
        """
        解析一个完整的 ble_imu_pkt_t 数据包。
        data 是 notify 收到的原始字节（可能包含head）。
        """
        if len(data) < 20:
            return False

        try:
            # 跳过 head (pkg_type + pkg_len = 3字节)
            # ble_imu_pkt_t: head(3) + sensor_id(1) + q[4](16) = 20字节
            sensor_id = data[3]
            # q[0..3] 是 float little-endian
            qw, qx, qy, qz = struct.unpack_from('<4f', data, 4)
            # status 不在 ble_imu_pkt_t 里，暂时设为0
            # （后续如果需要状态，可以扩展数据包或从其他通道获取）
            status = 0

            if sensor_id < SENSOR_ID_MIN or sensor_id > SENSOR_ID_MAX:
                return False

            self.sensors[sensor_id].update(qw, qx, qy, qz, status)
            self.sig_sensor_updated.emit(sensor_id)
            return True

        except Exception as e:
            print(f"[SensorDataParser] 解析失败: {e}")
            return False

    def get_sensor(self, sensor_id):
        """获取指定传感器的数据"""
        return self.sensors.get(sensor_id)

    def get_all_sensors(self):
        """获取所有传感器数据（按ID排序）"""
        return [self.sensors[sid] for sid in range(SENSOR_ID_MIN, SENSOR_ID_MAX + 1)]

    def get_active_count(self):
        """获取有有效数据的传感器数量"""
        return sum(1 for s in self.sensors.values() if s.valid)
