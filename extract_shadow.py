"""Convert a raster image into a silhouette SVG.

This script reads any image file that OpenCV can decode (PNG, JPEG,
WEBP, etc.), detects the opaque or non‑black region (the subject),
creates a filled black mask of that region and writes an SVG containing
one or more <path> elements. Everything outside the silhouette is
transparent when rendered by an SVG viewer.

Usage:
    python extract_shadow.py input.png output.svg
    python extract_shadow.py input.jpg output.svg
    python extract_shadow.py input.webp output.svg

Dependencies are listed in requirements.txt and can be installed with
`pip install -r requirements.txt`.
"""
# author: 2026-03-03 by dong


import sys
import cv2
import numpy as np
import svgwrite


def generate_shadow_mask(
    input_path: str,
    fill_intensity: int = 100,
    blur_ksize: int = 5,
    canny_low: int = 50,
    canny_high: int = 150,
    close_ksize: int = 5,
) -> tuple:
    """Load image and generate a shadow mask with adjustable parameters.

    The original implementation only exposed ``fill_intensity``; the
    algorithm now accepts a few additional knobs that control the low‑level
    edge/contour extraction.  These are surfaced via the GUI sliders so the
    user can tune them on problematic inputs.

    Parameters beyond ``fill_intensity`` have the following meaning:

    * ``blur_ksize`` – size of the Gaussian blur kernel (must be odd, >=1).
      Increasing this suppresses fine texture and noise.
    * ``canny_low`` / ``canny_high`` – thresholds for the Canny edge
      detector.  Lower values make the detector more sensitive.
    * ``close_ksize`` – size of the structuring element used when closing
      the raw edge image; larger values bridge wider gaps in edges.

    The remaining behaviour (edge‑based extraction + Otsu fallback, mask
    clean‑up, fill‑intensity erosion) is unchanged.

    Args:
        input_path: Path to the input image
        fill_intensity: 0-100, where 0 is detail lines only, 100 is fully filled
        blur_ksize: odd integer for blur kernel
        canny_low: lower threshold for Canny edges
        canny_high: upper threshold for Canny edges
        close_ksize: kernel size for morphological closing of edge map

    Returns:
        Tuple of (mask, height, width, original_image)
    """
    # read image (preserve alpha if present)
    img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"could not read image '{input_path}'")

    # build binary mask of the subject.  When an alpha channel is present we
    # simply threshold it, but for ordinary RGB images we need a more
    # sophisticated approach because the background might be white (or any
    # other colour) and the naive ``threshold(gray,1)`` used previously would
    # simply select every non‑black pixel and thus end up filling the entire
    # canvas.  The new strategy is:
    #
    # 1. convert to grayscale and blur to suppress noise
    # 2. run Canny edge detection to find outlines of the subject
    # 3. close small gaps in the edge map so we get a few large, continuous
    #    contours
    # 4. pick the largest contour and rasterise it to produce a filled mask
    # 5. if that fails (eg. a very flat image) fall back to an Otsu threshold
    #    and then make sure the smaller of the two regions is treated as the
    #    subject (this handles white backgrounds gracefully)
    if img.shape[2] == 4:
        alpha = img[:, :, 3]
        _, mask = cv2.threshold(alpha, 0, 255, cv2.THRESH_BINARY)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # normalise blur kernel size to an odd number >=1
        bks = max(1, blur_ksize | 1)
        blur = cv2.GaussianBlur(gray, (bks, bks), 0)
        # Canny edge extraction using supplied thresholds
        edges = cv2.Canny(blur, canny_low, canny_high)
        # closing kernel also needs to be odd
        cks = max(1, close_ksize | 1)
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (cks, cks))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_close)

        cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            # largest external contour should correspond to the subject
            best = max(cnts, key=cv2.contourArea)
            mask = np.zeros_like(gray)
            cv2.drawContours(mask, [best], -1, 255, thickness=cv2.FILLED)
        else:
            # fall back to a standard Otsu threshold
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if cv2.countNonZero(mask) > mask.size // 2:
                mask = cv2.bitwise_not(mask)

    # clean up the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # For low fill_intensity, blend edge details with the mask
    if fill_intensity < 50:
        # Extract edges within the mask region to get facial features, etc.
        edges = cv2.Canny(mask, 50, 150)
        # Add the edges detail to the mask
        mask = cv2.bitwise_or(mask, edges)

    # Adjust fill by erosion - lower fill_intensity = more erosion
    if 0 <= fill_intensity < 100:
        erosion_iterations = max(1, int((100 - fill_intensity) / 12))
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.erode(mask, kernel_erode, iterations=erosion_iterations)

    height, width = mask.shape[:2]
    return mask, height, width, img


def image_to_svg_shadow(input_path: str, output_path: str, fill_intensity: int = 100) -> None:
    """Load **any** supported raster image and write a silhouette SVG.

    The behavior is the same as the original ``png_to_svg_shadow`` but
    the name and documentation have been generalized because OpenCV
    already handles dozens of common formats. If the image contains an
    alpha channel it is used to determine the subject; otherwise a
    simple brightness threshold is applied to the grayscale version.
    
    Args:
        input_path: Path to the input image
        output_path: Path to the output SVG
        fill_intensity: 0-100, where 0 is outline only, 100 is fully filled
    """
    mask, height, width, img = generate_shadow_mask(input_path, fill_intensity)

    # find external contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        raise ValueError("no contours found in the image--is the file empty?")

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


# backwards compatibility: original name kept as alias
png_to_svg_shadow = image_to_svg_shadow


if __name__ == "__main__":
    # we tolerate extra parameters for advanced filters; any missing
    # values will use defaults.  The order is:
    #   <input> <output> [fill] [blur] [canny_low] [canny_high] [close]
    if len(sys.argv) < 3 or len(sys.argv) > 8:
        print("Usage: python extract_shadow.py <input-image> <output.svg> [fill_intensity] [blur] [canny_low] [canny_high] [close]")
        print("  fill_intensity: 0-100 (default 100)")
        print("  blur: odd kernel size for Gaussian blur (default 5)")
        print("  canny_low, canny_high: thresholds for edge detection (50,150)")
        print("  close: kernel size for closing operation (default 5)")
        sys.exit(1)

    inp, outp = sys.argv[1], sys.argv[2]
    fill_intensity = 100
    blur = 5
    canny_low = 50
    canny_high = 150
    close = 5
    if len(sys.argv) >= 4:
        try:
            fill_intensity = int(sys.argv[3])
            if not 0 <= fill_intensity <= 100:
                raise ValueError("fill_intensity must be between 0 and 100")
        except ValueError as e:
            print(f"error: {e}")
            sys.exit(1)
    if len(sys.argv) >= 5:
        blur = int(sys.argv[4])
    if len(sys.argv) >= 6:
        canny_low = int(sys.argv[5])
    if len(sys.argv) >= 7:
        canny_high = int(sys.argv[6])
    if len(sys.argv) == 8:
        close = int(sys.argv[7])
    
    try:
        image_to_svg_shadow(
            inp,
            outp,
            fill_intensity,
            blur_ksize=blur,
            canny_low=canny_low,
            canny_high=canny_high,
            close_ksize=close,
        )
        print(
            f"wrote silhouette SVG to {outp} (fill_intensity={fill_intensity}, blur={blur}, canny=({canny_low},{canny_high}), close={close})"
        )
    except Exception as exc:
        print("error:", exc)
        sys.exit(2)

