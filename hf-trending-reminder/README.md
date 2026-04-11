# Hugging Face 热门模型定时提醒

定时任务，每天上午 9:00 到晚上 8:00，每 2 小时获取一次 Hugging Face 热门模型并发送到飞书。

## 功能

- 📊 获取 Hugging Face 热门模型前 10 名
- 📱 通过飞书机器人自动推送消息
- ⏰ 定时执行（北京时间 9:00-20:00，每 2 小时）
- 🌐 支持国内镜像（hf-mirror.com）

## 配置

### 1. 创建飞书机器人

在飞书群组中添加自定义机器人：
- 复制 Webhook 地址

### 2. 配置环境变量

```bash
# 创建配置文件
cd /root/.openclaw/workspace/cron
cp .env.example .env

# 编辑配置文件，填写 Webhook 地址
nano .env
```

配置文件内容：
```bash
# 飞书配置
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_SECRET=
```

### 3. 配置定时任务

定时任务文件：`/etc/cron.d/hf_trending`

运行时间：
- 上午 9:00
- 上午 11:00
- 下午 13:00
- 下午 15:00
- 下午 17:00
- 晚上 19:00
- 晚上 21:00

## 文件说明

```
/root/.openclaw/workspace/
├── skills/
│   └── hf-trending-reminder/
│       └── SKILL.md          # 技能说明文档
├── cron/
│   ├── hf_trending.py        # 主脚本
│   ├── .env                  # 环境变量配置（需要创建）
│   ├── .env.example          # 环境变量配置示例
│   └── README.md             # 说明文档
└── scripts/
    └── hf_trending.py        # 脚本副本
```

## 运行测试

```bash
# 加载环境变量
cd /root/.openclaw/workspace/cron
source .env

# 运行脚本
python3 hf_trending.py
```

## 日志

日志文件：`/root/.openclaw/workspace/cron/hf_trending.log`

## 使用说明

### 手动触发

```bash
# 设置环境变量
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 运行脚本
python3 /root/.openclaw/workspace/scripts/hf_trending.py
```

### 查看定时任务状态

```bash
# 查看定时任务列表
crontab -l

# 查看日志
tail -f /root/.openclaw/workspace/cron/hf_trending.log
```

### 修改运行时间

编辑 `/etc/cron.d/hf_trending` 文件：

```bash
# 每天运行时间（北京时间）
0 9,11,13,15,17,19,21 * * * root /usr/bin/python3 /root/.openclaw/workspace/scripts/hf_trending.py >> /root/.openclaw/workspace/cron/hf_trending.log 2>&1
```

## 输出格式

飞书消息格式：
```
🔥 当前 Hugging Face 热门模型前 10 名：

1. Qwen/Qwen3.5-35B-A3B
2. Qwen/Qwen3.5-27B
...

⏰ 更新时间: 2026-02-27 15:09:11
```

## 故障排查

### 1. 消息未发送

检查飞书 Webhook 配置：
```bash
cat /root/.openclaw/workspace/cron/.env
```

### 2. 网络问题

确保可以访问 Hugging Face 镜像：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 3. 定时任务未执行

检查 cron 服务状态：
```bash
service cron status
```

查看日志：
```bash
tail -f /root/.openclaw/workspace/cron/hf_trending.log
```

## 技术细节

- 使用 `huggingface_hub` 库获取模型列表
- 使用 `requests` 库发送飞书消息
- 自动处理网络超时和重试
- 使用北京时间（UTC+8）

## 依赖

```bash
pip install huggingface_hub requests
```

## 注意事项

- 飞书 Webhook 地址需要保密
- 定时任务以 root 用户运行
- 日志文件会持续增长，建议定期清理
- 网络不稳定时可能需要增加超时时间
