# -*- coding: utf-8 -*-
import os
import re
import json
import time
import requests

# 从环境变量获取配置
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
SERVER_CHAN_KEY = os.getenv("SERVER_CHAN_KEY")

WEATHER_URL = "https://weather.com/zh-SG/weather/hourbyhour/l/42f0a76cf8c76f1a87a8e0c2c62b2997b17f9628c03ff9103b8487a194dba6df"

# 天气描述映射到中文
WEATHER_DESC = {
    "sunny": "晴",
    "mostly sunny": "晴",
    "partly cloudy": "晴云",
    "mostly cloudy": "云阴",
    "cloudy": "阴",
    "clear": "晴",
    "rain": "雨",
    "light rain": "小雨",
    "moderate rain": "中雨",
    "heavy rain": "大雨",
    "drizzle": "小雨",
    "showers": "阵雨",
    "scattered showers": "阵雨",
    "thunderstorms": "雷雨",
    "tstorms": "雷雨",
    "snow": "雪",
    "fog": "雾",
    "mist": "雾",
    "wind": "风",
}


def get_weather_desc(desc):
    """根据天气描述返回中文"""
    desc = desc.lower()
    for key, text in WEATHER_DESC.items():
        if key in desc:
            return text
    return "多云"


# 天气图标映射
WEATHER_ICONS = {
    "sunny": "☀️",
    "mostly sunny": "☀️",
    "partly cloudy": "⛅",
    "mostly cloudy": "🌥",
    "cloudy": "☁️",
    "clear": "☀️",
    "rain": "🌧",
    "light rain": "🌦",
    "heavy rain": "🌨",
    "thunderstorms": "⛈",
    "snow": "❄️",
    "fog": "🌫",
    "wind": "💨",
}

# 天气描述映射到图标
def get_weather_icon(desc):
    """根据天气描述返回图标"""
    desc = desc.lower()
    for key, icon in WEATHER_ICONS.items():
        if key in desc:
            return icon
    return "☁️"


def parse_weather_from_web():
    """从 weather.com 网页获取天气数据"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    for attempt in range(3):
        try:
            resp = requests.get(WEATHER_URL, headers=headers, timeout=30)
            break
        except requests.exceptions.Timeout:
            if attempt < 2:
                print(f"请求超时，重试 {attempt + 1}/3...")
                time.sleep(2)
            else:
                raise RuntimeError("获取天气页面失败")

    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code}")

    html = resp.text

    # 尝试从页面中提取 JSON 数据
    # weather.com 会在页面中嵌入小时预报数据
    pattern = r'window\.\w+\s*=\s*(\{.*?"hourlyForecast".*?\})'
    match = re.search(pattern, html)

    if not match:
        # 尝试另一种模式
        pattern2 = r'"hourlyForecast"\s*:\s*(\[.*?\])'
        match = re.search(pattern2, html)

    if not match:
        raise RuntimeError("无法解析天气数据，页面结构可能已变化")

    try:
        # 提取并解析 JSON
        json_str = match.group(1) if match.lastindex else match.group(0)
        # 修复 JSON 格式问题
        json_str = re.sub(r'([{,])(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\3":', json_str)
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON 解析失败: {e}")

    # 提取小时预报
    hourly = data.get("hourlyForecast", []) if isinstance(data, dict) else data

    if not hourly:
        raise RuntimeError("未找到小时预报数据")

    # 构建天气信息
    results = []
    now_hour = time.localtime().tm_hour

    for hour_data in hourly[:25]:  # 取25小时数据
        try:
            time_str = hour_data.get("time", "")
            temp = hour_data.get("temp", {}).get("value", "")
            unit = hour_data.get("temp", {}).get("unit", "C")
            precip = hour_data.get("precipChance", {}).get("value", "0")
            wx_phrase = hour_data.get("wxPhraseLong", "")

            # 提取小时数
            hour_match = re.search(r'(\d{1,2}):00', time_str)
            if hour_match:
                hour = int(hour_match.group(1))
            else:
                continue

            # 转换天气描述为中文
            weather_desc = get_weather_desc(wx_phrase)
            icon = get_weather_icon(wx_phrase)

            line1 = f"【{hour:02d}:00】{weather_desc}{icon}"
            line2 = f"温度{temp}°{unit}  降雨{precip}%"
            results.append(line1)
            results.append(line2)

        except Exception as e:
            continue

    if not results:
        raise RuntimeError("未能解析任何天气数据")

    return "\n".join(results)


def get_weather():
    """获取天气预报 - 优先使用豆包API"""
    # 优先使用豆包API（更准确）
    if DOUBAO_API_KEY:
        try:
            print("尝试使用豆包API获取天气...")
            return get_weather_from_api()
        except Exception as e:
            print(f"豆包API失败: {e}")

    # 备用：从 weather.com 获取
    print("尝试从 weather.com 获取天气数据...")
    return parse_weather_from_web()


def get_weather_from_api():
    """从豆包API获取天气预报"""
    api_key = require_env("DOUBAO_API_KEY")

    prompt = """
你是专业天气预报员。
请生成 厦门市同安区 大同街道 & 祥平街道 今天 18:00~明天 12:00 逐小时天气预报。
严格按下面格式输出，不要多余文字，不要解释，只输出预报：

请按以下格式输出，每小时2行：
第一行：【18:00】晴☀️
第二行：温度21°C  降雨1%

使用下面固定图标，不能用其他：
晴 ☀️
多云 ⛅
阴 ☁️
晴云 🌤
云阴 🌥
小雨 🌦
中雨 🌧
大雨 🌨
雷阵雨 ⛈

只输出 18:00—次日12:00，共18小时。
""".strip()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "doubao-seed-2-0-pro-260215",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    for attempt in range(3):
        try:
            resp = requests.post(
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            break
        except requests.exceptions.Timeout:
            if attempt < 2:
                print(f"请求超时，重试 {attempt + 1}/3...")
                time.sleep(attempt + 1)
            else:
                raise RuntimeError("请求超时，已重试3次")

    if not resp.ok:
        raise RuntimeError(f"DOUBAO HTTP {resp.status_code}: {resp.text}")

    resp_json = resp.json()
    if resp_json.get("error"):
        raise RuntimeError(f"DOUBAO error: {resp_json['error']}")

    return resp_json["choices"][0]["message"]["content"]


def require_env(name):
    """检查环境变量是否存在"""
    val = os.getenv(name)
    if not val or not val.strip():
        raise RuntimeError(f"Missing environment variable: {name}")
    return val.strip()


def send_feishu(content):
    """发送到飞书"""
    webhook = require_env("FEISHU_WEBHOOK")

    msg = {
        "msg_type": "text",
        "content": {
            "text": f"🌤 厦门同安 每日天气预报（18:00-次日12:00）\n\n{content}"
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
        "title": "🌤 厦门同安每日天气预报（18:00-次日12:00）",
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
