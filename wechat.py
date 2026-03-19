# -*- coding: utf-8 -*-
"""
微信公众号推送模块
用于将天气信息推送到微信公众号
"""

import requests
import os
import json
import time

# 微信公众号配置（从环境变量读取，保证安全性）
APP_ID = os.getenv("WX_APP_ID", "wx7d8e57fe8e17466c")
APP_SECRET = os.getenv("WX_APP_SECRET", "d8d727b09431ee7af2829d5632d9a263")

# 微信API地址
ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
TEMPLATE_SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/template/send"
DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
MASS_SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/mass/sendall"


def get_access_token():
    """
    获取微信 access_token
    access_token 是调用微信API的凭证，有效期2小时

    Returns:
        str: access_token 字符串

    Raises:
        RuntimeError: 获取失败时抛出异常
    """
    params = {
        "grant_type": "client_credential",
        "appid": APP_ID,
        "secret": APP_SECRET
    }

    try:
        response = requests.get(ACCESS_TOKEN_URL, params=params, timeout=30)
    except requests.RequestException as e:
        raise RuntimeError(f"请求微信API失败: {e}") from e

    result = response.json()

    # 检查是否有错误
    if "errcode" in result and result["errcode"] != 0:
        raise RuntimeError(f"微信API错误: {result.get('errmsg', '未知错误')}")

    if "access_token" not in result:
        raise RuntimeError(f"获取access_token失败: {result}")

    return result["access_token"]


def send_template_message(access_token: str, user_openid: str, weather_content: str) -> bool:
    """
    发送模板消息给用户
    需要用户已关注公众号并绑定模板消息

    Args:
        access_token: 微信访问令牌
        user_openid: 用户的openid
        weather_content: 天气内容

    Returns:
        bool: 发送是否成功
    """
    url = f"{TEMPLATE_SEND_URL}?access_token={access_token}"

    # 模板消息结构
    template_data = {
        "touser": user_openid,
        "template_id": "YOUR_TEMPLATE_ID",  # 需要替换为实际的模板ID
        "data": {
            "date": {
                "value": time.strftime("%Y-%m-%d"),
                "color": "#173177"
            },
            "weather": {
                "value": weather_content,
                "color": "#e67e22"
            }
        }
    }

    try:
        response = requests.post(url, json=template_data, timeout=30)
        result = response.json()

        if result.get("errcode") == 0:
            return True
        else:
            print(f"模板消息发送失败: {result}")
            return False

    except requests.RequestException as e:
        print(f"发送模板消息请求失败: {e}")
        return False


def create_draft(access_token: str, title: str, content: str, thumb_media_id: str = None) -> str:
    """
    创建草稿箱文章

    Args:
        access_token: 微信访问令牌
        title: 文章标题
        content: 文章内容（HTML格式）
        thumb_media_id: 封面图片media_id（可选）

    Returns:
        str: 草稿的media_id，失败返回None
    """
    url = f"{DRAFT_ADD_URL}?access_token={access_token}"

    # 文章结构
    articles = [{
        "title": title,
        "author": "天气机器人",
        "content": content,
        "digest": content[:120],  # 摘要
        "content_source_url": "",
        "thumb_media_id": thumb_media_id or ""
    }]

    try:
        response = requests.post(url, json={"articles": articles}, timeout=30)
        result = response.json()

        if result.get("errcode") == 0:
            return result.get("media_id")
        else:
            print(f"创建草稿失败: {result}")
            return None

    except requests.RequestException as e:
        print(f"创建草稿请求失败: {e}")
        return None


def send_mass_message(access_token: str, media_id: str, is_to_all: bool = True) -> bool:
    """
    群发消息（通过草稿箱文章）

    Args:
        access_token: 微信访问令牌
        media_id: 草稿的media_id
        is_to_all: 是否发送给全部用户

    Returns:
        bool: 发送是否成功
    """
    url = f"{MASS_SEND_URL}?access_token={access_token}"

    # 群发请求结构
    data = {
        "filter": {
            "is_to_all": is_to_all,
            "tag_id": 0
        },
        "mpnews": {
            "media_id": media_id
        },
        "msgtype": "mpnews"
    }

    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()

        if result.get("errcode") == 0:
            return True
        else:
            print(f"群发消息失败: {result}")
            return False

    except requests.RequestException as e:
        print(f"群发消息请求失败: {e}")
        return False


def publish_weather_to_wechat(weather_content: str) -> bool:
    """
    将天气信息发布到微信公众号（通过创建草稿）
    注意：群发需要认证服务号

    Args:
        weather_content: 天气内容

    Returns:
        bool: 是否成功
    """
    try:
        # 第一步：获取 access_token
        print("正在获取微信access_token...")
        access_token = get_access_token()
        print("获取access_token成功")

        # 第二步：生成HTML格式的文章内容
        title = f"🌤 厦门同安每日天气预报（{time.strftime('%Y-%m-%d')} 06:00-次日06:00）"

        # 将纯文本天气转换为HTML格式，保留换行
        content_html = weather_content.replace("\n", "<br/>")

        # 添加一些样式
        html_content = f"""
        <div style="padding: 20px; font-size: 16px; line-height: 1.8;">
            <h2 style="color: #173177; text-align: center;">{title}</h2>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin-top: 15px;">
                {content_html}
            </div>
            <p style="text-align: center; color: #999; margin-top: 20px;">
                推送时间：{time.strftime('%H:%M')}
            </p>
        </div>
        """

        # 第三步：创建草稿
        print("正在创建草稿...")
        media_id = create_draft(access_token, title, html_content)

        if media_id:
            print(f"草稿创建成功，media_id: {media_id}")

            # 第四步：尝试群发（需要认证服务号权限）
            # 如果没有权限，这一步会失败，但草稿已创建
            if send_mass_message(access_token, media_id):
                print("群发成功！")
                return True
            else:
                print("注意：群发需要认证服务号权限，草稿已保存")
                print("您可以登录微信公众号后台手动发布草稿")
                return True
        else:
            print("创建草稿失败")
            return False

    except RuntimeError as e:
        print(f"微信公众号推送失败: {e}")
        return False
    except Exception as e:
        print(f"未知错误: {e}")
        return False


# 如果直接运行此文件，进行测试
if __name__ == "__main__":
    test_weather = """08:00 晴 ☀️
09:00 多云 ⛅
10:00 晴 ☀️
11:00 阴 ☁️
12:00 小雨 🌦"""

    print("=" * 50)
    print("测试微信公众号推送")
    print("=" * 50)

    result = publish_weather_to_wechat(test_weather)

    if result:
        print("\n✅ 推送测试完成")
    else:
        print("\n❌ 推送测试失败")
