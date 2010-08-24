#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyurg

urg = pyurg.UrgDevice()

if not urg.connect():
    print 'Could not connect.'
    exit()

data, timestamp = urg.capture()

for length in data:
    print length
