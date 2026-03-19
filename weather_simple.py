# -*- coding: utf-8 -*-
import requests
import time

# 配置 - 直接写死密钥
DOUBAO_API_KEY = "ec271d52-563f-4813-9e7d-d0cb6e697b06"
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/a730d3fb-b3e3-44e8-828f-f51a22482f71"

DOUBAO_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
MODEL = "doubao-seed-2-0-pro-260215"


def get_weather():
    """获取天气预报"""
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
        "Authorization": f"Bearer {DOUBAO_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    resp = requests.post(DOUBAO_URL, headers=headers, json=data, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"DOUBAO HTTP {resp.status_code}: {resp.text}")

    resp_json = resp.json()
    if resp_json.get("error"):
        raise RuntimeError(f"DOUBAO error: {resp_json['error']}")

    return resp_json["choices"][0]["message"]["content"]


def send_feishu(content):
    """发送到飞书"""
    msg = {
        "msg_type": "text",
        "content": {
            "text": f"🌤 厦门同安 每日天气预报（06:00-次日06:00）\n\n{content}"
        },
    }
    resp = requests.post(FEISHU_WEBHOOK, json=msg, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"FEISHU HTTP {resp.status_code}: {resp.text}")


def main():
    """主函数"""
    print("=" * 50)
    print("开始获取天气...")
    weather = get_weather()
    print("天气获取成功")

    print("正在发送到飞书...")
    send_feishu(weather)
    print("✅ 飞书发送成功")
    print(weather)


if __name__ == "__main__":
    main()
