import sys
import os
import cv2
import mediapipe as mp
import mido
import time
import numpy as np
import collections
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTextEdit, QSlider, QSizePolicy, QSpacerItem
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QPalette, QColor, QImage, QPixmap, QIcon, QBrush

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
script_dir = os.path.dirname(os.path.realpath(__file__))

class VideoThread(QThread):
    update_frame = pyqtSignal(QImage)
    update_log = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.running = False

    def run(self):
        # Initialize MIDI output
        try:
            self.midi_port = mido.open_output(self.params['midi_port'])
            self.update_log.emit(f"Connected to MIDI port: {self.params['midi_port']}")
        except Exception as e:
            self.update_log.emit(f"Error initializing MIDI: {e}")
            return

        # Initialize MediaPipe Hands
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        mp_drawing = mp.solutions.drawing_utils

        # Initialize webcam
        cap = cv2.VideoCapture(self.params['camera_index'])
        if not cap.isOpened():
            self.update_log.emit("Error: Could not open webcam.")
            return

        # Set higher frame rate if supported
        cap.set(cv2.CAP_PROP_FPS, 60)

        # Initialize history for smoothing
        note_history = collections.deque(maxlen=self.params['smoothing_window'])
        velocity_history = collections.deque(maxlen=self.params['smoothing_window'])

        def hand_to_midi(hand_landmarks):
            raw_note = int(np.interp(hand_landmarks.landmark[8].y, [0, 1], [self.params['max_note'], self.params['min_note']]))
            raw_velocity = int(np.interp(hand_landmarks.landmark[4].y, [0, 1], [127, 30]))
            
            note_history.append(raw_note)
            velocity_history.append(raw_velocity)
            
            note = int(sum(note_history) / len(note_history))
            velocity = int(sum(velocity_history) / len(velocity_history))
            
            return note, velocity

        def is_fist(hand_landmarks):
            return all(hand_landmarks.landmark[tip].y > hand_landmarks.landmark[mid].y 
                       for tip, mid in [(8,6), (12,10), (16,14), (20,18)])

        last_note = None
        last_time = time.time()
        hold_note = False

        self.running = True
        while self.running:
            success, image = cap.read()
            if not success:
                self.update_log.emit("Ignoring empty camera frame.")
                continue

            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
            results = hands.process(image)

            # Apply green tint
            green_tinted = image.copy()
            green_tinted[:,:,0] = image[:,:,0] * 0.5  # Reduce red channel
            green_tinted[:,:,2] = image[:,:,2] * 0.5  # Reduce blue channel
            green_tinted[:,:,1] = np.clip(image[:,:,1] * 1.2, 0, 255)  # Boost green channel

            image = cv2.cvtColor(green_tinted, cv2.COLOR_RGB2BGR)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                    fist = is_fist(hand_landmarks)
                    if fist:
                        hold_note = True
                        self.update_log.emit("Fist detected, holding note")
                    else:
                        hold_note = False
                        self.update_log.emit("Hand open, ready to change note")

                    note, velocity = hand_to_midi(hand_landmarks)
                    self.update_log.emit(f"Smoothed note: {note}, velocity: {velocity}")

                    if not hold_note and (last_note is None or abs(note - last_note) >= self.params['note_change_threshold']):
                        if last_note is not None:
                            for channel in range(16):
                                self.midi_port.send(mido.Message('note_off', note=last_note, channel=channel))
                                self.update_log.emit(f"Sent Note Off: {last_note} on channel {channel}")
                        for channel in range(16):
                            self.midi_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=channel))
                            self.update_log.emit(f"Sent Note On: {note}, Velocity: {velocity} on channel {channel}")
                        last_note = note
                        last_time = time.time()

            elif last_note is not None and time.time() - last_time > 0.1:
                for channel in range(16):
                    self.midi_port.send(mido.Message('note_off', note=last_note, channel=channel))
                    self.update_log.emit(f"Sent Note Off (no hand): {last_note} on channel {channel}")
                last_note = None

            h, w, ch = image.shape
            bytes_per_line = ch * w
            convert_to_qt_format = QImage(image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            p = convert_to_qt_format.scaled(640, 360, Qt.KeepAspectRatio)
            self.update_frame.emit(p)

        cap.release()
        self.midi_port.close()

    def stop(self):
        self.running = False
        self.wait()

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Background, Qt.black)
        self.setPalette(palette)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)

        # App logo
        logo_label = QLabel()
        logo_path = os.path.join(script_dir, 'logo.png')
        logo_pixmap = QPixmap(logo_path).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        layout.addWidget(logo_label)


        # App name
        title_label = QLabel("Madson's Symphony of Freedom")
        title_label.setStyleSheet("color: #00FFCA; font: 12pt 'Consolas';")
        layout.addWidget(title_label)
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Minimize button
        self.minimize_button = QPushButton("−")  # Using a simple minus sign
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setStyleSheet("""
            QPushButton {
                background-color: #333;
                border: none;
                color: #00FFCA;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.minimize_button.clicked.connect(self.parent.showMinimized)
        layout.addWidget(self.minimize_button)

        # Close button
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #333;
                border: none;
                color: #00FFCA;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.close_button.clicked.connect(self.parent.close)
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        self.start = QPoint(0, 0)
        self.pressing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start = self.mapToGlobal(event.pos()) - self.parent.pos()
            self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing:
            self.parent.move(self.mapToGlobal(event.pos()) - self.start)

    def mouseReleaseEvent(self, event):
        self.pressing = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MadHand")
        
        # Remove default title bar
        self.setWindowFlag(Qt.FramelessWindowHint)
        
        # Icon
        script_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(script_dir, 'icon.ico')
        self.setWindowIcon(QIcon(icon_path))

        # Set the background image
        script_dir = os.path.dirname(os.path.realpath(__file__))
        image_path = os.path.join(script_dir, 'green space.jpg')
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(QPixmap(image_path)))
        self.setPalette(palette)

        # Apply styles
        self.setStyleSheet("""
            QLabel { 
                color: #00FFCA; 
                font-size: 16px; 
                font-family: 'Consolas'; 
                padding: 5px;
                background-color: rgba(0, 0, 0, 0);
            }
            QComboBox, QSlider { 
                background-color: rgba(0, 0, 0, 0);
                color: #00FFCA; 
                border: 1px solid #00FFCA; 
                padding: 5px;
                font-family: 'Consolas';
                font-size: 14px;
            }
            QComboBox:hover, QSlider:hover { 
                border: 1px solid #FF00FF; 
            }
            QPushButton { 
                background-color: rgba(0, 0, 0, 0);
                color: #00FFCA; 
                border: 2px solid #00FFCA;
                padding: 10px;
                font-weight: bold;
                font-family: 'Consolas';
                font-size: 14px;
            }
            QPushButton:hover { 
                background-color: rgba(255, 0, 127, 0.5);
                color: #ffffff; 
                border: 2px solid #FF00FF;
            }
            QTextEdit { 
                background-color: rgba(0, 0, 0, 0.5);
                color: #00FFCA; 
                border: 1px solid #00FFCA;
                font-family: 'Consolas';
                font-size: 14px;
                padding: 10px;
            }
        """)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Custom title bar
        self.title_bar = CustomTitleBar(self)
        layout.addWidget(self.title_bar)

        # Title label
        title_label = QLabel("MadHand \n [Handcrafted Sound Waves]")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 20px; 
            font-family: 'Consolas'; 
            font-weight: bold; 
            color: #00FFCA; 
            margin: 5px 0;
            background-color: rgba(0, 0, 0, 0);
            padding: 5px;
        """)
        layout.addWidget(title_label)

        # MIDI Input Selection
        midi_ports = mido.get_output_names()
        midi_layout = self.create_labeled_combo("MIDI Output", midi_ports if midi_ports else ["No MIDI ports available"])
        layout.addLayout(midi_layout)

        # Camera Selection
        camera_layout = self.create_labeled_combo("Webcam", [f"Camera {i}" for i in range(5)])
        layout.addLayout(camera_layout)

        # Min and Max Note
        note_layout = QHBoxLayout()
        note_layout.addLayout(self.create_labeled_slider("Min Note", 0, 127, 21))
        note_layout.addLayout(self.create_labeled_slider("Max Note", 0, 127, 108))
        layout.addLayout(note_layout)

        # Smoothing Window Size
        layout.addLayout(self.create_labeled_slider("Smoothing Window", 1, 20, 8))

        # Note Change Threshold
        layout.addLayout(self.create_labeled_slider("Note Change Threshold", 1, 20, 6))

        # Run and Stop Buttons
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("RUN")
        self.run_button.clicked.connect(self.start_processing)
        self.stop_button = QPushButton("STOP")
        self.stop_button.clicked.connect(self.stop_processing)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        # Video Display
        self.video_label = QLabel()
        self.video_label.setStyleSheet("border: 2px solid #32ad60; background-color: #185032;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_label)

        # Log Display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.log_text)

        self.video_thread = None

    def create_labeled_combo(self, label, items):
        layout = QHBoxLayout()
        label_widget = QLabel(label)
        combo = QComboBox()
        combo.setObjectName(label)
        combo.addItems(items)
        layout.addWidget(label_widget)
        layout.addWidget(combo)
        return layout

    def create_labeled_slider(self, label, min_val, max_val, default_val):
        layout = QHBoxLayout()
        label_widget = QLabel(label)
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName(label)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        value_label = QLabel(str(default_val))
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
        layout.addWidget(label_widget)
        layout.addWidget(slider)
        layout.addWidget(value_label)
        return layout

    def start_processing(self):
        try:
            midi_port = self.findChild(QComboBox, "MIDI Output").currentText()
            if midi_port == "No MIDI ports available":
                raise ValueError("No MIDI ports available")
            
            params = {
                'midi_port': midi_port,
                'camera_index': self.findChild(QComboBox, "Webcam").currentIndex(),
                'min_note': self.findChild(QSlider, "Min Note").value(),
                'max_note': self.findChild(QSlider, "Max Note").value(),
                'smoothing_window': self.findChild(QSlider, "Smoothing Window").value(),
                'note_change_threshold': self.findChild(QSlider, "Note Change Threshold").value()
            }
            
            if params['min_note'] >= params['max_note']:
                raise ValueError("Min Note must be less than Max Note")
            
            self.video_thread = VideoThread(params)
            self.video_thread.update_frame.connect(self.update_video)
            self.video_thread.update_log.connect(self.update_log)
            self.video_thread.start()
            self.run_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        except Exception as e:
            self.update_log(f"Error starting processing: {str(e)}")

    def stop_processing(self):
        if self.video_thread:
            self.video_thread.stop()
            self.run_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def update_video(self, image):
        self.video_label.setPixmap(QPixmap.fromImage(image))

    def update_log(self, message):
        self.log_text.append(message)
        logging.info(message)

    def closeEvent(self, event):
        if self.video_thread:
            self.video_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())