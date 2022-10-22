#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: leeyoshinari
import os
import re
import time
import json
import queue
import traceback
from concurrent.futures import ThreadPoolExecutor
import requests
import redis
import influxdb
from common import get_config, logger, get_ip, toTimeStamp


class Task(object):
    def __init__(self):
        self.IP = get_ip()
        self.group_key = None
        self.start_time = 0
        self.pattern = 'summary\+(\d+)in.*=(\d+.\d+)/sAvg:(\d+)Min:(\d+)Max:(\d+)Err:(\d+)\(.*Active:(\d+)Started'
        self.influx_host = '127.0.0.1'
        self.influx_port = 8086
        self.influx_username = 'root'
        self.influx_password = '123456'
        self.influx_database = 'test'
        self.redis_host = '127.0.0.1'
        self.redis_port = 6379
        self.redis_password = '123456'
        self.redis_db = 0
        self.get_configure_from_server()

        self.thread_pool = int(get_config('threadPool'))
        self.access_log = get_config('nginxLogPath')
        self.monitor_task = queue.Queue()  # FIFO queue
        self.executor = ThreadPoolExecutor(self.thread_pool)    # thread pool

        self.influx_client = None
        self.redis_client = None



    def get_configure_from_server(self):
        url = f'http://{get_config("address")}/monitor/nginx/register/first'
        post_data = {
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
                        self.influx_host = response_data['data']['influx']['host']
                        self.influx_port = response_data['data']['influx']['port']
                        self.influx_username = response_data['data']['influx']['username']
                        self.influx_password = response_data['data']['influx']['password']
                        self.influx_database = response_data['data']['influx']['database']
                        self.redis_host = response_data['data']['redis']['host']
                        self.redis_port = response_data['data']['redis']['port']
                        self.redis_password = response_data['data']['redis']['password']
                        self.redis_db = response_data['data']['redis']['db']
                        break

                time.sleep(1)

            except:
                logger.error(traceback.format_exc())
                time.sleep(1)


    def connect_influx(self):
        self.influx_client = influxdb.InfluxDBClient(self.influx_host, self.influx_port, self.influx_username,
                                                     self.influx_password, self.influx_database)


    def check_status(self, is_run=True):
        try:
            res = os.popen('ps -ef|grep jmeter |grep -v grep').readlines()
            if res and is_run:  # 是否启动成功
                return True
            elif not res and not is_run:    # 是否停止成功
                return True
            else:
                return False
        except:
            logger.error(traceback.format_exc())



    def write_to_influx(self, line):
        d = [json.loads(r) for r in line]
        data = [sum(r) for r in zip(*d)]
        line = [{'measurement': 'performance_jmeter_task',
                 'tags': {'task': str(self.task_id), 'host': 'all'},
                 'fields': {'c_time': time.strftime("%Y-%m-%d %H:%M:%S"), 'samples': data[0], 'tps': data[1],
                            'avg_rt': data[2], 'min_rt': data[3], 'max_rt': data[4], 'err': data[5], 'active': data[6]}}]
        self.influx_client.write_points(line)  # write to database

    def parse_log(self, log_path):
        while not os.path.exists(log_path):
            time.sleep(0.5)

        position = 0
        with open(log_path, mode='r', encoding='utf-8') as f1:
            while True:
                line = f1.readline().strip()
                if 'Summariser: summary +' in line:
                    logger.debug(f'Nginx - access.log - {self.task_id} - {line}')
                    c_time = line.split(',')[0].strip()
                    res = re.findall(self.pattern, line.replace(' ', ''))[0]
                    logger.debug(res)
                    if res[-1] == '0':
                        break
                else:
                    self.change_init_TPS()

                cur_position = f1.tell()
                if cur_position == position:
                    time.sleep(0.2)
                    continue
                else:
                    position = cur_position

    def kill_process(self):
        try:
            res = os.popen("ps -ef|grep jmeter |grep -v grep |awk '{print $2}' |xargs kill -9").read()
        except:
            logger.error(traceback.format_exc())


    def request_post(self, url, post_data):
        header = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json; charset=UTF-8"}
        res = requests.post(url=url, json=post_data, headers=header)
        logger.debug(url)
        return res

if __name__ == '__main__':
    RedisHost = '101.200.52.208'
    RedisPort = 6369
    RedisPassword = 'leeyoshi'
    RedisDB = 1
    r = redis.Redis(host=RedisHost, port=RedisPort, password=RedisPassword, db=RedisDB, decode_responses=True)
    print(r.get('123'))

