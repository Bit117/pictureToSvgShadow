import os, sys
print('CWD:', os.getcwd())
try:
    from extract_shadow import image_to_svg_shadow
    print('imported extract_shadow')
except Exception as e:
    print('IMPORT_ERROR', e)
    raise

try:
    import numpy as np
    import cv2
    print('imported numpy and cv2')
except Exception as e:
    print('LIB_IMPORT_ERROR', e)
    raise

# create RGBA image
h,w = 100,100
img = np.zeros((h,w,4), dtype=np.uint8)
cv2.circle(img, (50,50), 30, (255,255,255,255), -1)
input_path = 'test_input.png'
cv2.imwrite(input_path, img)
output_dir = 'test_output'
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, 'test_output.svg')

try:
    image_to_svg_shadow(input_path, output_path)
    print('SUCCESS', output_path)
    print('OUTPUT_SIZE', os.path.getsize(output_path))
    with open(output_path, 'r', encoding='utf-8') as f:
        data = f.read(200)
    print('PREVIEW:', data.replace('\n','\\n'))
except Exception as e:
    print('CONVERT_ERROR', e)
    raise
