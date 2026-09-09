"""
下载管理器：支持断点续传、多任务队列、暂停/继续、超时重传
类似迅雷的下载任务管理：同一时间只有一个任务在下载，其他任务排队等待
"""
import os
import time
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

CMD_FILE_UPLOAD = 0x05
CMD_FILE_UPLOAD_COMPRESSED = 0x0A


class DownloadStatus:
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


STATUS_TEXT = {
    DownloadStatus.PENDING: "Waiting",
    DownloadStatus.DOWNLOADING: "Downloading",
    DownloadStatus.PAUSED: "Paused",
    DownloadStatus.COMPLETED: "Completed",
    DownloadStatus.FAILED: "Failed",
    DownloadStatus.CANCELLED: "Cancelled",
}


class DownloadTask(QObject):
    """单个下载任务"""
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int, int)  # received, total

    def __init__(self, remote_path: str, save_path: str, send_cmd_callback, use_compressed: bool = False):
        super().__init__()
        self.remote_path = remote_path
        self.save_path = save_path
        self.temp_path = save_path + ".downloading"
        self.file_name = os.path.basename(save_path)
        self.use_compressed = use_compressed
        self.total_size = 0
        self.received_size = 0
        self.status = DownloadStatus.PENDING
        self._file_handle = None
        self._send_cmd = send_cmd_callback
        self._retry_count = 0
        self._max_retries = 10

        # 超时定时器：10秒没收到数据就重传
        self._timeout_timer = QTimer()
        self._timeout_timer.setInterval(10000)
        self._timeout_timer.timeout.connect(self._on_timeout)

        # 断点续传：检查临时文件
        if os.path.exists(self.temp_path):
            self.received_size = os.path.getsize(self.temp_path)
            if self.received_size > 0:
                self.status = DownloadStatus.PAUSED

    def start(self):
        if self.status in (DownloadStatus.DOWNLOADING, DownloadStatus.COMPLETED):
            return
        try:
            self._file_handle = open(self.temp_path, "ab")
        except Exception as e:
            self.status = DownloadStatus.FAILED
            self.status_changed.emit(self.status)
            return
        self._set_status(DownloadStatus.DOWNLOADING)
        self._request_batch()

    def pause(self):
        if self.status != DownloadStatus.DOWNLOADING:
            return
        self._timeout_timer.stop()
        self._close_file()
        self._set_status(DownloadStatus.PAUSED)

    def resume(self):
        if self.status != DownloadStatus.PAUSED:
            return
        self.start()

    def cancel(self):
        self._timeout_timer.stop()
        self._close_file()
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except:
                pass
        self._set_status(DownloadStatus.CANCELLED)

    def _request_batch(self):
        """向ESP32请求从当前偏移量开始的一批数据"""
        name_bytes = self.remote_path.encode("utf-8")
        # payload: name_len(2B LE) + name + offset(4B LE)
        payload = bytearray()
        payload.extend(len(name_bytes).to_bytes(2, "little"))
        payload.extend(name_bytes)
        payload.extend(self.received_size.to_bytes(4, "little"))
        # 命令包: cmd_id(1B) + param_len(2B) + payload
        cmd_pkt = bytearray()
        cmd_id = CMD_FILE_UPLOAD_COMPRESSED if self.use_compressed else CMD_FILE_UPLOAD
        cmd_pkt.append(cmd_id)
        cmd_pkt.extend(len(payload).to_bytes(2, "little"))
        cmd_pkt.extend(payload)
        self._send_cmd(bytes(cmd_pkt))
        self._timeout_timer.start()

    def _on_timeout(self):
        """超时重传"""
        if self.status != DownloadStatus.DOWNLOADING:
            return
        self._retry_count += 1
        if self._retry_count > self._max_retries:
            self._timeout_timer.stop()
            self._close_file()
            self._set_status(DownloadStatus.FAILED)
            return
        self._request_batch()

    def on_data_chunk(self, file_total: int, offset: int, data: bytes):
        """处理收到的数据块"""
        if self.status != DownloadStatus.DOWNLOADING:
            return False

        if self.total_size == 0:
            self.total_size = file_total

        # 只接受连续块（offset == received_size），跳过重复块
        if offset == self.received_size:
            try:
                self._file_handle.write(data)
                self._file_handle.flush()
                self.received_size += len(data)
            except Exception:
                self._timeout_timer.stop()
                self._close_file()
                self._set_status(DownloadStatus.FAILED)
                return False
        elif offset < self.received_size:
            pass  # 重复块，忽略
        else:
            # 丢块了，重传当前偏移量
            self._request_batch()
            return False

        self._retry_count = 0
        self.progress_changed.emit(self.received_size, self.total_size)

        if self.received_size >= self.total_size and self.total_size > 0:
            self._finish_download()

        return True

    def on_batch_end(self, next_offset: int):
        """收到批次结束通知：如果还没下载完，立即请求下一批（不等待超时）"""
        if self.status != DownloadStatus.DOWNLOADING:
            return
        # 如果ESP32说的next_offset和我们已下载的一致，且还没完成，立即继续
        if next_offset == self.received_size and self.received_size < self.total_size:
            self._request_batch()
        elif next_offset < self.received_size:
            # 重复的批次结束通知，忽略
            pass
        else:
            # offset不一致，可能丢块了，重传当前偏移量
            self._request_batch()

    def _finish_download(self):
        self._timeout_timer.stop()
        self._close_file()
        try:
            # 如果正式文件已存在，先删除
            if os.path.exists(self.save_path):
                os.remove(self.save_path)
            # 重命名临时文件为正式文件
            os.rename(self.temp_path, self.save_path)
        except Exception:
            try:
                # 兜底：复制临时文件到正式文件，然后删除临时文件
                import shutil
                shutil.copy2(self.temp_path, self.save_path)
                if os.path.exists(self.temp_path):
                    os.remove(self.temp_path)
            except Exception as e:
                self._set_status(DownloadStatus.FAILED)
                return
        # 最后确认临时文件不存在
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except:
                pass

        # 自动检测gzip格式并解压（ESP32压缩下载的文件）
        try:
            with open(self.save_path, "rb") as f:
                magic = f.read(2)
            if magic == b'\x1f\x8b':  # gzip magic number
                import gzip
                # 解压后的文件名：去掉.gz后缀
                if self.save_path.endswith(".gz"):
                    final_path = self.save_path[:-3]
                else:
                    final_path = self.save_path + ".extracted"
                with gzip.open(self.save_path, "rb") as gz_in:
                    with open(final_path, "wb") as out:
                        out.write(gz_in.read())
                # 删除gz文件，更新保存路径
                os.remove(self.save_path)
                self.save_path = final_path
                self.file_name = os.path.basename(final_path)
        except Exception as e:
            pass  # 解压失败保留原文件

        self._set_status(DownloadStatus.COMPLETED)

    def _close_file(self):
        if self._file_handle:
            try:
                self._file_handle.close()
            except:
                pass
            self._file_handle = None

    def _set_status(self, status):
        self.status = status
        self.status_changed.emit(status)

    def progress_percent(self) -> int:
        if self.total_size == 0:
            return 0
        return int(self.received_size * 100 / self.total_size)


class DownloadManager(QObject):
    """下载任务管理器：任务队列调度，同一时间只有一个任务在下载"""
    task_added = pyqtSignal(object)
    task_removed = pyqtSignal(object)

    def __init__(self, send_cmd_callback):
        super().__init__()
        self._send_cmd = send_cmd_callback
        self.tasks = []
        self._current_task = None  # 当前正在下载的任务

    def add_task(self, remote_path: str, save_path: str, use_compressed: bool = False) -> DownloadTask:
        task = DownloadTask(remote_path, save_path, self._send_cmd, use_compressed)
        self.tasks.append(task)
        # 监听任务状态变化，用于队列调度
        task.status_changed.connect(lambda s, t=task: self._on_task_status_changed(t, s))
        self.task_added.emit(task)

        # 队列调度：如果当前没有任务在下载，立即开始；否则保持PENDING等待
        if self._current_task is None or self._current_task.status != DownloadStatus.DOWNLOADING:
            self._start_next_task()
        return task

    def remove_task(self, task: DownloadTask):
        if task in self.tasks:
            # 如果是当前任务，先取消
            if task is self._current_task:
                task.cancel()
                self._current_task = None
            else:
                task.cancel()
            self.tasks.remove(task)
            self.task_removed.emit(task)
            # 如果移除的是当前任务，尝试开始下一个
            if self._current_task is None:
                self._start_next_task()

    def resume_task(self, task: DownloadTask):
        """恢复一个已暂停的任务：如果当前无下载任务则立即开始，否则排队等待"""
        if task.status != DownloadStatus.PAUSED:
            return
        if self._current_task is None or self._current_task.status != DownloadStatus.DOWNLOADING:
            # 当前无任务下载，立即恢复
            self._current_task = task
            task.resume()
        else:
            # 当前有任务在下载，设为PENDING排队等待
            task._set_status(DownloadStatus.PENDING)

    def _start_next_task(self):
        """从队列中找到第一个PENDING状态的任务开始下载"""
        if self._current_task is not None and self._current_task.status == DownloadStatus.DOWNLOADING:
            return  # 已有任务在下载
        for task in self.tasks:
            if task.status == DownloadStatus.PENDING:
                self._current_task = task
                task.start()
                return
        # 没有等待中的任务
        self._current_task = None

    def _on_task_status_changed(self, task: DownloadTask, status: str):
        """任务状态变化回调：当任务结束时，自动开始下一个等待中的任务"""
        # 如果当前任务结束（完成/失败/暂停/取消），释放当前任务槽位，开始下一个
        if task is self._current_task and status in (
            DownloadStatus.COMPLETED,
            DownloadStatus.FAILED,
            DownloadStatus.PAUSED,
            DownloadStatus.CANCELLED,
        ):
            self._current_task = None
            self._start_next_task()

    def on_data_chunk(self, file_total: int, offset: int, data: bytes) -> bool:
        """分发数据块到当前下载中的任务"""
        if self._current_task and self._current_task.status == DownloadStatus.DOWNLOADING:
            return self._current_task.on_data_chunk(file_total, offset, data)
        return False

    def on_batch_end(self, next_offset: int):
        """分发批次结束通知到当前下载中的任务"""
        if self._current_task and self._current_task.status == DownloadStatus.DOWNLOADING:
            self._current_task.on_batch_end(next_offset)

    def has_downloading(self) -> bool:
        return self._current_task is not None and self._current_task.status == DownloadStatus.DOWNLOADING
