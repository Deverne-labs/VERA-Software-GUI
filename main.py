import sys
import cv2
import os
import glob
import serial

from pygrabber.dshow_graph import FilterGraph
import com 


from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTabWidget, QComboBox, QSlider, QCheckBox
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt



# ---------- Cross-platform port listing ----------
def list_serial_ports():
    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):  # Linux / macOS
        return sorted(glob.glob("/dev/tty*"))
    elif sys.platform.startswith("win"):  # Windows
        try:
            import serial.tools.list_ports
            return [port.device for port in serial.tools.list_ports.comports()]
        except ImportError:
            return [f"COM{i}" for i in range(1, 21)]  # fallback guess
    else:
        return []

def list_video_ports():
    if sys.platform.startswith("linux"):
        return sorted(glob.glob("/dev/video*"))
    elif sys.platform.startswith("win"):
        graph = FilterGraph()
        devices = graph.get_input_devices()
        return [f"{i}: {name}" for i, name in enumerate(devices)]
    else:
        return []

# ---------- Camera Widget ----------
class CameraWidget(QLabel):
    def __init__(self):
        super().__init__()
        self.cap = None
        self.setText("Camera not connected")
        self.setAlignment(Qt.AlignCenter)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def start_camera(self, index=0):
        # If a camera is already open, release it first
        if hasattr(self, "cap") and self.cap is not None:
            if self.cap.isOpened():
                print("Closing previously opened camera...")
                self.cap.release()
                self.timer.stop()

        # Now open the new camera
        if sys.platform.startswith("win"):
            # Use DirectShow backend on Windows
            self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(index)

        # Check if the camera opened successfully
        if self.cap.isOpened():
            print(f"Camera started on index {index}")
            self.timer.start(30)
        else:
            print("No camera detected")
            self.setText("No camera detected")


    def update_frame(self):
        if self.cap is None:
            return
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            qimg = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)

            # Use smooth transformation for scaling
            pixmap = QPixmap.fromImage(qimg).scaled(
                self.width(),
                self.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation  # <-- this makes it smoother
            )
            self.setPixmap(pixmap)

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        event.accept()





















# ---------- Main Window ----------
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

        self.param_flip_h = False
        self.param_flip_v = False

        self.param_denoise2d = 0
        self.param_denoise3d = 0

        self.shutterspeed = 0
        self.brightness = 0

        self.contrast = 0
        self.saturation = 0
        self.sharpen = 0

    def device_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Serial Port:"))
        self.serial_port_combo = QComboBox()
        self.serial_port_combo.addItems(list_serial_ports())
        layout.addWidget(self.serial_port_combo)

        layout.addWidget(QLabel("Video Port:"))
        self.video_port_combo = QComboBox()
        self.video_port_combo.addItems(list_video_ports())
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
        self.wdr_cb.stateChanged.connect(lambda: self.ActionWDR_CB("WDR", self.wdr_cb))
        layout.addWidget(self.wdr_cb)

        self.night_cb = QCheckBox("NIGHT MODE")
        self.night_cb.stateChanged.connect(lambda: self.ActionNM_CB("NIGHT MODE", self.night_cb))
        layout.addWidget(self.night_cb)

        self.fliph_cb = QCheckBox("FLIP H")
        self.fliph_cb.stateChanged.connect(lambda: self.ActionFH_CB("FLIP H", self.fliph_cb))
        layout.addWidget(self.fliph_cb)

        self.flipv_cb = QCheckBox("FLIP V")
        self.flipv_cb.stateChanged.connect(lambda: self.ActionFV_CB("FLIP V", self.flipv_cb))
        layout.addWidget(self.flipv_cb)

        self.overlay_cb = QCheckBox("OVERLAY")
        self.overlay_cb.stateChanged.connect(lambda: self.ActionOV_CB("OVERLAY", self.overlay_cb))
        layout.addWidget(self.overlay_cb)

        # 2D Denoise
        self.label_2d = QLabel("2D DENOISE")
        layout.addWidget(self.label_2d)
        self.slider_2d = QSlider(Qt.Horizontal)
        self.slider_2d.setRange(0, 3)
        self.slider_2d.valueChanged.connect(lambda value: self.Action2dDenoise_slider("2D DENOISE", value))
        layout.addWidget(self.slider_2d)

        # 3D Denoise
        self.label_3d = QLabel("3D DENOISE")
        layout.addWidget(self.label_3d)
        self.slider_3d = QSlider(Qt.Horizontal)
        self.slider_3d.setRange(0, 3)
        self.slider_3d.valueChanged.connect(lambda value: self.Action3dDenoise_slider("3D DENOISE", value))
        layout.addWidget(self.slider_3d)

        # Shutter
        self.label_shutter = QLabel("SHUTTER")
        layout.addWidget(self.label_shutter)
        self.slider_shutter = QSlider(Qt.Horizontal)
        self.slider_shutter.setRange(0, 19)
        self.slider_shutter.valueChanged.connect(lambda value: self.ActionShutter_slider("SHUTTER", value))
        layout.addWidget(self.slider_shutter)

        # Brightness
        self.label_brightness = QLabel("BRIGHTNESS")
        layout.addWidget(self.label_brightness)
        self.slider_brightness = QSlider(Qt.Horizontal)
        self.slider_brightness.setRange(0, 99)
        self.slider_brightness.valueChanged.connect(lambda value: self.ActionBrightness_slider("BRIGHTNESS", value))
        layout.addWidget(self.slider_brightness)

        # Contrast
        self.label_contrast = QLabel("CONTRAST")
        layout.addWidget(self.label_contrast)
        self.slider_contrast = QSlider(Qt.Horizontal)
        self.slider_contrast.setRange(0, 255)
        self.slider_contrast.valueChanged.connect(lambda value: self.ActionContrast_slider("CONTRAST", value))
        layout.addWidget(self.slider_contrast)

        # Saturation
        self.label_saturation = QLabel("SATURATION")
        layout.addWidget(self.label_saturation)
        self.slider_saturation = QSlider(Qt.Horizontal)
        self.slider_saturation.setRange(0, 99)
        self.slider_saturation.valueChanged.connect(lambda value: self.ActionSaturation_slider("SATURATION", value))
        layout.addWidget(self.slider_saturation)

        # Sharpen
        self.label_sharpen = QLabel("SHARPEN")
        layout.addWidget(self.label_sharpen)
        self.slider_sharpen = QSlider(Qt.Horizontal)
        self.slider_sharpen.setRange(0, 9)
        self.slider_sharpen.valueChanged.connect(lambda value: self.ActionSharpen_slider("SHARPEN", value))
        layout.addWidget(self.slider_sharpen)

        # Continue similarly for CONTRAST, SATURATION, SHARPEN

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












    def send_serial_data(self, text_string):
        """
        Send ASCII characters over the open serial connection.
        Example: "AA5503000C03CAFDC7A455AA"
        """
        if hasattr(self, "serial_conn") and self.serial_conn and self.serial_conn.is_open:
            try:
                # Encode the string to bytes as ASCII
                data = text_string.encode('ascii')
                self.serial_conn.write(data)
                print(f"Sent to serial: {text_string}")
            except Exception as e:
                print(f"Error sending data: {e}")
        else:
            print("Serial port not connected")











    # --------- Methods for reporting checkbox and sliders ---------
    def ActionWDR_CB(self, name, cb):
        if cb.isChecked() :
            frame = com.build_frame(com.WRITE_OP,com.WDR_REG,0x03)
            self.serial_conn.write(frame.encode("ascii"))
        else :
            frame = com.build_frame(com.WRITE_OP,com.WDR_REG,0x00)
            self.serial_conn.write(frame.encode("ascii"))


    def ActionNM_CB(self, name, cb):
        if cb.isChecked() :
            frame = com.build_frame(com.WRITE_OP,com.DAYNIGHT_REG,0xFE)
            self.serial_conn.write(frame.encode("ascii"))
        else :
            frame = com.build_frame(com.WRITE_OP,com.DAYNIGHT_REG,0xFF)
            self.serial_conn.write(frame.encode("ascii"))


    def ActionFH_CB(self, name, cb):
        self.param_flip_h = cb.isChecked()
        self.UpdateFlipMode()

    def ActionFV_CB(self, name, cb):
        self.param_flip_v = cb.isChecked()
        self.UpdateFlipMode()

    def UpdateFlipMode(self):
        if (self.param_flip_h and self.param_flip_v) :
            value = 0x03
        elif (self.param_flip_h and not self.param_flip_v):
            value = 0x01
        elif (not self.param_flip_h and  self.param_flip_v):
            value = 0x02
        elif (not self.param_flip_h and not self.param_flip_v):
            value = 0x00

        frame = com.build_frame(com.WRITE_OP,com.MIRROR_REG,value)
        self.serial_conn.write(frame.encode("ascii"))

    def ActionOV_CB(self, name, cb):
        if cb.isChecked() :
            frame = com.build_frame(com.WRITE_OP,com.OVERLAY_REG,0x01)
            self.serial_conn.write(frame.encode("ascii"))
        else :
            frame = com.build_frame(com.WRITE_OP,com.OVERLAY_REG,0x00)
            self.serial_conn.write(frame.encode("ascii"))



    def Action2dDenoise_slider(self, name, value):
        self.param_denoise2d = value        
        self.UpdateDenoiseMode()


    def Action3dDenoise_slider(self, name, value):
        self.param_denoise3d = value        
        self.UpdateDenoiseMode()

    def UpdateDenoiseMode(self):
        if (self.param_denoise2d == 0) :
            if (self.param_denoise3d == 0) :
                value = 0x00
            elif (self.param_denoise3d == 1):
                value = 0x01
            elif (self.param_denoise3d == 2):
                value = 0x02
            elif (self.param_denoise3d == 3):
                value = 0x03
        elif (self.param_denoise2d == 1):
            if (self.param_denoise3d == 0) :
                value = 0x04
            elif (self.param_denoise3d == 1):
                value = 0x05
            elif (self.param_denoise3d == 2):
                value = 0x06
            elif (self.param_denoise3d == 3):
                value = 0x07
        elif (self.param_denoise2d == 2):
            if (self.param_denoise3d == 0) :
                value = 0x08
            elif (self.param_denoise3d == 1):
                value = 0x09
            elif (self.param_denoise3d == 2):
                value = 0x0A
            elif (self.param_denoise3d == 3):
                value = 0x0B
        elif (self.param_denoise2d == 3):
            if (self.param_denoise3d == 0) :
                value = 0x0C
            elif (self.param_denoise3d == 1):
                value = 0x0D
            elif (self.param_denoise3d == 2):
                value = 0x0E
            elif (self.param_denoise3d == 3):
                value = 0x0F
        frame = com.build_frame(com.WRITE_OP,com.DENOISE_REG,value)
        self.serial_conn.write(frame.encode("ascii"))


    def ActionShutter_slider(self, name, value):

        if (value == 0) :
            param = 0x40
        elif (value == 1):
            param = 0x41
        elif (value == 2):
            param = 0x42
        elif (value == 3):
            param = 0x43
        elif (value == 4):
            param = 0x44
        elif (value == 5):
            param = 0x45
        elif (value == 6):
            param = 0x46
        elif (value == 7):
            param = 0x47
        elif (value == 8):
            param = 0x48
        elif (value == 9):
            param = 0x49
        elif (value == 10):
            param = 0xA4
        elif (value == 11):
            param = 0x4B
        elif (value == 12):
            param = 0x4C
        elif (value == 13):
            param = 0x4D
        elif (value == 14):
            param = 0x4E
        elif (value == 15):
            param = 0x4F
        elif (value == 16):
            param = 0x50
        elif (value == 17):
            param = 0x51
        elif (value == 18):
            param = 0x52
        elif (value == 19):
            param = 0x53

        frame = com.build_frame(com.WRITE_OP,com.SHUTTER_REG,param)
        self.serial_conn.write(frame.encode("ascii"))

    def ActionBrightness_slider(self, name, value):
        frame = com.build_frame(com.WRITE_OP,com.BRIGHT_REG,value)
        self.serial_conn.write(frame.encode("ascii"))

    def ActionContrast_slider(self, name, value):
        frame = com.build_frame(com.WRITE_OP,com.CONTRAST_REG,value)
        self.serial_conn.write(frame.encode("ascii"))

    def ActionSaturation_slider(self, name, value):
        frame = com.build_frame(com.WRITE_OP,com.SAT_REG,value)
        self.serial_conn.write(frame.encode("ascii"))

    def ActionSharpen_slider(self, name, value):
        frame = com.build_frame(com.WRITE_OP,com.SHARP_REG,value)
        self.serial_conn.write(frame.encode("ascii"))

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

        # --------- Connect camera ---------
        video_text = self.video_port_combo.currentText()
        index = None

        if sys.platform.startswith("linux") and video_text.startswith("/dev/video"):
            # Example: /dev/video0 → index 0
            index = int(video_text.replace("/dev/video", ""))
        elif sys.platform.startswith("win"):
            if ":" in video_text:
                # Example: "0: Integrated Webcam" → index 0
                index = int(video_text.split(":")[0].strip())
            elif video_text.isdigit():
                # Fallback: just "0"
                index = int(video_text)

        if index is not None:
            self.camera_widget.start_camera(index)
            print(f"Camera connected to {video_text}")
            connected = True

        # --------- Connect serial ---------
        serial_text = self.serial_port_combo.currentText()

        # Close any existing serial connection first
        if hasattr(self, "serial_conn") and self.serial_conn is not None:
            if self.serial_conn.is_open:
                print(f"Closing previously opened serial port {self.serial_conn.port}")
                self.serial_conn.close()

        if serial_text:
            try:
                # Open the serial port at 115200 baud
                self.serial_conn = serial.Serial(port=serial_text, baudrate=115200, timeout=1)
                if self.serial_conn.is_open:
                    print(f"Serial port connected to {serial_text} at 115200 baud")
                    connected = True
            except Exception as e:
                print(f"Failed to open serial port {serial_text}: {e}")
                self.serial_conn = None
        else:
            self.serial_conn = None

        # Enable tabs if connected to at least one device
        self.tabs.setTabEnabled(1, connected)
        self.tabs.setTabEnabled(2, connected)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
