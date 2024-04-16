alias ls4-venv='source ~/ls4_venv/bin/activate'
alias vnc_off='sudo systemctl set-default graphical'
alias vnc_on='sudo systemctl set-default multi-user'
alias start_vnc='/usr/bin/vncserver -depth 24 -geometry 2000x1200 -localhost no :2'
alias stop_vnc='vncserver -kill :1'
alias up='cd $x; cd archon-main; pip install .; cd $x'
alias reset='scripts/reset.bash'
alias test='scripts/test.bash'
alias mos='scripts/make_mosaic.csh'
alias abort='scripts/abort.bash'
