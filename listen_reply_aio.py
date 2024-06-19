import aiohttp
import asyncio
import threading
import time
import json
from hashlib import md5
import urllib.parse as urlp
import sys


API_PB_PAGE = 'http://c.tieba.baidu.com/c/f/pb/page?'
API_FRS_PAGE = 'http://c.tieba.baidu.com/c/f/frs/page?'
API_PB_FLOOR = 'http://c.tieba.baidu.com/c/f/pb/floor?'

PARAM_CLIENT = {
	'BDUSS': 'R3Yi1mUFNCQnBaZVcxdFBmUzZvbzBoM3AwQWRUNWtScWhNbldqTnltU1djNlJqRVFBQUFBJCQAAAAAAQAAAAEAAADhmZtmRERhbmdmZXIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJbmfGOW5nxjfk',
}

type Params = dict[str, str]
type Json = dict

def gen_url(api: str, param: Params) -> str:
	param['sign'] = _sign(param)
	return api + urlp.urlencode(param)

def _sign(param: Params) -> str:
	#如果已经存在, 则重新签名
	if 'sign' in param:
		del param['sign']
	param.update(PARAM_CLIENT)
	param: Params = dict(sorted(param.items()))
	s: str = ''; k: str; v: str
	for k, v in param.items():
		s += k + '=' + v
	s += 'tiebaclient!!!'
	return md5(s.encode('utf-8')).hexdigest()

async def api_json(api: str, param: Params) -> Json:
	url: str = gen_url(api, param)
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			return json.loads(await response.text())


'''
吧首页的贴子
'''
async def forum_first_page(kw: str, *, pn: int=1, rn: int=20) -> Json:
	param: Params = {
		'kw': kw,
		'pn': str(pn),
		'rn': str(rn),
	}
	return await api_json(API_FRS_PAGE, param)

'''
kz: thread id
pn: 当前页数
rn: 请求的回帖数
reverse: 倒序
'''
async def thread_page(kz: int, *, pn: int=1, rn: int=30, reverse: bool=False) -> Json:
	param: Params = {
		'kz': str(kz),
		'pn': str(pn),
		'rn': str(rn),
	}
	if reverse == True:
		param['r'] = '1'
	return await api_json(API_PB_PAGE, param)

async def thread_floor(kz: int, pid: int, *, pn: int=1) -> Json:
	param: Params = {
		'kz': str(kz),
		'pid': str(pid),
		'pn': str(pn),
	}
	return await api_json(API_PB_FLOOR, param)


def print_post(post: dict) -> None:
	print(
f"""-----
delta_time:{time.time() - post['time']}
{post['author']['id']}
{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(post['time']))}
{post['content']}
-----""")

'''
forum: 贴吧名
last_time: 上次检查的时间
'''
async def check_first_thread(forum: str, *, last_time: int=0) -> int:
	thread_list: list = (await forum_first_page(forum))['thread_list']
	for thread in thread_list:
		if thread['is_top'] == 0: # 跳过置顶帖
			break
	tid: int = thread['tid']
	last_reply_time = max(last_time, thread['last_time_int'])

	is_running = True
	task_queue = asyncio.Queue(maxsize=3)
	lock = threading.Lock()
	new_flag = False

	async def producer(tid: int) -> None:
		for pn in range((await thread_page(tid))['page']['total_page'], 0, -1):
			await task_queue.put(pn)
		nonlocal is_running
		is_running = False

	async def worker(i: int):
		while True:
			try:
				pn = await asyncio.wait_for(task_queue.get(), timeout=1)
			except asyncio.TimeoutError:
				if is_running is False:
					return
			else:
				nonlocal tid
				nonlocal last_reply_time, last_time, new_flag
				nonlocal lock
				new_time = last_reply_time
				for post in (await thread_page(tid, pn=pn))['post_list']:
					if post['time'] > last_time:
						new_flag = True
						print_post(post)
						new_time = max(new_time, post['time'])
					pid = post['id']
					# 遍历楼中楼
					sub_pn = 0
					while True:
						sub_pn += 1
						sub_page: Json = await thread_floor(tid, pid, pn=sub_pn)
						if 'subpost_list' not in sub_page:
							break
						for post in sub_page['subpost_list']:
							if post['time'] > last_time:
								new_flag = True
								print_post(post)
								new_time = max(new_time, post['time'])
						if sub_pn == sub_page['page']['total_page']:
							break
				with lock:
					last_reply_time = max(last_reply_time, new_time)

	workers = [worker(i) for i in range(3)]
	await asyncio.gather(*workers, producer(tid))

	return last_reply_time

'''
forum: 贴吧名
last_time: 上次检查的时间
'''
async def listen_reply(forum: str, *, last_time: int=0) -> None:
	while True:
		last_time = await check_first_thread(forum, last_time=last_time)


if __name__ == '__main__':
	asyncio.run(listen_reply('最爱小鸭', last_time=0))