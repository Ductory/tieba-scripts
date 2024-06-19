import requests
import time
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

def api_json(api: str, param: Params) -> Json:
	url: str = gen_url(api, param)
	return requests.get(url).json()


'''
吧首页的贴子
'''
def forum_first_page(kw: str, *, pn: int=1, rn: int=20) -> Json:
	param: Params = {
		'kw': kw,
		'pn': str(pn),
		'rn': str(rn),
	}
	return api_json(API_FRS_PAGE, param)

'''
kz: thread id
pn: 当前页数
rn: 请求的回帖数
reverse: 倒序
'''
def thread_page(kz: int, *, pn: int=1, rn: int=30, reverse: bool=False) -> Json:
	param: Params = {
		'kz': str(kz),
		'pn': str(pn),
		'rn': str(rn),
	}
	if reverse == True:
		param['r'] = '1'
	return api_json(API_PB_PAGE, param)

def thread_floor(kz: int, pid: int, *, pn: int=1) -> Json:
	param: Params = {
		'kz': str(kz),
		'pid': str(pid),
		'pn': str(pn),
	}
	return api_json(API_PB_FLOOR, param)

'''
forum: 贴吧名
last_time: 上次检查的时间
'''
def check_first_thread(forum: str, *, last_time: int=0) -> int:
	def print_post(post: dict) -> None:
		print(f"delta_time:{time.time() - post['time']}")
		print(post['author']['id'])
		print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(post['time'])))
		print(post['content'])
	
	try:
		thread_list: list = forum_first_page(forum)['thread_list']
		for thread in thread_list:
			if thread['is_top'] == 0: # 跳过置顶帖
				break
		tid: int = thread['tid']
		# if thread['last_time_int'] <= last_time:
		# 	return last_time
		last_reply_time = max(last_time, thread['last_time_int'])
		new_flag = False
		# 遍历所有楼层
		pn: int = 0
		while True:
			pn += 1
			page: Json = thread_page(tid, pn=pn)
			for post in page['post_list']:
				if post['time'] > last_time:
					new_flag = True
					print_post(post)
					last_reply_time = max(last_reply_time, post['time'])
				pid = post['id']
				# 遍历楼中楼
				sub_pn: int = 0
				while True:
					sub_pn += 1
					sub_page: Json = thread_floor(tid, pid, pn=sub_pn)
					if 'subpost_list' not in sub_page:
						break
					for post in sub_page['subpost_list']:
						if post['time'] > last_time:
							new_flag = True
							print_post(post)
							last_reply_time = max(last_reply_time, post['time'])
					if sub_pn == sub_page['page']['total_page']:
						break
			if page['page']['has_more'] == 0: # 没有更多内容了
				break
	except Exception as e:
		pass
	return last_reply_time if new_flag else last_time

'''
forum: 贴吧名
last_time: 上次检查的时间
'''
def listen_reply(forum: str, *, last_time: int=0) -> None:
	while True:
		last_time = check_first_thread(forum, last_time=last_time)
		time.sleep(1)


if __name__ == '__main__':
	listen_reply('最爱小鸭', last_time=0)