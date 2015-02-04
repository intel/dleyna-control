#!/usr/bin/env python

# launches an app after first clearing proxy settings
# for example, launch-without-proxy-settings gupnp-av-cp


import os
import sys
from subprocess import call


try:
  #print os.environ;
  del os.environ["http_proxy"];
  del os.environ["https_proxy"];
  del os.environ["ftp_proxy"];
  del os.environ["socks_proxy"];
  del os.environ["no_proxy"];

  print '\n';
  print '\n';

  #print os.environ;
except Exception, e:
  print e;
  pass

if len(sys.argv) > 1:
  print "launching ",
  print sys.argv[1:];

  call(sys.argv[1:]);

