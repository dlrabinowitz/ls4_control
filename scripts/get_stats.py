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

    hdu = fits.PrimaryHDU(data)
    fits_header = hdu.header
    for k in header:
      fits_header[k] = header[k]

    hdul = fits.HDUList([hdu])
    hdul.writeto(output,overwrite=True)
    hdul.close()

def get_colbias_stats(data=None,pre_x=0,post_x=0,pre_y=0,post_y=0,amp_name=None):

    width=data.shape[1]
    height=data.shape[0]

    y1 = int(height/2)
    y2 = height
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
    avg= z1/float(n)
    rms = np.sqrt((z2/(float(n)) - avg*avg))

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

    if n>10:
      avg= z1/float(n)
      rms = np.sqrt((z2/(float(n)) - avg*avg))
    else:
      avg=0.0
      rms=0.0

    return avg,rms

def get_rowbias_stats(data=None,pre_x=0,post_x=0,pre_y=0,post_y=0,amp_name=None):

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

    return avg,rms

def get_stats(conf=None):
  im_list = conf['images']
  num_images = len(im_list)

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


  shape = (hdu_list[0].data).shape
  for im in im_list:
     hdu_list = fits.open(im)
     im_data_raw = hdu_list[0].data
     im_head = hdu_list[0].header
     assert im_data_raw.shape == shape,\
             "image %s has shape(%s) inconsitent with first image(%s)" %\
                   (im,im_data_raw.shape,shape)
     ccd_name= im_head['CCD_NAME'].strip()
     amp_name = im_head['AMP_NAME'].strip()

     # for the NE quadrant CCD in A position, orientations are reversed for both amps
     if ccd_name == 'NE_A' and amp_name == 'LEFT':
            amp_name = 'RIGHT'
     elif ccd_name == 'NE_A' and amp_name == 'RIGHT':
            amp_name = 'LEFT'


     assert ccd_name in ccd_map.keys(),"ccd_name %s not in ccd_map" % ccd_name
     assert amp_name in ['LEFT','RIGHT'],"amp_name %s must be LEFT or RIGHT" % amp_name

     col_avg,col_rms = get_colbias_stats(im_data_raw,prescan_x, postscan_x,prescan_y,postscan_y,amp_name)
     row_avg,row_rms = get_rowbias_stats(im_data_raw,prescan_x, postscan_x,prescan_y,postscan_y,amp_name)

     print("%s  colbavg,rms: %7.3f %7.3f rowavg,rms: %7.3f %7.3f image: %s %s" % (ccd_name,col_avg,col_rms,row_avg,row_rms,im,amp_name))

def namelist(s):
    return s.split(",")

def get_params():
  conf={}
  parser = argparse.ArgumentParser(description="tool to make mosaic fromLS4 exposure images")
  parser.add_argument('--images', metavar='i', type=namelist, default='')
  parser.add_argument('--x1', metavar='x', type=int, default=-1)
  parser.add_argument('--dx', metavar='w', type=int, default=-1)
  parser.add_argument('--y1', metavar='y', type=int, default=-1)
  parser.add_argument('--dy', metavar='h', type=int, default=-1)
  parser.add_argument('--output', metavar='c', type=str, default='test.fits')
  parser.add_argument('--bias', metavar='b', type=bool, default=False)
  conf.update(vars(parser.parse_args()))

  return (conf)

conf = get_params()
get_stats(conf)
