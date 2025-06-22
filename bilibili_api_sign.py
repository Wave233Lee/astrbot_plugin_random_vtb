import time
import urllib.parse
import hashlib


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
    # 示例请求参数
    params = {
        "platform": "web",
        "parent_area_id": "9",
        "area_id": "0",
        "page": "8",
        "web_location": "444.253",
        "w_webid": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzcG1faWQiOiI0NDQuMjUzIiwiYnV2aWQiOiJFMTRGMjdGOC0xRjA1LThGMkItNUI1Ni1DNjYwNjNFMkYxOUEwODIxNmluZm9jIiwidXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChNYWNpbnRvc2g7IEludGVsIE1hYyBPUyBYIDEwXzE1XzcpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xMzcuMC4wLjAgU2FmYXJpLzUzNy4zNiBFZGcvMTM3LjAuMC4wIiwiY3JlYXRlZF9hdCI6MTc1MDYwMTgzOSwidHRsIjo4NjQwMCwidXJsIjoibGl2ZS5iaWxpYmlsaS5jb20vcC9lZGVuL2FyZWEtdGFncz9wYXJlbnRBcmVhSWQ9OVx1MDAyNmFyZWFJZD0wIiwicmVzdWx0Ijoibm9ybWFsIiwiaXNzIjoiZ2FpYSIsImlhdCI6MTc1MDYwMTgzOX0.dx-0NjMBSGedTb5ZPMBu04GCgqRdE-yF51WFI1ZEfqfewDsc_sXcsrUpOyZlkimtwa5QHLoTl9CflspdKCkBrQDrEb-rmcDBfTYdOh6lU4qz5st7SCf3Ukb7kWPfI7cWqT9CuTAbX0z197pBwR429HctOP1rfLSLbTgKVD24puPWmitKwoU5OYrYK_cFRdTVpELd0kUrzRq2z8UqfCBk_UdPpApxrYGuBNeSluNV90fa7-t-RGHSROf2RJcG6L4D69FjOIKcc7H_Xbv2kBI22J1diIuAHSM1HxJRHMirDSZCDm4MoywUZcihyiAeBL8LPKU1ZjQwJjVJRV_kntOPzg",
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