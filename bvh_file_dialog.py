import json
import os
from PyQt6.QtWidgets import (QDialog, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTextEdit, QLabel, QMessageBox, QFileDialog,
                             QProgressBar, QWidget, QListWidget, QListWidgetItem, QAbstractItemView)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QSettings, QTimer
from typing import Optional
from download_manager import DownloadManager, DownloadStatus, STATUS_TEXT

# BLE命令ID（与ESP32端ble_bvh.h一致）
CMD_LIST_DIR = 0x03
CMD_FILE_SELECT = 0x04
CMD_FILE_UPLOAD = 0x05
CMD_FILE_DELETE = 0x06
CMD_SAVE_REMARK = 0x09


class BvhFileManagerDialog(QDialog):
    sig_send_ble_cmd = pyqtSignal(bytes)
    sig_log = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BVH File Manager")
        self.resize(960, 680)
        self.setModal(False)
        self.setStyleSheet("""
            QDialog { background-color: #f5f7fa; }
            QLabel { color: #2c3e50; font-size: 12px; }
            QPushButton {
                background-color: #3498db; color: white; border: none;
                padding: 8px 16px; border-radius: 4px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #1a5276; }
            QPushButton#btn_delete { background-color: #e74c3c; }
            QPushButton#btn_delete:hover { background-color: #c0392b; }
            QPushButton#btn_download { background-color: #27ae60; }
            QPushButton#btn_download:hover { background-color: #1e8449; }
            QTextEdit {
                border: 1px solid #bdc3c7; border-radius: 4px; padding: 6px;
                background-color: white; color: #2c3e50; font-size: 12px;
            }
            QTreeWidget {
                border: 1px solid #bdc3c7; border-radius: 6px;
                background-color: white; color: #2c3e50; font-size: 13px; padding: 4px;
                outline: none;
            }
            QTreeWidget::item { padding: 6px; border-radius: 3px; color: #2c3e50; }
            QTreeWidget::item:hover { background-color: #d6eaf8; color: #1a5276; }
            QTreeWidget::item:selected { background-color: #1a5276; color: #ffffff; font-weight: bold; }
            QScrollBar:vertical {
                background: #ecf0f1; width: 12px; margin: 0; border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #95a5a6; min-height: 30px; border-radius: 6px; margin: 2px;
            }
            QScrollBar::handle:vertical:hover { background: #7f8c8d; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal {
                background: #ecf0f1; height: 12px; margin: 0; border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #95a5a6; min-width: 30px; border-radius: 6px; margin: 2px;
            }
            QScrollBar::handle:horizontal:hover { background: #7f8c8d; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
            QProgressBar {
                border: 1px solid #bdc3c7; border-radius: 4px; text-align: center;
                background-color: white; height: 20px; font-size: 11px;
            }
            QProgressBar::chunk { background-color: #27ae60; border-radius: 3px; }
        """)

        self.current_path: str = "/sdcard/Syntrak_records"
        self._selected_bvh_fullpath: Optional[str] = None

        # 下载管理器（支持断点续传、多任务、暂停/继续）
        self.download_mgr = DownloadManager(self.sig_send_ble_cmd.emit)
        self.download_mgr.task_added.connect(self._on_download_task_added)
        self.download_mgr.task_removed.connect(self._on_download_task_removed)

        # -------- 创建大图标 --------
        self.icon_folder = self._create_folder_icon()
        self.icon_bvh = self._create_bvh_icon()

        # -------- UI布局 --------
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # === 左侧：文件树 ===
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        title_label = QLabel("📁  Device File Tree")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50;")
        left_layout.addWidget(title_label)

        self.label_path = QLabel(self.current_path)
        self.label_path.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 2px 8px;")
        left_layout.addWidget(self.label_path)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type"])
        self.tree.setColumnWidth(0, 320)
        self.tree.setColumnWidth(1, 80)
        self.tree.setIconSize(QSize(40, 40))
        self.tree.setIndentation(28)
        self.tree.setAlternatingRowColors(False)
        self.tree.setAnimated(True)
        left_layout.addWidget(self.tree, stretch=1)

        # 按钮行1：刷新
        btn_row1 = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄  Refresh")
        btn_row1.addWidget(self.btn_refresh)
        btn_row1.addStretch()
        left_layout.addLayout(btn_row1)

        # 按钮行2：删除 + 下载
        btn_row2 = QHBoxLayout()
        self.btn_delete = QPushButton("🗑  Delete")
        self.btn_delete.setObjectName("btn_delete")
        self.btn_download = QPushButton("⬇  Download")
        self.btn_download.setObjectName("btn_download")
        btn_row2.addWidget(self.btn_delete)
        btn_row2.addWidget(self.btn_download)
        left_layout.addLayout(btn_row2)

        # 下载任务列表（类似迅雷）
        download_title = QLabel("⬇️  Download Tasks")
        download_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50; padding: 4px 0;")
        left_layout.addWidget(download_title)

        self.download_list = QListWidget()
        self.download_list.setStyleSheet("""
            QListWidget { background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 6px; padding: 4px; }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #eee; color: #2c3e50; }
            QListWidget::item:selected { background-color: #e3f2fd; }
        """)
        self.download_list.setMinimumHeight(120)
        self.download_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.download_list.customContextMenuRequested.connect(self._on_download_list_menu)
        left_layout.addWidget(self.download_list)

        self.label_status = QLabel("")
        self.label_status.setStyleSheet("color: #27ae60; font-size: 11px; padding: 2px 4px;")
        left_layout.addWidget(self.label_status)

        main_layout.addLayout(left_layout, stretch=3)

        # === 右侧：备注面板 ===
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        title_right = QLabel("📝  File Remarks")
        title_right.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50;")
        right_layout.addWidget(title_right)

        self.label_selected_file = QLabel("No file selected")
        self.label_selected_file.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 2px 4px;")
        self.label_selected_file.setWordWrap(True)
        right_layout.addWidget(self.label_selected_file)

        self.edit_note = QTextEdit()
        self.edit_note.setMinimumHeight(200)
        self.edit_note.setPlaceholderText("Select a .bvh file to view/edit remarks")
        right_layout.addWidget(self.edit_note, stretch=1)

        # 字数统计 + 保存按钮放同一行，节省垂直空间
        bottom_row = QHBoxLayout()
        self.label_count = QLabel("0 / 200")
        self.label_count.setStyleSheet("color: #95a5a6; font-size: 11px;")
        self.btn_save_note = QPushButton("💾  Save Remark")
        bottom_row.addWidget(self.label_count)
        bottom_row.addStretch()
        bottom_row.addWidget(self.btn_save_note)
        right_layout.addLayout(bottom_row)

        # 底部占位区，让编辑框底部与左侧树视图底部平齐
        # （左侧底部有两行按钮+进度条+状态，右侧只有一行按钮，需补高度差）
        bottom_spacer = QWidget()
        bottom_spacer.setFixedHeight(56)
        right_layout.addWidget(bottom_spacer)

        main_layout.addLayout(right_layout, stretch=2)

        # 信号绑定
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double_click)
        self.tree.currentItemChanged.connect(self._on_item_selected)
        self.edit_note.textChanged.connect(self._update_note_counter)
        self.btn_refresh.clicked.connect(self.refresh_dir)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_download.clicked.connect(self._on_download)
        self.btn_save_note.clicked.connect(self._on_save_note)

    # ==================== 图标创建 ====================
    def _create_folder_icon(self) -> QIcon:
        pix = QPixmap(48, 48)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 文件夹主体
        painter.setBrush(QColor("#f39c12"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(4, 14, 40, 28, 4, 4)
        # 文件夹标签
        painter.setBrush(QColor("#e67e22"))
        painter.drawRoundedRect(4, 10, 18, 10, 3, 3)
        painter.end()
        return QIcon(pix)

    def _create_bvh_icon(self) -> QIcon:
        pix = QPixmap(48, 48)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 文件主体
        painter.setBrush(QColor("#3498db"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(8, 4, 32, 40, 3, 3)
        # 文件折角
        painter.setBrush(QColor("#2980b9"))
        painter.drawPolygon(
            [QPoint(30, 4), QPoint(40, 4), QPoint(40, 14)]
        )
        # 文字
        painter.setPen(QColor("white"))
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "BVH")
        painter.end()
        return QIcon(pix)

    # ==================== 工具函数 ====================
    def _build_cmd_pkt(self, cmd_id: int, payload: bytes = b"") -> bytes:
        pkt = bytearray()
        pkt.append(cmd_id)
        pkt.extend(len(payload).to_bytes(2, byteorder="little"))
        pkt.extend(payload)
        return bytes(pkt)

    def _get_item_full_path(self, item: QTreeWidgetItem) -> str:
        """从树节点获取完整文件路径"""
        parts = []
        while item is not None:
            parts.insert(0, item.text(0))
            item = item.parent()
        return self.current_path + "/" + "/".join(parts)

    def _update_note_counter(self):
        txt = self.edit_note.toPlainText()
        if len(txt) > 200:
            self.edit_note.setPlainText(txt[:200])
        cnt = len(self.edit_note.toPlainText())
        self.label_count.setText(f"{cnt} / 200")

    # ==================== 目录列表 ====================
    def clear_file_tree(self):
        self.tree.clear()
        self._selected_bvh_fullpath = None
        self.edit_note.clear()
        self.label_selected_file.setText("No file selected")

    def refresh_dir(self):
        self.clear_file_tree()
        payload = self.current_path.encode("utf-8")
        pkt = self._build_cmd_pkt(CMD_LIST_DIR, payload)
        self.sig_send_ble_cmd.emit(pkt)
        self.sig_log.emit(f"[FileMgr] send CMD_LIST_DIR: {self.current_path}")
        self.label_status.setText("Refreshing file list...")

    def process_file_response(self, payload_bytes: bytes):
        """处理递归目录树JSON"""
        try:
            text = payload_bytes.decode("utf-8", errors="ignore")
            data = json.loads(text)
        except Exception as e:
            self.sig_log.emit(f"[FileMgr] JSON parse error: {e}")
            self.label_status.setText("Failed to parse file list")
            return

        if "path" in data:
            self.current_path = data["path"]
            self.label_path.setText(self.current_path)

        items = data.get("items", [])
        self._build_tree_items(items, None)

        # 默认展开最后一个文件夹
        last_dir_item = None
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == "dir":
                last_dir_item = item
        if last_dir_item:
            self.tree.expandItem(last_dir_item)

        count = self._count_items(items)
        self.label_status.setText(f"Loaded {count} items")
        self.sig_log.emit(f"[FileMgr] render tree from {self.current_path}, {count} items")

        # 延迟滚动到底部，确保树视图渲染完成
        QTimer.singleShot(50, self.tree.scrollToBottom)

    def _build_tree_items(self, items: list, parent: Optional[QTreeWidgetItem]):
        """递归构建树形节点"""
        for item in items:
            name = item.get("name", "")
            itype = item.get("type", "file")
            tree_item = QTreeWidgetItem()
            tree_item.setText(0, name)
            tree_item.setText(1, "Folder" if itype == "dir" else "BVH")

            if itype == "dir":
                tree_item.setIcon(0, self.icon_folder)
                tree_item.setData(0, Qt.ItemDataRole.UserRole, "dir")
                children = item.get("children", [])
                if children:
                    self._build_tree_items(children, tree_item)
            else:
                tree_item.setIcon(0, self.icon_bvh)
                tree_item.setData(0, Qt.ItemDataRole.UserRole, "bvh")

            if parent is None:
                self.tree.addTopLevelItem(tree_item)
            else:
                parent.addChild(tree_item)

    def _count_items(self, items: list) -> int:
        count = len(items)
        for item in items:
            if item.get("type") == "dir":
                count += self._count_items(item.get("children", []))
        return count

    # ==================== 文件选择 & 备注 ====================
    def _on_item_clicked(self, item: QTreeWidgetItem, col):
        """单击文件夹展开/折叠"""
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type == "dir":
            if item.isExpanded():
                self.tree.collapseItem(item)
            else:
                self.tree.expandItem(item)

    def _on_item_double_click(self, item: QTreeWidgetItem, col):
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type == "dir":
            if item.isExpanded():
                self.tree.collapseItem(item)
            else:
                self.tree.expandItem(item)

    def _on_item_selected(self, curr, prev):
        self.edit_note.clear()
        self.edit_note.setPlaceholderText("Select a .bvh file to view/edit remarks")
        self._selected_bvh_fullpath = None
        if curr is None:
            self.label_selected_file.setText("No file selected")
            return
        item_type = curr.data(0, Qt.ItemDataRole.UserRole)
        if item_type != "bvh":
            self.label_selected_file.setText("Selected: folder")
            return

        fullpath = self._get_item_full_path(curr)
        self._selected_bvh_fullpath = fullpath
        self.label_selected_file.setText(f"Selected: {curr.text(0)}")

        payload = fullpath.encode("utf-8")
        pkt = self._build_cmd_pkt(CMD_FILE_SELECT, payload)
        self.sig_send_ble_cmd.emit(pkt)
        self.sig_log.emit(f"[FileMgr] send CMD_FILE_SELECT: {fullpath}")

    def process_remark_response(self, payload_bytes: bytes):
        remark = payload_bytes.decode("utf-8", errors="ignore")
        if not remark.strip():
            self.edit_note.setPlaceholderText("New file (no remark yet)")
            self.edit_note.clear()
            self.label_status.setText("No remark saved for this file")
        else:
            self.edit_note.setPlainText(remark[:200])
            self.label_status.setText("Remark loaded")
        self._update_note_counter()
        self.sig_log.emit(f"[FileMgr] remark received, len={len(remark)}")

    def _on_save_note(self):
        if self._selected_bvh_fullpath is None:
            QMessageBox.warning(self, "Tips", "Please select a .bvh file first")
            return
        bvh_path = self._selected_bvh_fullpath
        note = self.edit_note.toPlainText()[:200]

        fname_bytes = bvh_path.encode("utf-8")
        note_bytes = note.encode("utf-8")
        payload = bytearray()
        payload.extend(len(fname_bytes).to_bytes(2, byteorder="little"))
        payload.extend(fname_bytes)
        payload.extend(len(note_bytes).to_bytes(2, byteorder="little"))
        payload.extend(note_bytes)

        pkt = self._build_cmd_pkt(CMD_SAVE_REMARK, bytes(payload))
        self.sig_send_ble_cmd.emit(pkt)
        self.sig_log.emit(f"[FileMgr] send CMD_SAVE_REMARK: {bvh_path}")
        self.label_status.setText("Remark saved to device")
        QMessageBox.information(self, "Save", "Remark saved successfully!")

    # ==================== 删除 ====================
    def _on_delete(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Tips", "Please select a file to delete")
            return
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type != "bvh":
            QMessageBox.warning(self, "Tips", "Only .bvh files can be deleted")
            return

        fname = item.text(0)
        fullpath = self._get_item_full_path(item)
        ret = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete file:\n{fname}\n\nThis will also delete the associated .des remark file.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        payload = fullpath.encode("utf-8")
        pkt = self._build_cmd_pkt(CMD_FILE_DELETE, payload)
        self.sig_send_ble_cmd.emit(pkt)
        self.sig_log.emit(f"[FileMgr] send CMD_FILE_DELETE: {fullpath}")
        self.label_status.setText(f"Deleted: {fname}")

        # 延迟刷新列表
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self.refresh_dir)

    # ==================== 下载 ====================
    def _on_download(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Tips", "Please select a file to download")
            return
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type != "bvh":
            QMessageBox.warning(self, "Tips", "Only .bvh files can be downloaded")
            return

        fname = item.text(0)
        fullpath = self._get_item_full_path(item)

        # 缺省文件名：日期目录 + "_" + 文件名，例如 20260826_1.bvh
        path_parts = fullpath.replace("\\", "/").split("/")
        default_name = fname
        if len(path_parts) >= 2:
            date_dir = path_parts[-2]
            if date_dir and date_dir not in ("Syntrak_records", "sdcard"):
                default_name = f"{date_dir}_{fname}"

        # 记住上次保存位置
        settings = QSettings("Syntrak", "SyntrakView")
        last_dir = settings.value("last_save_dir", os.path.expanduser("~"))
        default_save_path = os.path.join(last_dir, default_name)

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save BVH File", default_save_path, "BVH Files (*.bvh);;All Files (*)"
        )
        if not save_path:
            return

        # 保存本次目录，下次作为默认
        settings.setValue("last_save_dir", os.path.dirname(save_path))

        # 添加到下载管理器（压缩下载待ESP32端miniz调试完成后启用）
        task = self.download_mgr.add_task(fullpath, save_path, use_compressed=False)
        self.label_status.setText(f"Added download: {fname}")
        self.sig_log.emit(f"[FileMgr] add download: {fullpath} -> {save_path}")

    def process_file_chunk(self, payload: bytes):
        """处理文件分块数据，转发给下载管理器"""
        if len(payload) < 10:
            return
        file_total = int.from_bytes(payload[0:4], "little")
        offset = int.from_bytes(payload[4:8], "little")
        data_len = int.from_bytes(payload[8:10], "little")
        data = payload[10:10 + data_len]
        self.download_mgr.on_data_chunk(file_total, offset, data)

    def process_batch_end(self, next_offset: int):
        """收到批次结束通知，转发给下载管理器立即请求下一批"""
        self.download_mgr.on_batch_end(next_offset)

    # ==================== 下载任务列表管理 ====================
    def _on_download_task_added(self, task):
        list_item = QListWidgetItem()
        list_item.setData(Qt.ItemDataRole.UserRole, task)
        self.download_list.addItem(list_item)
        self._update_download_list_item(list_item, task)
        task.status_changed.connect(lambda s, t=task, li=list_item: self._update_download_list_item(li, t))
        task.progress_changed.connect(lambda r, tot, t=task, li=list_item: self._update_download_list_item(li, t))

    def _on_download_task_removed(self, task):
        for i in range(self.download_list.count()):
            item = self.download_list.item(i)
            t = item.data(Qt.ItemDataRole.UserRole)
            if t is task:
                self.download_list.takeItem(i)
                break

    def _update_download_list_item(self, list_item: QListWidgetItem, task):
        status_text = STATUS_TEXT.get(task.status, task.status)
        percent = task.progress_percent()
        size_kb = task.total_size / 1024 if task.total_size > 0 else 0
        received_kb = task.received_size / 1024
        color = "#2c3e50"
        if task.status == DownloadStatus.DOWNLOADING:
            color = "#2980b9"
        elif task.status == DownloadStatus.COMPLETED:
            color = "#27ae60"
        elif task.status == DownloadStatus.FAILED:
            color = "#e74c3c"
        elif task.status == DownloadStatus.PAUSED:
            color = "#f39c12"
        text = f"📄 {task.file_name}\n   {percent}%  ({received_kb:.1f}/{size_kb:.1f} KB)  -  {status_text}"
        list_item.setText(text)
        list_item.setForeground(QColor(color))

    def _on_download_list_menu(self, pos):
        item = self.download_list.itemAt(pos)
        if not item:
            return
        task = item.data(Qt.ItemDataRole.UserRole)
        if not task:
            return
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        if task.status == DownloadStatus.DOWNLOADING:
            action_pause = menu.addAction("Pause")
            action_pause.triggered.connect(task.pause)
        elif task.status == DownloadStatus.PAUSED:
            action_resume = menu.addAction("Resume")
            action_resume.triggered.connect(lambda: self.download_mgr.resume_task(task))
        elif task.status == DownloadStatus.PENDING:
            action_resume = menu.addAction("Start Now")
            action_resume.triggered.connect(lambda: self.download_mgr.resume_task(task))
        if task.status in (DownloadStatus.FAILED, DownloadStatus.CANCELLED, DownloadStatus.COMPLETED):
            action_remove = menu.addAction("Remove from List")
            action_remove.triggered.connect(lambda: self.download_mgr.remove_task(task))
        action_cancel = menu.addAction("Cancel Download")
        action_cancel.triggered.connect(task.cancel)
        menu.exec(self.download_list.mapToGlobal(pos))
