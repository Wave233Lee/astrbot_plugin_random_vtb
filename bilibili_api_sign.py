import time
import urllib.parse
import hashlib
import re
import requests


def v(s):
    """字符偏移解密：每个字符Unicode减1"""
    return ''.join(chr(ord(c) - 1) for c in s)


def g(s):
    """按固定索引序列提取字符形成32位密钥"""
    indices = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
        27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
        37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
        22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
    ]
    result = []
    for idx in indices:
        if idx < len(s):
            result.append(s[idx])
    return ''.join(result)[:32]


def prepare_params(params):
    """准备请求参数：
    1. 移除特殊字符 !'()*
    2. 按键名排序
    3. URL编码参数
    """
    # 移除特殊字符
    cleaned_params = {}
    for key, value in params.items():
        if isinstance(value, str):
            # 移除 !'()* 字符
            cleaned_value = ''.join(c for c in value if c not in "!'()*")
            cleaned_params[key] = cleaned_value
        else:
            cleaned_params[key] = value

    # 按键名排序
    sorted_keys = sorted(cleaned_params.keys())

    # URL编码
    encoded_params = []
    for key in sorted_keys:
        value = cleaned_params[key]
        encoded_key = urllib.parse.quote(str(key), safe='')
        encoded_value = urllib.parse.quote(str(value), safe='')
        encoded_params.append(f"{encoded_key}={encoded_value}")

    return '&'.join(encoded_params)


def calculate_wrid(params, img_key, sub_key):
    """计算w_rid签名"""
    # 1. 生成签名密钥
    combined_key = img_key + sub_key
    signature_key = g(combined_key)

    # 2. 添加时间戳
    wts = int(time.time())
    params_with_ts = dict(params, wts=wts)

    # 3. 准备参数字符串
    param_str = prepare_params(params_with_ts)

    # 4. 拼接密钥并计算MD5
    data = param_str + signature_key
    w_rid = hashlib.md5(data.encode('utf-8')).hexdigest()

    return w_rid, wts


def extract_w_webid_from_html(html_content):
    """从HTML中提取w_webid（access_id）"""
    # 方法1: 正则匹配
    pattern = r'window\._render_data_\s*=\s*({[^}]+})'
    match = re.search(pattern, html_content)

    if match:
        try:
            render_data = json.loads(match.group(1))
            return render_data.get('access_id')
        except:
            pass

    # 方法2: 直接搜索access_id
    pattern2 = r'"access_id"\s*:\s*"([^"]+)"'
    match2 = re.search(pattern2, html_content)
    if match2:
        return match2.group(1)

    return None


# 使用示例
def get_w_webid_from_bilibili():
    """从B站页面获取w_webid"""
    url = "https://live.bilibili.com/p/eden/area-tags?parentAreaId=9&areaId=0"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        'Referer': 'https://live.bilibili.com/'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        w_webid = extract_w_webid_from_html(response.text)
        return w_webid
    else:
        print(f"请求失败: {response.status_code}")
        return None


# 默认密钥（来自JS代码）
x = {
    "wbiImgKey": "d569546b86c252:db:9bc7e99c5d71e5",
    "wbiSubKey": "557251g796:g54:f:ee94g8fg969e2de"
}

# 解密默认密钥
default_img_key = v(x["wbiImgKey"])  # "c458435a75b141;ca;8ab6d88b4c60d4"
default_sub_key = v(x["wbiSubKey"])  # "446140f685;f43;e;dd83f7ef858d1cd"

# 示例使用
if __name__ == "__main__":
    # 获取w_webid
    w_webid = get_w_webid_from_bilibili()

    # 示例请求参数
    params = {
        "platform": "web",
        "parent_area_id": "9",
        "area_id": "0",
        "sort_type": "online",
        "page": "3",
        "web_location": "444.253",
        "w_webid": w_webid,
    }

    # 计算w_rid
    w_rid, wts = calculate_wrid(params, default_img_key, default_sub_key)

    # 添加签名到请求参数
    signed_params = dict(params, w_rid=w_rid, wts=wts)

    print("签名后的请求参数:")
    for k, v in signed_params.items():
        print(f"{k}: {v}")

    print("\n请求URL示例:")
    query_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in signed_params.items()])
    print(f"https://api.live.bilibili.com/xlive/web-interface/v1/second/getList?{query_string}")
