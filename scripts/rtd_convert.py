#rtd_convert.py
#
# calculate rtd temperature from resistanc using lookup table
#
import os
import sys

def extrap(t=None,x=None):

    x1=None
    y1=None
    x2=None
    y2=None
    for data in t:
       if data[1]<x:
          y1=data[0]
          x1=data[1]
       else:
          y2=data[0]
          x2=data[1]

       if x1 is not None and x2 is not None:
          slope = (y2-y1)/(x2-x1)
          y= y1 + slope*(x-x1)
          return y
    return None
          

def get_table():
    ls4_control_root = os.environ['LS4_CONTROL_ROOT']
    rtd_table = ls4_control_root + "/" + "scripts" + "/" + "rtd_conversion.dat"

    try:
      f=open(rtd_table,"r")
    except Exception as e:
      print("can't open file %s for reading: %s" % e)
      sys.exit(-1)

    table=[]
    for l in f.readlines():
      if "#" not in l:
         l1 = l.split()
         table.append([float(l1[0]),float(l1[1]),float(l1[2])])

    f.close()
    return table


if len(sys.argv)!=2:
  print("syntax: rtd_convert.py rtd-ohms")
  sys.exit(-1)

rtd_ohms = float(sys.argv[1])
table=get_table()
t=extrap(table,rtd_ohms)
print(t)







