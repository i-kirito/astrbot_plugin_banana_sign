<div align="center">

# 🍌 香蕉签到画图插件 🍌

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org)
[![AstrBot](https://img.shields.io/badge/AstrBot-4.10.0%2B-75B9D8.svg)](https://github.com/AstrBotDevs/AstrBot)

**签到获取香蕉积分，消耗积分使用 AI 画图功能**

</div>

## 主要特性

### 签到系统
- 每日签到获取香蕉积分
- 连续签到 7 天额外奖励
- 积分排行榜

### 画图功能
- 支持 OpenAI、Gemini 接口规范和流式传输模式
- 整合 Vertex AI Anonymous 逆向提供商，免费无限的 4K 图片生成
- 支持 LLM 函数调用工具
- 灵活的参数配置，支持提示词级别的粒度控制
- 支持预设提示词和用户文本占位符
- 支持备用提供商降级调用
- 智能补充头像参考
- 支持图片自动切片（超长图按高度分片发送）

## 签到指令

| 指令 | 说明 |
|------|------|
| `/签到` | 每日签到获取香蕉 |
| `/香蕉余额` | 查看当前积分 |
| `/签到排行` | 查看排行榜 |
| `/签到帮助` | 显示帮助信息 |

## 画图指令

| 指令 | 说明 |
|------|------|
| `<触发词>` | 使用预设提示词生成图片（消耗积分） |
| `/lm添加 <触发词>` | 快捷添加预设提示词 |
| `/lm删除 <触发词>` | 快捷删除预设提示词 |
| `/lm列表` | 查看所有预设提示词 |
| `/lm提示词 <触发词>` | 查看预设的完整提示词 |
| `/画图队列` | 查看当前队列状态 |

## 快捷参数

支持在提示词中直接使用快捷参数，无需前缀：

| 参数 | 说明 | 示例 |
|------|------|------|
| `1k` / `2k` / `4k` | 分辨率（大小写不敏感） | `表白 画猫咪 2k` |
| 提供商名称 | 指定提供商（如 Banana、反重力、GCLI） | `表白 画猫咪 banana` |

也支持传统参数格式：

| 参数 | 短参数 | 说明 | 示例 |
|------|--------|------|------|
| `--image_size` | `-s` | 分辨率 | `表白 -s 2K` |
| `--providers` | `-p` | 提供商 | `表白 -p Banana` |

**组合示例：**
```
表白 画一只小猫 2k
表白 画一只小狗 4k banana
表白 画猫咪 反重力 2k
```

## 默认触发词

- `bnn` - 需要图片输入
- `bnt` - 纯文本生成
- `bna` - 收集模式
- `手办化` - 手办风格转换

## 配置说明

### 签到配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `daily_reward` | 每日签到奖励香蕉数 | 1 |
| `streak_bonus` | 连续7天额外奖励 | 1 |
| `cost_per_draw` | 每次画图消耗香蕉数 | 1 |
| `consume_enabled` | 是否启用积分消耗 | true |

### 提供商配置

支持配置主提供商和两个备用提供商，当主提供商失败时自动降级。

### 图片切片配置

用于解决平台对单图尺寸/体积限制导致的发送失败问题：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `image_slice_config.enabled` | 是否启用自动切片 | false |
| `image_slice_config.max_height` | 单张切片最大高度（像素） | 1536 |
| `image_slice_config.max_base64_len` | 单张切片最大 Base64 长度（0 表示不限制） | 0 |
| `image_slice_config.max_slices` | 单图最大切片数 | 8 |

> 说明：Telegram 平台下会自动套用 10MB 单图安全上限，即使 `max_base64_len` 设为 0 也会生效。

## 版本历史

### v2.0.6 (2026-02-08)
- [Feat] 新增图片自动切片功能（按高度/体积分片发送）
- [Feat] 新增 `image_slice_config` 配置项

### v2.0.5 (2026-02-03)
- [Feat] 快捷参数：支持直接写 `2k`/`4k` 设置分辨率
- [Feat] 快捷参数：支持直接写提供商名称（如 `banana`、`反重力`）
- [Feat] 短参数：`-s` 代替 `--image_size`，`-p` 代替 `--providers`
- [Feat] 参数大小写不敏感
- [Feat] 队列系统：并发控制 + `/画图队列` 命令
- [Perf] 异步保存数据，避免阻塞事件循环
- [Fix] 积分扣除逻辑：触发即扣除，不退还

### v2.0.4 (2026-01-29)
- [Refactor] 整合 big_banana 画图功能，支持 47+ 预设词
- [Feat] 签到系统：每日签到获取香蕉积分
- [Feat] 积分消耗：画图需消耗香蕉积分
- [Feat] 积分排行榜功能
- [Feat] 管理员手动添加积分指令 `/香蕉添加`

### v1.0.0 (2026-1-28)
- [Init] 初始版本，仅签到功能

## 致谢

画图功能基于 [astrbot_plugin_big_banana](https://github.com/sukafon/astrbot_plugin_big_banana) 重构，感谢原作者 Sukafon & CatCat。

## License

MIT License
