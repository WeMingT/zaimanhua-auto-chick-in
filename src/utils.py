"""共享工具函数"""
import os
import json
import requests
from urllib.parse import unquote
from dotenv import load_dotenv


# 配置
PAGE_TIMEOUT = 60000


def extract_user_info_from_cookies(cookie_str):
    """从 Cookie 中提取用户信息用于设置 localStorage"""
    user_info = {}

    # 解析 lginfo cookie - 它是 URL 编码的 JSON
    for item in cookie_str.split(';'):
        item = item.strip()
        if item.startswith('lginfo='):
            lginfo_value = item[7:]  # Remove 'lginfo='
            lginfo_decoded = unquote(lginfo_value)
            # 尝试解析为 JSON
            try:
                parsed = json.loads(lginfo_decoded)
                # 确保解析结果是字典类型（防止 JSON 字符串字面量导致 .get() 失败）
                if isinstance(parsed, dict):
                    user_info = parsed
            except json.JSONDecodeError:
                # 如果不是 JSON，尝试解析 key=value&key=value 格式
                for pair in lginfo_decoded.split('&'):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        user_info[k] = v
            break

    # 如果没有从 lginfo 获取到，尝试从 addinfo 获取
    if not user_info.get('uid'):
        for item in cookie_str.split(';'):
            item = item.strip()
            if item.startswith('addinfo='):
                # addinfo 格式: uid|username|phone|token
                parts = item[8:].split('|')
                if len(parts) >= 4:
                    user_info = {
                        'uid': int(parts[0]),
                        'username': parts[1],
                        'nickname': parts[1],
                        'bind_phone': parts[2],
                        'token': parts[3]
                    }
                break

    # 确保有 token
    if not user_info.get('token'):
        for item in cookie_str.split(';'):
            item = item.strip()
            if item.startswith('token='):
                user_info['token'] = item[6:]
                break

    return user_info


def init_localstorage(page, cookie_str):
    """在当前页面设置 localStorage 以确保 Vue 应用识别登录状态"""
    user_info = extract_user_info_from_cookies(cookie_str)

    if not user_info.get('uid'):
        print("警告: 无法从 Cookie 中提取用户信息")
        return False

    # 如果 user_info 已经是完整的 lginfo 格式，直接使用
    # 否则构建完整的 lginfo 对象
    if 'setPasswd' not in user_info:
        lginfo = {
            "uid": int(user_info.get('uid', 0)),
            "username": user_info.get('username', user_info.get('nickname', '')),
            "nickname": user_info.get('nickname', user_info.get('username', '')),
            "email": user_info.get('email', ''),
            "photo": user_info.get('photo', ''),
            "bind_phone": user_info.get('bind_phone', ''),
            "sex": int(user_info.get('sex', 0)),
            "token": user_info.get('token', ''),
            "setPasswd": 1,
            "bindWechat": user_info.get('bindWechat', False),
            "bindQq": user_info.get('bindQq', False),
            "bindSina": user_info.get('bindSina', False),
            "status": user_info.get('status', 1),
            "is_sign": user_info.get('is_sign', True),
            "user_level": user_info.get('user_level', 1),
            "isInUserWhitelist": user_info.get('isInUserWhitelist', False)
        }
    else:
        lginfo = user_info

    # Set localStorage
    lginfo_json = json.dumps(lginfo, ensure_ascii=False)
    page.evaluate(f'localStorage.setItem("lginfo", {json.dumps(lginfo_json)})')
    print(f"已设置 localStorage (uid: {lginfo.get('uid')})")
    return True


def _make_account_label(default_label, cookie_str):
    """从 Cookie 中提取用户名，生成带用户名的账号标签"""
    try:
        user_info = extract_user_info_from_cookies(cookie_str)
        if isinstance(user_info, dict):
            name = user_info.get('nickname') or user_info.get('username')
            if name:
                return f"{default_label} ({name})"
    except Exception:
        pass
    return default_label


def validate_cookie(cookie_str):
    """验证 Cookie 是否有效，返回 (is_valid, error_msg)"""
    user_info = extract_user_info_from_cookies(cookie_str)
    token = user_info.get('token') if isinstance(user_info, dict) else None

    if not token:
        return False, "Cookie 中未找到 token"

    task_result = get_task_list(token)
    if task_result is None:
        return False, "无法连接到服务器"
    if task_result.get('errno') != 0:
        errmsg = task_result.get('errmsg', '未知错误')
        return False, f"API 返回错误: {errmsg}"

    return True, None


def get_all_cookies():
    """获取所有账号的 Cookie"""
    load_dotenv()  # 自动加载 .env 文件（本地测试用）

    cookies_list = []
    single = os.environ.get('ZAIMANHUA_COOKIE')
    if single:
        label = _make_account_label('默认账号', single)
        cookies_list.append((label, single))
    i = 1
    while True:
        cookie = os.environ.get(f'ZAIMANHUA_COOKIE_{i}')
        if cookie:
            label = _make_account_label(f'账号 {i}', cookie)
            cookies_list.append((label, cookie))
            i += 1
        else:
            break
    return cookies_list


def parse_cookies(cookie_str):
    """解析 Cookie 字符串为 Playwright 格式"""
    cookies = []
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            name, value = item.split('=', 1)
            cookies.append({
                'name': name.strip(),
                'value': value.strip(),
                'domain': '.zaimanhua.com',
                'path': '/'
            })
    return cookies


def get_task_list(token):
    """通过 API 获取任务列表"""
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://i.zaimanhua.com/',
        'Accept': 'application/json, text/plain, */*',
    }

    try:
        resp = requests.get('https://i.zaimanhua.com/lpi/v1/task/list', headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  获取任务列表失败: HTTP {resp.status_code}")
            return None
    except Exception as e:
        print(f"  获取任务列表异常: {e}")
        return None


def extract_tasks_from_response(task_result):
    """从任务 API 响应中提取所有任务列表

    API 响应结构:
    {
        "errno": 0,
        "data": {
            "task": {
                "dayTask": [...],      # 每日任务
                "newUserTask": [...]   # 新用户任务
            },
            "userCurrency": {...}
        }
    }

    任务状态值:
    - status=1: 未完成
    - status=2: 可领取（任务已完成，等待领取奖励）
    - status=3: 已完成（奖励已领取）
    """
    if not task_result or task_result.get('errno') != 0:
        return []

    data = task_result.get('data', {})
    if not isinstance(data, dict):
        return []

    # 尝试从嵌套结构中提取任务
    task_data = data.get('task', {})
    if isinstance(task_data, dict):
        day_tasks = task_data.get('dayTask', [])
        new_user_tasks = task_data.get('newUserTask', [])
        if day_tasks or new_user_tasks:
            all_tasks = (day_tasks or []) + (new_user_tasks or [])
            # 过滤掉非字典类型的项目，防止 'str' object has no attribute 'get' 错误
            return [t for t in all_tasks if isinstance(t, dict)]

    # 回退：尝试其他可能的结构
    if 'list' in data:
        tasks = data.get('list', [])
        return [t for t in tasks if isinstance(t, dict)]
    if 'tasks' in data:
        tasks = data.get('tasks', [])
        return [t for t in tasks if isinstance(t, dict)]

    return []


def print_task_status(cookie_str, label=""):
    """打印当前任务状态（用于调试）"""
    token = None
    user_info = extract_user_info_from_cookies(cookie_str)
    # 确保 user_info 是字典类型
    if isinstance(user_info, dict):
        token = user_info.get('token')
    if not token:
        for item in cookie_str.split(';'):
            item = item.strip()
            if item.startswith('token='):
                token = item[6:]
                break

    if not token:
        print(f"  [{label}] 无法获取 token，跳过任务状态检查")
        return

    print(f"\n=== 任务状态 {label} ===")
    task_result = get_task_list(token)

    if task_result:
        print(f"  API 响应: errno={task_result.get('errno')}")
        if task_result.get('errno') == 0:
            tasks = extract_tasks_from_response(task_result)

            if tasks:
                print(f"  任务数量: {len(tasks)}")
                for task in tasks:
                    task_id = task.get('id') or task.get('taskId')
                    task_name = task.get('title') or task.get('name') or task.get('taskName', '未知')
                    task_desc = task.get('desc', '')
                    status = task.get('status', '?')

                    # 状态说明: 1=未完成, 2=可领取, 3=已完成
                    status_desc = {1: '未完成', 2: '可领取', 3: '已完成'}.get(status, f'未知({status})')

                    # 获取奖励信息
                    currency = task.get('currency', {})
                    credits = currency.get('credits', 0) if isinstance(currency, dict) else 0

                    print(f"    - [{task_id}] {task_name}: {status_desc}")
                    if task_desc:
                        print(f"        描述: {task_desc}")
                    if credits:
                        print(f"        奖励: {credits} 积分")
            else:
                data = task_result.get('data', {})
                print(f"  原始数据: {json.dumps(data, ensure_ascii=False)[:500]}")
        else:
            print(f"  API 错误: {task_result.get('errmsg', '未知错误')}")
    else:
        print("  无法获取任务列表")


def claim_task_reward(token, task_id):
    """通过 API 领取单个任务奖励"""
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://i.zaimanhua.com/',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
    }

    last_result = None

    # 尝试多种 API 端点和参数组合
    # 组合 1: POST 请求 + JSON body（最常见的 RESTful 风格）
    json_body_endpoints = [
        'https://i.zaimanhua.com/lpi/v1/task/receive',
        'https://i.zaimanhua.com/lpi/v1/task/claim',
        'https://i.zaimanhua.com/lpi/v1/task/get_reward',
    ]

    # 尝试不同的参数名: id, taskId, task_id
    param_names = ['id', 'taskId', 'task_id']

    for url in json_body_endpoints:
        for param_name in param_names:
            try:
                json_body = {param_name: task_id}
                resp = requests.post(url, headers=headers, json=json_body, timeout=10)
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get('errno') == 0 or result.get('code') == 0:
                        return True, result
                    errmsg = result.get('errmsg', '') or result.get('message', '')
                    if '已领取' in errmsg or '已完成' in errmsg:
                        return True, result
                    last_result = result
            except Exception as e:
                last_result = {'errmsg': str(e)}
                continue

    # 组合 2: GET 请求 + query string（旧版兼容）
    for param_name in param_names:
        query_urls = [
            f'https://i.zaimanhua.com/lpi/v1/task/receive?{param_name}={task_id}',
            f'https://i.zaimanhua.com/lpi/v1/task/claim?{param_name}={task_id}',
            f'https://i.zaimanhua.com/lpi/v1/task/get_reward?{param_name}={task_id}',
        ]
        for url in query_urls:
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get('errno') == 0 or result.get('code') == 0:
                        return True, result
                    errmsg = result.get('errmsg', '') or result.get('message', '')
                    if '已领取' in errmsg or '已完成' in errmsg:
                        return True, result
                    last_result = result
            except Exception as e:
                last_result = {'errmsg': str(e)}
                continue

    return False, last_result


def claim_rewards(page, cookie_str=None):
    """在用户中心领取已完成任务的积分

    优先使用 API 方式领取，如果失败则回退到 UI 方式

    任务状态值:
    - status=1: 未完成
    - status=2: 可领取（任务已完成，等待领取奖励）
    - status=3: 已完成（奖励已领取）
    """
    print("\n=== 领取积分任务 ===")

    # 尝试从 cookie_str 获取 token
    token = None
    if cookie_str:
        user_info = extract_user_info_from_cookies(cookie_str)
        # 确保 user_info 是字典类型
        if isinstance(user_info, dict):
            token = user_info.get('token')
        if not token:
            for item in cookie_str.split(';'):
                item = item.strip()
                if item.startswith('token='):
                    token = item[6:]
                    break

    # 如果有 token，尝试 API 方式
    if token:
        print("尝试通过 API 领取奖励...")
        task_result = get_task_list(token)

        if task_result and task_result.get('errno') == 0:
            tasks = extract_tasks_from_response(task_result)

            claimed_count = 0
            claimable_count = 0

            for task in tasks:
                task_id = task.get('id') or task.get('taskId')
                task_name = task.get('title') or task.get('name') or task.get('taskName', '未知任务')
                status = task.get('status', 0)

                # 状态说明:
                # - status=2: 可领取（任务已完成，等待领取奖励）
                # - status=3: 已完成（奖励已领取）
                if status == 2:
                    claimable_count += 1
                    print(f"  发现可领取任务: {task_name} (ID: {task_id}, status={status})")

                    if task_id:
                        success, result = claim_task_reward(token, task_id)
                        if success:
                            print(f"    [OK] 领取成功")
                            claimed_count += 1
                        else:
                            print(f"    [FAIL] 领取失败")
                elif status == 3:
                    print(f"  任务已领取: {task_name} (ID: {task_id}, status={status})")
                elif status == 1:
                    print(f"  任务未完成: {task_name} (ID: {task_id}, status={status})")

            if claimable_count == 0:
                print("没有可领取的奖励（没有已完成的任务）")
            else:
                print(f"尝试领取 {claimable_count} 个任务，成功 {claimed_count} 个")

            return True  # API 调用成功就返回 True

    # 回退到 UI 方式
    print("回退到 UI 方式领取...")
    try:
        # 访问用户中心
        print("访问用户中心...")
        page.goto('https://i.zaimanhua.com/', wait_until='domcontentloaded')
        page.wait_for_timeout(5000)

        # 查找所有可领取的按钮（尝试多种选择器）
        selectors = [
            ".okBtn", ".claim-btn", ".receive-btn", 
            "button:has-text('领取')", 
            "div:has-text('可领取')",  # 新增：针对测试中发现的文本
            "text=可领取积分",        # 新增：精确匹配
            "[class*='领取']"
        ]
        claim_buttons = []
        for selector in selectors:
            try:
                # 使用 query_selector_all 可能拿不到伪元素或动态文本，
                # 尝试 locator.all() 会更稳泛，但这里保持结构，先加 selector
                if 'text=' in selector:
                    buttons = page.locator(selector).all()
                else:
                    buttons = page.query_selector_all(selector)
                
                if buttons:
                    for btn in buttons:
                        # 再次过滤，确保可见且不是“已领取”
                        try:
                            if not btn.is_visible(): continue
                            txt = btn.inner_text()
                            if "已领取" in txt: continue
                            if btn not in claim_buttons:
                                claim_buttons.append(btn)
                        except: pass
            except:
                pass

        claimed_count = 0

        if claim_buttons:
            print(f"找到 {len(claim_buttons)} 个可领取的奖励")
            for i, btn in enumerate(claim_buttons):
                try:
                    btn_text = btn.inner_text()
                    print(f"  点击领取按钮 {i+1}: {btn_text}")
                    btn.click()
                    page.wait_for_timeout(1500)
                    claimed_count += 1
                except Exception as e:
                    print(f"  领取按钮 {i+1} 点击失败: {e}")

            print(f"成功领取 {claimed_count} 个奖励")
            return claimed_count > 0
        else:
            print("没有可领取的奖励")
            return True  # 没有奖励也算成功

    except Exception as e:
        print(f"领取积分失败: {e}")
        return False


def create_browser_context(playwright, cookie_str):
    """创建浏览器上下文"""
    cookies = parse_cookies(cookie_str)
    print(f"已解析 {len(cookies)} 个 Cookie")

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080}
    )
    context.add_cookies(cookies)
    page = context.new_page()
    page.set_default_timeout(PAGE_TIMEOUT)

    return browser, context, page
