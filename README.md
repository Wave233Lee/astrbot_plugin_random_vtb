# Random_VTB 随机管人插件
> 赫赫，管人痴

## 目前支持的功能
- /dd （随机推送一个正在直播的管人直播间）
- /dd 虚拟Singer（可指定B站虚拟区下子分区）
- /嗨幕 5424（直接推送指定直播间）
- /嗨幕 添加 杠杠 3473884（添加直播间号代称，代称已存在会覆盖）
- /嗨幕 删除 杠杠 3473884（删除直播间号代称）
- /嗨幕 杠杠（推送代称的直播间）
- /点灯（~~什么？你问点灯是啥，0点来5424告诉你答案~~ 回来吧红毛鸡蛋，我最骄傲的信仰🥹🥹🥹）
- 自然语言询问某主播正在播什么（用别称的话阿B容易搜不出来，后面再想想办法🤔）

<img src="https://alist.wavelee.top/p/Screenshot_9d26c6446fd7bb8e41d99b6262b17def.png?sign=gFq-vWJpngwAIKulKAFOiycz_zMfeVLO_xjfHvo0IBE=:0" width="420px">

> 询问主播直播内容功能有时会重复发送消息，跟astr代码有关，后面再优化😈

<img src="https://alist.wavelee.top/d/QQ20260315-121635.png?sign=_xh7nxeFOaUJezNgmmncII8RAWB_3H0-YNtpQgRfnNg=:0" width="420px">

<img src="https://alist.wavelee.top/d/QQ20260315-120933.png?sign=e_UoAEh0_aXlCOr9ftzFbWS2hWfOAxv9kYFs4XbWCsw=:0" width="420px">


## 可调整的配置
- enable_live_detect: 是否自动解析直播间链接并发送直播信息和关键帧，默认开启
- max_page: 直播间列表最大随机页数，太大的话可能会超出总数而且随机到没人的直播间
- interval_seconds: dd命令响应间隔，默认10秒

## 必填的配置
### sessdata,buvid3,buvid4
从Cookie里取

> 鉴权越来越严了，可恶的阿姨😠
> 推荐安装 astrbot_plugin_bilibili 并进行登陆，可以蹭蹭鉴权🤤

> 看管人，就来5424

## 更新日志

### v1.2.0
- 新增自动识别直播间链接发送关键帧

### v1.1.9
- 新增自然语言询问主播直播内容功能
