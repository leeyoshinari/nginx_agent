#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: leeyoshinari
import os
import re
import time
import json
import threading
import traceback
import requests
from common import get_config, logger, get_ip


class Task(object):
    def __init__(self):
        self.IP = get_ip()
        self.group_key = None
        self.prefix = ''
        self.start_time = 0
        self.influx_post_url = f'http://{get_config("address")}/influx/batch/write'
        # log_format  main   '$remote_addr - $remote_user [$time_iso8601] $request_method $request_uri $server_protocol $status $body_bytes_sent $upstream_response_time "$http_referer" "$http_user_agent" "$http_x_forwarded_for"';
        self.compiler = re.compile(r'(?P<ip>.*?)- - \[(?P<time>.*?)\] (?P<method>.*?) (?P<path>.*?) (?P<protocol>.*?) (?P<status>.*?) (?P<bytes>.*?) (?P<rt>.*?) "(?P<referer>.*?)" "(?P<ua>.*?)"')
        self.access_log = get_config('nginxLogPath')
        self.get_configure_from_server()
        if not self.access_log:
            self.find_nginx_log()

        t = threading.Thread(target=self.parse_log, args=())
        t.start()

    def get_configure_from_server(self):
        url = f'http://{get_config("address")}/register'
        post_data = {
            'type': 'nginx-agent',
            'host': self.IP,
            'port': get_config('port'),
        }
        while True:
            try:
                res = self.request_post(url, post_data)
                logger.debug(f"The result of registration is {res.content.decode('unicode_escape')}")
                if res.status_code == 200:
                    response_data = json.loads(res.content.decode('unicode_escape'))
                    if response_data['code'] == 0:
                        self.group_key = 'nginx_' + response_data['data']['groupKey']
                        self.prefix = response_data['data']['prefix']
                        break
                time.sleep(1)
            except:
                logger.error(traceback.format_exc())
                time.sleep(1)

    def find_nginx_log(self):
        res = os.popen("ps -ef|grep nginx |grep master|awk '{print $2}'").read()
        logger.info(f'nginx pid is: {res}')
        nginx_pid = res.strip()
        if nginx_pid:
            res = os.popen(f'pwdx {nginx_pid}').read()
            nginx_path = res.strip().split(' ')[-1].strip()
            self.access_log = os.path.join(os.path.dirname(nginx_path), 'logs', 'access.log')
        else:
            logger.error('Nginx is not found ~')
            raise Exception('Nginx is not found ~')

    def parse_log(self):
        if not os.path.exists(self.access_log):
            raise Exception(f'Not found nginx log: {self.access_log}')

        position = 0
        with open(self.access_log, mode='r', encoding='utf-8') as f1:
            lines = f1.readlines()   # jump to current newest line, ignore old lines.
            while True:
                lines = f1.readlines()
                cur_position = f1.tell()
                if cur_position == position:
                    time.sleep(0.2)
                    continue
                else:
                    position = cur_position
                    self.parse_line(lines)

    def parse_line(self, lines):
        for line in lines:
            if self.prefix in line:
                if 'static' in line and '.' in line:
                    continue
                else:
                    logger.debug(f'Nginx - access.log -- {line}')
                    res = self.compiler.match(line).groups()
                    path = res[3].split('?')[0].strip()
                    if 'PerformanceTest' in res[9]:
                        source = 'test'
                    else:
                        source = 'normal'
                    c_time = res[1].strip('+')[0].replace('T', ' ').strip()
                    rt = float(res[7].split(',')[-1].strip()) if ',' in res[7] else float(res[7].strip())
                    line = [{'measurement': self.group_key, 'tags': {'source': source},
                             'fields': {'c_time': c_time, 'client': res[0].strip(), 'path': path, 'status': int(res[5]), 'size': int(res[6]), 'rt': rt}}]
                    logger.info(line)


    def request_post(self, url, post_data):
        header = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json; charset=UTF-8"}
        try:
            res = requests.post(url=url, json=post_data, headers=header)
            return res
        except:
            raise

