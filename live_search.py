"""
B站"直播间搜索"接口封装

"""
import asyncio
import hashlib
import random
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

MIXIN_TABLE = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
                27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
                37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
                22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52]

SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
ROOM_INFO_URL = "https://api.live.bilibili.com/room/v1/Room/get_info"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# 一级分区: 虚拟主播
VUP_PARENT_ID = 9
# 虚拟主播下的二级分区名
VTB_CATES = ("虚拟Singer", "虚拟Gamer", "虚拟声优", "虚拟日常",
             "虚拟男V", "虚拟APEX", "虚拟PK")

# 语义词典: 条件 -> 建议的检索关键词
SEMANTIC_TAGS: Dict[str, List[str]] = {
    "唱歌": ["唱歌", "唱见", "歌回", "翻唱", "原创曲", "VOCALOID", "音MAD",
             "戏腔", "歌势", "弹唱", "歌唱", "音乐"],
    "乐器": ["钢琴", "吉他", "小提琴", "架子鼓", "乐器", "演奏"],
    "游戏": ["游戏", "主机", "音游", "FPS", "MOBA", "steam"],
    "杂谈": ["杂谈", "聊天", "电台", "日常", "陪伴"],
    "手书": ["手书", "板绘", "绘画", "画师"],
    "舞蹈": ["舞蹈", "宅舞", "舞见"],
    "声优": ["声优", "配音", "广播剧", "伪音"],
    "美食": ["美食", "吃播", "做饭", "料理"],
    "学习": ["学习", "自习室", "考研", "考试"],
    "户外": ["户外", "旅行", "散步"],
    "情感": ["情感", "恋爱", "恋爱脑", "男友", "女友"],
    "综艺": ["综艺", "整活", "企划", "联动", "周年"],
    "虚拟日常": ["虚拟日常", "手游", "vtuber", "vup"],
}

# 停用词: 从用户条件里剔除的噪声
STOP_WORDS = ("我想要", "我想看", "推荐", "找一下", "找找", "帮我", "一下",
               "有哪些", "有没有", "谁在", "哪些", "直播间", "直播的",
               "管人", "正在", "现在", "在播", "的", "了", "吗", "呢", "呀",
               "会", "想", "要", "看", "来", "个", "些")

MAX_KEYWORDS = 3        # 一次最多打几个关键词, 多了容易被风控
CACHE_TTL = 600        # 关键词结果缓存 10 分钟
KEY_TTL = 1800         # wbi key 缓存 30 分钟


def clean_html(s: str) -> str:
    """去掉搜索结果里的 <em class="keyword"> 高亮"""
    return re.sub(r"<[^>]+>", "", s or "")


def extract_keywords(condition: str) -> List[str]:
    """
    把自然语言条件抽成检索关键词组
    "要唱歌的" -> ["唱歌", "唱见", "歌回"]
    """
    cond = (condition or "").strip()
    if not cond:
        return []

    kws: List[str] = []

    # 1) 词典命中: 条件里出现某类标签词, 就把该类的关键词展开进来
    low = cond.lower()
    for _, words in SEMANTIC_TAGS.items():
        if any(w.lower() in low for w in words):
            kws.extend(words)

    # 2) 清洗后的原条件本身(去掉噪声词)也算一个关键词
    stripped = cond
    for w in STOP_WORDS:
        stripped = stripped.replace(w, " ")
    stripped = stripped.strip()
    # "在玩游戏" -> "玩游戏"
    while stripped.startswith("在") and len(stripped) > 2:
        stripped = stripped[1:]
    if stripped:
        kws.insert(0, stripped)

    # 3) 去重 + 限量
    out: List[str] = []
    for k in kws:
        k = k.strip()
        if k and k not in out:
            out.append(k)
    return out[:MAX_KEYWORDS]


class BiliSearcher:
    """带 WBI 签名 + 风控重试 + 缓存的直播间搜索器"""

    def __init__(self, cookie: str, ua: str = UA):
        self.cookie = cookie
        self.ua = ua
        self._session: Optional[aiohttp.ClientSession] = None
        self._img: Optional[str] = None
        self._sub: Optional[str] = None
        self._key_ts: float = 0.0
        self._lock = asyncio.Lock()
        self._cache: Dict[str, Tuple[float, List[dict]]] = {}

    # ---------- 底层 ----------
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20),
                headers={
                    "User-Agent": self.ua,
                    "Cookie": self.cookie,
                },
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _refresh_key(self, force: bool = False):
        """从 nav 接口动态取 wbi key(主站那套), 带缓存"""
        async with self._lock:
            if not force and self._img and time.time() - self._key_ts < KEY_TTL:
                return
            session = await self._get_session()
            async with session.get(NAV_URL,
                                   headers={"Referer": "https://www.bilibili.com/"}) as resp:
                data = await resp.json(content_type=None)
            wbi = (data.get("data") or {}).get("wbi_img") or {}
            img = wbi.get("img_url", "").rsplit("/", 1)[-1].split(".")[0]
            sub = wbi.get("sub_url", "").rsplit("/", 1)[-1].split(".")[0]
            if img and sub:
                self._img, self._sub, self._key_ts = img, sub, time.time()

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """标准 WBI 签名"""
        assert self._img and self._sub, "wbi key 未初始化"
        raw = self._img + self._sub
        mixin = "".join(raw[i] for i in MIXIN_TABLE if i < len(raw))[:32]
        p = dict(params)
        p["wts"] = int(time.time())
        query = urllib.parse.urlencode([
            (k, "".join(c for c in str(v) if c not in "!'()*"))
            for k, v in sorted(p.items())
        ])
        p["w_rid"] = hashlib.md5((query + mixin).encode()).hexdigest()
        return p

    def _cache_get(self, key: str) -> Optional[List[dict]]:
        item = self._cache.get(key)
        if item and time.time() - item[0] < CACHE_TTL:
            return item[1]
        return None

    def _cache_put(self, key: str, rooms: List[dict]):
        self._cache[key] = (time.time(), rooms)

    # ---------- 语义召回 ----------
    async def search(self, keyword: str, page: int = 1, order: str = "click",
                     tries: int = 5) -> List[dict]:
        """按关键词搜索直播间(只返回正在直播的)"""
        ck = f"{keyword}|{page}|{order}"
        cached = self._cache_get(ck)
        if cached is not None:
            return cached

        session = await self._get_session()
        for i in range(tries):
            try:
                await self._refresh_key(force=(i > 0))
                params = self._sign({
                    "search_type": "live",
                    "keyword": keyword,
                    "page": page,
                    "order": order,
                })
                async with session.get(
                    SEARCH_URL, params=params,
                    headers={"Referer": "https://search.bilibili.com/live"},
                ) as resp:
                    payload = await resp.json(content_type=None)
                data = payload.get("data") or {}
                if payload.get("code") == 0 and isinstance(data.get("result"), dict):
                    rooms = data["result"].get("live_room") or []
                    if rooms:
                        self._cache_put(ck, rooms)
                        return rooms
            except Exception:
                pass
            # 被风控(v_voucher)时换一把 key 再试, 并退避
            await asyncio.sleep(3 + i * 2)
        return []

    # ---------- 分区确认 ----------
    async def get_room_info(self, room_id: int) -> dict:
        """免签名的直播间详情, 用来确认 parent_area_id"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{ROOM_INFO_URL}?room_id={room_id}",
                headers={"Referer": "https://live.bilibili.com/"},
            ) as resp:
                payload = await resp.json(content_type=None)
            return payload.get("data") or {}
        except Exception:
            return {}

    async def is_virtual_up(self, room: dict, check_limit: int = 20) -> Tuple[bool, str]:
        """
        判断是不是虚拟主播(管人)
        返回 (是否管人, 分区名)
        """
        cate = clean_html(room.get("cate_name"))
        if cate in VTB_CATES:
            return True, cate
        if cate:
            # 已经有分区名了, 不是虚拟主播的二级分区, 直接排除
            return False, cate
        info = await self.get_room_info(room.get("roomid"))
        if info.get("parent_area_id") == VUP_PARENT_ID:
            return True, info.get("area_name", "")
        return False, info.get("area_name", cate)

    # ---------- 完整漏斗 ----------
    async def search_by_condition(self, condition: str, limit: int = 40) -> List[dict]:
        """
        按条件搜索"正在直播的虚拟主播"
        流程: 关键词抽取 -> 语义召回 -> 在播过滤 -> 条件命中 -> 虚拟主播确认
        """
        keywords = extract_keywords(condition)
        if not keywords:
            return []

        def collect(items: List[dict]) -> List[dict]:
            """在播 + 符合条件(标题/标签/分区命中关键词即可)"""
            out = []
            for r in items:
                if r.get("live_status") != 1:
                    continue
                blob = " ".join([
                    clean_html(r.get("title")),
                    r.get("tags") or "",
                    clean_html(r.get("cate_name")),
                ]).lower()
                if not any(k.lower() in blob for k in keywords):
                    continue
                out.append(r)
            return out

        # 1. 召回(串行, 间隔开一点别把接口打炸)
        rooms: List[dict] = []
        seen = set()

        async def recall(page: int):
            for idx, kw in enumerate(keywords):
                got = await self.search(kw, page=page)
                for r in got:
                    rid = r.get("roomid")
                    if rid and rid not in seen:
                        seen.add(rid)
                        rooms.append(r)
                if idx < len(keywords) - 1:
                    await asyncio.sleep(1.5)

        await recall(1)
        if not rooms:
            return []

        # 2. 粗过滤
        cands = collect(rooms)

        # 2.5. 候选太少就补一页, 扩大召回面
        if len(cands) < 12:
            await recall(2)
            cands = collect(rooms)

        # 3. 虚拟主播确认
        #    白名单分区(cate_name)免费且最准, 优先收;
        #    剩下的名额才用 get_info 反查, 免得白名单外的房间把名额占光
        out: List[dict] = []
        others: List[dict] = []
        for r in cands:
            cate = clean_html(r.get("cate_name"))
            if cate in VTB_CATES:
                r = dict(r)
                r["_area"] = cate
                out.append(r)
            else:
                others.append(r)

        for r in others[:max(0, limit - len(out))]:
            ok, area = await self.is_virtual_up(r)
            if ok:
                r = dict(r)
                r["_area"] = area
                out.append(r)
        return out

    async def search_virtual_up(self, keyword: str = "虚拟主播",
                                limit: int = 20) -> List[dict]:
        """随便捞几个在播的虚拟主播(兜底用, 不做关键词命中过滤)"""
        rooms = await self.search(keyword)
        cands = [r for r in rooms if r.get("live_status") == 1]
        out: List[dict] = []
        for r in cands[:limit]:
            ok, area = await self.is_virtual_up(r)
            if ok:
                r = dict(r)
                r["_area"] = area
                out.append(r)
        return out


def weighted_sample(rooms: List[dict], k: int = 5) -> List[dict]:
    """按粉丝数加权随机, 避免总推小透明"""
    pool = list(rooms)
    picked: List[dict] = []
    while pool and len(picked) < k:
        weights = [(r.get("attentions") or 0) ** 0.5 + 1 for r in pool]
        r = random.choices(pool, weights=weights, k=1)[0]
        picked.append(r)
        pool.remove(r)
    return picked
