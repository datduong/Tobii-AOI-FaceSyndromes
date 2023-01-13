import cv2
import json
import numpy as np
import pandas as pd
import os
from pathlib import Path
import pickle
from PIL import Image, ImageDraw
import sys

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------- #

# ! follow https://github.com/rajpurkarlab/cheXlocalize

# ---------------------------------------------------------------------------- #

def calculate_iou(pred_mask, gt_mask, true_pos_only):
    """
    Calculate IoU score between two segmentation masks.

    Args:
        pred_mask (np.array): binary segmentation mask
        gt_mask (np.array): binary segmentation mask
    Returns:
        iou_score (np.float64)
    """
    intersection = np.logical_and(pred_mask, gt_mask)
    union = np.logical_or(pred_mask, gt_mask)

    if true_pos_only:
        if np.sum(pred_mask) == 0 or np.sum(gt_mask) == 0:
            iou_score = np.nan
        else:
            iou_score = np.sum(intersection) / (np.sum(union))
    else:
        if np.sum(union) == 0: 
            # ! union has no overlapping, so return 0 intead of nan ??
            # ! at extreme threshold, this happens if we put in all black images (so 0 or 0 = 0)
            iou_score = np.nan
        else:
            iou_score = np.sum(intersection) / (np.sum(union))

    return iou_score


def cam_to_segmentation(cam_mask, threshold=None, smoothing=False, k=0, img_dir=None, prefix=None, transparent_to_white=False, plot_grayscale_map=False, plot_segmentation=False, plot_default_otsu=False, resize=None, cut_off_pixel=None):
    """
    Threshold a saliency heatmap to binary segmentation mask.
    Args:
        cam_mask (torch.Tensor): heat map in the original image size (H x W).
            Will squeeze the tensor if there are more than two dimensions.
        threshold (np.float64): threshold to use
        smoothing (bool): if true, smooth the pixelated heatmaps using box filtering
        k (int): size of kernel used for box filter smoothing (int); k must be
                 >= 0; if k is > 0, make sure to set if_smoothing to True,
                 otherwise no smoothing would be performed.

    Returns:
        segmentation (np.ndarray): binary segmentation output
    """

    # ! original code reads in pickle https://github.com/rajpurkarlab/cheXlocalize
    # if (len(cam_mask.size()) > 2):
    #     cam_mask = cam_mask.squeeze()

    # assert len(cam_mask.size()) == 2

    # # normalize heatmap
    # mask = cam_mask - cam_mask.min()
    # mask = mask.div(mask.max()).data
    # mask = mask.cpu().detach().numpy()

    # ! read saliency image, or a numpy
    # ! if input is numpy, then it should be 2D matrix on grayscale 0-255
    if type(cam_mask) == str: 
        if transparent_to_white: 
            mask = Image.open(os.path.join(img_dir,cam_mask))
            new_image = Image.new("RGBA", (mask.size), "WHITE") # Create a white rgba background
            new_image.paste(mask, (0, 0), mask)              # Paste the image on the background. Go to the links given below for details.
            mask = new_image.convert('RGB') 
            mask=np.array(mask)  # ! https://stackoverflow.com/questions/43232813/convert-opencv-image-format-to-pil-image-format
        else: 
            mask = cv2.imread(os.path.join(img_dir,cam_mask))

        if resize is not None: 
            mask = cv2.resize(mask, resize, interpolation = cv2.INTER_AREA)

        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY) # ! convert grayscale

        if cut_off_pixel is not None: 
            # remove black pixel that are not dark enough (these can noise, or @thresh needs this?)
            mask = np.array(mask) 
            mask = np.where (mask<cut_off_pixel,mask,0) # set lighter color pixel (above @cut_off_pixel) as 0
            
        if plot_grayscale_map: 
            img = Image.fromarray(np.array(mask), 'L')
            img.show()

    else: 
        # ! 
        if cut_off_pixel is not None: 
            # remove black pixel that are not dark enough (these can noise, or @thresh needs this?)
            mask = np.where (mask<cut_off_pixel,mask,0) # set lighter color pixel (above @cut_off_pixel) as 0
        mask = cam_mask # ! read in numpy, so we set mask=cam_mask
        
    # ---------------------------------------------------------------------------- #

        
    if smoothing:
        # heatmap = cv2.applyColorMap(mask, cv2.COLORMAP_JET) # ! no reason to apply a color mapping to make @heatmap. we already have @heatmap in wanted color
        # gray_img = cv2.boxFilter(cv2.cvtColor(heatmap, cv2.COLOR_RGB2GRAY),
        #                          -1, (k, k)) # ! no reason to convert grayscale if read in as grayscale
        mask = cv2.boxFilter(mask, -1, (k, k)) # ! smoothing on original grayscale image. 

    formated_input_img_as_np = np.array(mask) # ! may need this later for bootstrap, this is the input image after resize and smoothing (if used)
    
    # use Otsu's method to find threshold if no threshold is passed in
    if threshold is None:
        # mask = np.uint8(255 * mask) # ! grayscale should already be on 0-255 unit scale
        #
        mask = 255 - mask # ! this flip 0 into 255 and 255 into 0. 

        # maxval = np.max(mask) 
        maxval = 255 # ! grayscale uses 0 to 255
        thresh = cv2.threshold(mask, 0, maxval, cv2.THRESH_OTSU)[1] # ! this should not differ from @segmentation_output ?? @thres looks same as @segmentation

        if plot_default_otsu: # ! plot
            img = Image.fromarray(np.uint8(thresh), 'L')
            img.show()

        # draw out contours
        cnts = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        polygons = []
        for cnt in cnts:
            if len(cnt) > 1:
                polygons.append([list(pt[0]) for pt in cnt])

        # create segmentation based on contour
        img_dims = (mask.shape[1], mask.shape[0])
        segmentation_output = Image.new("L", img_dims, "#000000") # ! using "Image.new('1', img_dims)" creates a black image. # https://pillow.readthedocs.io/en/stable/reference/Image.html
        for polygon in polygons:
            coords = [(point[0], point[1]) for point in polygon]
            ImageDraw.Draw(segmentation_output).polygon(coords,
                                                        outline=255,
                                                        fill=255) # ! fill=1 fills in white spots, color image 0=black, 255=white
            
        segmentation = np.array(segmentation_output, dtype="int")//255 # mod 255 to bring back to 0/1 scale

    else:
        segmentation_output = None
        thresh = None
        mask = np.array(mask)/255.0 # so white=255 will be converted into value 1, black=0 stays as 0
        segmentation = np.array(mask < threshold, dtype="int") # ! use < because we want black (low value pixel) to show up as TRUE


    if plot_segmentation: # ! plot
        segmentation_as_png = Image.fromarray(np.uint8(segmentation*255), 'L')
        # segmentation_as_png.show()
        prefix = 'smoothk'+str(k) if smoothing else 'nosmooth'
        prefix = prefix + '-' + 'thresh'+str(threshold) if threshold is not None else 'otsu'
        temp = prefix + '-' + cam_mask.split('/')[-1]
        segmentation_as_png.save(os.path.join(img_dir,temp))

    # segmentation must be strict 0/1
    assert np.count_nonzero((segmentation!=0) & (segmentation!=1))==0 # https://stackoverflow.com/questions/40595967/fast-way-to-check-if-a-numpy-array-is-binary-contains-only-0-and-1

    return segmentation, formated_input_img_as_np


# ---------------------------------------------------------------------------- #

# William Syndrome, Image 2, Syndrome vs Non Synrome Correct, Syndrome Name Incorrect
# '22q11.2DS, Image 14, Syndromic vs non syndromic Correct, Syndrome name Correct.png'
 
# k = 20 # ! play around with this. 
# threshold = .8 # np.nan # .5 # np.nan
# smoothing = True


# img_dir = 'C:/Users/duongdb/Documents/ManyFaceConditions12012022/Classify/b4ns448wlEqualss10lr3e-05dp0.2b64ntest1NormalNotAsUnaff/EvalTestImgLabelIndex4/AverageAttr_test_Occlusion2.0/'
# img_name = 'KSSlide133_heatmappositiveAverage.png'
# segmentation_occ, segmentation_output, thresh = cam_to_segmentation(img_name, threshold=threshold, smoothing=smoothing, k=k, img_dir=img_dir, prefix='smoothk10_', transparent_to_white=False,resize=(720,720))

# # ---------------------------------------------------------------------------- #

# k = 20 # ! play around with this. 
# threshold = np.nan # .5 # np.nan
# smoothing = True

# img_dir = 'C:/Users/duongdb/Documents/OneDrive_2022-12-28/Eye Tracking aggregates 2/'

# # for threshold in [.95,.9,.75]:    
# #     print ('thres',threshold)  

# img_name = 'Kabuki Syndrome, Image 11, Syndromic vs Non Syndromic Correct_2.png'

# segmentation, segmentation_output, thresh = cam_to_segmentation(img_name, threshold=threshold, smoothing=smoothing, k=k, img_dir=img_dir, prefix='smoothk10_', transparent_to_white=True)

# # np.count_nonzero((segmentation!=0) & (segmentation!=1))==0 # https://stackoverflow.com/questions/40595967/fast-way-to-check-if-a-numpy-array-is-binary-contains-only-0-and-1

# img_name = 'Kabuki Syndrome, Image 11, Syndromic vs Non Syndromic Incorrect_2.png'
# segmentation2, segmentation_output, thresh = cam_to_segmentation(img_name, threshold=threshold, smoothing=smoothing, k=k, img_dir=img_dir, prefix='smoothk10_', transparent_to_white=True)

# mIoU = calculate_iou(segmentation, segmentation2, true_pos_only=False) 
# print (mIoU)

# mIoU = calculate_iou(segmentation, segmentation_occ, true_pos_only=False) 
# print (mIoU)

# mIoU = calculate_iou(segmentation2, segmentation_occ, true_pos_only=False) 
# print (mIoU)
