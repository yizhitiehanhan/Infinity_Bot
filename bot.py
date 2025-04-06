import asyncio
import sys
from curl_cffi.requests import AsyncSession
from loguru import logger



logger.remove()
logger.add(sys.stdout, colorize=True, format="<g>{time:HH:mm:ss:SSS}</g> | <level>{message}</level>")


class Twitter:
    def __init__(self, auth_token):
        self.auth_token = auth_token
        bearer_token = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
        defaulf_headers = {
            "authority": "x.com",
            "origin": "https://x.com",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
            "authorization": bearer_token,
        }
        defaulf_cookies = {"auth_token": auth_token}
        self.Twitter = AsyncSession(headers=defaulf_headers, cookies=defaulf_cookies, timeout=120, impersonate="chrome120")
        self.auth_code = None

    async def get_auth_code(self):
        try:
            params = {
                'code_challenge': '0ioze5m20493ny2',
                'code_challenge_method': 'plain',
                'client_id': 'OE52bVNwQkNOeWhwSGY1Y0hDck46MTpjaQ',
                'redirect_uri': 'https://www.infinityg.ai',
                'response_type': 'code',
                'scope': 'tweet.read offline.access tweet.write tweet.moderate.write users.read follows.read follows.write like.read like.write',
                'state': 'profile'
            }
            response = await self.Twitter.get('https://x.com/i/api/2/oauth2/authorize', params=params)
            if "code" in response.json() and response.json()["code"] == 353:
                self.Twitter.headers.update({"x-csrf-token": response.cookies["ct0"]})
                return await self.get_auth_code()
            elif response.status_code == 429:
                await asyncio.sleep(5)
                return self.get_auth_code()
            elif 'auth_code' in response.json():
                self.auth_code = response.json()['auth_code']
                return True
            logger.error(f'{self.auth_token} 获取auth_code失败')
            return False
        except Exception as e:
            logger.error(e)
            return False

    async def twitter_authorize(self):
        try:
            if not await self.get_auth_code():
                return False
            data = {
                'approval': 'true',
                'code': self.auth_code,
            }
            response = await self.Twitter.post('https://x.com/i/api/2/oauth2/authorize', data=data)
            if 'redirect_uri' in response.text:
                return True
            elif response.status_code == 429:
                await asyncio.sleep(5)
                return self.twitter_authorize()
            logger.error(f'{self.auth_token}  推特授权失败')
            return False
        except Exception as e:
            logger.error(f'{self.auth_token}  推特授权异常：{e}')
            return False


class Infinity:
    def __init__(self, address,auth_token,proxy):
        self.client = AsyncSession(timeout=120, impersonate="chrome120", proxy=proxy)
        self.twitter = Twitter(auth_token)
        self.auth_token=auth_token
        self.proxy=proxy
        self.address=address

    async def login(self):
        try:
            json_data={
                "loginChannel": "MAIN_PAGE",
                "walletChain": "Ethereum",
                "walletType": "metamask",
                "walletAddress": self.address,
                "inviteCode": "NGKTCY"
            }
            res = await self.client.post('https://api.infinityg.ai/api/v1/user/auth/wallet_login',json=json_data)
            if res.json()['code'] == "90000":
                token = res.json()['data']['token']
                self.client.headers.update({"Authorization": f"Bearer {token}"})
                logger.success(f'{[self.address]} 登录成功')
                return await self.doTask()
            logger.error(f'{[self.address]} 登录失败: {res.text}')
            return False
        except Exception as e:
            logger.error(f'{[self.address]} 登录失败: {e}')
            return False
        

    async def doTask(self, do=False):
        try:
            res = await self.client.post('https://api.infinityg.ai/api/v1/task/list')
            if res.json()['code'] == "90000":
                if res.json()['data']['twitterUserName'] is None:
                    if await self.bindTwitter():
                        logger.success(f"[{self.address}] 推特绑定成功")
                    else:
                        return False    
                family_task = res.json()['data']['taskModelResponses'][0]['taskResponseList']
                communit_task = res.json()['data']['taskModelResponses'][2]['taskResponseList']
                all_task = family_task + communit_task 
                family_task_noFinsh = [task for task in all_task if task.get('status') != 3]
                if family_task_noFinsh:
                    for task in family_task_noFinsh:
                        json_data={
                            "taskId":task.get('taskId')
                        }
                        taskDesc = task.get('taskDesc')
                        res =await self.client.post('https://api.infinityg.ai/api/v1/task/complete',json=json_data)
                        if res.json()['code']== "90000":
                            res =await self.client.post('https://api.infinityg.ai/api/v1/task/claim',json=json_data)
                            if res.json()['code']== "90000":
                                logger.success(f"[{self.address}] [{taskDesc}]执行成功")
                            else:
                                logger.error(f"[{self.address}] [{taskDesc}]执行失败 {res.text}")
                                return False
                        else:
                            return False               
                return await self.checkIn()
            logger.error(f"[{self.address}] 任务失败")
            return False
        except Exception as e:
            logger.error(f"[{self.address}] 任务失败：{e}")
            return False  


    async def bindTwitter(self):
        try:
            if not await self.twitter.twitter_authorize():
                return False
            params = {
                'state': "profile",
                'code': self.twitter.auth_code,
            }
            res = await self.client.get("https://api.infinityg.ai/api/v1/oauth/getTwitterCode", params=params)
            if res.status_code == 200:
                return True
            logger.error(f"[{self.address}] 绑定推特失败")
            return False
        except Exception as e:
            logger.error(f"[{self.address}] 绑定推特失败：{e}")
            return False     

    async def checkIn(self):
        try:
            res = await self.client.post('https://api.infinityg.ai/api/v1/task/checkIn/')
            if res.json()['code'] == "90000":
                logger.success(f"[{self.address}] 签到成功,[{res.text}]")
            else:
                logger.error(f'{self.address}] 签到失败')             
            return True
        except Exception as e:
            logger.error(f'{[self.auth_token]} 签到失败: {e}')
            return False      


async def do(semaphore, account_line):
    async with semaphore:
        accounts = account_line.strip().split('----')
        for _ in range(3):
            if await Infinity(accounts[0], accounts[1],accounts[2]).login():
                break


async def main(file_path, semaphore):
    semaphore = asyncio.Semaphore(semaphore)
    with open(file_path, 'r') as f:
        task = [do(semaphore, account_line) for account_line in f]
    await asyncio.gather(*task)


if __name__ == '__main__':
    asyncio.run(main("D:\\WorkSpace\\web3Task\\社交签到\\voyage\\config.txt", 1))
