#!/usr/bin/env python

import getopt
import getpass
import os
import subprocess
import sys
from pwd import getpwnam
from grp import getgrnam

### Config - Change this to match your environment
##
# The dn where machine accounts reside. Use adsiedit to figure this out.
OUPATH = 'OU=SubContain,OU=Container,DC=adName,DC=internalOffice,DC=local'

# Domain name
DOMAIN = 'adName.internalOffice.local'

# Domain name - shortname. ex: adName\username or username@adName
DOMAIN_SHORTNAME = 'adName'

# User account or admin account that can bind machines
BINDNAME = 'UserAccountThatCanBind'
BINDPASS = 'SomePassword'
##
### End Config

# Ansi code for colors
C_WARNING = '\033[93m'  #PINK
C_FAIL = '\033[31m'     #RED
C_END = '\033[0m'       #CLOSING TAG

# Max length name AD will recognize. Shorten it if needed.
HOSTNAME_LIMIT = 15

def isADBound():
  # dsconfigad -show exit code is always 0 :( sooo....
  # String length = 0 is not bound to AD
  # String length > 0 is bound to AD
  return bool(subprocess.check_output(["dsconfigad", "-show"]))

def getFDEStatus():
  fdestatus = str(subprocess.check_output(["fdesetup", "status"])).rstrip()

  return bool(fdestatus.count("FileVault is On."))

def getHostName(nametype):
  with open(os.devnull, 'w') as fnull:
    try:
      return str(subprocess.check_output(["scutil", "--get", nametype], \
             stderr=fnull)).rstrip()
    except:
      return ""

def setHostName(hostname):
  try:
    for nametype in ("ComputerName", "LocalHostName", "HostName"):
      subprocess.call(["scutil", "--set", nametype, hostname])
  except:
    pass

#def checkExistingADEntry(cn):
  # TODO: Check if a computer name already exists in Active Directory

def isValidHostName(hostname):
  validhostname = True

  if len(hostname) > HOSTNAME_LIMIT:
    validhostname = False

  if len(hostname) == 0:
    validhostname = False

  if ' ' in hostname:
    validhostname = False

  ## Optional: Add additional checks for a well formed hostname.

  ## example - check if the first 3 chars to matches a given prefix
  ## if hostname[:3].lower() != "abc"
  ##   validhostname = False

  return validhostname

def getUsersList():
  userlist = []

  for line in os.listdir('/Users'):
    if os.path.isdir('/Users/' + line) and line != 'Shared':
      userlist.append(line)

  return userlist

def selectUser(userlist):
  validchoice = False

  while not validchoice:
    while True:
      try:
        print "\nSelect the local account / home folder to migrate.\n"

        for index in range(len(userlist)):
          print "[" + str(index) + "] " + userlist[index]

        selected = int(raw_input("Home Folder: "))
        break
      except:
        print C_WARNING + "You need to enter a number." + C_END

    if selected in range(len(userlist)):
      confirm = raw_input("Migrate " + userlist[int(selected)] +
                          "'s local account and home folder? [y/n] ") 
      if confirm.lower() == 'y':
        validchoice = True
    else:
      print C_WARNING + "You did not make a proper selection." + C_END 

  return userlist[selected]

def bindToAD():
  ## TODO Query AD to verify that the computer name does not already exist.

  print ""
  print "Binding machine to Active Directory."
  print "This might take a while..."
  print "If this goes on forever, ^C and try running the script again."
  print "Sometimes there's a problem talking to the closest DC."
  print "If this is a persistant problem make sure the computer name" \
        "does not already exist in AD.\n"

  output = ''

  try:
    subprocess.call(['dsconfigad', '-domain', DOMAIN, \
             '-ou', OUPATH, '-mobile', 'enable', \
             '-mobileconfirm', 'disable', '-useuncpath', 'disable', \
             '-username', BINDNAME, '-password', BINDPASS])
  except:
    sys.exit(C_FAIL + "There was a problem binding to Active Directory." + C_END)

  print "Machine is bound to Active Directory.\n"
  return True

def isADUser(adusername):
  try:
    exitcode = True
    getpwnam(DOMAIN_SHORTNAME + '\\' + adusername).pw_uid
  except:
    exitcode = False

  return exitcode

def deleteOldUser(username):
  # Delete the user's account from dscl & remove it from the local admin group
  with open(os.devnull, "w") as fnull:
    try:
      exitcode = subprocess.call(["dscl", ".", "-delete", "/Users/" + username], \
                                 stdout=fnull, stderr=fnull)
    except:
      # Explicitly setting to 1 for all errors
      exitcode = 1

    # User might not be in the admin group... don't care if this is the case. 
    subprocess.call(["dscl", ".", "-delete", "/Groups/admin", "GroupMembership", \
                    username], stdout=fnull, stderr=fnull)

  return not exitcode   # unix & python true/false are oppposite from each other

def updateHomeFolder(adusername, oldhomefolder):
  newhomefolder = '/Users/' + adusername
  oldhomefolder = '/Users/' + oldhomefolder

  # Get uid of the adusername
  # TODO refactor this with isADUser()
  noerrorsfound = True
  try:
    uid = getpwnam(DOMAIN_SHORTNAME + '\\' + adusername).pw_uid
    gid = getgrnam(DOMAIN_SHORTNAME + '\Domain Users').gr_gid
  except:
    noerrorsfound = False

  if noerrorsfound:
    if not os.path.exists(newhomefolder):
      os.rename(oldhomefolder, newhomefolder)

    try:
      domain_user = DOMAIN_SHORTNAME + '\\' + adusername
      domain_users = DOMAIN_SHORTNAME + '\Domain Users'
      subprocess.call(['chown', '-R', domain_user + ':' + \
                      domain_users, newhomefolder])
    except:
      print C_FAIL + "There was a problem running chown." + C_END
      noerrorsfound = False
  else:
    print C_FAIL + "Could not id " + adusername + " or Domain Users." + C_END

  return noerrorsfound

def setMachineAdmins(grouplist):
  if grouplist:
    groups = ', '.join(grouplist)
    subprocess.call(["dsconfigad", "-groups", groups]) 

def setMachineAdmin(username):
  # Assume username is not empty
  subprocess.call(["dscl", ".", "-append", "/Groups/admin", \
                  "GroupMembership", username])

def main(argv):
  print ""

  if isADBound():
    sys.exit(C_FAIL + "This machine is already bound to Active Directory." + C_END)
  
  if getFDEStatus():
    sys.exit(C_FAIL + "The drive is already encrypted. \
             Decrypt it before adding the Mac to AD." + C_END)
  
  isvalidname = True

  for namekey in ("ComputerName", "LocalHostName", "HostName"):
    namevalue = getHostName(namekey)
    if not isValidHostName(namevalue):
      isvalidname = False

  if not isvalidname:
    while not isvalidname:
      print C_WARNING + "The computer name does not meet naming standards " \
            "and must be updated." + C_END
      newhostname = raw_input("New computer name? ")
      isvalidname = isValidHostName(newhostname)

    setHostName(newhostname)

  bindToAD()

  # Assume homefolder eq the old username
  homefolderlist = getUsersList()
  homefolder = selectUser(homefolderlist)
  adusername = homefolder   # There's a chance that homefolder == aduser
  olduid = getpwnam(homefolder).pw_uid

  isproperusername = False
  while not isproperusername:
    usernameprompt = raw_input("Is " + adusername + " the proper AD username? ")

    if usernameprompt.lower() == "y":
      if isADUser(adusername):
        isproperusername = True
      else:
        print C_WARNING + "Could not find " + adusername + " in AD. " \
              "Try again.\n" + C_END
        adusername = raw_input("What's the proper AD user name? ")
    else:
      adusername = raw_input("What's the proper AD user name? ")
  
  if not deleteOldUser(homefolder):
    print C_WARNING + "There was a problem removing " + homefolder + "'s " \
          "local account.\nPerhaps local account doesn't exist.\n" \
          "Continuing on..." + C_END
    print "Updating file permissions."

  if updateHomeFolder(adusername, homefolder):
    print "Setting Admin groups and updating file permissions."

    # Admin accounts' primary group should be set to groups below
    # or the admin account won't have admin access to the box
    # If you have additional groups that should be able to admin a box,
    # add them to admin_groups.
    admin_groups = [DOMAIN_SHORTNAME + "\\domain admins"]
    setMachineAdmins(admin_groups)
    setMachineAdmin(adusername)

    # Update file permissions in /Applications and /usr/local
    # TODO: Super lazy... Redo this so that shell=True isn't used... 
    subprocess.call("find /Applications -user " + str(olduid) + " -exec chown "\
                    + "-R " + adusername + " {} \;", shell=True)

    subprocess.call("find /usr/local -user " + str(olduid) + " -exec chown "\
                    + "-R " + adusername + " {} \;", shell=True)
    
    print "AD Migration completed!\n"
    print "Don't forget to have the user log on and " \
          "update their keychain password."
  else:
    print C_WARNING + "There was a problem setting file permissions for " + \
          adusername + "." + C_END

if __name__ == "__main__":
  if getpass.getuser() != 'root':
    sys.exit(C_FAIL + 'sudo is needed to run this script' + C_END)
  main(sys.argv[1:])
