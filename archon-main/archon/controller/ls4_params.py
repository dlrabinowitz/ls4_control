
MAX_COMMAND_ID = 0xFF
MAX_CONFIG_LINES = 16384


#######
# added by D. Rabinowitz

FOLLOWER_TIMEOUT_MSEC = 10000
AMPS_PER_CCD = 2
CCDS_PER_QUAD = 8

# for fake control:
FAKE_LINECOUNT = 4120
FAKE_PIXELCOUNT = 1050
FAKE_AMPS_PER_CCD = 2
FAKE_CCDS_PER_QUAD = 8
FAKE_BYTES_PER_PIXEL = 2

# Note +/-100 V supply voltages changed to +/- 50.0 V by G. Bredthauer
# 2024 Feb 16 to keep op-amp on XV BIASS from overheating. THis change
# prevents operation of DECam CCDS with Vsub > 40.0 V
P100_SUPPLY_VOLTAGE = 50.0
N100_SUPPLY_VOLTAGE = -50.0

# seconds for time out when acquiring status lock
STATUS_LOCK_TIMEOUT = 1.0 

# block size when fetching raw data from controller
LS4_BLOCK_SIZE=1024

# Keywords and values to enable/disable Vsun bias on CCDs
# VSUB is voltage 1 of Module 9 on the controllers. WHen
# enabled. +40 Volts is applied to the Vsub bias. When
# disabled, 0.0 volts is applied instead. 

VSUB_ENABLE_KEYWORD = "XVP_ENABLE1"
VSUB_MODULE = "MOD9"
VSUB_ENABLE_VAL = 1
VSUB_DISABLE_VAL = 0 
VSUB_APPLY_COMMAND = "APPLYMOD08"

STATUS_START_BIT = 0x2
# maximum expected fetch time (sec) for a full image
MAX_FETCH_TIME = 30.0

#time (sec) required for controller to reboot 
REBOOT_TIME = 10

#time (sec) for Vsub to stabalize after erase procedure completes
POST_ERASE_DELAY = 1.0 
