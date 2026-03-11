def decrypt(s):
    """字符偏移解密：每个字符Unicode减1"""
    return ''.join(chr(ord(c) - 1) for c in s)


def extract_first_user_info(live_info: dict) -> dict | None:
    """
    从搜索返回数据中提取第一个用户的基本信息和直播间号
    :param live_info: API返回的原始数据字典
    :return: 包含用户信息的字典，若未找到则返回None
    """
    for result_item in live_info.get('result', []):
        if result_item.get('result_type') == 'bili_user':
            data_list = result_item.get('data', [])
            if data_list:
                first_user = data_list[0]
                user_info = {
                    'uname': first_user.get('uname'),
                    'is_live': first_user.get('is_live'),
                    'room_id': first_user.get('room_id'),  # 直播间号
                }
                return user_info
    return None
