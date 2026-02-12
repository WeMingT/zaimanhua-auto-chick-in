import time
import random
import requests
import json
import argparse
from playwright.sync_api import sync_playwright
from utils import get_all_cookies, extract_user_info_from_cookies, print_task_status, claim_task_reward, claim_rewards, create_browser_context

# Configuration
API_BASE = "https://v4api.zaimanhua.com/app/v1"
PAGE_READ_TIME = 8  # Seconds per page
USER_AGENT = 'okhttp/4.9.3'

class ZaimanhuaAppReader:
    def __init__(self, cookie_str, debug=False):
        self.cookie_str = cookie_str
        self.user_info = extract_user_info_from_cookies(cookie_str)
        self.token = self.user_info.get('token')
        self.debug = debug
        
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'User-Agent': USER_AGENT,
            'Accept': 'application/json, text/plain, */*', 
        }
        
    def get_token(self):
        return self.token

    def get_task_status(self, task_id):
        """获取特定任务的状态码。返回状态码或 None。"""
        url = "https://i.zaimanhua.com/lpi/v1/task/list"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('errno') == 0:
                    task_data = data.get('data', {}).get('task', {})
                    tasks = []
                    if isinstance(task_data, dict):
                         tasks.extend(task_data.get('dayTask', []) or [])
                         tasks.extend(task_data.get('newUserTask', []) or [])
                    
                    for task in tasks:
                        if task.get('id') == task_id:
                            status = task.get('status')
                            if self.debug:
                                print(f"DEBUG: 任务 {task_id} 当前状态为 {status}")
                            return status
            return None
        except Exception as e:
            print(f"检查任务状态出错: {e}")
            return None

    def get_comic_list(self):
        """获取漫画列表"""
        url = f"{API_BASE}/comic/rank/list"
        params = {
            'tag_id': '0',
            'page': '1',
            '_v': '2.2.5'
        }
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('errno') == 0:
                    data_obj = data.get('data')
                    if isinstance(data_obj, dict):
                        return data_obj.get('data', [])
                    elif isinstance(data_obj, list):
                        return data_obj
            print(f"获取漫画列表失败: {resp.text[:100]}")
        except Exception as e:
            print(f"获取漫画列表出错: {e}")
        return []

    def get_chapter_list(self, comic_id):
        """获取漫画章节"""
        url = f"{API_BASE}/comic/detail/{comic_id}"
        params = {'_v': '2.2.5'}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('errno') == 0:
                    inner_data = data.get('data', {}).get('data', {})
                    volumes = inner_data.get('chapters', [])
                    all_chapters = []
                    for volume in volumes:
                        if 'data' in volume and isinstance(volume['data'], list):
                            for chapter in volume['data']:
                                if chapter.get('canRead', True):
                                    all_chapters.append(chapter)
                    return all_chapters
            print(f"获取章节列表失败 {comic_id}: {resp.text[:100]}")
        except Exception as e:
            print(f"获取章节列表出错: {e}")
        return []

    def get_chapter_images(self, comic_id, chapter_id):
        """获取章节图片"""
        url = f"{API_BASE}/comic/chapter/{comic_id}/{chapter_id}"
        params = {'_v': '2.2.5'}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('errno') == 0:
                    chapter_data = data.get('data', {}).get('data', {})
                    images = chapter_data.get('images') or chapter_data.get('page_url')
                    return images
            print(f"获取图片列表失败 {comic_id}/{chapter_id}")
        except Exception as e:
            print(f"获取图片列表出错: {e}")
        return []

    def simulate_reading(self, minutes=1):
        """模拟阅读指定时长（分钟）"""
        print(f"开始模拟阅读 {minutes} 分钟...")
        
        start_time = time.time()
        end_time = start_time + (minutes * 60)
        
        comics = self.get_comic_list()
        if not comics:
            print("未找到任何漫画。" )
            return False
            
        random.shuffle(comics)
        total_images_read = 0
        
        while time.time() < end_time:
            if not comics:
                comics = self.get_comic_list()
                if not comics: break
                random.shuffle(comics)
                
            comic = comics.pop()
            comic_id = comic.get('comic_id')
            comic_name = comic.get('title', '未知')
            
            chapters = self.get_chapter_list(comic_id)
            if not chapters: continue
                
            chapter = random.choice(chapters)
            chapter_id = chapter.get('chapter_id')
            
            images = self.get_chapter_images(comic_id, chapter_id)
            if not images: continue
                
            for i, img_url in enumerate(images):
                if time.time() >= end_time: break
                try:
                    requests.get(img_url, headers=self.headers, timeout=10)
                    total_images_read += 1
                except: pass
                
                # 模拟每页阅读时间
                sleep_time = PAGE_READ_TIME + random.uniform(-1, 2)
                if minutes < 0.5: sleep_time = 0.5 # 快速测试模式
                time.sleep(sleep_time)
            
            time.sleep(2)
            
        print(f"本次阅读结束，阅读了 {total_images_read} 页。" )
        return True

def try_ui_claim(cookie_str):
    """尝试使用 Playwright UI 领取奖励"""
    print("启动浏览器尝试 UI 领取...")
    with sync_playwright() as p:
        browser, context, page = create_browser_context(p, cookie_str)
        try:
            success = claim_rewards(page, cookie_str)
            return success
        except Exception as e:
            print(f"UI 领取出错: {e}")
            return False
        finally:
            browser.close()

def run_auto_read():
    parser = argparse.ArgumentParser(description='Zaimanhua Auto Read Script')
    parser.add_argument('--max-minutes', type=int, default=30, help='最大阅读时长（分钟）')
    parser.add_argument('--debug', action='store_true', help='开启调试日志')
    args = parser.parse_args()

    MAX_MINUTES = args.max_minutes
    TASK_ID = 13 # 海螺小姐 (阅读10分钟)

    cookies_list = get_all_cookies()
    if not cookies_list:
        print("未发现 Cookie 记录。" )
        return False
        
    for label, cookie_str in cookies_list:
        print(f"\n{'='*60}")
        print(f"账号: {label}")
        print(f"{'='*60}")

        # 验证 Cookie 有效性
        from utils import validate_cookie
        is_valid, error_msg = validate_cookie(cookie_str)
        if not is_valid:
            print(f"[ERROR] Cookie 无效: {error_msg}")
            print(f"请更新 {label} 的 Cookie")
            continue

        reader = ZaimanhuaAppReader(cookie_str, debug=args.debug)
        token = reader.get_token()
        if not token:
            print("Token 无效，跳过该账号。")
            continue
        
        # 1. 初始检查
        status = reader.get_task_status(TASK_ID)
        
        # 根据用户确认：Status 2 = 可领取，Status 3 = 已完成
        if status == 3:
            print(f"任务 {TASK_ID} 已完成 (Status 3)。")
            # 顺便检查其他奖励
            try_ui_claim(cookie_str)
            continue
            
        elif status == 2:
             print(f"任务 {TASK_ID} 处于“可领取”状态 (Status 2)。尝试领取...")
             success, res = claim_task_reward(token, TASK_ID)
             if success:
                 print(f"API 领取成功！")
                 status = 3
             else:
                 print(f"API 领取失败 (响应: {res})。尝试切换到 UI 领取模式...")
                 if try_ui_claim(cookie_str):
                     print("UI 领取成功！")
                     status = 3
                 else:
                     print("UI 领取也失败了，可能需要继续阅读？")
                     
        elif status is None:
            print(f"无法确定任务 {TASK_ID} 的状态，跳过阅读。")
            continue
            
        if status != 3:
            print(f"任务 {TASK_ID} 尚未结束 (Status {status})，开始阅读循环。")
            # 2. 阅读循环
            for m in range(1, MAX_MINUTES + 1):
                print(f"\n--- 第 {m}/{MAX_MINUTES} 分钟 ---")
                reader.simulate_reading(minutes=1)
                
                # 每分钟检查一次状态
                new_status = reader.get_task_status(TASK_ID)
                
                if new_status == 3:
                     print(f"\n任务 {TASK_ID} 已变成 Status 3 (已完成)。")
                     break
                
                if new_status == 2:
                    print(f"状态为 2 (可领取)。尝试领取...")
                    success, res = claim_task_reward(token, TASK_ID)
                    if success:
                        print(f"API 领取成功！任务结束。")
                        break
                    else:
                        print(f"API 领取失败 (响应: {res})。尝试 UI 领取...")
                        if try_ui_claim(cookie_str):
                            print("UI 领取成功！任务结束。")
                            break
                        else:
                            print("UI 领取失败，继续阅读...")

                if m == MAX_MINUTES:
                    print(f"\n已达到最大阅读时长 {MAX_MINUTES} 分钟，任务仍未完成 (Status {new_status})。")

        # 3. 结束前再次尝试 UI 领取所有奖励
        # try_ui_claim(cookie_str)
            
    return True

if __name__ == "__main__":
    success = run_auto_read()
    exit(0 if success else 1)