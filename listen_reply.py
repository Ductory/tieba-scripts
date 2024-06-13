import requests
import time
from hashlib import md5
import urllib.parse as urlp


API_PB_PAGE = 'http://c.tieba.baidu.com/c/f/pb/page?'
API_FRS_PAGE = 'http://c.tieba.baidu.com/c/f/frs/page?'


type Params = dict[str, str]
type Json = dict

def gen_url(api: str, param: Params) -> str:
	param['sign'] = _sign(param)
	return api + urlp.urlencode(param)

def _sign(param: Params) -> str:
	#如果已经存在, 则重新签名
	if 'sign' in param:
		del param['sign']
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
def thread_page(kz: int, *, pn: int=1, rn: int=20, reverse: bool=False) -> Json:
	param: Params = {
		'kz': str(kz),
		'pn': str(pn),
		'rn': str(rn)
	}
	if reverse == True:
		param['r'] = '1'
	return api_json(API_PB_PAGE, param)


'''
forum: 贴吧名
last_time: 上次检查的时间
'''
def check_first_thread(forum: str, *, last_time: int=0) -> int:
	thread_list: list = forum_first_page(forum)['thread_list']
	for thread in thread_list:
		if thread['is_top'] == 0: # 跳过置顶帖
			break
	last_reply_time = thread['last_time_int']
	post_list: list = thread_page(thread['tid'], reverse=True)['post_list'] # 倒序
	for post in post_list:
		if post['time'] <= last_time: # 说明之前已经检查过了
			break
		print(post['author']['id']) # 回帖者的uid（旧版）。不会获取楼中楼的
		print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(post['time'])))
		print(post['content'])
	return last_reply_time

'''
forum: 贴吧名
last_time: 上次检查的时间
'''
def listen_reply(forum: str, *, last_time: int=0) -> None:
	while True:
		last_time = check_first_thread(forum, last_time=last_time)
		time.sleep(1)


if __name__ == '__main__':
	listen_reply('最爱春雷')