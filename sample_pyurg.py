#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyurg

# For initializing.
urg = pyurg.UrgDevice()

# Connect to the URG device.
# If could not conncet it, get False from urg.connect()
if not urg.connect():
    print 'Could not connect.'
    exit()

# Get length datas and timestamp.
# If missed, get [] and -1 from urg.capture()
data, timestamp = urg.capture()

# Print lengths.
for length in data:
    print length
