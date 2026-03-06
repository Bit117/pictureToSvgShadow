# Image to SVG Shadow Extractor

A simple Python command-line tool that extracts the silhouette ("shadow")
from any raster image (PNG, JPEG, WEBP, etc.) and outputs a corresponding
SVG file with the region filled in black and the rest left transparent.

## Features

- Detects subject via alpha channel or brightness.
- Cleans up small holes with morphological operations.
- **Adjustable fill intensity**: Control shadow solidity from outline-only to fully filled.
- Converts outlines into SVG `<path>` elements.
- Outputs an SVG that is the same size as the input image.
- Modern PyQt5 GUI with real-time preview.

## Requirements

Install dependencies via pip:

```bash
pip install -r requirements.txt
```

## Usage

### Command-line

```bash
# Basic usage (default: fully filled shadow)
python extract_shadow.py example.png shadow.svg

# With fill intensity control (0-100)
# 0 = outline only, 100 = solid fill
python extract_shadow.py example.png shadow.svg 50
python extract_shadow.py example.jpg shadow.svg 0
```

### Graphical User Interface (PyQt5)

**NEW**: The application now features a modern PyQt5 GUI with real-time preview!

Run the GUI:

```bash
python app.py
```

**Features**:

- **Two Preview Windows**: See both original image and shadow result side-by-side
- **Square, Scrollable / Zoomable Previews**: Both preview panels maintain a square region; use the mouse wheel or double-click to zoom in/out, with scrollbars appearing for images larger than the square
- **Fill Intensity Slider**: Adjust from 0 (detail lines & facial features) to 100 (solid fill)
  - Low values (0-30): Extract fine detail lines - perfect for capturing facial features, contours
  - Medium values (30-70): Balance between details and fill
  - High values (70-100): More solid shadow
- **Advanced Filters**: Three additional sliders let you tune the edge detection that produces the mask:
  - **Blur** – smooths the source before edge detection; higher values reduce noise but may erase thin lines
  - **Canny low / Canny high** – thresholds for the Canny edge detector; lower thresholds make the algorithm more sensitive to faint edges
  - **Close** – size of the morphological kernel used to bridge gaps in the raw edge map
  Adjusting these parameters can reveal facial features or help separate foreground from a busy/white background.
- **Live Preview**: See the effect immediately as you adjust the sliders
- **Export as SVG**: Click the export button to save the result

The preview updates in real-time as you move the slider, allowing you to find the perfect balance between detail and solid shadows.

## Notes

- The tool looks for the external contour(s) of opaque or non-black regions.
  In the original version only an alpha channel or a simple brightness
  threshold was used, which meant that non‑transparent images with light
  or white backgrounds produced completely filled silhouettes.  The current
  release uses edge detection and contour analysis (with an Otsu fallback)
  to reliably segment the foreground object even on complex or pale
  backgrounds.
- **Fill Intensity Control**:
  - **0-30%**: Outline and detail lines mode - captures facial features, internal contours, and fine details
  - **30-70%**: Medium mode - blends details with partial fill
  - **70-100%**: Solid fill mode - progressively fills in shadows
- If you need more advanced edge detection (e.g. for smooth gradients),
  you can preprocess the image or modify the script.
- Further enhancements might include exporting one path per connected
  component, smoothing the path, or using a vectorization library like
  `potrace` for higher-quality curves.

## Building a standalone executable

The PyQt5 GUI can be bundled into a single `.exe` using
[PyInstaller](https://www.pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
```

After running the command the executable will appear in `dist/app.exe`.
Double-click it to start the GUI; the behaviour is identical to running
`python app.py`.
