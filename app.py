import os
import sys
import cv2
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QSlider, QFileDialog, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QImage, QFont
from extract_shadow import generate_shadow_mask, image_to_svg_shadow


class SquareScrollArea(QScrollArea):
    """A QScrollArea that always tries to remain square.

    The layout system will query heightForWidth when arranging widgets. By
    returning the same value we encourage a square region. A size hint is also
    provided for reasonable initial dimensions.
    """
    def heightForWidth(self, width):
        return width

    def hasHeightForWidth(self):
        return True

    def sizeHint(self):
        return QSize(350, 350)


class ImageToSvgShadowApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image to SVG Shadow Converter")
        self.setGeometry(50, 50, 1400, 900)
        
        self.input_image_path = None
        self.original_pixmap = None
        self.shadow_pixmap = None
        # hold full‑size pixmaps for zooming
        self.original_pixmap_full = None
        self.shadow_pixmap_full = None
        # current zoom factors (0 means "fit to area" initially)
        self.original_zoom = 0.0
        self.shadow_zoom = 0.0
        
        self.init_ui()
        # install event filter so we can capture wheel events on the labels
        self.original_label.installEventFilter(self)
        self.shadow_label.installEventFilter(self)
    
    def init_ui(self):
        """Initialize the user interface with improved layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout: preview area (left) + controls (right)
        main_layout = QHBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # ========== LEFT SIDE: Preview Area ==========
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # Original image preview
        left_layout.addWidget(self._create_section_label("Original Image"))
        self.original_label = QLabel()
        # remove hard limits so that previews can grow and scroll
        # self.original_label.setMinimumSize(280, 280)
        # self.original_label.setMaximumSize(350, 350)
        self.original_label.setStyleSheet(
            "border: 1px solid #ddd; background-color: #f5f5f5; border-radius: 4px;"
        )
        self.original_label.setAlignment(Qt.AlignCenter)
        # put inside a scroll area so user can pan/zoom
        self.original_scroll = SquareScrollArea()
        self.original_scroll.setWidget(self.original_label)
        self.original_scroll.setWidgetResizable(True)
        left_layout.addWidget(self.original_scroll)
        
        # Shadow preview
        left_layout.addWidget(self._create_section_label("Shadow Preview"))
        self.shadow_label = QLabel()
        # self.shadow_label.setMinimumSize(280, 280)
        # self.shadow_label.setMaximumSize(350, 350)
        self.shadow_label.setStyleSheet(
            "border: 1px solid #ddd; background-color: #000; border-radius: 4px;"
        )
        self.shadow_label.setAlignment(Qt.AlignCenter)
        self.shadow_scroll = SquareScrollArea()
        self.shadow_scroll.setWidget(self.shadow_label)
        self.shadow_scroll.setWidgetResizable(True)
        left_layout.addWidget(self.shadow_scroll)
        
        left_layout.addStretch()
        
        # ========== RIGHT SIDE: Control Panel ==========
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)
        
        # Title
        title_label = QLabel("Controls")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        right_layout.addWidget(title_label)
        
        # Open image button
        self.open_btn = QPushButton("📁 Open Image")
        self.open_btn.clicked.connect(self.open_image)
        self.open_btn.setMinimumHeight(40)
        self.open_btn.setFont(QFont("Arial", 10))
        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        right_layout.addWidget(self.open_btn)
        
        # Image info
        self.image_info_label = QLabel("No image selected")
        self.image_info_label.setStyleSheet("color: #666; font-size: 11px;")
        self.image_info_label.setWordWrap(True)
        right_layout.addWidget(self.image_info_label)
        
        right_layout.addSpacing(15)
        
        # Separator line
        separator = QLabel()
        separator.setStyleSheet("border-top: 1px solid #ddd;")
        separator.setFixedHeight(1)
        right_layout.addWidget(separator)
        
        right_layout.addSpacing(10)
        
        # Fill intensity section
        intensity_title = QLabel("Fill Intensity")
        intensity_title_font = QFont()
        intensity_title_font.setPointSize(11)
        intensity_title_font.setBold(True)
        intensity_title.setFont(intensity_title_font)
        right_layout.addWidget(intensity_title)
        
        # Slider value display
        self.intensity_label = QLabel("100%")
        intensity_value_font = QFont()
        intensity_value_font.setPointSize(18)
        intensity_value_font.setBold(True)
        intensity_value_font.setFamily("Courier New")
        self.intensity_label.setFont(intensity_value_font)
        self.intensity_label.setAlignment(Qt.AlignCenter)
        self.intensity_label.setStyleSheet("color: #2196F3; padding: 5px;")
        right_layout.addWidget(self.intensity_label)
        
        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(100)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(10)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #ddd;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1976D2;
            }
        """)
        self.slider.sliderMoved.connect(self.on_slider_changed)
        right_layout.addWidget(self.slider)
        
        # Slider labels
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("0%\n(Detail)"))
        info_layout.addStretch()
        info_layout.addWidget(QLabel("100%\n(Solid)"))
        info_label_style = "font-size: 10px; color: #999; text-align: center;"
        for widget in [info_layout.itemAt(i).widget() for i in range(info_layout.count()) if info_layout.itemAt(i).widget()]:
            widget.setStyleSheet(info_label_style)
        right_layout.addLayout(info_layout)
        
        right_layout.addSpacing(20)
        
        # Advanced parameters heading
        adv_title = QLabel("Advanced Filters")
        adv_font = QFont()
        adv_font.setPointSize(11)
        adv_font.setBold(True)
        adv_title.setFont(adv_font)
        right_layout.addWidget(adv_title)
        
        # blur kernel size
        blur_layout = QHBoxLayout()
        blur_layout.addWidget(QLabel("Blur"))
        self.blur_label = QLabel("5")
        blur_layout.addStretch()
        blur_layout.addWidget(self.blur_label)
        right_layout.addLayout(blur_layout)
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setMinimum(1)
        self.blur_slider.setMaximum(31)
        self.blur_slider.setSingleStep(2)
        self.blur_slider.setPageStep(2)
        self.blur_slider.setValue(5)
        self.blur_slider.setTickPosition(QSlider.TicksBelow)
        self.blur_slider.setTickInterval(5)
        self.blur_slider.sliderMoved.connect(lambda v: self._update_label(self.blur_label, v))
        self.blur_slider.sliderMoved.connect(self.on_slider_changed)
        right_layout.addWidget(self.blur_slider)
        
        # canny thresholds
        canny_layout = QHBoxLayout()
        canny_layout.addWidget(QLabel("Canny low"))
        self.canny_low_label = QLabel("50")
        canny_layout.addStretch()
        canny_layout.addWidget(self.canny_low_label)
        right_layout.addLayout(canny_layout)
        self.canny_low_slider = QSlider(Qt.Horizontal)
        self.canny_low_slider.setMinimum(0)
        self.canny_low_slider.setMaximum(255)
        self.canny_low_slider.setValue(50)
        self.canny_low_slider.setTickPosition(QSlider.TicksBelow)
        self.canny_low_slider.setTickInterval(51)
        self.canny_low_slider.sliderMoved.connect(lambda v: self._update_label(self.canny_low_label, v))
        self.canny_low_slider.sliderMoved.connect(self.on_slider_changed)
        right_layout.addWidget(self.canny_low_slider)
        
        canny_high_layout = QHBoxLayout()
        canny_high_layout.addWidget(QLabel("Canny high"))
        self.canny_high_label = QLabel("150")
        canny_high_layout.addStretch()
        canny_high_layout.addWidget(self.canny_high_label)
        right_layout.addLayout(canny_high_layout)
        self.canny_high_slider = QSlider(Qt.Horizontal)
        self.canny_high_slider.setMinimum(0)
        self.canny_high_slider.setMaximum(255)
        self.canny_high_slider.setValue(150)
        self.canny_high_slider.setTickPosition(QSlider.TicksBelow)
        self.canny_high_slider.setTickInterval(51)
        self.canny_high_slider.sliderMoved.connect(lambda v: self._update_label(self.canny_high_label, v))
        self.canny_high_slider.sliderMoved.connect(self.on_slider_changed)
        right_layout.addWidget(self.canny_high_slider)
        
        # closing kernel size
        close_layout = QHBoxLayout()
        close_layout.addWidget(QLabel("Close"))
        self.close_label = QLabel("5")
        close_layout.addStretch()
        close_layout.addWidget(self.close_label)
        right_layout.addLayout(close_layout)
        self.close_slider = QSlider(Qt.Horizontal)
        self.close_slider.setMinimum(1)
        self.close_slider.setMaximum(31)
        self.close_slider.setSingleStep(2)
        self.close_slider.setPageStep(2)
        self.close_slider.setValue(5)
        self.close_slider.setTickPosition(QSlider.TicksBelow)
        self.close_slider.setTickInterval(5)
        self.close_slider.sliderMoved.connect(lambda v: self._update_label(self.close_label, v))
        self.close_slider.sliderMoved.connect(self.on_slider_changed)
        right_layout.addWidget(self.close_slider)
        
        right_layout.addSpacing(20)
        
        # Separator
        separator2 = QLabel()
        separator2.setStyleSheet("border-top: 1px solid #ddd;")
        separator2.setFixedHeight(1)
        right_layout.addWidget(separator2)
        
        right_layout.addSpacing(10)
        
        # Export button
        self.export_btn = QPushButton("✓ Export as SVG")
        self.export_btn.clicked.connect(self.export_svg)
        self.export_btn.setMinimumHeight(45)
        self.export_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover:!disabled {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #999;
            }
        """)
        right_layout.addWidget(self.export_btn)
        
        right_layout.addStretch()
        
        # Assemble main layout (give the preview more weight than the controls)
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)
        
        central_widget.setLayout(main_layout)
    
    def _create_section_label(self, text: str) -> QLabel:
        """Create a styled section label."""
        label = QLabel(text)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet("color: #333;")
        return label

    def _update_label(self, label: QLabel, value: int) -> None:
        """Utility used by sliders to show the current value."""
        label.setText(str(value))
    
    def open_image(self):
        """Open file dialog to select an image."""
        filetypes = "Image files (*.png *.jpg *.jpeg *.webp *.bmp *.tiff);;All files (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select an image", "", filetypes
        )
        
        if file_path:
            self.input_image_path = file_path
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / 1024  # KB
            self.image_info_label.setText(f"📄 {file_name}\n({file_size:.1f} KB)")
            self.export_btn.setEnabled(True)
            self.slider.setValue(100)  # Reset slider
            # reset zoom so the image initially fits
            self.original_zoom = 0.0
            self.shadow_zoom = 0.0
            self.update_previews()
    
    def on_slider_changed(self):
        """Update preview when slider is moved."""
        if self.input_image_path:
            self.update_previews()
    
    def update_previews(self):
        """Update both original and shadow previews."""
        if not self.input_image_path:
            return
        
        fill_intensity = self.slider.value()
        self.intensity_label.setText(f"{fill_intensity}%")
        # advanced params
        blur = self.blur_slider.value()
        canny_low = self.canny_low_slider.value()
        canny_high = self.canny_high_slider.value()
        close_sz = self.close_slider.value()
        
        try:
            # Load original image
            original_img = cv2.imread(self.input_image_path, cv2.IMREAD_UNCHANGED)
            if original_img is None:
                raise ValueError("Failed to load image")
            
            # Convert to RGB(A)
            if len(original_img.shape) == 3:
                if original_img.shape[2] == 4:
                    original_rgb = cv2.cvtColor(original_img, cv2.COLOR_BGRA2RGBA)
                else:
                    original_rgb = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
            else:
                original_rgb = cv2.cvtColor(original_img, cv2.COLOR_GRAY2RGB)
            
            # save full pixmap for zooming
            self.original_pixmap_full = self._convert_to_pixmap(original_rgb)
            # apply current zoom (or fit if zoom == 0)
            self._apply_zoom(self.original_label, self.original_pixmap_full, self.original_zoom, self.original_scroll)
            
            # Generate and display shadow mask
            mask, height, width, _ = generate_shadow_mask(
                self.input_image_path,
                fill_intensity,
                blur_ksize=blur,
                canny_low=canny_low,
                canny_high=canny_high,
                close_ksize=close_sz,
            )
            
            # Convert mask to displayable format
            display_img = np.zeros((height, width, 3), dtype=np.uint8)
            display_img[mask > 0] = [255, 255, 255]  # White shadow
            
            self.shadow_pixmap_full = self._convert_to_pixmap(display_img)
            self._apply_zoom(self.shadow_label, self.shadow_pixmap_full, self.shadow_zoom, self.shadow_scroll)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update preview:\n{str(e)}")
    
    def _scale_image(self, img: np.ndarray, max_size: int = 330) -> np.ndarray:
        """Scale image to fit preview area while maintaining aspect ratio.

        This helper is still used in tests and some non‑GUI paths, but the
        viewer itself now prefers to work with the full image and let the
        scroll/zoom logic handle sizing.
        """
        height, width = img.shape[:2]
        scale = min(max_size / width, max_size / height)
        scaled_width = int(width * scale)
        scaled_height = int(height * scale)
        return cv2.resize(img, (scaled_width, scaled_height))
    
    def _apply_zoom(self, label: QLabel, pixmap: QPixmap, zoom: float, scroll_area: QScrollArea):
        """Scale a stored pixmap according to the zoom factor and apply to a label.

        `zoom` is a floating point multiplier (1.0 == 100%).  A sentinel value of
        0 means "fit to square area" – the largest square that fits inside the
        scroll area's viewport.  This keeps the original behaviour during the
        initial display but enforces a square preview region.
        """
        # Basic sanity checks
        if pixmap is None:
            return
        if scroll_area is None or not hasattr(scroll_area, "viewport"):
            # fallback: just show original pixmap scaled by zoom
            try:
                size = pixmap.size() * (zoom or 1.0)
                label.setPixmap(pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                label.adjustSize()
            except Exception:
                pass
            return

        try:
            if zoom == 0:
                # fit to the largest square inside the viewport
                area = scroll_area.viewport().size()
                side = min(area.width(), area.height())
                area = QSize(side, side)
                scaled = pixmap.scaled(area, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                size = pixmap.size() * zoom
                scaled = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled)
            label.adjustSize()
        except Exception as e:
            # keep application running; log to console
            print(f"[Warning] _apply_zoom failed: {e}")

    def eventFilter(self, source, event):
        # intercept wheel events on the preview labels to zoom
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.Wheel and source in (self.original_label, self.shadow_label):
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            if source is self.original_label:
                self.original_zoom *= factor
                # clamp
                self.original_zoom = max(0.1, min(self.original_zoom, 10))
                self._apply_zoom(self.original_label, self.original_pixmap_full, self.original_zoom, self.original_scroll)
            else:
                self.shadow_zoom *= factor
                self.shadow_zoom = max(0.1, min(self.shadow_zoom, 10))
                self._apply_zoom(self.shadow_label, self.shadow_pixmap_full, self.shadow_zoom, self.shadow_scroll)
            return True
        elif event.type() == QEvent.MouseButtonDblClick and source in (self.original_label, self.shadow_label):
            # double‑click toggles between fit and 100%
            if source is self.original_label:
                self.original_zoom = 1.0 if self.original_zoom == 0.0 else 0.0
                self._apply_zoom(self.original_label, self.original_pixmap_full, self.original_zoom, self.original_scroll)
            else:
                self.shadow_zoom = 1.0 if self.shadow_zoom == 0.0 else 0.0
                self._apply_zoom(self.shadow_label, self.shadow_pixmap_full, self.shadow_zoom, self.shadow_scroll)
            return True
        return super().eventFilter(source, event)

    def _convert_to_pixmap(self, cv_img: np.ndarray) -> QPixmap:
        """Convert OpenCV image to QPixmap."""
        h, w = cv_img.shape[:2]
        if len(cv_img.shape) == 3 and cv_img.shape[2] == 3:
            ch = 3
            bytes_per_line = ch * w
            qt_image = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            ch = 1
            bytes_per_line = w
            qt_image = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        
        return QPixmap.fromImage(qt_image)
    
    def export_svg(self):
        """Export the current image as SVG."""
        if not self.input_image_path:
            QMessageBox.warning(self, "Warning", "Please select an image first")
            return
        
        # Suggest output path
        base_name = os.path.splitext(os.path.basename(self.input_image_path))[0]
        suggested_path = os.path.join(os.path.dirname(self.input_image_path), f"{base_name}_shadow.svg")
        
        filetypes = "SVG files (*.svg);;All files (*.*)"
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save SVG", suggested_path, filetypes
        )
        
        if output_path:
            try:
                fill_intensity = self.slider.value()
                image_to_svg_shadow(self.input_image_path, output_path, fill_intensity)
                QMessageBox.information(
                    self, "✓ Success", 
                    f"SVG exported successfully!\n\n{output_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export SVG:\n{str(e)}")


def main():
    app = QApplication(sys.argv)
    window = ImageToSvgShadowApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
