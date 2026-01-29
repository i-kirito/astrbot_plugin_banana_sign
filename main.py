"""
AstrBot 香蕉签到插件
每日签到获得香蕉积分，消耗积分使用 big_banana 画图功能
通过高优先级消息拦截器实现积分控制，不修改 big_banana 插件
"""

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import os
import json
from datetime import datetime, date
from typing import Dict, Any, Set


@register("astrbot_plugin_banana_sign", "ikirito", "香蕉签到系统 - 签到获取积分，消耗积分画图", "1.0.0", "https://github.com/i-kirito/astrbot_plugin_banana_sign")
class BananaSignPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config

        # 数据持久化目录
        self.data_dir = os.path.join(os.getcwd(), "data", "astrbot_plugin_banana_sign")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)

        self.data_file = os.path.join(self.data_dir, "user_data.json")
        self.user_data = self._load_data()

        # 配置项
        self.daily_reward = config.get("daily_reward", 1)  # 每日签到奖励
        self.streak_bonus = config.get("streak_bonus", 1)  # 连续签到奖励
        self.cost_per_draw = config.get("cost_per_draw", 1)  # 每次画图消耗

        # 是否启用积分消耗（可配置关闭）
        self.consume_enabled = config.get("consume_enabled", True)

        # big_banana 触发词缓存
        self.big_banana_triggers: Set[str] = set()
        self._triggers_loaded = False

        logger.info(f"[BananaSign] 插件已加载，用户数: {len(self.user_data.get('users', {}))}")

    def _load_data(self) -> Dict[str, Any]:
        """加载用户数据"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"[BananaSign] 加载数据失败: {e}")
        return {"users": {}}

    def _save_data(self):
        """保存用户数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[BananaSign] 保存数据失败: {e}")

    def _get_user(self, user_id: str) -> Dict[str, Any]:
        """获取用户数据，不存在则创建"""
        user_id = str(user_id)
        if user_id not in self.user_data["users"]:
            self.user_data["users"][user_id] = {
                "bananas": 0,           # 香蕉积分
                "total_signs": 0,       # 总签到次数
                "streak": 0,            # 连续签到天数
                "last_sign": None,      # 上次签到日期
                "total_used": 0         # 总使用次数
            }
        return self.user_data["users"][user_id]

    def _load_big_banana_triggers(self):
        """从 big_banana 插件配置中加载触发词"""
        if self._triggers_loaded:
            return

        try:
            # 从 AstrBot 配置文件加载（正确路径）
            config_path = os.path.join(
                os.getcwd(), "data", "config",
                "astrbot_plugin_big_banana_config.json"
            )
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    prompts = config.get("prompt", [])
                    for item in prompts:
                        if not item:
                            continue
                        # 提取第一个词作为触发词
                        cmd = item.split()[0] if item else ""
                        if cmd.startswith("[") and cmd.endswith("]"):
                            # 多触发词格式 [cmd1,cmd2]
                            for c in cmd[1:-1].split(","):
                                if c.strip():
                                    self.big_banana_triggers.add(c.strip())
                        elif cmd:
                            self.big_banana_triggers.add(cmd)
                    logger.info(f"[BananaSign] 已加载 big_banana 触发词: {self.big_banana_triggers}")
                    self._triggers_loaded = True
            else:
                logger.warning(f"[BananaSign] big_banana 配置文件不存在: {config_path}")
        except Exception as e:
            logger.warning(f"[BananaSign] 加载 big_banana 触发词失败: {e}")

    # ========== 供其他插件调用的 API ==========

    def get_balance(self, user_id: str) -> int:
        """获取用户香蕉余额"""
        user = self._get_user(user_id)
        return user.get("bananas", 0)

    def consume_banana(self, user_id: str, amount: int = 1) -> bool:
        """消耗香蕉积分"""
        user = self._get_user(user_id)
        if user["bananas"] >= amount:
            user["bananas"] -= amount
            user["total_used"] += amount
            self._save_data()
            logger.info(f"[BananaSign] 用户 {user_id} 消耗 {amount} 香蕉，剩余 {user['bananas']}")
            return True
        return False

    def add_banana(self, user_id: str, amount: int = 1):
        """添加香蕉积分"""
        user = self._get_user(user_id)
        user["bananas"] += amount
        self._save_data()
        logger.info(f"[BananaSign] 用户 {user_id} 获得 {amount} 香蕉，当前 {user['bananas']}")

    # ========== 高优先级消息拦截器 ==========

    @filter.event_message_type(filter.EventMessageType.ALL, priority=10)
    async def intercept_big_banana(self, event: AstrMessageEvent):
        """
        高优先级拦截器：在 big_banana 处理之前检查积分
        priority=10 确保在 big_banana (priority=5) 之前执行
        """
        if not self.consume_enabled:
            return  # 未启用积分消耗，放行

        # 延迟加载触发词
        self._load_big_banana_triggers()

        if not self.big_banana_triggers:
            return  # 没有触发词，放行

        # 获取消息文本
        plain_components = [
            comp for comp in event.get_messages() if isinstance(comp, Comp.Plain)
        ]
        if plain_components:
            message_str = " ".join(comp.text for comp in plain_components).strip()
        else:
            message_str = event.message_str

        if not message_str:
            return

        # 提取命令（第一个词）
        cmd = message_str.split()[0] if message_str else ""

        # 检查是否匹配 big_banana 触发词
        if cmd not in self.big_banana_triggers:
            return  # 不是画图命令，放行

        # 检查积分
        user_id = str(event.get_sender_id())
        user = self._get_user(user_id)

        if user["bananas"] < self.cost_per_draw:
            # 积分不足，拦截并提示
            yield event.plain_result(
                f"🍌 香蕉不足！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"当前余额: {user['bananas']} 香蕉\n"
                f"画图需要: {self.cost_per_draw} 香蕉\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💡 使用 /签到 获取香蕉"
            )
            event.stop_event()  # 阻止后续处理
            return

        # 积分足够，消耗并放行
        user["bananas"] -= self.cost_per_draw
        user["total_used"] += self.cost_per_draw
        self._save_data()
        logger.info(f"[BananaSign] 用户 {user_id} 消耗 {self.cost_per_draw} 香蕉画图，剩余 {user['bananas']}")
        # 不 yield 任何内容，让消息继续传递给 big_banana

    # ========== 签到指令 ==========

    @filter.command("签到")
    async def sign_in(self, event: AstrMessageEvent):
        """每日签到"""
        user_id = str(event.get_sender_id())
        user = self._get_user(user_id)

        today = date.today().isoformat()
        last_sign = user.get("last_sign")

        # 检查是否已签到
        if last_sign == today:
            yield event.plain_result(
                f"🍌 今天已经签到过了~\n"
                f"━━━━━━━━━━━━━━━\n"
                f"当前余额: {user['bananas']} 香蕉\n"
                f"连续签到: {user['streak']} 天\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💡 香蕉可用于画图功能"
            )
            return

        # 计算连续签到
        if last_sign:
            try:
                last_date = datetime.strptime(last_sign, "%Y-%m-%d").date()
                if (date.today() - last_date).days == 1:
                    user["streak"] += 1
                else:
                    user["streak"] = 1
            except:
                user["streak"] = 1
        else:
            user["streak"] = 1

        # 计算奖励
        reward = self.daily_reward
        bonus_msg = ""

        # 连续签到7天额外奖励
        if user["streak"] % 7 == 0:
            reward += self.streak_bonus
            bonus_msg = f"\n🎁 连续 {user['streak']} 天，额外 +{self.streak_bonus} 香蕉！"

        # 更新数据
        user["bananas"] += reward
        user["total_signs"] += 1
        user["last_sign"] = today
        self._save_data()

        yield event.plain_result(
            f"🍌 签到成功！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"获得: +{reward} 香蕉{bonus_msg}\n"
            f"当前余额: {user['bananas']} 香蕉\n"
            f"连续签到: {user['streak']} 天\n"
            f"累计签到: {user['total_signs']} 次\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 香蕉可用于画图功能"
        )

    @filter.command("香蕉余额")
    async def check_balance(self, event: AstrMessageEvent):
        """查看余额"""
        user_id = str(event.get_sender_id())
        user = self._get_user(user_id)

        yield event.plain_result(
            f"🍌 我的香蕉账户\n"
            f"━━━━━━━━━━━━━━━\n"
            f"当前余额: {user['bananas']} 香蕉\n"
            f"已使用: {user.get('total_used', 0)} 次\n"
            f"连续签到: {user['streak']} 天\n"
            f"累计签到: {user['total_signs']} 次\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 每次画图消耗 {self.cost_per_draw} 香蕉"
        )

    @filter.command("签到排行")
    async def leaderboard(self, event: AstrMessageEvent):
        """签到排行榜"""
        users = self.user_data.get("users", {})
        if not users:
            yield event.plain_result("暂无签到记录")
            return

        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1].get("bananas", 0),
            reverse=True
        )[:10]

        lines = ["🏆 香蕉排行榜 Top 10", "━━━━━━━━━━━━━━━"]

        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, data) in enumerate(sorted_users):
            medal = medals[i] if i < 3 else f"{i+1}."
            display_id = f"{uid[:4]}***{uid[-2:]}" if len(uid) > 6 else uid
            lines.append(f"{medal} {display_id}: {data.get('bananas', 0)} 🍌")

        yield event.plain_result("\n".join(lines))

    @filter.command("签到帮助")
    async def show_help(self, event: AstrMessageEvent):
        """显示帮助"""
        yield event.plain_result(
            f"🍌 香蕉签到系统\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"【指令】\n"
            f"  /签到        每日签到获取香蕉\n"
            f"  /香蕉余额    查看当前积分\n"
            f"  /签到排行    查看排行榜\n"
            f"\n"
            f"【积分规则】\n"
            f"  每日签到: +{self.daily_reward} 香蕉\n"
            f"  连续7天: 额外 +{self.streak_bonus} 香蕉\n"
            f"\n"
            f"【消耗规则】\n"
            f"  画图消耗: {self.cost_per_draw} 香蕉/次\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
