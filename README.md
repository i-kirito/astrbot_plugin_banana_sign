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
- 支持群聊和用户白名单配置

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
| `/lm白名单添加` | 添加白名单 |
| `/lm白名单删除` | 删除白名单 |
| `/lm白名单列表` | 查看白名单 |

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

## 版本历史

### v2.0.1 (2026-1-29)
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
