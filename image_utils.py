"""
    Contains various image utility functions.
    Most importantly:
     *add_saliency_to_image to overlay frames with saliency maps
     *and generate_video to create videos from given frames.
"""

import numpy as np
import matplotlib.pyplot as plt
import coloredlogs, logging
import skimage
from skimage import filters, transform
import skimage.feature
from skimage.util import *
import sys
import cv2
import os
import re
import scipy

def add_saliency_to_image(saliency, image, saliency_brightness = 2):
    '''
    adds a saliency map(in green) over a given image
    :param saliency: the saliency map to be applied
    :param image: the original image
    :param saliency_brightness: the brightness of the saliency map
    :return: the overlayed image
    '''
    
    image_shape = (image.shape[0],image.shape[1])
    saliency = transform.resize(saliency, image_shape, order=0, mode='reflect')
    
    zeros = np.zeros(image_shape)
    saliency = np.stack((zeros, saliency, zeros), axis=-1)
    saliency *= saliency_brightness

    final_image = image + saliency
    final_image = np.clip(final_image, 0, 1)
    
    return final_image
    
def add_blur_saliency_to_image(saliency, image, saliency_brightness = .9):
    '''
    adds a saliency map(in green) over a given image
    :param saliency: the saliency map to be applied
    :param image: the original image
    :param saliency_brightness: the brightness of the saliency map
    :return: the overlayed image
    : site with info on tracking pacman: https://rdmilligan.wordpress.com/2015/01/12/opencv-contours-for-pac-man/
    '''

    image_shape = (image.shape[0],image.shape[1])
    
    saliency = transform.resize(saliency, image_shape, order=0, mode='reflect')
    saliency *= saliency_brightness
#    print("Blur mask: ")
#    print(saliency)
    final_image, edges = simple_non_uniform_blur(image, saliency)
    final_image[edges] = (252,252,252)
    
    final_image = np.clip(final_image, 0, 1)
    return final_image
    
def simple_non_uniform_blur(img, sal, percentile=.85, sigma_img=5, sigma_sal=10):

# percentile: how tight of circles to draw around saliency
# sigma_img: how blurry to make the blurred parts
# sigma_sal: how much to combine nearby regions into one

    sal_blurred = scipy.ndimage.filters.gaussian_filter(sal, sigma_sal)
    img_blurred = scipy.ndimage.filters.gaussian_filter(img, [sigma_img, sigma_img, 0])
    levels = sorted(sal_blurred.flat)
    mask = sal_blurred > levels[int(percentile*len(levels))]
    
    # try to add white line to edge here
    edged_mask = skimage.feature.canny(mask, sigma = 3)
    
#    final_array = np.moveaxis(np.array([mask*img[:, :, i] + (~mask)*img_blurred[:, :, i] for i in range(3)]),[1, 2, 0], [0, 1, 2])

    final_array = np.moveaxis(np.array([mask*img[:, :, i] + (~mask)*img_blurred[:, :, i] for i in range(3)]),[1, 2, 0], [0, 1, 2])
    
    return final_array, edged_mask

def create_edge_image(image):
    ''' creates a edge version of an image
    :param image: the original image
    :return: edge only version of the image
    '''
    image = skimage.color.rgb2gray(image)
    image = filters.sobel(image)
    image = np.stack((image, image, image), axis=-1)
    return image

def output_saliency_map(saliency, image, scale_factor = 3, saliency_factor = 10, edges = True):
    ''' scales the image and adds the saliency map
    :param saliency:
    :param image:
    :param scale_factor: factor to scale height and width of the image
    :param saliency_factor:
    :param edges: if True, creates a edge version of the image first
    :return:
    '''
    image = np.squeeze(image)
    output_shape = (image.shape[0] * scale_factor, image.shape[1] * scale_factor)
    image = transform.resize(image, output_shape, order=0, mode='reflect')
    if edges:
        image = create_edge_image(image, output_shape)

    final_image = add_saliency_to_image(saliency, image, saliency_factor)

    return final_image
    
def output_blur_saliency_map(saliency, image, scale_factor = 3, saliency_factor = 2, edges = True):
    ''' scales the image and adds the saliency map
    :param saliency:
    :param image:
    :param scale_factor: factor to scale height and width of the image
    :param saliency_factor:
    :param edges: if True, creates a edge version of the image first
    :return:
    '''
    
    image = np.squeeze(image)
    output_shape = (image.shape[0] * scale_factor, image.shape[1] * scale_factor)
    image = transform.resize(image, output_shape, order=0, mode='reflect')
    
    if edges:
        image = create_edge_image(image, output_shape)

    final_image = add_blur_saliency_to_image(saliency, image, saliency_factor)

    return final_image

def saliency_in_channel(saliency, image, scale_factor = 3, saliency_brightness = 2, channel = 1):
    '''
    Ressizes image and adds saliency
    :param saliency:
    :param image:
    :param scale_factor:
    :param saliency_factor:
    :return:
    '''
    image = np.squeeze(image)
    output_shape = (image.shape[0] * scale_factor, image.shape[1] * scale_factor)
    image = transform.resize(image, output_shape, order=0, mode='reflect')
    saliency = transform.resize(saliency, output_shape, order=0, mode='reflect')
    saliency = saliency * saliency_brightness
    image[:,:,channel] = saliency
    image = np.clip(image, 0, 1)

    return image

def normalise_image(image):
    '''normalises image by forcing the min and max values to 0 and 1 respectively
     :param image: the input image
    :return: normalised image as numpy array
    '''
    try:
        image = np.asarray(image)
    except:
        print('Cannot convert image to array')
    image = image - image.min()
    if image.max() != 0:
        image = image / image.max()
    return image

def show_image(image):
    '''shortcut to show an image with matplotlib'''
    plt.imshow(image)
    plt.show()

def crop_image_button(image, part = 0.18 ):
    '''
    cuts the lower *part* from an image
    :param image: the image to be cropped
    :param part: part of the image to be cut (expects floats between 0 and 1)
    :return: the cropped image
    '''
    image_length = image.shape[0]
    pixels = int(image_length * part)
    crop = image[0:image_length - pixels,:, :]
    return crop
    
def draw_black_box(image):
    # Create the basic mask
    mask = np.ones(shape=image.shape[0:2], dtype="bool")
    # Draw filled rectangle on the mask image
    rows, columns = skimage.draw.rectangle(start=(368, 130), end=(470, 220))
    mask[rows, columns] = False
    image[~mask] = 0
    return image

def add_black_pixels(image,pixels = 80):
    '''
    adds black pixels to the bottom of an image
    :param image: the image
    :param pixels: the number of black pixels to be added
    :return: image with black pixels
    '''
    image_length = image.shape[0]
    new_image = np.zeros((image_length + pixels, image.shape[1], image.shape[2]), dtype=image.dtype)
    new_image[0:image_length, :, :] = image
    return new_image


def interpolate(array1, array2, t):
    '''
    linear interpolation between two frames of a state
    :param array1: starting array
    :param array2: end array
    :param t: time parameter, goes from -1 to 3 ( 0=0.25, 3=1 in the normal interpolation formula)
    :return: the interpolated array
    '''
    t = (t * 0.25) + 0.25
    float_array = (array2 * t) + (array1 * (1 - t))
    int_array = float_array.astype('uint8')
    return int_array

def generate_video(args, image_folder, out_path, name="video.mp4", image_indices=None, crop_images = True, black_pixels = 80):
    ''' creates a video from images in a folder
    :param image_folder: folder containing the images
    :param out_path: output folder for the video
    :param name: name of the output video
    :param image_indices: states to be included in the summary video
    :return: nothing, but saves the video in the given path
    '''
    
    logger = logging.getLogger()
    coloredlogs.install(level='DEBUG', fmt='%(asctime)s,%(msecs)03d %(filename)s[%(process)d] %(levelname)s %(message)s')
    logger.setLevel(logging.DEBUG)
    
    if args.verbose:
        logger.info("Image indices are: ")
        logger.info(image_indices)
    if not (os.path.isdir(image_folder)):
                os.makedirs(image_folder)
    #            os.rmdir(image_folder)
    images = [img for img in os.listdir(image_folder)]
    images = natural_sort(images)
    #fourcc = cv2.VideoWriter_fourcc(*'H264') #important for browser support, MP4V is not working with browsers
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 30
    height, width, layers = 420,320,3
    if not (os.path.isdir(out_path)):
        os.makedirs(out_path)
    video = cv2.VideoWriter(out_path + name, fourcc, fps, (width,height + black_pixels))
    if (args.verbose):
        logger.info("Just made video writer")
    old_state_index = None
    black_frame = np.zeros((height + black_pixels, width, layers),np.uint8)
    black_frame_number = int(fps)

    # Make Movies
    for image in images:
        to_write = False
        if (args.verbose):
            logger.info("Not to write")
        try:
            image_str = image.split('_')
            state_index = int(image_str[1])
            if (args.verbose):
                logger.info("Just broke up image string: " + str(state_index))
            if (state_index in image_indices) or (image_indices is None):
                if (args.verbose):
                    logger.info("check if the states are successive and insert black frames, if the are not")
                if old_state_index != None and state_index != old_state_index + 1 and state_index != old_state_index:
                    for n in range(black_frame_number):
                        if (args.verbose):
                            logger.info("write a black frame")
                        video.write(black_frame)
                old_state_index = state_index

                i = cv2.imread(os.path.join(image_folder, image))
                if (args.verbose):
                    logger.debug("IMREAD")
                if crop_images:
                    i = crop_image_button(i, part = 0.05)
                    if (args.verbose):
                        logger.info("Crop images")
                i = cv2.resize(i, (width,height))
                if (args.verbose):
                    logger.info("Resize")
                if crop_images:
                    i = add_black_pixels(i, pixels=black_pixels)
                    if (args.verbose):
                        logger.info("Add black pixels")
                if crop_images:
                    i = draw_black_box(i)
                to_write = True
        except Exception as e:
            print(e)
            if (args.verbose):
                print('Try next image.')
            continue
        if to_write:
            if args.verbose:
                logger.info("And to write is true")
                logger.info("and i is " + str(image_str))
            video.write(i)
            if (args.verbose):
                logger.info("And to write is true")

    cv2.destroyAllWindows()
    video.release()

def natural_sort( l ):
    """ Sort the given list in natural sort (the way that humans expect).
    """
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    l.sort( key=alphanum_key )
    return l

def save_image(file_name,image):
    """
    saves image under file_name and creates the directory if it does not exist yet
    :param file_name:
    :param image:
    :return: nothing
    """
    if not (os.path.isdir(file_name)):
        os.makedirs(file_name)
        os.rmdir(file_name)
    plt.imsave(file_name, image)

#pass



