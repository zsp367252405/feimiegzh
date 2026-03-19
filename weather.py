# -*- coding: utf-8 -*-
import os
import time
import requests

# 从环境变量获取配置
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
SERVER_CHAN_KEY = os.getenv("SERVER_CHAN_KEY")

DOUBAO_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
MODEL = "doubao-seed-2-0-pro-260215"


def require_env(name):
    """检查环境变量是否存在"""
    val = os.getenv(name)
    if not val or not val.strip():
        raise RuntimeError(f"Missing environment variable: {name}")
    return val.strip()


def get_weather():
    """获取天气预报"""
    api_key = require_env("DOUBAO_API_KEY")

    prompt = """
你是专业天气预报员。
请生成 厦门市同安区 大同街道 & 祥平街道 今天 06:00~明天 06:00 逐小时天气预报。
严格按下面格式输出，不要多余文字，不要解释，只输出预报：

时间  天气  图标
使用下面固定图标，不能用其他：
晴 ☀️
多云 ⛅
阴 ☁️
晴转多云 🌤
多云转阴 🌥
小雨 🌦
中雨 🌧
大雨 🌨
雷阵雨 ⛈

只输出 06:00—次日06:00，逐小时一条，格式工整。
""".strip()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    # 添加重试机制
    for attempt in range(3):
        try:
            resp = requests.post(DOUBAO_URL, headers=headers, json=data, timeout=120)
            break
        except requests.exceptions.Timeout:
            if attempt < 2:
                print(f"请求超时，{attempt+1}秒后重试...")
                time.sleep(attempt + 1)
            else:
                raise RuntimeError("请求超时，已重试3次")

    if not resp.ok:
        raise RuntimeError(f"DOUBAO HTTP {resp.status_code}: {resp.text}")

    resp_json = resp.json()
    if resp_json.get("error"):
        raise RuntimeError(f"DOUBAO error: {resp_json['error']}")

    return resp_json["choices"][0]["message"]["content"]


def send_feishu(content):
    """发送到飞书"""
    webhook = require_env("FEISHU_WEBHOOK")

    msg = {
        "msg_type": "text",
        "content": {
            "text": f"🌤 厦门同安 每日天气预报（06:00-次日06:00）\n\n{content}"
        },
    }
    resp = requests.post(webhook, json=msg, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"FEISHU HTTP {resp.status_code}: {resp.text}")


def send_server_chan(content):
    """发送到 Server 酱（微信推送）"""
    key = require_env("SERVER_CHAN_KEY")

    url = f"https://sctapi.ftqq.com/{key}.send"

    data = {
        "title": "🌤 厦门同安每日天气预报（06:00-次日06:00）",
        "desp": content
    }

    resp = requests.post(url, data=data, timeout=30)
    result = resp.json()

    if result.get("code") != 0:
        raise RuntimeError(f"Server酱推送失败: {result.get('message')}")


def main():
    """主函数"""
    print("=" * 50)
    print("开始获取天气...")
    weather = get_weather()
    print("天气获取成功")

    # 发送到飞书
    if FEISHU_WEBHOOK:
        print("正在发送到飞书...")
        send_feishu(weather)
        print("✅ 飞书发送成功")

    # 发送到 Server 酱
    if SERVER_CHAN_KEY:
        print("正在发送到微信（Server酱）...")
        send_server_chan(weather)
        print("✅ 微信发送成功")

    print("\n天气内容：")
    print(weather)


if __name__ == "__main__":
    main()
