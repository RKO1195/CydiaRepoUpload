#!/usr/bin/env python

import os
import sys
import fnmatch
import paramiko

remote_path = "/srv/http/repo/"
repo = "myrepo.com"
user = "myuser"


def errorMsg( str ):
  print(str)
  sys.exit()

# Open control file
if os.path.exists('control'):
  with open('control', 'rb') as f:
      try:
          for line in f:
            if line.startswith('Version:'):
              #get version from file
              version = line.split()[1]
              print("The version of the compiled code is: \n" + version + "\n")

      except:
          errorMsg("Couldn't read control file!")
else:
  errorMsg("Found no control file!")


# Print pwd
print("Path at terminal when executing this file: \n" + os.getcwd() + "\n")


# Get most recent .deb file with correct version number
matches = []
for root, dirnames, filenames in os.walk(os.getcwd()):
    for filename in fnmatch.filter(filenames, '*.deb'):
        matches.append(os.path.join(root, filename))

newest = max(matches, key=os.path.getmtime)

if version in newest:
  print("Most recent .deb file is: \n" + newest + "\n")
else:
  errorMsg("Most recently changed .deb file isn't same version as in control file!")


# SSH
print("Setting up SSH connection...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
  ssh.connect(repo, username=user, key_filename=os.path.expanduser('~/.ssh/id_rsa'))
except:
  errorMsg("Server seems to be offline.")

sftp = ssh.open_sftp()


# Copy .deb file
print("Copying .deb file...")
sftp.put(newest, remote_path + filename)

path = os.path.splitext(filename)[0]

print("Creating directories...")
try:
  sftp.chdir(remote_path + os.path.join(path, "DEBIAN"))  # Test if path exists
except IOError:
  sftp.mkdir(remote_path + os.path.join(path))  # Create path
  sftp.chdir(remote_path + os.path.join(path))
  sftp.mkdir(os.path.join("DEBIAN"))
  sftp.chdir(os.path.join("DEBIAN"))


def foundName( str, name ):
  for line in str:
    if name in line:
      return True

  return False


# Copy control file
print("Copying control file...")
sftp.put(os.getcwd() + "/control", "control")


# Update packages.sh
readFile = sftp.file(remote_path + '/packages.sh', 'r')
if foundName( readFile, path ):
  print "Found name already"
else:
  print "Could not find filename, writing..."
  writeFile = sftp.file(remote_path + '/packages.sh', 'a')
  writeFile.write("dpkg-deb -Zgzip -b " + path + "\n")
  writeFile.close()

readFile.close()


# Update repo
print("Updating repo...")
stdin, stdout, ssh_stderr = ssh.exec_command('(cd /srv/http/repo; ./update.sh)')
print stdout.readlines()

ssh.close()