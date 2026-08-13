# Random_VTB 随机管人插件
> 赫赫，管人痴

## 目前支持的功能
- /dd （随机推送一个正在直播的管人直播间）
- /dd 虚拟Singer（可指定B站虚拟区下子分区）
- /点灯（~~什么？你问点灯是啥，0点来5424告诉你答案~~ 回来吧红毛鸡蛋，我最骄傲的信仰🥹🥹🥹）
- 询问某主播正在播什么
- 自动识别直播间链接输出直播间信息&截图
- 查询正在播的管人

<img src="https://alist.wavelee.top/p/Screenshot_9d26c6446fd7bb8e41d99b6262b17def.png?sign=gFq-vWJpngwAIKulKAFOiycz_zMfeVLO_xjfHvo0IBE=:0" width="420px">

<img src="https://alist.wavelee.top/d/QQ20260315-121635.png?sign=_xh7nxeFOaUJezNgmmncII8RAWB_3H0-YNtpQgRfnNg=:0" width="420px">

<img src="https://alist.wavelee.top/d/QQ20260315-120933.png?sign=e_UoAEh0_aXlCOr9ftzFbWS2hWfOAxv9kYFs4XbWCsw=:0" width="420px">


## 可调整的配置
- enable_live_detect: 是否自动解析直播间链接并发送直播信息和关键帧，默认开启
- max_page: 直播间列表最大随机页数，太大的话可能会超出总数而且随机到没人的直播间

## 必填的配置
### sessdata,buvid3,buvid4
从Cookie里取

> 鉴权越来越严了，可恶的阿姨😠
> 推荐安装 astrbot_plugin_bilibili 并进行登陆，可以蹭蹭鉴权🤤

> 看管人，就来5424

## 更新日志

### v1.2.1
- 新增查询在播的管人直播间

### v1.2.0
- 新增自动识别直播间链接发送关键帧

### v1.1.9
- 新增自然语言询问主播直播内容功能
