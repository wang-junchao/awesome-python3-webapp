#协程异步模型
#logging模块定义了一些函数和模块，可以帮助我们队一个应用程序或库实现一个灵活的事件日志处理系统
#logging模块可以记录错误信息，并在错误信息记录后继续执行
import logging
#设置logging的默认lever为INFO
#日志级别大小关系为：CRITICAL>ERROR>WARNING>INFO>DEBUG>NOTSET
import logging.basicConfig(level=logging.INFO)
#asyncio内置对异步IO的支持
import asyncio,
#os模块提供了调用操作系统的接口函数
import os
#json模块提供了python对象到Json模块的转换
import json
#各种操作时间的函数
import time
#datetime是处理日期和时间的标准库
from datetime import datetime
#aiohttp是基于asyncio实现的http框架
from aiohttp import web

def index(request):
	return web.Response(body=b'<h1>Awesome</h1>',content_type='text/html',charset='UTF-8') #必须制定content_type  否则无法识别

@asyncio.coroutinev 

def init(loop):
	#创建APP对象
	app=web.Application(loop=loop)
	app.router.add_route('GET','/',index)#app的请求方式及打开首页
	srv=yield from loop.create_server(app.make_handler(),'127.0.0.1',9000)
	logging.info('server started at httpL//127.0.0.1:9000...')
	return srv
#asyncio的编程模块实际上就是一个消息循环，我们从asyncio模块中直接获取一个eventloop（事件循环）的引用，//
#然后把需要执行的协程扔到eventloop中执行，就实现了异步IO
#第一步就是妖获取eventloop

#get_event_loop()=>获取当前脚本下的事件循环，返回一个eventloo对象（这个对象类型是'asyncio.windows_events._WindowsSelectorEventLoop')//
#实现AbstractEventLoop(事件循环的基类)接口，如果当前脚本下没有事件循环，将抛出异常，get_event_loop()永远不会抛出None

loop=asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()