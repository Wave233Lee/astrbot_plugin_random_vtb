# Random_VTB 随机管人插件
> 赫赫，管人痴

## 目前支持的功能
- /dd （随机推送一个正在直播的管人直播间）
- /dd 虚拟Singer（可指定B站虚拟区下子分区）
- /嗨幕 5424（直接推送指定直播间）
- /嗨幕 添加 4075 22924075（添加直播间号代称，代称已存在会覆盖）
- /嗨幕 删除 4075 22924075（删除直播间号代称）
- /点灯（什么？你问点灯是啥，0点来5424告诉你答案）

<img src="https://alist.wavelee.top/p/Screenshot_9d26c6446fd7bb8e41d99b6262b17def.png?sign=gFq-vWJpngwAIKulKAFOiycz_zMfeVLO_xjfHvo0IBE=:0" width="420px">

## 目前支持的配置
- max_page: 直播间列表最大随机页数，太大的话可能会超出总数而且随机到没人的直播间，默认是8
- interval_seconds: 命令响应间隔，默认10秒

## 必填的配置
- access_id 从页面元素里搜，不知道多久更新一次了
- sessdata,buvid3,buvid4 从Cookie里取
- img_key,sub_key两个key从前端js文件取 https://s1.hdslb.com/bfs/static/blive/live-region/static/js/chunk-vendors.*.js （*为随机字符），k很久没更新了用默认的就行（应该
> 鉴权越来越严了，可恶的阿姨😠

> 看管人，就来5424
