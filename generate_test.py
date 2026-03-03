import cv2, numpy as np
import os

from extract_shadow import image_to_svg_shadow

OUTDIR = r'c:\Users\admin\Documents\code\project\pictureToSvgShadow\test_outputs'
if not os.path.exists(OUTDIR):
    os.makedirs(OUTDIR)

# create a simple RGBA circle image
img = np.zeros((100, 100, 4), dtype=np.uint8)
cv2.circle(img, (50, 50), 30, (255, 255, 255, 255), -1)

# save in a few common formats
paths = []
for ext in ('png', 'jpg', 'webp'):
    path = os.path.join(OUTDIR, f'test.{ext}')
    cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) if ext != 'png' else img)
    paths.append(path)
    print(f'wrote {path}')

# convert each to SVG shadow using our utility
for path in paths:
    svg_path = os.path.splitext(path)[0] + '.svg'
    image_to_svg_shadow(path, svg_path)
    print(f'created shadow {svg_path}')
