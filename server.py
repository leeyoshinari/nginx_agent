#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: leeyoshinari
import os
import asyncio
from aiohttp import web
from common import get_ip, get_config
from dealController import Task

HOST = get_ip()
task = Task()
PID = os.getpid()
with open('pid', 'w', encoding='utf-8') as f:
    f.write(str(PID))


async def get_variable(request):
    return web.json_response({'code': 0, 'data': {'groupKey': task.group_key, 'prefix': task.prefix}})


async def main():
    app = web.Application()

    app.router.add_route('GET', '/get/variable', get_variable)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, get_config('port'))
    await site.start()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_forever()
