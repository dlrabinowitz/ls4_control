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
from astropy.modeling import models, fitting
from astropy.modeling.models import Spline1D
from astropy.modeling.fitting import SplineSmoothingFitter
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

def subtract_surface(data=None,pre_x=0,post_x=0,pre_y=0,post_y=0,amp_name=None,y1=None,y2=None):

    width=data.shape[1]
    height=data.shape[0]


    if amp_name == 'LEFT':
        x1 = width-post_x+1
        x2 = width
        fit_x1 = 10
        fit_x2 = x1  - 10 
    else:
        x1=1
        x2 = post_x-1
        fit_x1 = x2 + 10
        fit_x2 = width - 10


    x_mid = (fit_x1 + fit_x2 ) /2
    xa = int(x_mid - 10)
    xb = int(x_mid + 10)
    y_mid = (y1 + y2 ) /2
    ya = int(y_mid - 10)
    yb = int(y_mid + 10)

    temp_data = np.zeros(shape=data.shape,dtype=np.double)
    temp_data = data
    print("shape temp_data: %s" % str(temp_data.shape))
    data1 = np.zeros(shape=data.shape,dtype=np.ushort)
    data1 = data

    print("y1,y2: %d %d" % (y1,y2))
    print("fit_x1,fit_x2: %d %d" % (fit_x1,fit_x2))

    p_init=models.Polynomial2D(degree=3)
    #fit_p = fitting.LevMarLSQFitter()
    fit_p = fitting.LinearLSQFitter()
    z = temp_data[y1:y2,fit_x1:fit_x2]

    """
    y,x = np.mgrid[:z.shape[0],:z.shape[1]]
    p = fit_p(p_init,x,y,z)
    z_pred = p(x,y)
    print("before correction: min,max = %7.3f %7.3f" % (z.min(),z.max()))
    offset = np.average(z[ya:yb,xa:xb])
    print("offset = %7.3f" % offset)
    z = z - z_pred + offset
    print("after correction: min,max = %7.3f %7.3f" % (z.min(),z.max()))
    data1[y1:y2,fit_x1:fit_x2] = z
    """

    """
    x=range(fit_x1,fit_x2)
    x=np.asarray(x)
    for row in range(y1,y2):
      y = temp_data[row,fit_x1:fit_x2]
      try:
        pfit=np.polyfit(x,y,deg=3)
      except Exception as e:
        print ("Exception getting polyfit: %s" % e)
        pfit=[0.0,0.0]

      p = np.poly1d(pfit)
      data1[row,fit_x1:fit_x2] = y - p(x) + np.average(y)
    """

    x=range(fit_x1,fit_x2)
    x=np.asarray(x)
    spl = Spline1D()
    fitter = SplineSmoothingFitter()

    block_size=100
    row = y1
    while row < y2:

      # compute average of 10 rows
      if row + block_size < y2:
         b = block_size
      else:
         b = y2 - row + 1

      row2 = row + b
      if row2 > row+1:
        y = temp_data[row,fit_x1:fit_x2]
        n_rows = 1.0
        for r in range(row+1,row2):
           y += temp_data[r,fit_x1:fit_x2]
           n_rows += 1.0
        y = y / n_rows

        # fit spline to average
        sfit = fitter(spl,x,y,k=3,s=len(y)/10)

        # subtract spline for each of the rows in the block
        for r in range(row,row2):
          offset = np.average(temp_data[row,fit_x1:fit_x2])
          dy = temp_data[r,fit_x1:fit_x2] - sfit(x) + offset
          data1[r,fit_x1:fit_x2] = dy 
          print ("row %d: max-min = %7.3f" % (r,dy.max()-dy.min()))

      # go to the next block of rows
      row += block_size

    return data1


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

  mos_data=np.zeros(shape=[ccds_per_col*height,ccds_per_row*amps_per_ccd*width],dtype=np.ushort)

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
     tap_name = im_head['TAP_NAME'].strip()

     #print(ccd_name,amp_name,tap_name)

     position = amp_name

     assert ccd_name in ccd_map.keys(),"ccd_name %s not in ccd_map" % ccd_name
     assert amp_name in ['LEFT','RIGHT'],"amp_name %s must be LEFT or RIGHT" % amp_name


     # flip meaning of Right and Left
     if amp_name == 'RIGHT':
          position = 'LEFT'
     elif amp_name == 'LEFT':
          position = 'RIGHT'



     if (tap_name == "AD2L" ) and ("SW" in  ccd_name):
         y1 = 10
         y1 = shape[0] - 40
         surface_fit = True
     else:
         y1 = 10
         y2 = shape[0]
         surface_fit = False


     if conf['bias']:
       im_data,bias,rms = subtract_col_bias(im_data_raw,prescan_x, postscan_x,prescan_y,postscan_y,amp_name,y1,y2)
     else:
       im_data=im_data_raw
       bias=0.0
       rms=0.0

     if surface_fit:
       y1 = 1
       y2 = shape[0]-postscan_y
       im_data = subtract_surface(im_data,prescan_x, postscan_x,prescan_y,postscan_y,amp_name,y1,y2)

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
