import sys
import cv2
import os
import glob
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTabWidget, QComboBox, QSlider, QCheckBox
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt

os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = '/home/lbo/.local/lib/python3.6/site-packages/cv2/qt/plugins'

class CameraWidget(QLabel):
    def __init__(self):
        super().__init__()
        self.cap = None
        self.setText("Camera not connected")
        self.setAlignment(Qt.AlignCenter)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def start_camera(self, index=0):
        self.cap = cv2.VideoCapture(index)
        if self.cap.isOpened():
            self.timer.start(30)
        else:
            self.setText("No camera detected")

    def update_frame(self):
        if self.cap is None:
            return
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            qimg = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
            self.setPixmap(QPixmap.fromImage(qimg).scaled(
                self.width(), self.height(), Qt.KeepAspectRatio
            ))

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        event.accept()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Evaluation Tool")
        self.resize(1200, 600)

        main_layout = QHBoxLayout(self)

        self.tabs = QTabWidget()
        self.device_tab_widget = self.device_tab()
        self.settings_tab_widget = self.settings_tab()
        self.advanced_tab_widget = self.advanced_tab()

        self.tabs.addTab(self.device_tab_widget, "DEVICE")
        self.tabs.addTab(self.settings_tab_widget, "SETTINGS")
        self.tabs.addTab(self.advanced_tab_widget, "ADVANCED")

        # Disable settings and advanced until connection
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)

        self.camera_widget = CameraWidget()

        main_layout.addWidget(self.tabs, 2)
        main_layout.addWidget(self.camera_widget, 5)

    def device_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Serial Port:"))
        self.serial_port_combo = QComboBox()
        self.serial_port_combo.addItems(sorted(glob.glob("/dev/tty*")))
        layout.addWidget(self.serial_port_combo)

        layout.addWidget(QLabel("Video Port:"))
        self.video_port_combo = QComboBox()
        self.video_port_combo.addItems(sorted(glob.glob("/dev/video*")))
        layout.addWidget(self.video_port_combo)

        connect_btn = QPushButton("CONNECT")
        connect_btn.clicked.connect(self.connect_devices)
        layout.addWidget(connect_btn)

        layout.addStretch()
        return tab

    def settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Checkboxes
        self.wdr_cb = QCheckBox("WDR")
        self.wdr_cb.stateChanged.connect(lambda: self.report_checkbox("WDR", self.wdr_cb))
        layout.addWidget(self.wdr_cb)

        self.night_cb = QCheckBox("NIGHT MODE")
        self.night_cb.stateChanged.connect(lambda: self.report_checkbox("NIGHT MODE", self.night_cb))
        layout.addWidget(self.night_cb)

        self.fliph_cb = QCheckBox("FLIP H")
        self.fliph_cb.stateChanged.connect(lambda: self.report_checkbox("FLIP H", self.fliph_cb))
        layout.addWidget(self.fliph_cb)

        self.flipv_cb = QCheckBox("FLIP V")
        self.flipv_cb.stateChanged.connect(lambda: self.report_checkbox("FLIP V", self.flipv_cb))
        layout.addWidget(self.flipv_cb)

        self.overlay_cb = QCheckBox("OVERLAY")
        self.overlay_cb.stateChanged.connect(lambda: self.report_checkbox("OVERLAY", self.overlay_cb))
        layout.addWidget(self.overlay_cb)

        # Sliders
        sliders = [
            ("2D DENOISE", 0, 10), ("3D DENOISE", 0, 10), ("SHUTTER", 0, 255),
            ("BRIGHTNESS", 0, 255), ("CONTRAST", 0, 255), ("SATURATION", 0, 255),
            ("SHARPEN", 0, 10)
        ]

        self.slider_widgets = {}
        for name, mn, mx in sliders:
            layout.addWidget(QLabel(name))
            slider = QSlider(Qt.Horizontal)
            slider.setRange(mn, mx)
            slider.valueChanged.connect(lambda value, n=name: self.report_slider(n, value))
            layout.addWidget(slider)
            self.slider_widgets[name] = slider

        layout.addStretch()
        return tab

    def advanced_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Firmware File:"))
        self.firmware_combo = QComboBox()
        self.firmware_combo.addItems(sorted(glob.glob("./vcf/*.hex")))
        layout.addWidget(self.firmware_combo)

        update_btn = QPushButton("UPDATE")
        update_btn.clicked.connect(self.update_push)
        layout.addWidget(update_btn)

        export_btn = QPushButton("EXPORT LOG")
        export_btn.clicked.connect(self.export_push)
        layout.addWidget(export_btn)

        layout.addStretch()
        return tab

    # --------- Methods for reporting checkbox and sliders ---------
    def report_checkbox(self, name, cb):
        state = "activate" if cb.isChecked() else "deactivate"
        print(f"{name} {state}")

    def report_slider(self, name, value):
        print(f"{name}: {value}")

    # --------- Update/Export functions ---------
    def update_push(self):
        print("UPDATE push")

    def export_push(self):
        print("EXPORT LOG push")

    # --------- Connect Devices ---------
    def connect_devices(self):
        connected = False

        # Connect camera
        video_text = self.video_port_combo.currentText()
        if video_text.startswith("/dev/video"):
            index = int(video_text.replace("/dev/video", ""))
            self.camera_widget.start_camera(index)
            print(f"Camera connected to {video_text}")
            connected = True

        # Connect serial (simulation)
        serial_text = self.serial_port_combo.currentText()
        if serial_text.startswith("/dev/tty"):
            print(f"Serial port connected to {serial_text}")
            connected = True

        # Enable tabs if connected to at least one device
        self.tabs.setTabEnabled(1, connected)
        self.tabs.setTabEnabled(2, connected)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
