#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: leeyoshinari
import os
import re
import time
import json
import threading
import traceback
import configparser
import logging.handlers
import redis
import requests


cfg = configparser.ConfigParser()
cfg.read('config.conf', encoding='utf-8')
def get_config(key):
    return cfg.get('server', key, fallback=None)

LEVEL = get_config('level')
backupcount = int(get_config('backupCount'))
log_path = get_config('logPath')

if not os.path.exists(log_path):
    os.mkdir(log_path)

log_level = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s[line:%(lineno)d] - %(message)s')
logger.setLevel(level=log_level.get(LEVEL))

file_handler = logging.handlers.TimedRotatingFileHandler(
    os.path.join(log_path, 'monitor.log'), when='midnight', interval=1, backupCount=backupcount)
file_handler.suffix = '%Y-%m-%d.log'
# file_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def get_ip():
    """
    Get server's IP address
    :return: IP address
    """
    try:
        if get_config('host'):
            IP = get_config('host')
        else:
            result = os.popen("hostname -I |awk '{print $1}'").readlines()
            logger.debug(result)
            if result:
                IP = result[0].strip()
                logger.info(f'The IP address is: {IP}')
            else:
                logger.warning('Server IP address not found!')
                IP = '127.0.0.1'
    except:
        IP = '127.0.0.1'
    return IP


class Task(object):
    def __init__(self):
        self.IP = get_ip()
        self.group_key = None
        self.prefix = ''
        self.influx_stream = 'influx_stream'  # stream name
        self.redis_host = '127.0.0.1'
        self.redis_port = 6379
        self.redis_password = '123456'
        self.redis_db = 0
        # log_format  main   '$remote_addr - $remote_user [$time_iso8601] $request_method $request_uri $server_protocol $status $body_bytes_sent $upstream_response_time "$http_referer" "$http_user_agent" "$http_x_forwarded_for"';
        self.compiler = re.compile(r'(?P<ip>.*?)- - \[(?P<time>.*?)\] (?P<method>.*?) (?P<path>.*?) (?P<protocol>.*?) (?P<status>.*?) (?P<bytes>.*?) (?P<rt>.*?) "(?P<referer>.*?)" "(?P<ua>.*?)"')
        self.access_log = get_config('nginxAccessLogPath')
        self.get_configure_from_server()
        if not self.access_log:
            self.find_nginx_log()

        self.redis_client = redis.StrictRedis(host=self.redis_host, port=self.redis_port, password=self.redis_password,
                                    db=self.redis_db, decode_responses=True)
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
                res = request_post(url, post_data)
                logger.debug(f"The result of registration is {res.content.decode('unicode_escape')}")
                self.redis_host = res['redis']['host']
                self.redis_port = res['redis']['port']
                self.redis_password = res['redis']['password']
                self.redis_db = res['redis']['db']
                self.group_key = 'nginx_' + res['groupKey']
                self.prefix = res['prefix']
                break
            except:
                logger.error(traceback.format_exc())
                time.sleep(1)

    def find_nginx_log(self):
        res = os.popen("ps -ef|grep nginx |grep -v grep |grep master|awk '{print $2}'").read()
        nginx_pid = res.strip()
        logger.info(f'nginx pid is: {nginx_pid}')
        if nginx_pid:
            res = os.popen(f'pwdx {nginx_pid}').read()
            nginx_path = res.strip().split(' ')[-1].strip()
            self.access_log = os.path.join(os.path.dirname(nginx_path), 'logs', 'access.log')
            if not os.path.exists(self.access_log):
                raise Exception(f'Not found nginx log: {self.access_log}')
        else:
            logger.error('Nginx is not found ~')
            raise Exception('Nginx is not found ~')

    def parse_log(self):
        logger.info(self.access_log)
        if not os.path.exists(self.access_log):
            logger.error(f'Not found nginx log: {self.access_log}')
            raise Exception(f'Not found nginx log: {self.access_log}')

        position = 0
        with open(self.access_log, mode='r', encoding='utf-8') as f1:
            lines = f1.readlines()   # jump to current newest line, ignore old lines.
            while True:
                try:
                    lines = f1.readlines()
                    cur_position = f1.tell()
                    if cur_position == position:
                        time.sleep(0.1)
                        continue
                    else:
                        position = cur_position
                        self.parse_line(lines)
                except:
                    logger.error(traceback.format_exc())

    def parse_line(self, lines):
        for line in lines:
            if self.prefix in line:
                if 'static' in line and '.' in line:
                    continue
                else:
                    logger.debug(f'Nginx - access.log -- {line}')
                    res = self.compiler.match(line).groups()
                    logger.debug(res)
                    path = res[3].split('?')[0].strip()
                    if 'PerformanceTest' in res[9]:
                        source = 'PerformanceTest'
                    else:
                        source = 'Normal'
                    c_time = res[1].split('+')[0].replace('T', ' ').strip()
                    try:
                        rt = float(res[7].split(',')[-1].strip()) if ',' in res[7] else float(res[7].strip())
                    except ValueError:
                        logger.error(f'parse error: {line}')
                        rt = 0.0
                    error = 0 if int(res[5]) < 400 else 1
                    self.write_redis({'measurement': self.group_key, 'tags': {'source': source, 'path': path},
                             'fields': {'c_time': c_time, 'client': res[0].strip(), 'status': int(res[5]),
                                        'size': int(res[6]), 'rt': rt, 'error': error}})

    def write_redis(self, data):
        try:
            self.redis_client.xadd(self.influx_stream, {'nginx': [data]})
        except:
            logger.error(traceback.format_exc())


def request_post(url, post_data):
    header = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json; charset=UTF-8"}
    try:
        res = requests.post(url=url, json=post_data, headers=header)
        logger.info(f"The result of request is {res.content.decode('unicode_escape')}")
        if res.status_code == 200:
            response_data = json.loads(res.content.decode('unicode_escape'))
            del res
            if response_data['code'] == 0:
                return response_data['data']
            else:
                logger.error(response_data['msg'])
                raise Exception(response_data['msg'])
    except:
        logger.error(traceback.format_exc())
        raise


if __name__ == '__main__':
    task = Task()
    PID = os.getpid()
    with open('pid', 'w', encoding='utf-8') as f:
        f.write(str(PID))
