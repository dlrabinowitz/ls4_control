############################
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2024-01-16
# @Filename: ls4_camera.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# mosaic.py
#
################################

import sys
from astropy.io import fits
import warnings
from astropy.io.fits.verify import VerifyWarning
import argparse
import numpy as np

# Notes about LS4 tap lines and CCD placement
#
# For each quadrant of the CCD (NW, NE, SW, SE) there are 8 connectors (A, B, ..., H)
# on the mother board, one for each CCD location in the focal plane:
#
#         __________________NORTH__________________
#       |                     |                     |
#       | NW-A NW-B NW-C NW-D | NE-E NE-F NE-G NE-H |
#       |                     |                     |
#       |                     |                     |
#       |                     |                     |
#       | NW-E NW-F NW-G NW-H | NE-A NE-B NE-C NE-D |
#       |                     |                     |
#  WEST | ____________________|_____________________| EAST
#       |                     |                     |
#       |                     |                     |
#       | SW-A SW-B SW-C SW-D | SE-E SE-F SE-G SE-H |
#       |                     |                     |
#       |                     |                     |
#       |                     |                     |
#       | SW-E SW-F SW-G SW-H | SE-A SE-B SE-C SE-D |
#       |                     |                     |
#       | __________________SOUTH___________________|
#
#
# The controller reads out each CCD by two video amplifier outputs or "taps". These
# two outputs read out the "left" and "right" halves of the CCD, respectively.
# and max 8 CCDs. However, the controller can be configured only a subset of the tap.
#
# The taps are numbered 1 to 16, and are assigned a direction for storing the images
# pixels into the frame buffer ("L" or "R"). This preserves the relative pixel orientation
# in the data buffer. The connection in the mother board are assigned taps, as follows:
#
# motherboard controller taps
# location    (left, right)
# A           AD3L,  AD4R
# B           AD2L,  AD1R
# C           AD8L,  AD7R
# D           AD6L,  AD5R
# E           AD12L, AD11R
# F           AD10L, AD9R
# G           AD13L, AD14R
# H           AD15L, AD16R
#
#
# The relevant FITS header parmeters are:
#CCD_NAME= 'NE_A    '
#AMP_NAME= 'RIGHT   '
#TAP_NAME= 'AD4L    '
#
#
ccd_map = {'NW_A':[0,0],
           'NW_B':[1,0],
           'NW_C':[2,0],
           'NW_D':[3,0],
           'NE_E':[4,0],
           'NE_F':[5,0],
           'NE_G':[6,0],
           'NE_H':[7,0],
           'NW_E':[0,1],
           'NW_F':[1,1],
           'NW_G':[2,1],
           'NW_H':[3,1],
           'NE_A':[4,1],
           'NE_B':[5,1],
           'NE_C':[6,1],
           'NE_D':[7,1],
           'SW_A':[0,2],
           'SW_B':[1,2],
           'SW_C':[2,2],
           'SW_D':[3,2],
           'SE_E':[4,2],
           'SE_F':[5,2],
           'SE_G':[6,2],
           'SE_H':[7,2],
           'SW_E':[0,3],
           'SW_F':[1,3],
           'SW_G':[2,3],
           'SW_H':[3,3],
           'SE_A':[4,3],
           'SE_B':[5,3],
           'SE_C':[6,3],
           'SE_D':[7,3]}

ccds_per_row = 8
ccds_per_col = 4
amps_per_ccd = 2
#CCD_NAME= 'NE_A    '
#AMP_NAME= 'RIGHT   '
#TAP_NAME= 'AD4L    '


def write_fits(data=None,header=None,output='test.fits'):

    warnings.simplefilter('ignore',category=VerifyWarning)
    hdu = fits.PrimaryHDU(data)
    fits_header = hdu.header
    for k in header:
      fits_header[k] = header[k]

    hdul = fits.HDUList([hdu])
    hdul.writeto(output,overwrite=True)
    hdul.close()

def subtract_col_bias(data=None,pre_x=0,post_x=0,pre_y=0,post_y=0,amp_name=None,y1=None,y2=None):

    width=data.shape[1]
    height=data.shape[0]

    if amp_name == 'LEFT':
        x1 = width-post_x+1
        x2 = width
    else:
        x1=1
        x2 = post_x-1
    n=0
    z1=0.0
    z2=0.0
    for x in range(x1,x2):
        for y in range(y1,y2):
            z = float(data[y][x])
            z2 = z2 + (z*z)
            z1 = z1 + z
            n += 1

    try:
      avg= z1/float(n)
      rms = np.sqrt((z2/(float(n)) - avg*avg))
    except Exception as e:
      print("unable to get meaningful avg and rms from overscan: %s" % e)
      sys.exit(-1)

    #3-sigma clip
    n=0
    z1=0.0
    z2=0.0
    z_min = avg-(3.0*rms)
    z_max = avg+(3.0*rms)
    for x in range(x1,x2):
        for y in range(y1,y2):
            z = float(data[y][x])
            if z>z_min and z < z_max:
              z2 = z2 + (z*z)
              z1 = z1 + z
              n += 1

    try:
      if n>10:
        avg= z1/float(n)
        rms = np.sqrt((z2/(float(n)) - avg*avg))
      else:
        avg=0.0
        rms=0.0
    except Exception as e:
      print("bad sigma clipping: %s" % e)



    temp_data = np.zeros(shape=data.shape,dtype=np.double)
    temp_data = data
    temp_data = temp_data - avg + 1000.0
    data1 = np.zeros(shape=data.shape,dtype=np.ushort)
    data1 = temp_data

    return data1,avg,rms

def subtract_row_bias(data=None,pre_x=0,post_x=0,pre_y=0,post_y=0,amp_name=None):

    width=data.shape[1]
    height=data.shape[0]

    n=0
    z1=0.0
    z2=0.0
    y1 = height-10
    y2 = height
    x1=1
    x2=width

    for y in range(y1,y2):
       for x in range(x1,x2):
            z = float(data[y][x])
            z2 = z2 + (z*z)
            z1 = z1 + z
            n += 1
    avg= z1/float(n)
    rms = np.sqrt((z2/(float(n)) - avg*avg))
    data1 = (data + 1000) - int(avg)

    return data1,avg,rms

def assemble_mosaic(conf=None):
  im_list = conf['images']
  im_list_dark = None
  num_images = len(im_list)
  num_dark_images=0

  print("%s" % conf['dark_images'])
  if conf['dark_images'] != ['']:
     im_list_dark = conf['dark_images']
     num_dark_images = len(im_list_dark)
     if num_dark_images != num_images:
        print("dark image mismatch: %d %d" % (num_images,num_dark_images))
        sys.exit(-1)

  im = im_list[0]
  hdu_list = fits.open(im)
  im_head = hdu_list[0].header
  width=im_head['NAXIS1']
  height=im_head['NAXIS2']
  prescan_x = 6
  postscan_x = width - prescan_x - 1024
  prescan_y = 0
  postscan_y = height - 4096
  if postscan_y < 0:
     postscan_y = 0

  mos_data=np.zeros(shape=[ccds_per_col*height,ccds_per_row*amps_per_ccd*width],dtype=np.ushort)

  shape = (hdu_list[0].data).shape
  im_index = 0
  for im in im_list:
     hdu_list = fits.open(im)
     im_data_raw = hdu_list[0].data
     im_dark_data_raw = None
     im_head = hdu_list[0].header
     assert im_data_raw.shape == shape,\
             "image %s has shape(%s) inconsitent with first image(%s)" %\
                   (im,im_data_raw.shape,shape)
     ccd_name= im_head['CCD_NAME'].strip()
     amp_name = im_head['AMP_NAME'].strip()
     tap_name = im_head['TAP_NAME'].strip()

     position = amp_name

     assert ccd_name in ccd_map.keys(),"ccd_name %s not in ccd_map" % ccd_name
     assert amp_name in ['LEFT','RIGHT'],"amp_name %s must be LEFT or RIGHT" % amp_name

     if im_list_dark is not None:
        im_dark = im_list_dark[im_index]
        hdu_list = fits.open(im_dark)
        im_dark_data_raw = hdu_list[0].data
        assert im_dark_data_raw.shape == shape,\
             "dark image %s has shape(%s) inconsitent with first image(%s)" %\
                   (im_dark,im_dark_data_raw.shape,shape)
        im_index += 1

     # flip meaning of Right and Left
     if amp_name == 'RIGHT':
          position = 'LEFT'
     elif amp_name == 'LEFT':
          position = 'RIGHT'


     y1 = 10
     y2 = shape[0]

     """
     if (tap_name in ["AD1R", "AD2L"] ) and ("SW" in  ccd_name):
         y1 = y2 - 40
         print("y1,y2 = %d %d" % (y1,y2))
     """

     if  im_dark_data_raw is not None:
       im_data_raw = im_data_raw + 1000 - im_dark_data_raw

     if conf['bias']:
       im_data,bias,rms = subtract_col_bias(im_data_raw,prescan_x, postscan_x,prescan_y,postscan_y,amp_name,y1,y2)
     else:
       im_data=im_data_raw
       bias=0.0
       rms=0.0

     min_val = np.min(im_data)
     max_val = np.max(im_data)

     offsets = ccd_map[ccd_name]
     x0 = offsets[0]*width*amps_per_ccd
     if position == 'RIGHT':
        x0 += width
     y0 = offsets[1]*height
     print("ccd_name: %6s  tap_name: %6s amp_name: %6s bias: %07.1f rms: %07.3f image: %s" % \
            (ccd_name,tap_name,amp_name,bias,rms,im))

     mos_data[y0:y0+height,x0:x0+width]=np.flip(im_data)
     hdu_list.close()
  
  write_fits(mos_data,im_head,conf['output'])

def namelist(s):
    return s.split(",")

def get_params():
  conf={}
  parser = argparse.ArgumentParser(description="tool to make mosaic fromLS4 exposure images")
  parser.add_argument('--images', metavar='i', type=namelist, default='')
  parser.add_argument('--dark_images', metavar='d', type=namelist, default=[])
  parser.add_argument('--x1', metavar='x', type=int, default=-1)
  parser.add_argument('--dx', metavar='w', type=int, default=-1)
  parser.add_argument('--y1', metavar='y', type=int, default=-1)
  parser.add_argument('--dy', metavar='h', type=int, default=-1)
  parser.add_argument('--output', metavar='c', type=str, default='test.fits')
  parser.add_argument('--bias', metavar='b', type=bool, default=False)
  conf.update(vars(parser.parse_args()))

  return (conf)

conf = get_params()
assemble_mosaic(conf)
