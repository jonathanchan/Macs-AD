#!/usr/bin/env python

import os
import subprocess

pref = "/Library/Preferences/SystemConfiguration/com.apple.smb.server"

def getADName():

  # This command will always exit 0.
  # If the machine is not bound to Active Directory, the output is empty string
  ad_info = subprocess.check_output(["dsconfigad", "-show"])

  computer_account = False

  if ad_info != '':
    ad_info =  ad_info.split('\n')
    computer_account = ad_info[2].split('= ')[1].replace('$', '')
  
  return computer_account

def getHostName(nametype):
  with open(os.devnull, 'w') as fnull:
    try:
      return str(subprocess.check_output( \
        ['scutil', '--get', nametype], stderr=fnull)).rstrip()
    except:
      return ''

def setHostName(nametype, hostname):
  try:
    subprocess.call(["scutil", "--set", nametype, hostname])
  except:
    pass

def getNetBiosName():
  with open(os.devnull, 'w') as fnull:
    try:
      return subprocess.check_output(\
        ["defaults", 'read', pref, "NetBIOSName"], stderr=fnull).rstrip()
    except:
      return ''

def setNetBiosName(name):
  try:
    return subprocess.call(["defaults", 'write', pref, "NetBIOSName", name])
  except:
    pass

if __name__ == "__main__":
  computer_name = getADName() 

  if computer_name:
    for nametype in ('ComputerName', 'LocalHostName', 'HostName'):
      if getHostName(nametype) != computer_name:
        setHostName(nametype, computer_name)

    if getNetBiosName() != computer_name:
      setNetBiosName(computer_name)