import json
import random
import time
from typing import Dict, Optional

import apscheduler
import apscheduler.schedulers
import apscheduler.schedulers.asyncio
from .constant import *

from astrbot.api.event import filter, AstrMessageEvent, CommandResult, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Image, Plain
from bilibili_api import Credential
from bilibili_api.utils.network import Api

# 用于跟踪每个用户的状态，防止重复请求，重复间隔可配置
USER_STATES: Dict[str, Optional[float]] = {}


async def get_random_vtb_api(url: str, params: dict):
    return await Api(url=url, method="GET", credential=Credential()).update_params(**params).result


@register("dd", "Sasaki", "输入/dd随机推一个管人", "1.0.0", "https://github.com/Wave233Lee/astrbot_plugin_random_vtb")
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.cfg = config
        self.scheduler = apscheduler.schedulers.asyncio.AsyncIOScheduler()
        self.scheduler.add_job(self.clear_cache, "cron", hour=0, minute=0)
        self.scheduler.start()

    @filter.command("dd")
    async def dd(self, event: AstrMessageEvent):
        """输入/dd随机获取一个管人直播间"""
        interval_seconds = self.cfg["interval_seconds"]
        user_id = event.get_sender_id()  # 获取用户ID
        area_name = "全部"
        area_id = area_mapping[area_name]
        l = event.message_str.split(" ")
        if len(l) > 1:
            area_name = l[1]
            if area_name in area_mapping:
                area_id = area_mapping[area_name]

        # 判断响应间隔
        if user_id in USER_STATES:
            elapsed = int((time.time() - USER_STATES[user_id]))
            if elapsed < interval_seconds:
                return CommandResult().message("你的下一个管人还需" + str(interval_seconds - elapsed) + "秒到达")
        else:
            # 缓存用户请求时间
            USER_STATES[user_id] = time.time()

        url = 'https://api.live.bilibili.com/xlive/web-interface/v1/second/getList'
        max_page = 8
        if self.cfg["max_page"]:
            max_page = int(self.cfg["max_page"])
        page = random.randint(1, max_page)
        params = {
            "platform": "web",
            "parent_area_id": "9",
            "area_id": area_id,
            "page": page,
        }

        result = await get_random_vtb_api(url, params)

        liver_list = result['list']
        random_item = random.choice(liver_list)  # 随机选择一个对象
        uname = random_item['uname']
        title = random_item['title']
        roomid = random_item['roomid']
        system_cover = random_item['system_cover']
        watched =random_item['watched_show']['text_large']
        logger.info("随机获取的管人直播间:" + str(json.dumps(random_item, ensure_ascii=False)))

        plain = (
            f"赫赫，为你D到了【{uname}】\n"
            f"正在直播:【{title}】 {watched}\n"
            f"https://live.bilibili.com/{roomid}"
        )
        logger.info(plain)
        chain = [
            Plain(plain),
            Image.fromURL(system_cover),
        ]

        return CommandResult(chain=chain, use_t2i_=False)

    async def clear_cache(self):
        """每日定时清理过期缓存"""
        logger.info(f"每日定时清理过期缓存")
        interval_seconds = self.cfg["interval_seconds"]
        for user_id, last_time in USER_STATES:
            elapsed = str(int((time.time() - last_time) / 1000))
            if elapsed > interval_seconds:
                del USER_STATES[user_id]
