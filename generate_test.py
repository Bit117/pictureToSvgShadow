import cv2, numpy as np

img = np.zeros((100,100,4), dtype=np.uint8)
cv2.circle(img,(50,50),30,(255,255,255,255),-1)
cv2.imwrite(r'c:\Users\admin\Documents\code\project\pngToSvg\test.png', img)
print('wrote test.png')
