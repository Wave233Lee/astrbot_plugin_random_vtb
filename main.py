import json
import os
import random
import re
import time
import urllib.parse
import urllib

import apscheduler
import apscheduler.schedulers
import apscheduler.schedulers.asyncio
from mcp.types import CallToolResult, TextContent, ImageContent, ResourceLink

from astrbot.core.message.message_event_result import MessageChain
from .bilibili_api_sign import calculate_wrid, get_w_webid_from_bilibili
from .constant import *
from .utils import *

from astrbot.api.event import filter, AstrMessageEvent, CommandResult, MessageEventResult
from astrbot.api.event.filter import (
    EventMessageType,
    command,
    event_message_type,
    regex,
)
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Image, Plain
from bilibili_api import Credential, ResponseCodeException
from bilibili_api.utils.network import Api

DEFAULT_CFG = {
    "room_mapping": {
        "4075": "22924075",
        "0993": "23260993"
    }
}
DATA_PATH = "data/astrbot_plugin_random_vtb.json"


@register("astrbot_plugin_random_vtb", "Sasaki", "输入/dd随机推一个管人", "1.0.0",
          "https://github.com/Wave233Lee/astrbot_plugin_random_vtb")
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.cfg = config
        if not os.path.exists(DATA_PATH):
            with open(DATA_PATH, "w", encoding="utf-8-sig") as f:
                f.write(json.dumps(DEFAULT_CFG, ensure_ascii=False, indent=4))
        with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
            self.data = json.load(f)
        self.credential = Credential(sessdata=self.cfg["sessdata"], buvid3=self.cfg["buvid3"],
                                     buvid4=self.cfg["buvid4"])
        self.scheduler = apscheduler.schedulers.asyncio.AsyncIOScheduler()
        self.scheduler.start()
        self.enable_live_detect = self.cfg.get("enable_live_detect", True)

    @filter.command("dd")
    async def dd(self, event: AstrMessageEvent):
        """输入/dd随机获取一个管人直播间"""
        area_name = "全部"
        area_id = area_mapping[area_name]
        l = event.message_str.split(" ")
        if len(l) > 1:
            area_name = l[1]
            if area_name in area_mapping:
                area_id = area_mapping[area_name]

        max_page = 8
        if self.cfg["max_page"]:
            max_page = int(self.cfg["max_page"])
        page = random.randint(1, max_page)
        # 阿B的密钥（可能随前端更新而变更）
        img_key = self.cfg["img_key"]
        sub_key = self.cfg["sub_key"]
        bili_ticket = get_w_webid_from_bilibili()
        params = {
            "area_id": area_id,
            "page": page,
            "parent_area_id": "9",
            "platform": "web",
            "web_location": "444.253",
            "w_webid": bili_ticket,
        }
        w_rid, wts = calculate_wrid(params, decrypt(img_key), decrypt(sub_key))
        params = {**params, "w_rid": w_rid, "wts": wts}

        query_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in dict(params).items()])
        full_url = f"{live_list_url}?{query_string}"
        logger.info(f"{full_url}")

        result = await self.call_bilibili_api(live_list_url, params)

        liver_list = result['list']
        random_item = random.choice(liver_list)  # 随机选择一个对象
        uname = random_item['uname']
        title = random_item['title']
        roomid = random_item['roomid']
        system_cover = random_item['system_cover']
        watched = random_item['watched_show']['text_large']
        logger.debug("随机获取的管人直播间:" + str(json.dumps(random_item, ensure_ascii=False)))

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

    @command("点灯")
    async def lighting(self, event: AstrMessageEvent):
        """送出一个奇遇盲盒"""

        sender_name = event.get_sender_name()
        # 直接使用 random.choices 按权重随机选择（返回列表，取第一个元素）
        item = random.choices(random_box, weights=[x['prob'] for x in random_box], k=1)[0]
        plain = f"感谢{sender_name}赠送的【{item['name']}】轰动尼阿里嘎多～"
        logger.info(plain)
        chain = [
            Plain(plain),
            Image.fromURL(item['gif']),
        ]
        return CommandResult(chain=chain, use_t2i_=False)

    @filter.llm_tool(name="search_bili_liver")
    async def search_bili_liver(self, event: AstrMessageEvent, keyword: str) -> CallToolResult:
        '''当用户希望查询某个主播时，提取出对象关键词调用此工具。
        包含图片时调用 send_message_to_user 发送图片给用户。
        同时发送直播间链接：https://live.bilibili.com/blanc/{直播间号}

        Args:
            keyword(string): 关键词
        '''
        params = {
            "page": 1,
            "page_size": 1,
            "platform": "pc",
            "keyword": keyword,
        }

        search_result = await self.call_bilibili_api(search_url, params)

        user_info = extract_first_user_info(search_result)
        if user_info:
            logger.info("提取的用户基本信息：")
            for key, value in user_info.items():
                logger.info(f"{key}: {value}")
            info_str = f"用户名：{user_info['uname']}，是否在播：{user_info['is_live']}，直播间号：{user_info['room_id']}"
        else:
            logger.info("未找到用户信息")
            info_str = "未找到用户信息"

        keyframe = None
        if user_info and user_info.get('is_live'):
            params = {
                "room_id": user_info.get('room_id'),
            }
            live_info = await self.call_bilibili_api(live_info_url, params)

            title = live_info['title']
            info_str += f"，直播间标题：{title}"
            keyframe = live_info['keyframe'] or live_info['user_cover']
            logger.info(f"{title}: {keyframe}")

        umo = event.unified_msg_origin
        provider_id = await self.context.get_current_chat_provider_id(umo=umo)
        cfg = self.context.get_config(umo=event.unified_msg_origin)
        p_settings = cfg["provider"]
        provider = next((p for p in p_settings if p.get("id") == provider_id), None)
        modalities = provider.get("modalities", [])
        # 判断当前模型是否支持图像
        support_image = "image" in modalities

        content: list[TextContent | ImageContent] = []
        # 有直播截图且模型支持图像输入时额外返回截图
        if keyframe and support_image:
            data, content_type = url_to_base64_image(keyframe)
            content.append(ImageContent(type="image", data=data, mimeType=content_type))

        content.append(TextContent(text=info_str, type="text"))
        result = CallToolResult(content=content)
        logger.debug(f"search_bili_liver result: {result}")
        return result

    @filter.llm_tool(name="search_living_vtb")
    async def search_living_vtb(self, event: AstrMessageEvent) -> CallToolResult:
        '''当用户询问有哪些人在播时调用此工具，随机推几个当前正在直播的管人。
        输出名称、直播间标题、直播间链接。
        '''
        img_key = self.cfg["img_key"]
        sub_key = self.cfg["sub_key"]
        bili_ticket = get_w_webid_from_bilibili()
        params = {
            "area_id": "0",
            "page": 1,
            "parent_area_id": "9",
            "platform": "web",
            "web_location": "444.253",
            "w_webid": bili_ticket,
        }
        w_rid, wts = calculate_wrid(params, decrypt(img_key), decrypt(sub_key))
        params = {**params, "w_rid": w_rid, "wts": wts}

        result = await self.call_bilibili_api(live_list_url, params)
        liver_list = result.get('list') or []
        if not liver_list:
            return CallToolResult(content=[TextContent(text="暂无正在直播的管人", type="text")])

        sample = random.sample(liver_list, min(5, len(liver_list)))
        lines = []
        for item in sample:
            uname = item.get('uname', '')
            title = item.get('title', '')
            roomid = item.get('roomid', '')
            lines.append(
                f"【{uname}】正在直播:【{title}】https://live.bilibili.com/{roomid}"
            )
        info_str = "\n\n".join(lines)
        return CallToolResult(content=[TextContent(text=info_str, type="text")])

    @event_message_type(EventMessageType.ALL)
    async def parse_miniapp_live_info(self, event: AstrMessageEvent):
        if self.enable_live_detect:
            for msg_element in event.message_obj.message:
                if (
                    hasattr(msg_element, "type")
                    and msg_element.type == "Json"
                    and hasattr(msg_element, "data")
                ):
                    json_string = msg_element.data
                    try:
                        if isinstance(json_string, dict):
                            parsed_data = json_string
                        else:
                            parsed_data = json.loads(json_string)
                        meta = parsed_data.get("meta", {})
                        news = meta.get("news", {})
                        jump_url = news.get("jumpUrl")
                        if not jump_url:
                            return None
                        room_url = await b23_to_room_url(jump_url)
                        match = re.search(live_reg, room_url, re.IGNORECASE)
                        if not match:
                            return None
                        # 匹配到直播间链接
                        if match:
                            room_id = match.group(1)
                            await self.send_live_info(event, room_id)

                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode JSON string: {json_string}")
                    except Exception as e:
                        logger.error(f"An error occurred during JSON processing: {e}")
        return None

    @regex(live_reg)
    async def get_live_info(self, event: AstrMessageEvent):
        room_id = None
        if self.enable_live_detect:
            match = re.search(live_reg, event.message_str, re.IGNORECASE)
            if not match:
                return None
            # 匹配到直播间链接
            if match:
                room_id = match.group(1)
        if room_id is None:
            return None
        logger.info(f"解析到直播间号{room_id}")
        await self.send_live_info(event, room_id)
        return None

    async def send_live_info(self, event: AstrMessageEvent, room_id: str):
        params = {
            "room_id": room_id,
        }
        try:
            live_info = await self.call_bilibili_api(live_info_url, params)
        except ResponseCodeException as e:
            logger.error(e)
            return None
        logger.debug("直播间信息:" + str(json.dumps(live_info, ensure_ascii=False)))
        params = {
            "uid": live_info["uid"],
        }
        usr_info = await self.call_bilibili_api(usr_info_url, params)
        u_info = dict(usr_info["info"])
        uname = u_info["uname"]
        # 判断是否在播
        if live_info["live_status"] != 1:
            return None
        title = live_info['title']
        keyframe = live_info['keyframe'] or live_info['user_cover']
        plain = (
            f"【{uname}】正在直播:【{title}】\n"
            f"https://live.bilibili.com/{room_id}"
        )
        logger.info(plain)
        await event.send(
            MessageChain().message(plain).url_image(keyframe)
        )
        return None

    async def call_bilibili_api(self, url: str, params: dict):
        return await Api(url=url, method="GET", credential=self.credential).update_params(**params).result
