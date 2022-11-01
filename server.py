#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: leeyoshinari
import os
import time
import traceback
from common import get_ip, logger, get_config
from taskController import Task

HOST = get_ip()
task = Task()
PID = os.getpid()
with open('pid', 'w', encoding='utf-8') as f:
    f.write(str(PID))
