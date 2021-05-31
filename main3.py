# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 09:05:10 2019

This script counts tree rings along a drawn line. 
The script opens a file selector and wait for the user to draw 
a line which the script will count the tree ring along.
Click Esc to move from one screen to another. 

@author: Ron Simenhois
"""

import cv2
import numpy as np
from PIL.Image import Image
from scipy import signal
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

x1, x2, y1, y2 = 0, 0, 0, 0
tImg = None
draw = False


def onMouse(event, x, y, flags, paprm):
    """
    An event call function:
        this function draws  a blue line between the point where the mouse was clicked and the mouse location,
        It saves the end of line points.
    Parameters:
        event: int - the mouse action code
        x, y: int - the curser location on the image
        flags: unused
        params: unused
    returns: None
    """
    global x1, x2, y1, y2, tImg, draw
    if draw:
        tImg = img.copy()
    if event == cv2.EVENT_LBUTTONDOWN:
        draw = True
        x1, x2, y1, y2 = 0, 0, 0, 0
        x1 = x
        y1 = y

    elif event == cv2.EVENT_LBUTTONUP:
        cv2.line(tImg, (x1, y1), (x, y), (255, 0, 0), 2)
        x2, y2 = x, y
        draw = False

    elif event == cv2.EVENT_MOUSEMOVE and flags == cv2.EVENT_FLAG_LBUTTON:
        if draw:
            cv2.line(tImg, (x1, y1), (x, y), (255, 0, 0), 2)
            x2, y2 = x, y


def rotate_image(img, p1, p2):
    """
    Calculate rotation angle to transfom a line between two point to be horizontal
    and rotate an image by this angle
    Parameters:
        img: a numpy array - the image to rotate
        p1, p2: (int,int) - start and end points of the rotation line
    """

    def _rotate_point(p, rotationMatrix):
        """
        A helper function that return point location after linear transformation
        Parameters:
            p:(int, int) - point to transform
            rotationMatrix - transformation matrix
        """
        return rotationMatrix.dot(np.array(p + (1,))).astype(int)

    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        rotation_angle = 90
    else:
        rotation_angle = np.rad2deg(np.arctan((y1 - y2) / (x1 - x2)))

    # center = (int(abs(x1-x2)), int(abs(y1-y2)))
    rows, cols = img.shape[:2]
    center = (cols / 2, rows / 2)
    rotationMat = cv2.getRotationMatrix2D(center, rotation_angle, 1)

    # rotation calculates the cos and sin, taking absolutes of those.
    abs_cos = abs(rotationMat[0, 0])
    abs_sin = abs(rotationMat[0, 1])

    # calculate the new width and height
    new_w = int(rows * abs_sin + cols * abs_cos)
    new_h = int(rows * abs_cos + cols * abs_sin)

    # subtract old image center (bringing image back to original) and add the new image center coordinates before rotation
    rotationMat[0, 2] += new_w / 2 - center[0]
    rotationMat[1, 2] += new_h / 2 - center[1]

    rotated = cv2.warpAffine(img, rotationMat, (new_w, new_h))

    rx1, ry1 = _rotate_point(p1, rotationMat)
    rx2, ry2 = _rotate_point(p2, rotationMat)

    return rotated, rx1, ry1, rx2, ry2


def count_and_map_rings(img, x1, y1, x2, y2):
    """
    Calculates the average pixel intensities of 5 pixels along the counting line, 
    draw rectangle of the area where the intensities are calculated and uses derivitive > 0 to idenrify ring locations
    amd number of rings
    Parameters:
        img: numpy array - the image rotated to where the marked count line is horizontal 
        x1: int - the x location at the begining of the count line on the rotated image
        y1: int - the y location at the begining of the count line on the rotated image
        x2: int - the x location at the end of the count line on the rotated image
        y2: int - the x location at the end of the count line on the rotated image
    Return:
        line: numpy array - the image with 60 pixels around the count line by the line length
        inensity: numpy array float (1, count line length) - average pixel intensity of 5 pixles around the count line
        threshold: float - # of std from mean to set as threshold for ring count
        rings: numpy array bool (1, count line length) - True for ring marker, False inbtween rings
        count: int - number of rings in line
    """
    # Define image strip around the ring count line
    line = img[ry1 - 30: ry1 + 30, min(rx1, rx2):max(rx1, rx2)]
    gray = cv2.cvtColor(line[30:35, :, :], cv2.COLOR_BGR2GRAY)

    threshold = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 3, 3)
    # kernel = np.ones((5, 5), np.float32) / 25
    # gaussian = cv2.filter2D(np.asarray(threshold), -1, kernel)

    # # 연결되어 있던 것을 끊어내 주기 위해 opening
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
    # res = cv2.Canny(closing, 120, 220)

    # sobelX = cv2.Sobel(closing, cv2.CV_64F, 1, 0, ksize=1)
    # sobelX = cv2.convertScaleAbs(sobelX)
    # sobelY = cv2.Sobel(closing, cv2.CV_64F, 0, 1, ksize=1)
    # sobelY = cv2.convertScaleAbs(sobelY)
    # res = cv2.addWeighted(sobelX, 1, sobelY, 1, 0)

    res = cv2.Laplacian(closing, cv2.CV_8U)

    line = cv2.rectangle(line, (0, 30), (line.shape[1], 35), (0, 0, 0), 1)
    n = 2
    b = [1.0 / n] * n
    a = 1.0
    m_res = res.mean(axis=0)
    f_intensity = signal.filtfilt(b, a, m_res)
    rings = (np.diff(np.clip(np.diff(f_intensity), -10, 0)) < -1)
    count = int((np.diff(rings) > 0).sum() / 2)

    return line, m_res, rings, count


def plot_map_rings(img, intensity, rings, count):
    """
    Show the image section aroung the ring count line and plot pixel intensity along the ring count line and ring
    locatuons below.
    Parameters:
        img: numpy array - the image with 60 pixels around the count line by the line length
        inensity: numpy array float (1, count line length) - average pixel intensity of 5 pixles around the count line
        threshold: float - # of std from mean to set as threshold for ring count
        rings: numpy array bool (1, count line length) - True for ring marker, False inbtween rings
        count: int - number of rings in img
    Return:
        None
    """
    fig, (axim, axin, axring) = plt.subplots(nrows=3, ncols=1, figsize=(15, 8))
    axim.imshow(img[..., ::-1], aspect="auto")
    axim.set_title("Cross section of the tree trunk where the ring are counted")
    axim.axis("off")
    axim.margins(0)
    axin.plot(intensity)
    axin.set_title("Average pixle intencity on the y axis inside the black box")
    # axin.hlines(threshholds, xmax=-1, xmin=len(intensity), colors="r")
    axin.margins(0)
    x = np.arange(rings.shape[0])
    axring.fill_between(x, 0, rings)
    axring.set_title("Ring markers, total ring count is {}".format(count))
    axring.margins(0)
    plt.tight_layout()
    plt.show()


def save_rings_map(rings):
    Tk().withdraw()
    save_file = asksaveasfilename(filetypes=[("Comma Separated Values", "*.csv")]) + ".csv"
    if save_file != ".csv":
        rings_map = (np.diff(rings) > 0)
        df = pd.DataFrame({"pixels from center": list(range(rings_map.shape[0])), "rings": rings_map})
        df = df[df["rings"] == True]
        df = df[["pixels from center"]]
        df["ring id"] = list(range(df.shape[0]))
        df.to_csv(save_file, index=False)


# Select image and read it
Tk().withdraw()
img_file = askopenfilename(filetypes=(("jpeg files", "*.jpg"), ("all files", "*.*")))
img = cv2.imread(img_file)

# Set the window and mouse event for line draw with a mouse
cv2.namedWindow("Tree rings", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Tree rings", onMouse)

tImg = img.copy()
# Wait for a line to be drawn and update the image with a new line every time the  mouse moves
while True:
    cv2.imshow("Tree rings", tImg)
    k = cv2.waitKey(30)
    if k & 0xFF == 27:
        cv2.destroyAllWindows()
        break

if (x1, y1) != (x2, y2):
    tImg = img.copy()

    # ################## TEST ####################
    gray = cv2.cvtColor(tImg, cv2.COLOR_BGR2GRAY)
    threshold = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 3, 3)
    # t_kernel = np.ones((5, 5), np.float32) / 25
    # t_gaussian = cv2.filter2D(np.asarray(t_threshold), -1, t_kernel)

    # # 연결되어 있던 것을 끊어내 주기 위해 opening
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
    # res = cv2.Canny(closing, 120, 220)

    # sobelX = cv2.Sobel(closing, cv2.CV_64F, 1, 0, ksize=3)
    # sobelX = cv2.convertScaleAbs(sobelX)
    # sobelY = cv2.Sobel(closing, cv2.CV_64F, 0, 1, ksize=3)
    # sobelY = cv2.convertScaleAbs(sobelY)
    # res = cv2.addWeighted(sobelX, 1, sobelY, 1, 0)

    res = cv2.Laplacian(closing, cv2.CV_8U)

    cv2.imshow('gray', gray)
    # cv2.imshow('gaussian', gaussian)
    cv2.imshow('threshold', threshold)
    cv2.imshow('opening', opening)
    cv2.imshow('closing', closing)
    cv2.imshow('res', res)
    cv2.waitKey()
    cv2.destroyAllWindows()
    # exit()
    # ################## TEST ####################

    # Rotate the image so the drawn line will be horizontal for easy calculations
    rotated, rx1, ry1, rx2, ry2 = rotate_image(tImg, (x1, y1), (x2, y2))

    img_strip, intensity, rings_map, rings_count = count_and_map_rings(rotated, rx1, ry1, rx2, ry2)
    plot_map_rings(img_strip, intensity, rings_map, rings_count)
    print('The age of the tree:' + repr(rings_count) + ' years')
