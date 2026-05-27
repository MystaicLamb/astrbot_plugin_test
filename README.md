# 每日单词 (DailyWord)

AstrBot 每日单词学习插件，支持单词卡片推送、复习、排行榜与定时自动推送。

## 功能

- `/今日单词` — 随机抽取一个单词，以卡片图片形式展示，自动打卡
- `/复习单词` — 从已学单词中随机抽取一个复习
- `/我的进度` — 查看个人学习统计（连续打卡天数、累计学习、每日目标）
- `/单词本 [数量]` — 列出最近学过的单词，默认 10 个，最多 50 个
- `/排行榜` — 群内学习排行榜（仅群聊可用）
- `/设置目标 <数字>` — 设置每日学习目标（1~1000）
- `/推送设置` — 设置/查看每日自动推送（支持私聊/群聊）

## 安装

1. 将插件文件夹放入 AstrBot 的 `data/plugins/` 目录
2. 确保词库 JSON 文件（如 `cet4_words.json`）位于 `wordbank/` 目录下
3. 在 AstrBot 管理面板启用插件

## 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `daily_push.enabled` | bool | `false` | 是否开启每日自动推送 |
| `daily_push.push_time` | string | `"08:00"` | 推送时间（24 小时制） |
| `daily_push.target_type` | string | `"private"` | 推送目标类型（`private` / `group`） |
| `daily_push.target_id` | string | `""` | 推送目标 ID（QQ 号或群号） |
| `daily_target` | int | `10` | 每日默认学习目标单词数 |
| `include_learned` | bool | `false` | 是否抽取已学过的单词 |
| `word_bank` | string | `"cet4"` | 默认词库（`cet4` / `cet6`） |

## 指令

### `/今日单词`

随机抽取一个新单词，以 HTML 卡片图片形式展示。每次使用自动打卡。

```
📖 每日单词
┌──────────────────┐
│  apple  /ˈæp.əl/ │
│  苹果             │
│  "An apple a..." │
│  连续 5天 累计42词 │
│  今日 3/10        │
└──────────────────┘
🔥 连续 5 天  |  📚 累计 42 词  |  🎯 今日 3/10
```

- 默认从**未学过的单词**中抽取
- 开启 `include_learned` 配置后，包含已学过的单词，卡片会标注"已学习"
- 学习词库全部完成后提示"已学完"

### `/复习单词`

从已学过的单词中随机抽取一个复习，卡片标注"复习单词"及复习次数。

### `/我的进度`

```
📊 我的学习进度
━━━━━━━━━━━━━━
🔥 连续打卡: 5 天
📚 累计学习: 42 词
🎯 每日目标: 10 词
📅 最后打卡: 2026-05-27
```

### `/单词本 [数量]`

```
📒 最近学过的 5 个单词
━━━━━━━━━━━━━━
1. apple - 苹果
2. book - 书
3. cat - 猫
...
```

### `/排行榜`

仅群聊可用，展示群内学习排名（按累计学习单词数降序）。

### `/设置目标 <数字>`

```
/设置目标 15
🎯 每日学习目标已设置为 15 词！加油！
```

### `/推送设置`

```
/推送设置           # 查看当前推送状态
/推送设置 on        # 开启自动推送
/推送设置 off       # 关闭自动推送
/推送设置 123456789 # 设置推送到指定 QQ（私聊）
```

## 词库格式

`wordbank/` 目录下的 JSON 文件，每条记录格式：

```json
{
  "word": "apple",
  "phonetic": "/ˈæp.əl/",
  "meaning": "n. 苹果",
  "example": "An apple a day keeps the doctor away.",
  "category": "cet4",
  "frequency": 1
}
```

## 自定义卡片样式

修改 `main.py` 顶部的 `WORD_CARD_TMPL` 常量，使用 HTML + CSS 自由定制单词卡片外观。模板引擎为 Jinja2，可用变量：

| 变量 | 说明 |
|------|------|
| `card_tag` | 卡片标签（每日单词 / 复习单词 / 每日单词 · 已学习） |
| `word.word` | 单词 |
| `word.phonetic` | 音标 |
| `word.meaning` | 释义 |
| `word.example` | 例句 |
| `streak` | 连续打卡天数 |
| `total` | 累计学习单词数 |
| `today_learned` | 今日已学数量 |
| `target` | 每日目标数量 |

## 依赖

- AstrBot >= v3.5
- aiosqlite
- Jinja2（AstrBot 内置）

## 文件结构

```
astrbot_plugin_dailyword/
├── main.py              # 插件主逻辑（指令、卡片渲染）
├── metadata.yaml         # 插件元信息
├── _conf_schema.json     # 配置项定义
├── requirements.txt      # Python 依赖
├── logo.png              # 插件图标
├── database/
│   └── db.py             # SQLite 数据库操作
├── wordbank/
│   ├── loader.py         # 词库加载与单词抽取
│   └── cet4_words.json   # 词库 JSON 文件
└── tasks/
    └── scheduler.py      # 定时推送调度器
