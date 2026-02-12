"""抽奖自动化模块"""
import hashlib
import time
import os
import requests

from utils import extract_user_info_from_cookies, get_all_cookies, parse_cookies, validate_cookie
from playwright.sync_api import sync_playwright

# 配置
BASE_URL = "https://luck-draw.zaimanhua.com"
SECRET = "pD4vj_159753twt"
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"


def generate_sign(channel: str, timestamp: int) -> str:
    """生成 API 签名"""
    raw = f"{channel}{timestamp}{SECRET}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_api_headers(token: str) -> dict:
    """生成 API 请求头"""
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": MOBILE_UA,
        "Referer": BASE_URL,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }


def get_api_params() -> dict:
    """生成 API 请求参数"""
    timestamp = int(time.time() * 1000)
    return {
        "channel": "h5",
        "timestamp": timestamp,
        "sign": generate_sign("h5", timestamp)
    }


def check_lottery_status(token: str) -> dict:
    """获取抽奖状态和任务完成情况"""
    headers = get_api_headers(token)
    params = get_api_params()

    try:
        resp = requests.get(f"{BASE_URL}/drawApi/draw/draw_load", params=params, headers=headers)
        result = resp.json()
        return result
    except Exception as e:
        print(f"  [x] 获取抽奖状态异常: {e}")
        return {}


def execute_lottery_api(token: str) -> dict:
    """通过 API 执行一次抽奖"""
    headers = get_api_headers(token)
    params = get_api_params()

    try:
        resp = requests.get(f"{BASE_URL}/drawApi/draw/drawing", params=params, headers=headers)
        result = resp.json()

        errno = result.get("errno")
        errmsg = result.get("errmsg", "")
        data = result.get("data", {})

        if errno == 0:
            # 奖品信息在 data.prize.name 中
            prize_info = data.get("prize", {})
            prize_name = prize_info.get("name") or data.get("prize_name") or "未知奖品"
            print(f"  [v] 抽奖成功！获得: {prize_name}")
            return result
        else:
            print(f"  [x] 抽奖失败: {errmsg or '未知错误'}")
            return result
    except Exception as e:
        print(f"  [x] 抽奖异常: {e}")
        return {}


def run_lottery_with_browser(cookie_str: str, token: str):
    """使用浏览器执行完整抽奖流程（包括点击任务按钮）"""
    print("\n  === 开始抽奖流程 (浏览器模式) ===")

    cookies = parse_cookies(cookie_str)
    # 为抽奖域名设置 cookies
    lottery_cookies = []
    for c in cookies:
        lottery_cookies.append({
            'name': c['name'],
            'value': c['value'],
            'domain': 'luck-draw.zaimanhua.com',
            'path': '/'
        })

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=MOBILE_UA,
            viewport={'width': 375, 'height': 812}  # iPhone X 尺寸
        )
        context.add_cookies(lottery_cookies)
        page = context.new_page()

        try:
            # 1. 访问抽奖页面
            print("\n  [1] 访问抽奖页面...")
            page.goto(BASE_URL, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(5000)

            # 确保在"活动介绍"标签页（第一个标签）
            tab_items = page.locator(".navTab .tabItem")
            if tab_items.count() > 0:
                first_tab = tab_items.first
                first_tab.click(timeout=3000)
                page.wait_for_timeout(1500)
                print("    已切换到活动介绍标签")

            # 滚动到页面底部找到任务区域
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)

            # 2. 获取当前状态
            print("\n  [2] 获取抽奖状态...")
            status = check_lottery_status(token)
            if status.get("errno") != 0:
                print(f"    获取状态失败: {status}")
                return

            data = status.get("data", {})
            times = data.get("times", 0)

            # 使用 xxxTimes 字段判断任务完成状态
            follow_done = data.get('followTimes', 0) > 0
            share_done = data.get('shareTimes', 0) > 0
            read_done = data.get('readTimes', 0) > 0

            print(f"    当前抽奖次数: {times}")
            print(f"    关注任务: {'已完成' if follow_done else '未完成'}")
            print(f"    分享任务: {'已完成' if share_done else '未完成'}")
            print(f"    阅读任务: {'已完成' if read_done else '未完成'}")

            # 3. 点击任务按钮
            # 活动介绍页面结构: .imgBoxP7 > .btn1 (任务一), .btn2 (任务二), .btn3 (任务三)
            # 直接根据按钮文本判断是否需要点击
            print("\n  [3] 执行任务...")
            initial_times = times

            # 任务一：关注微博
            print("    [任务一] 关注微博...")
            follow_btn = page.locator(".imgBoxP7 .btn1")
            if follow_btn.count() > 0:
                btn_text = follow_btn.inner_text(timeout=2000).strip()
                print(f"      按钮文本: '{btn_text}'")
                if "去完成" in btn_text:
                    try:
                        follow_btn.click(timeout=3000)
                        page.wait_for_timeout(1500)
                        print("      已点击")
                    except Exception as e:
                        print(f"      点击失败: {e}")
                elif "已完成" in btn_text:
                    print("      任务已完成")
            else:
                print("      未找到按钮")

            # 任务二：分享页面
            print("    [任务二] 分享页面...")
            share_btn = page.locator(".imgBoxP7 .btn2")
            if share_btn.count() > 0:
                btn_text = share_btn.inner_text(timeout=2000).strip()
                print(f"      按钮文本: '{btn_text}'")
                if "去完成" in btn_text:
                    try:
                        share_btn.click(timeout=3000)
                        page.wait_for_timeout(1500)

                        # 等待弹窗出现并点击"复制"按钮
                        copy_btn = page.locator(".copyBtn")
                        if copy_btn.is_visible(timeout=3000):
                            copy_btn.click(timeout=3000)
                            page.wait_for_timeout(1500)
                            print("      已点击复制按钮")
                        else:
                            print("      未找到复制按钮")
                    except Exception as e:
                        print(f"      分享任务失败: {e}")
                elif "已完成" in btn_text:
                    print("      任务已完成")
            else:
                print("      未找到按钮")

            # 任务三：阅读漫画
            print("    [任务三] 阅读漫画...")
            read_btn = page.locator(".imgBoxP7 .btn3")
            if read_btn.count() > 0:
                btn_text = read_btn.inner_text(timeout=2000).strip()
                print(f"      按钮文本: '{btn_text}'")
                if "去完成" in btn_text:
                    try:
                        read_btn.click(timeout=3000)
                        page.wait_for_timeout(1500)
                        print("      已点击")
                    except Exception as e:
                        print(f"      点击失败: {e}")
                elif "已完成" in btn_text:
                    print("      任务已完成")
            else:
                print("      未找到按钮")

            # 4. 重新获取状态检查是否有新的抽奖次数
            page.wait_for_timeout(1000)
            status = check_lottery_status(token)
            data = status.get("data", {})
            times = data.get("times", 0)

            if times > initial_times:
                print(f"\n    任务完成！抽奖次数: {initial_times} -> {times}")

            # 5. 执行抽奖（通过 API）
            if times > 0:
                print(f"\n  [4] 执行抽奖 ({times} 次)...")
                for i in range(times):
                    print(f"\n    第 {i+1} 次:")
                    execute_lottery_api(token)
                    if i < times - 1:
                        time.sleep(2)
            else:
                print("\n  [!] 没有可用的抽奖次数")

        except Exception as e:
            print(f"  [x] 浏览器操作异常: {e}")
        finally:
            browser.close()

    print("\n  === 抽奖流程结束 ===")


def run_lottery_api_only(token: str):
    """仅使用 API 执行抽奖流程（无法完成需要点击的任务）"""
    print("\n  === 开始抽奖流程 (API 模式) ===")

    # 1. 获取当前状态
    print("\n  [1] 获取抽奖状态...")
    status = check_lottery_status(token)

    if status.get("errno") != 0:
        print(f"    获取状态失败: {status}")
        return

    data = status.get("data", {})
    times = data.get("times", 0)
    vote_info = data.get("voteInfo", {})

    print(f"    当前抽奖次数: {times}")
    print(f"    关注任务: {'已完成' if data.get('followTimes', 0) > 0 else '未完成'}")
    print(f"    分享任务: {'已完成' if vote_info.get('isShare') else '未完成'}")
    print(f"    阅读任务: {'已完成' if vote_info.get('isReading') else '未完成'}")

    # 2. 执行抽奖
    if times > 0:
        print(f"\n  [2] 执行抽奖 ({times} 次)...")
        for i in range(times):
            print(f"\n    第 {i+1} 次:")
            execute_lottery_api(token)
            if i < times - 1:
                time.sleep(2)
    else:
        print("\n  [!] 没有可用的抽奖次数")
        print("       提示: 需要完成任务才能获得抽奖次数")

    print("\n  === 抽奖流程结束 ===")


def main():
    """主函数"""
    print("=== 抽奖任务自动化 ===\n")

    cookies_list = get_all_cookies()
    if not cookies_list:
        print("错误: 请设置 ZAIMANHUA_COOKIE 环境变量")
        return False

    all_success = True
    for account_name, cookie_str in cookies_list:
        print(f"\n{'='*50}")
        print(f"账号: {account_name}")
        print('='*50)

        # 验证 Cookie 有效性
        is_valid, error_msg = validate_cookie(cookie_str)
        if not is_valid:
            print(f"  [ERROR] Cookie 无效: {error_msg}")
            print(f"  请更新 {account_name} 的 Cookie")
            all_success = False
            continue

        user_info = extract_user_info_from_cookies(cookie_str)
        token = user_info.get('token', '')

        if not token:
            print("  错误: Cookie 中未找到 token")
            all_success = False
            continue

        print(f"  用户: {user_info.get('nickname', user_info.get('username', '未知'))}")

        # 使用浏览器模式执行（可以点击任务按钮）
        run_lottery_with_browser(cookie_str, token)

    return all_success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
