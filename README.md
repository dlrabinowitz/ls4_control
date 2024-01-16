# ls4_control
Python code to control LS4 camera
This was written to synchronously control four Archon controllers (STA).
It is built on top of the sdss-archon python code
(https://github.com/sdss/archon)
It has been tested with Ubunto 23.10


Installation:
    copy the base installationin

in bash:
    source scripts/setup.bash
    pip install -r ls4_requirements.txt
    cd archon-main
    pip install .
  

test:
    scripts/test.bash


  
  
