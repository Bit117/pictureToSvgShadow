# Image to SVG Shadow Extractor

A simple Python command-line tool that extracts the silhouette ("shadow")
from any raster image (PNG, JPEG, WEBP, etc.) and outputs a corresponding
SVG file with the region filled in black and the rest left transparent.

## Features

- Detects subject via alpha channel or brightness.
- Cleans up small holes with morphological operations.
- Converts outlines into SVG `<path>` elements.
- Outputs an SVG that is the same size as the input PNG.

## Requirements

Install dependencies via pip:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python extract_shadow.py example.png shadow.svg
python extract_shadow.py example.jpg shadow.svg
python extract_shadow.py example.webp shadow.svg
```

You can then open `shadow.svg` in any viewer; the black shape represents
the filled shadow, and the remainder will be transparent.

## Notes

- The tool currently looks for the external contour(s) of opaque
  or non‑black regions. If you need more advanced edge detection (e.g.
  for smooth gradients), you can preprocess the image or modify the
  script.

- Further enhancements might include exporting one path per connected
  component, smoothing the path, or using a vectorization library like
  `potrace` for higher-quality curves.
