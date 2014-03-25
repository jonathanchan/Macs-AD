#!/bin/sh
#Casper policy to install Homebrew
#Assuming that root is running this script

MountainLionDevTools=$4
MavericksDevTools=$5
tempAdminAccount="HomebrewInstaller"
export passwd=$(openssl rand -base64 $((RANDOM%10+20)))

function CreateTempAdminAccount() {
    local nextuid=$(($(dscl . -list /Users UniqueID | awk '{print $2}' | grep 5..$ | sort | tail -n 1)+1))

    dscl . create /Users/$tempAdminAccount
    dscl . create /Users/$tempAdminAccount RealName "Homebrew Installer"
    dscl . passwd /Users/$tempAdminAccount $passwd
    dscl . create /Users/$tempAdminAccount UniqueID $nextuid
    dscl . create /Users/$tempAdminAccount PrimaryGroupID 20
    dscl . append /Groups/admin GroupMembership $tempAdminAccount
    dscl . create /Users/$tempAdminAccount UserShell /bin/bash
    ##dscl . create /Users/$tempAdminAccount NFSHomeDirectory /Users/$tempAdminAccount
    ##cp -R /System/Library/User\ Template/English.lproj /Users/$tempAdminAccount
    ##chown -R $tempAdminAccount:staff /Users/$tempAdminAccount
}

function DeleteTempAdminAccount() {
    dscl . delete /Users/$tempAdminAccount
    dscl . delete /Groups/admin GroupMembership $tempAdminAccount
    #rm -rf /Users/$tempAdminAccount
}

function InstallCommandLineTools() {
    echo Install command line Tools
    curl $1 -o /tmp/cli.dmg
    if [ $? == 0 ]; then
        local mountResult=$(/usr/bin/hdiutil mount -private -noautoopen -noverify /tmp/cli.dmg -shadow)
        local mountVolume=$(echo "$mountResult" | grep Volumes | cut -f 3)
        local mountDevice=$(echo "$mountResult" | grep disk | head -1 | awk '{print $1}')
        local packageName=$(ls "$mountVolume" | grep "pkg")
        installer -pkg "$mountVolume"/"$packageName" -target /

        local installerExitCode=$?
        /usr/bin/hdiutil detach "$mountDevice" -force
        rm /tmp/cli.dmg*

        if [ $installerExitCode != 0 ]; then
            echo There was a problem installing $1.
            exit 1
        fi

    else
        echo Could not download $1.
        exit 1
    fi
}

function DetectCommandLineTools() {
    local version=$(/usr/bin/sw_vers | grep ProductVersion: | awk '{print $2}')

    if [[ $version =~ 10\.9.* ]]; then
        if ! [ -e /Library/Developer/CommandLineTools/usr/bin/clang ]; then
            echo Installing Dev Tools for Mavericks
            InstallCommandLineTools $MavericksDevTools
        else
            echo Command Line Tools for Mavericks are already installed.
        fi
    elif [[ $version =~ 10\.8.* ]]; then
        if ! [ -e /usr/bin/cc ]; then
            echo Installing Dev Tools for Mountain Lion
            InstallCommandLineTools $MountainLionDevTools
        else
            echo Command Line Tools for Mountain Lion are already installed.
        fi
    else
        echo Can\'t determine which version of OSX is being used.
        exit 1
    fi
}

if [ -z "$MountainLionDevTools" ] || [ -z "$MavericksDevTools" ]; then
    echo \$4 and \$5 are not defined.
    exit 1
fi

if [ -e '/usr/local/bin/brew' ]; then
    echo Homebrew is already installed.
    exit 1
fi

CURRENT_USER=$(last | grep console | grep "still logged in" | awk '{print $1}')

if [ -n "$CURRENT_USER" ]; then
    DetectCommandLineTools
    echo install homebrew
    CreateTempAdminAccount

    su $tempAdminAccount -c 'echo $passwd | sudo -S true && echo | ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"'
    if [ $? == 0 ]; then
    	echo Post install clean up...
    	echo Running brew doctor
        /usr/local/bin/brew doctor

        echo Fixing permissions
        find /usr/local -user $tempAdminAccount -exec chown -R $CURRENT_USER {} \;

        #echo Installing packages...
        #su $CURRENT_USER -c 'brew install tmux'
    else
        echo something went wrong
    fi

    DeleteTempAdminAccount
else
    echo No user is logged in.
    exit 1
fi