import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import time

# 配置全局变量
MONITOR_INTERVAL = 10  # 监控间隔（秒）

# 加载环境变量
load_dotenv()

# 配置参数
TELEGRAM_TOKEN = "7645103344:AAGaBWdeOrW3LHukDS9CwBIeEVGUzj0oVX0"
CHAT_ID = "6136287262"
STATUS_FILE = 'app_status.json'  # 状态存储文件
PACKAGE_LIST = [
    "com.mangatoonmc.viewer",
    # 在此添加其他需要监控的包名
]

def send_telegram_notification(message: str) -> bool:
    """发送Telegram通知（使用URL参数方式）"""
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    try:
        response = requests.post(
            api_url,
            params={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=15
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Telegram通知发送失败: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"API错误详情: {e.response.text}")
        return False

def check_app_status(package_name: str) -> bool:
    """改进版Google Play状态检测"""
    url = f"https://play.google.com/store/apps/details?id={package_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20, allow_redirects=False)
        
        # 精确检测下架状态
        if response.status_code == 404:
            return False
        if response.status_code == 200:
            return "此应用在您所在地区不可用" not in response.text  # 根据实际页面关键词调整
        return None
    except Exception as e:
        print(f"[{datetime.now()}] {package_name} 检测异常: {str(e)}")
        return None

def load_app_status() -> dict:
    """加载状态文件，增强错误处理"""
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        print(f"状态文件加载失败: {str(e)}，将创建新文件")
        return {}

def save_app_status(current_status: dict):
    """保存状态文件，确保原子写入"""
    try:
        with open(STATUS_FILE + '.tmp', 'w') as f:
            json.dump(current_status, f, indent=2)
        os.replace(STATUS_FILE + '.tmp', STATUS_FILE)
    except Exception as e:
        print(f"状态保存失败: {str(e)}")

def format_message(package: str, is_available: bool, is_initial: bool = False) -> str:
    """生成带初始化标记的消息"""
    status = "✅ 谷歌审核通过" if is_available else "❌ 包被下架"
    if is_initial:
        status = "⚙️ - " + status
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return (
        f"<b>谷歌包 上下架通知</b>\n\n"
        f"<b>包名:</b> <code>{package}</code>\n"
        f"<b>状态:</b> {status}\n"
        f"<b>检测时间:</b> {timestamp}\n"
        f"<b>商店链接:</b> https://play.google.com/store/apps/details?id={package}"
    )

def monitor_apps():
    """改进版监控逻辑，支持初始化通知"""
    while True:
        print("\n=== 开始新的监控周期 ===")
        previous_status = load_app_status()
        current_status = {}

        for package in PACKAGE_LIST:
            # 添加请求间隔防止封禁
            time.sleep(3)

            status = check_app_status(package)
            if status is None:
                print(f"[{datetime.now()}] {package} 检查失败，跳过更新")
                continue

            current_status[package] = status
            previous = previous_status.get(package)

            # 初始化通知逻辑
            if previous is None:
                print(f"[{datetime.now()}] {package} 初始化状态: {'可用' if status else '下架'}")
                message = format_message(package, status, is_initial=True)
                if send_telegram_notification(message):
                    print(f"[{datetime.now()}] {package} 初始化通知已发送")
            else:
                # 状态变化通知
                if previous != status:
                    message = format_message(package, status)
                    if send_telegram_notification(message):
                        print(f"[{datetime.now()}] {package} 状态变更通知已发送")
                    else:
                        print(f"[{datetime.now()}] {package} 状态变更通知发送失败")

        save_app_status(current_status)

        # 等待设定的时间间隔
        print(f"=== 监控周期完成，等待 {MONITOR_INTERVAL} 秒后继续 ===")
        time.sleep(MONITOR_INTERVAL)

if __name__ == "__main__":
    print("=== 正在验证Telegram配置 ===")
    # 取消测试通知的发送，直接进入循环
    print("\n=== 开始应用状态监控 ===")
    monitor_apps()