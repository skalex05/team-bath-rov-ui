import cv2
import pathlib
import os
import numpy as np

image_path = pathlib.Path(os.getcwd()) / "Stereo_Images"

# Load images (fix your paths first)

print(str(image_path / "L_0.png"))

imgL = cv2.imread(str(image_path / "L_0.png"), cv2.IMREAD_GRAYSCALE)
imgR = cv2.imread(str(image_path / "R_0.png"), cv2.IMREAD_GRAYSCALE)

# Verify images loaded properly
if imgL is None or imgR is None:
    print("Error: Could not load images")
    exit()

# Create StereoBM object with valid parameters
stereo = cv2.StereoBM_create(numDisparities=64, blockSize=21)  # blockSize must be odd

# Compute disparity
disparity = stereo.compute(imgL, imgR)

# Normalize for display
disparity_normalized = cv2.normalize(disparity, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)

# Display results
cv2.imshow('Disparity', disparity_normalized)
cv2.waitKey(0)
cv2.destroyAllWindows()