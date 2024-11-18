#!/home/daver/ls4_venv/bin/python
# get_telemetry.py
#
# read telemetry keywords from list of files and plot values

import sys
import matplotlib.pyplot as plt
import datetime
from astropy.io import fits

def read_list(file=None):

  file_list=[]
  try:
     f=open(file,"r")
     for l in f.readlines():
        file_list.append(l.strip())
     f.close()
  except Exception as e:
     print("unable to open file %s for reading" % file)

  return file_list

def read_telemetry(file=None,keywords=None):

  hdu_list = fits.open(file)
  im_head = hdu_list[0].header
  vals=[]
  for k in keywords:
     v=""
     try:
       #v=im_head[k].strip()
       v=im_head[k]
     except Exception as e:
       print("unable to read keyword %s from file %s" % (k,file))
     vals.append(v)

  return vals

def extract_vals(file_list=None,keywords=None,quad=None):

    if quad not in ['SW','NW','SE','NE']:
       print("unrecognized quad: %s" % quad)
       return None,None

    x=[]
    y_vals=[]

    n_vals = len(keywords)-2
    for i in range(0,n_vals):
      y_vals.append([])

    t0 = None
    for file in file_list:
      vals=read_telemetry(file,keywords)
      date_string=vals[0]
      timestamp=date_to_timestamp(date_string)
      if t0 is None:
         t0 = timestamp

      if quad in vals[1]:
        x.append((timestamp-t0)/86400)
        for i in range(2,len(keywords)):
          y_vals[i-2].append(float(vals[i]))

    return x,y_vals

def date_to_timestamp(date_string=None):

  date_string = date_string.replace("-"," ")    
  date_string = date_string.replace(":"," ")    
  date_string = date_string.replace("T"," ")    
  s = date_string.split(" ")
  y=[]
  for e in s:
     if "." in e:
       x=float(e)
       y.append(int(x))
     else:
       y.append(int(e))
  t=datetime.datetime(y[0],y[1],y[2],y[3],y[4],y[5])
  t = t.timestamp()
  return(t)
      
if len(sys.argv)!=2:
   print("syntax: get_telemtry [file_list]")
   sys.exit(0)

file_list=read_list(sys.argv[1])
if len(file_list) == 0:
   print("unable to read file list or emptry file")
   sys.exit(-1)

#keywords=['DATE-OBS','HIERARCH mod4/lvhc_v1'] 
v_keywords=['DATE-OBS','CCD_LOC',
          'mod4/lvhc_v1',
          'mod4/lvhc_v2',
          'mod4/lvhc_v3',
          'mod4/lvhc_v4',
          'mod4/lvhc_v5',
          'mod4/lvhc_v6',
          'mod9/xvp_v1',
          'mod9/xvp_v2',
          'mod9/xvp_v3',
          'mod9/xvp_v4',
          'mod9/xvn_v1',
          'mod9/xvn_v2',
          'mod9/xvn_v3',
          'mod9/xvn_v4']
i_keywords=['DATE-OBS','CCD_LOC',
          'mod4/lvhc_i1',
          'mod4/lvhc_i2',
          'mod4/lvhc_i3',
          'mod4/lvhc_i4',
          'mod4/lvhc_i5',
          'mod4/lvhc_i6',
          'mod9/xvp_i1',
          'mod9/xvp_i2',
          'mod9/xvp_i3',
          'mod9/xvp_i4',
          'mod9/xvn_i1',
          'mod9/xvn_i2',
          'mod9/xvn_i3',
          'mod9/xvn_i4']

x_sw_v,y_sw_v=extract_vals(file_list,v_keywords,'SW')
x_se_v,y_se_v=extract_vals(file_list,v_keywords,'SE')
x_nw_v,y_nw_v=extract_vals(file_list,v_keywords,'NW')
x_ne_v,y_ne_v=extract_vals(file_list,v_keywords,'NE')
x_sw_i,y_sw_i=extract_vals(file_list,i_keywords,'SW')
x_se_i,y_se_i=extract_vals(file_list,i_keywords,'SE')
x_nw_i,y_nw_i=extract_vals(file_list,i_keywords,'NW')
x_ne_i,y_ne_i=extract_vals(file_list,i_keywords,'NE')

fig, axs = plt.subplots(2,1)

for i in range(0,len(y_sw_v)):
    axs[0].scatter(x_sw_v,y_sw_v[i],s=1)
    axs[0].scatter(x_se_v,y_se_v[i],s=1)
    axs[0].scatter(x_nw_v,y_nw_v[i],s=1)
    axs[0].scatter(x_ne_v,y_ne_v[i],s=1)
for i in range(0,len(y_sw_i)):
    axs[1].scatter(x_sw_i,y_sw_i[i],s=1)
    axs[1].scatter(x_se_i,y_se_i[i],s=1)
    axs[1].scatter(x_nw_i,y_nw_i[i],s=1)
    axs[1].scatter(x_ne_i,y_ne_i[i],s=1)

axs[1].set_xlabel("time (d)")
axs[0].set_ylabel("V")
axs[1].set_ylabel("I")
now = datetime.datetime.now()
date_string=now.strftime("%d %m %Y %H:%M:%s")
axs[0].set_title("Telemetry"+" "+date_string)
output_image = "telem.png"
plt.savefig(output_image)
     
