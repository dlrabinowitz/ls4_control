import sys
import argparse
import numpy as np


def  read_bias_data(conf=None):
  #NE_A AD4R 13096.4 035.099

  try:
    f=open(conf['bias_data'],"r")
  except Exception as e:
    print("Exception opening file %s: %s" % (conf['bias_data'],e))
    sys.exit(-1)

  bias_data = {}
  for line in f.readlines():
    d1 = " ".join(line.split())
    d = d1.split(" ")
    ccd_name = d[0]
    l = ccd_name.replace("_"," ")
    l = " ".join(l.split())
    l = l.split(" ")
    ccd_name = l[0]
    tap_name = d[1]
    bias = float(d[2])
    rms = float(d[3])
    if ccd_name not in bias_data:
       bias_data[ccd_name]={}
    bias_data[ccd_name][tap_name]={'bias': bias, 'rms': rms}

  f.close()

  return bias_data

def  read_tap_settings(conf=None):
  #ne TAPLINE0 "AD4R 2 10300"

  try:
    f=open(conf['tap_settings'],"r")
  except Exception as e:
    print("Exception opening file %s: %s" % (conf['tap_settings'],e))
    return None

  tap_data = {}
  for line in f.readlines():
    d1 = " ".join(line.split())
    d2 = d1.replace("\"","")
    d = d2.split(" ")
    ccd_name = d[0].upper()
    tap_entry = d[1].upper()
    tap_name = d[2]
    gain = int(d[3])
    offset = int(d[4])
    if ccd_name not in tap_data:
       tap_data[ccd_name]={}
    tap_data[ccd_name][tap_name]={'gain': gain, 'offset': offset, 'tap_entry': tap_entry}

  f.close()
  return tap_data
   
   
conf={}
parser = argparse.ArgumentParser(description="utility to correct tap settings based on bias measurements")
parser.add_argument('--bias_data', metavar='b', type=str, default='bias.dat')
parser.add_argument('--tap_settings', metavar='t', type=str, default='tap_settings.dat')
parser.add_argument('--target_bias', metavar='u', type=float, default=5000.0)
conf.update(vars(parser.parse_args()))

bias_data = read_bias_data(conf)
if bias_data is None:
  print("failed to read bias_data")
  sys.exit(-1)

tap_data = read_tap_settings(conf)
if tap_data is None:
  print("failed to read tap_data")
  sys.exit(-1)

target_bias = conf['target_bias']

tap_names=[]
ccd_names=[]
bias_levels=[]
offsets=[]
noise_values=[]
tap_entries=[]
gain_values=[]

index = 0
bias_level_min = 1e0
index_min = -1
MAX_NOISE_LEVEL = 10.0
dy=[]

for ccd_name in bias_data:
   b = bias_data[ccd_name]
   t = tap_data[ccd_name]

   for tap_name in b:
       bias = b[tap_name]['bias']
       noise = b[tap_name]['rms']
       offset = t[tap_name]['offset']
       gain = t[tap_name]['gain']
       bias_levels.append(int(bias))
       offsets.append(int(offset))
       gain_values.append(int(gain))
       noise_values.append(noise)
       ccd_names.append(ccd_name)
       tap_names.append(tap_name)
       tap_entries.append(t[tap_name]['tap_entry'])
       dy.append((bias-target_bias))
       if bias < bias_level_min and noise < MAX_NOISE_LEVEL:
          bias_level_min=bias
          index_min = index
       index += 1

dy = np.asarray(dy)
dy_avg = np.average(dy)
dy_rms = np.std(dy)

num_amps = index
offset_min = 1e8
offset_max = -1e8
index_min = -1
index_max = -1

dc = []
for index in range(0,num_amps):
  #correction = float(target_bias - bias_levels[index])/float(gain_values[index])
  correction = float(target_bias - bias_levels[index])/1.0
  dc.append(correction)
  new_offset = offsets[index] + correction
  new_offset = max(-32767,new_offset)
  new_offset = min(32767,new_offset)

  print("# %s %s  bias: %05d offset: %05d  gain: %d  correction: %d" %\
      (ccd_names[index],tap_entries[index],bias_levels[index],offsets[index],gain_values[index],correction) )
  print("%s=\"%s, %d, %d\""  %\
      (tap_entries[index],tap_names[index],gain_values[index],new_offset))

  if new_offset < offset_min:
     offset_min = new_offset
     index_min = index
  if new_offset > offset_max:
     offset_max = new_offset
     index_max = index

dc = np.asarray(dc)
dc_avg = np.average(dc)
dc_rms = np.std(dc)

print ("dy avg,rms: %07.1f %07.1f   dc avg,rms: %07.1f %07.1f" % (dy_avg,dy_rms,dc_avg,dc_rms))
#print("min : %d %06.0f  bias: %7.3f  noise: %7.3f old_offset: %06.f" % \
#       (index_min,offset_min,bias_levels[index_min],noise_values[index_min],offsets[index_min]))
#print("max : %d %06.0f  bias: %7.3f  noise: %7.3f old_offset: %06.f" % \
#       (index_max,offset_max,bias_levels[index_max],noise_values[index_max],offsets[index_max]))






