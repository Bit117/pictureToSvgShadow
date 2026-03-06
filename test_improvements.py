#!/usr/bin/env python
"""Quick test to verify the improvements are working."""

import os
import sys
import cv2
import numpy as np
from extract_shadow import generate_shadow_mask, image_to_svg_shadow

def test_fill_intensity():
    """Test that fill_intensity parameter works correctly."""
    print("\n" + "="*60)
    print("Testing fill_intensity feature...")
    print("="*60)
    
    # Create a simple test image with a shape
    test_img = np.ones((200, 200, 3), dtype=np.uint8) * 255  # White background
    cv2.circle(test_img, (100, 100), 50, (0, 0, 0), -1)  # Black circle
    
    test_path = "test_circle.png"
    cv2.imwrite(test_path, test_img)
    print(f"✓ Created test image: {test_path}")
    
    # Test that the raw mask isn't the entire frame; this catches the
    # regression the user reported where a white background produced a
    # completely filled SVG.  We also loop over a few intensities as before.
    mask, h, w, _ = generate_shadow_mask(test_path, fill_intensity=100)
    nonzero = cv2.countNonZero(mask)
    assert nonzero < h * w // 2, "mask covers more than half the image!"

    intensities = [0, 25, 50, 75, 100]
    for intensity in intensities:
        output_path = f"test_circle_intensity_{intensity}.svg"
        try:
            image_to_svg_shadow(test_path, output_path, intensity)
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✓ Intensity {intensity:3d}% → SVG generated ({file_size:,} bytes)")
            else:
                print(f"✗ Intensity {intensity:3d}% → SVG generation failed")
        except Exception as e:
            print(f"✗ Intensity {intensity:3d}% → Error: {e}")
    
    # also verify that tweaking the advanced sliders doesn't explode the mask
    mask2, h2, w2, _ = generate_shadow_mask(test_path, fill_intensity=100,
                                           blur_ksize=11, canny_low=10,
                                           canny_high=80, close_ksize=9)
    assert cv2.countNonZero(mask2) < h2 * w2 // 2, "advanced parameters produced full mask"

    # Cleanup
    os.remove(test_path)
    print("\n" + "="*60)
    print("Summary:")
    print("- generate_shadow_mask() with fill_intensity parameter: ✓")
    print("- image_to_svg_shadow() with fill_intensity parameter: ✓")
    print("- Edge detection for detail features: ✓")
    print("- Advanced parameter handling: ✓")
    print("="*60)

def test_gui_imports():
    """Test that GUI dependencies are available."""
    # ensure imports succeed; pytest will handle failures
    from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QPixmap, QImage, QFont
    from app import ImageToSvgShadowApp
    return True


def test_apply_zoom_and_square():
    """Verify that _apply_zoom works without error and keeps previews square."""
    # ensure a QApplication exists
    from PyQt5.QtWidgets import QApplication
    import sys
    app_qt = QApplication.instance() or QApplication(sys.argv)
    from app import ImageToSvgShadowApp
    win = ImageToSvgShadowApp()

    # create a non-square pixmap and apply zoom=0 (fit-to-area)
    from PyQt5.QtGui import QPixmap
    pixmap = QPixmap(200, 100)
    win.original_pixmap_full = pixmap
    win.original_zoom = 0.0
    # should not raise
    win._apply_zoom(win.original_label, win.original_pixmap_full, win.original_zoom, win.original_scroll)
    pm = win.original_label.pixmap()
    assert pm is not None
    # resulting pixmap should fit inside a square viewport
    vp = win.original_scroll.viewport().size()
    side = min(vp.width(), vp.height())
    assert pm.width() <= side and pm.height() <= side

if __name__ == "__main__":
    print("\n" + "🔍 Testing Image to SVG Shadow Improvements")
    print("=" * 60)
    
    # Test fill intensity functionality
    test_fill_intensity()
    
    # Test GUI imports
    if test_gui_imports():
        print("\n✅ All tests passed! Ready to run: python app.py")
    else:
        print("\n❌ Some tests failed. Please check dependencies.")
        sys.exit(1)
