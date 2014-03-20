#!/bin/sh
# Installs Homebrew via Casper Policy
# Assumes the current user logged in is the user that will need to use brew.
## $4 and $5 are sent by Casper
## $4 and $5 should be an administrative account that exists on each Mac.

export PASSWD=$5
ADMIN_USER=$4
CURRENT_USER=$(last | grep console | grep "still logged in" | awk '{print $1}')

if [ -n "$CURRENT_USER" ]; then
	#TODO Install OSX Developer Tools for either 10.8 or 10.9

    su $ADMIN_USER -c 'echo $PASSWD | sudo -S true && echo | ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"'
    if [ $? == 0 ]; then
    	echo Post install clean up...
    	echo Running brew doctor
        brew doctor

        echo Fixing permissions
        find /usr/local -user $ADMIN_USER -exec chown -R $CURRENT_USER {} \;

        #echo Installing packages...
        #su $CURRENT_USER -c 'brew install tmux'
    fi
else
    echo No user is logged in.
    exit 1
fi
