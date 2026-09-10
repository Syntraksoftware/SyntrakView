"""最小化Qt3D测试 - 逐步排查崩溃原因"""
import sys
print("Step 1: imports...", flush=True)
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtGui import QVector3D, QColor
from PyQt6 import Qt3DCore, Qt3DRender, Qt3DExtras
print("Step 1 OK", flush=True)

app = QApplication(sys.argv)
print("Step 2: QApplication OK", flush=True)

# 测试1: 只创建Qt3DWindow
try:
    view = Qt3DExtras.Qt3DWindow()
    print("Step 3: Qt3DWindow created OK", flush=True)
except Exception as e:
    print(f"Step 3 FAILED: {e}", flush=True)
    sys.exit(1)

# 测试2: createWindowContainer
try:
    container = QWidget.createWindowContainer(view)
    print("Step 4: createWindowContainer OK", flush=True)
except Exception as e:
    print(f"Step 4 FAILED: {e}", flush=True)
    sys.exit(1)

# 测试3: 根实体和基本组件
try:
    root = Qt3DCore.QEntity()
    camera = view.camera()
    camera.lens().setPerspectiveProjection(45, 1.0, 0.1, 100)
    camera.setPosition(QVector3D(0, 1, 3))
    camera.setViewCenter(QVector3D(0, 0, 0))
    print("Step 5: camera OK", flush=True)
except Exception as e:
    print(f"Step 5 FAILED: {e}", flush=True)
    sys.exit(1)

# 测试4: 相机控制器
try:
    cam_ctrl = Qt3DExtras.QOrbitCameraController(root)
    cam_ctrl.setCamera(camera)
    print("Step 6: camera controller OK", flush=True)
except Exception as e:
    print(f"Step 6 FAILED: {e}", flush=True)
    sys.exit(1)

# 测试5: 一个简单的球体
try:
    sphere_entity = Qt3DCore.QEntity(root)
    sphere_mesh = Qt3DExtras.QSphereMesh()
    sphere_mesh.setRadius(0.5)
    sphere_entity.addComponent(sphere_mesh)
    sphere_mat = Qt3DExtras.QPhongMaterial()
    sphere_mat.setDiffuse(QColor(255, 100, 100))
    sphere_entity.addComponent(sphere_mat)
    sphere_transform = Qt3DCore.QTransform()
    sphere_transform.setTranslation(QVector3D(0, 0, 0))
    sphere_entity.addComponent(sphere_transform)
    print("Step 7: sphere entity OK", flush=True)
except Exception as e:
    print(f"Step 7 FAILED: {e}", flush=True)
    sys.exit(1)

# 测试6: 设置根实体
try:
    view.setRootEntity(root)
    print("Step 8: setRootEntity OK", flush=True)
except Exception as e:
    print(f"Step 8 FAILED: {e}", flush=True)
    sys.exit(1)

# 测试7: 显示窗口
try:
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.addWidget(container)
    w.resize(400, 500)
    w.show()
    print("Step 9: window shown OK", flush=True)
    print("ALL TESTS PASSED - close window to exit", flush=True)
    sys.exit(app.exec())
except Exception as e:
    print(f"Step 9 FAILED: {e}", flush=True)
    sys.exit(1)
