'''
组包器，根据分包数据
**分片帧头（每个 notify 分片都带 5 字节分片头）**

| 偏移       | 字段                   | 说明
| 0         | uint8_t flags         | bit0=1：首片 (SOF)；bit1=1：尾片 (EOF)
| 1         | uint16_t total_len    | 完整业务包总字节，小端
| 3         | uint16_t offset       | 当前分片在完整包内偏移，小端
| 5         | uint8[] chunk_data    | 分片业务数据，剩余全部字节
重新组包，组合完成，输出一个
'''
class BleNotifyReassembler:
    def __init__(self):
        self.reset()

    def reset(self):
        self.buf = bytearray()
        self.total_len = 0
        self.received_mask = bytearray()  # 每字节 0/1 标记是否已收到（丢分片检测）

    def feed(self, data:bytes):
        """输入每一次notify原始data，yield完整业务包(如有)。
        分片缺失时丢弃不完整包：缺失字节为0，会令某关节角度解析为0，
        导致人偶偶发大幅动作后回原位。"""
        if len(data) <5:
            self.reset()
            return
        flags = data[0]
        total_len = int.from_bytes(data[1:3], byteorder="little")
        offset = int.from_bytes(data[3:5], byteorder="little")
        chunk_data = data[5:]

        # 单片包(SOF+EOF，如20Hz角度包、设备信息包)本身完整：直接输出，不碰缓冲区。
        # 否则它会夹在多片包(文件列表JSON)中间把缓冲区重置，文件列表偶发丢失。
        if (flags & 0x03) == 0x03:
            if offset == 0 and len(chunk_data) == total_len:
                yield bytes(chunk_data)
            return

        # SOF：新帧开始，重置缓冲区
        if (flags & 0x01) !=0:
            self.buf = bytearray(total_len)
            self.total_len = total_len
            self.received_mask = bytearray(total_len)  # 全0=未收

        # 越界保护
        if (offset + len(chunk_data)) > self.total_len:
            self.reset()
            return

        # 拷贝分片到对应偏移，并标记已收
        self.buf[offset:offset+len(chunk_data)] = chunk_data
        self.received_mask[offset:offset+len(chunk_data)] = b'\x01' * len(chunk_data)

        # EOF：所有字节都已收到才输出完整包，否则丢弃（避免缺失处=0 造成角度突变）
        if (flags & 0x02) !=0:
            if self.total_len > 0 and (0 not in self.received_mask):
                yield bytes(self.buf)
            self.reset()


if __name__ == "__main__":
    # 自检：多片包中间夹一个单片包，两者都必须完整输出
    def frag(flags, total, off, data):
        return bytes([flags]) + total.to_bytes(2, "little") + off.to_bytes(2, "little") + data
    big = bytes(range(256)) * 2 + b"xyz"          # 515B，分3片
    single = b"\x01" + b"A" * 172                   # 角度包，单片
    r, out = BleNotifyReassembler(), []
    for f in (frag(0x01, len(big), 0, big[:239]),
              frag(0x03, len(single), 0, single),   # 夹在中间
              frag(0x00, len(big), 239, big[239:478]),
              frag(0x02, len(big), 478, big[478:])):
        out += list(r.feed(f))
    assert out == [single, big], out
    # 缺片仍丢弃
    r, out = BleNotifyReassembler(), []
    for f in (frag(0x01, len(big), 0, big[:239]), frag(0x02, len(big), 478, big[478:])):
        out += list(r.feed(f))
    assert out == [], out
    print("reassembler self-check OK")
