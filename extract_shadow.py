"""Convert a PNG image into a silhouette SVG.

This script reads a PNG, detects the opaque region (or the subject),
creates a filled black mask of that region and writes an SVG containing
one or more <path> elements. Everything outside the silhouette is
transparent when rendered by an SVG viewer.

Usage:
    python extract_shadow.py input.png output.svg

Dependencies are listed in requirements.txt and can be installed with
`pip install -r requirements.txt`.
"""

import sys
import cv2
import numpy as np
import svgwrite


def png_to_svg_shadow(input_path: str, output_path: str) -> None:
    # read image (preserve alpha if present)
    img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"could not read image '{input_path}'")

    # build binary mask of the subject
    if img.shape[2] == 4:
        alpha = img[:, :, 3]
        # anything with alpha > 0 is part of object
        _, mask = cv2.threshold(alpha, 0, 255, cv2.THRESH_BINARY)
    else:
        # use brightness threshold if no alpha
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)

    # optionally clean up the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # find external contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        raise ValueError("no contours found in the image--is the file empty?")

    height, width = mask.shape

    dwg = svgwrite.Drawing(output_path, size=(width, height))
    dwg.viewbox(0, 0, width, height)

    # add all contours as filled black paths
    for cnt in contours:
        pts = [(int(p[0][0]), int(p[0][1])) for p in cnt]
        if not pts:
            continue
        # build path data string
        path_data = f"M {pts[0][0]} {pts[0][1]}"
        for x, y in pts[1:]:
            path_data += f" L {x} {y}"
        path_data += " Z"
        dwg.add(dwg.path(d=path_data, fill="black", stroke="none"))

    dwg.save()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extract_shadow.py <input.png> <output.svg>")
        sys.exit(1)

    inp, outp = sys.argv[1], sys.argv[2]
    try:
        png_to_svg_shadow(inp, outp)
        print(f"wrote silhouette SVG to {outp}")
    except Exception as exc:
        print("error:", exc)
        sys.exit(2)
