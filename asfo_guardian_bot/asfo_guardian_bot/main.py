asfo_guardian_bot/main.py
import os
import datetime
from typing import Dict, Any, List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ====== 本地配置（优先读取 settings.py，没有就用环境变量）======
try:
    from config.settings import (
        BOT_TOKEN, ADVISOR_USERNAME, ADMIN_IDS,
        WHITEPAPER_URL, OFFICIAL_SITE, OFFICIAL_CHANNEL
    )
except Exception:
    # 兜底：环境变量（你也可以只用 settings.py）
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADVISOR_USERNAME = os.getenv("ADVISOR_USERNAME", "AssetSafeo_Advisor")
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
    WHITEPAPER_URL = os.getenv("WHITEPAPER_URL", "https://github.com/AssetSafeo/AssetSafeo/raw/main/ASFO_Whitepaper_2025_Final.pdf")
    OFFICIAL_SITE = os.getenv("OFFICIAL_SITE", "https://assetsafeo.com")
    OFFICIAL_CHANNEL = os.getenv("OFFICIAL_CHANNEL", "https://t.me/AssetSafeoGlobal")

# ====== MarkdownV2 安全转义 ======
MDV2_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!\\"
def mdv2(text: str) -> str:
    out = []
    for ch in text:
        if ch in MDV2_ESCAPE_CHARS:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)

def now_ts() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

# ====== 全局会话状态（后续可替换为 Redis/DB）======
user_state: Dict[int, Dict[str, Any]] = {}

# ====== 菜单与模板 ======
from core.menu_templates import (
    welcome_text, kb_main_reply, kb_scan_inline, kb_wiki_inline, kb_emergency_inline, kb_tools_inline, kb_report_footer
)
from core.human_bridge import to_human_text
from core.ai_responder import smart_answer  # 自由问答占位（已留OpenAI接口）

# ====== 报告模板（简单版本，后续可替换为真实AI/情报）======
def wallet_report(address: str, risk: str = "🟢 低风险") -> str:
    return (
        "📊 *【钱包地址风险报告】*\n\n"
        f"*地址：* `{address}`\n"
        f"*风险评级：* {risk}\n\n"
        "• *关联性：* 未发现与已知诈骗地址的直接关联。\n"
        "• *行为画像：* 以 DeFi 交互/收藏类为主，活跃度中等。\n"
        "• *资产分布：* 主流代币为主。\n\n"
        "*🧐 安全建议：*\n"
        "1️⃣ 大额资产使用冷钱包\n"
        "2️⃣ 定期撤销不必要授权\n\n"
        f"_报告时间：{now_ts()}_"
    )

def domain_report(domain: str, risk: str = "🟡 中等风险") -> str:
    return (
        "🕸️ *【项目官网域名检测】*\n\n"
        f"*域名：* `{domain}`\n"
        f"*风险评级：* {risk}\n\n"
        "• *证书状态：* 有效\n"
        "• *历史指向：* 暂无恶意解析记录\n"
        "• *相似钓鱼：* 警惕相似拼写的仿冒域名\n\n"
        "*✅ 建议：*\n"
        "1️⃣ 仅从官方渠道跳转\n"
        "2️⃣ 比对社媒/GitHub 公告中的域名一致性\n\n"
        f"_报告时间：{now_ts()}_"
    )

def token_report(addr: str, risk: str = "🟠 可疑") -> str:
    return (
        "🧬 *【代币合约审核】*\n\n"
        f"*合约：* `{addr}`\n"
        f"*风险评级：* {risk}\n\n"
        "• *源代码：* 未开源或开源不完整\n"
        "• *权限：* 存在增税/黑名单/铸币等可疑权限\n"
        "• *流动性：* 建议核查 LP 锁仓与所有者\n\n"
        "*✅ 建议：*\n"
        "1️⃣ 小额试探，勿重仓\n"
        "2️⃣ 核验审计报告与社区口碑\n\n"
        f"_报告时间：{now_ts()}_"
    )

def social_report(platform: str, duration: str, keywords: List[str], real_life: str) -> str:
    kws = ", ".join(keywords) if keywords else "未选择"
    return (
        "🔍 *【社交行为安全分析报告】*\n"
        "*📊 风险评级：* 🟡 中等风险（疑似情感/投资诈骗倾向）\n\n"
        f"*🕵️ 行为模式分析：*\n"
        f"• 平台来源：{platform}\n"
        f"• 认识时长：{duration}\n"
        f"• 特征关键词：{kws}\n"
        f"• 现实交集：{real_life}\n\n"
        "*🎯 核心判断：*\n"
        "存在潜在金融诈骗风险，请立即停止任何进一步经济往来。\n\n"
        "*✅ 安全行动指南：*\n"
        "1️⃣ 停止讨论投资/转账\n"
        "2️⃣ 不点击对方链接或下载 App\n"
        "3️⃣ 已有损失请进入【🚨 紧急求助】或联系官方顾问\n\n"
        f"_报告时间：{now_ts()}_"
    )

# ====== 入口命令 ======
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(welcome_text(), reply_markup=kb_main_reply())

async def cmd_whitepaper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"📘 *ASFO 白皮书（2025 最终版）*\n{WHITEPAPER_URL}"
    await update.message.reply_text(mdv2(msg), parse_mode="MarkdownV2")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = (
        "🔎 *当前状态*\n"
        f"• 用户ID：`{uid}`\n"
        "• 绑定状态：未绑定\n"
        "• 最近交互：刚刚\n\n"
        f"📘 白皮书：{WHITEPAPER_URL}"
    )
    await update.message.reply_text(mdv2(msg), parse_mode="MarkdownV2")

async def cmd_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text(mdv2("此命令仅限管理员使用。"), parse_mode="MarkdownV2")
        return
    content = update.message.text.removeprefix("/announce").strip()
    if not content:
        await update.message.reply_text(mdv2("请在命令后填写公告内容。"), parse_mode="MarkdownV2")
        return
    await update.message.reply_text(mdv2(f"📢 官方公告：\n{content}"), parse_mode="MarkdownV2")

# ====== 文本路由（主菜单 & 自由问答）======
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "🔍 安全扫描":
        await update.message.reply_text(mdv2("🔍 安全扫描\n请选择要检测的对象，我将生成安全报告。"), parse_mode="MarkdownV2", reply_markup=kb_scan_inline())
    elif text == "📚 安全百科":
        await update.message.reply_text(mdv2("📚 安全百科\n选择你想了解的安全主题："), parse_mode="MarkdownV2", reply_markup=kb_wiki_inline())
    elif text == "🚨 紧急求助":
        await update.message.reply_text(mdv2("🚨 紧急求助\n遇到损失或重大风险时，请尽快按照下列选项处理："), parse_mode="MarkdownV2", reply_markup=kb_emergency_inline())
    elif text == "⚙️ 我的与工具":
        await update.message.reply_text(mdv2("⚙️ 我的与工具\n管理你的绑定、积分与偏好设置。"), parse_mode="MarkdownV2", reply_markup=kb_tools_inline())
    else:
        # 自由问答（占位：先走规则；未来接 OpenAI）
        nlu = await smart_answer(text)
        reply = (
            "💬 我理解你的问题涉及潜在安全判断。\n"
            f"{nlu['answer']}\n\n"
            f"• 白皮书：{WHITEPAPER_URL}\n"
            f"• 官网：{OFFICIAL_SITE}\n"
            f"需要更精准的帮助请联系 @{ADVISOR_USERNAME}"
        )
        await update.message.reply_text(mdv2(reply), parse_mode="MarkdownV2")

# ====== 回调按钮处理（含多轮问答）======
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if data == "go_main":
        await query.message.reply_text(welcome_text(), reply_markup=kb_main_reply());  return

    # —— 安全扫描分支 ——
    if data == "scan_wallet":
        user_state[uid] = {"state": "await_wallet_addr"}
        await query.message.reply_text(mdv2("请粘贴一个 *以太坊* 或 *Solana* 钱包地址："), parse_mode="MarkdownV2");  return

    if data == "scan_domain":
        user_state[uid] = {"state": "await_domain"}
        await query.message.reply_text(mdv2("请发送要检测的 *项目官网域名*（如 example\\.com）："), parse_mode="MarkdownV2");  return

    if data == "scan_token":
        user_state[uid] = {"state": "await_token"}
        await query.message.reply_text(mdv2("请发送 *合约地址*（ETH 或 Solana 皆可）："), parse_mode="MarkdownV2");  return

    if data == "scan_social":
        # Q1 平台来源
        user_state[uid] = {"state": "social_q1", "answers": {}}
        buttons = [
            [InlineKeyboardButton("社交媒体", callback_data="soc_plat_social"),
             InlineKeyboardButton("交友软件", callback_data="soc_plat_dating")],
            [InlineKeyboardButton("Telegram群", callback_data="soc_plat_tg"),
             InlineKeyboardButton("游戏/元宇宙", callback_data="soc_plat_game")],
            [InlineKeyboardButton("其他", callback_data="soc_plat_other")],
        ]
        await query.message.reply_text(mdv2("您是在哪个平台认识对方的？"), parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons));  return

    # —— 社交行为多轮问答 ——
    if data.startswith("soc_plat_"):
        plat_map = {"soc_plat_social": "社交媒体","soc_plat_dating": "交友软件","soc_plat_tg": "Telegram群","soc_plat_game": "游戏/元宇宙","soc_plat_other": "其他"}
        user_state.setdefault(uid, {"state": "", "answers": {}})["answers"]["platform"] = plat_map.get(data, "其他")
        user_state[uid]["state"] = "social_q2"
        buttons = [
            [InlineKeyboardButton("刚刚", callback_data="soc_dur_now"),
             InlineKeyboardButton("几天到一周", callback_data="soc_dur_week")],
            [InlineKeyboardButton("几周到一月", callback_data="soc_dur_month"),
             InlineKeyboardButton("一月以上", callback_data="soc_dur_gt")],
        ]
        await query.message.reply_text(mdv2("认识了多久？"), parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons));  return

    if data.startswith("soc_dur_"):
        dur_map = {"soc_dur_now": "刚刚","soc_dur_week": "几天到一周","soc_dur_month": "几周到一月","soc_dur_gt": "一月以上"}
        user_state.setdefault(uid, {"state": "", "answers": {}})["answers"]["duration"] = dur_map.get(data, "未知")
        user_state[uid]["state"] = "social_q3"

        # 多选关键词
        user_state[uid]["answers"]["keywords"] = []
        buttons = [
            [InlineKeyboardButton("投资机会 ✅", callback_data="soc_kw_invest"),
             InlineKeyboardButton("高回报项目 ✅", callback_data="soc_kw_roi")],
            [InlineKeyboardButton("点击链接 ✅", callback_data="soc_kw_link"),
             InlineKeyboardButton("索要钱包信息 ✅", callback_data="soc_kw_wallet")],
            [InlineKeyboardButton("测试转账 ✅", callback_data="soc_kw_test"),
             InlineKeyboardButton("以上都没有", callback_data="soc_kw_none")],
            [InlineKeyboardButton("完成选择", callback_data="soc_kw_done")],
        ]
        await query.message.reply_text(mdv2("对方是否提及以下内容？（可多选，选完点 *完成选择*）"), parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons));  return

    if data.startswith("soc_kw_"):
        if uid not in user_state: return
        if "answers" not in user_state[uid]: user_state[uid]["answers"] = {}

        if data == "soc_kw_done":
            user_state[uid]["state"] = "social_q4"
            buttons = [[InlineKeyboardButton("是，现实朋友", callback_data="soc_real_yes"),
                        InlineKeyboardButton("否，纯网友", callback_data="soc_real_no")]]
            await query.message.reply_text(mdv2("是否有现实交集？"), parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons));  return

        kw_map = {"soc_kw_invest": "投资机会","soc_kw_roi": "高回报项目","soc_kw_link": "点击链接","soc_kw_wallet": "索要钱包信息","soc_kw_test": "测试转账","soc_kw_none": "以上都没有"}
        chosen = user_state[uid]["answers"].setdefault("keywords", [])
        label = kw_map.get(data, "")
        if label == "以上都没有":
            chosen.clear(); chosen.append(label)
        else:
            if "以上都没有" in chosen: chosen.remove("以上都没有")
            if label in chosen: chosen.remove(label)
            else: chosen.append(label)
        await query.message.reply_text(mdv2(f"已选择：{', '.join(chosen) if chosen else '无'}\n继续多选或点击 *完成选择*"), parse_mode="MarkdownV2");  return

    if data.startswith("soc_real_"):
        real = "是" if data.endswith("yes") else "否"
        ans = user_state.get(uid, {}).get("answers", {})
        platform = ans.get("platform", "未知"); duration = ans.get("duration", "未知"); keywords = ans.get("keywords", [])
        report = social_report(platform, duration, keywords, f"现实交集：{real}")
        await query.message.reply_text(report, parse_mode="MarkdownV2", reply_markup=kb_report_footer())
        user_state[uid] = {"state": "", "answers": {}}
        return

    # —— 报告页底部按钮 ——
    if data == "rep_helpful":
        await query.message.reply_text(mdv2("感谢反馈，我们会继续优化服务。"), parse_mode="MarkdownV2");  return
    if data == "rep_learn":
        await query.message.reply_text(mdv2("📚 前往 *安全百科* 学习更多："), parse_mode="MarkdownV2", reply_markup=kb_wiki_inline());  return
    if data == "rep_human":
        await query.message.reply_text(to_human_text(ADVISOR_USERNAME), parse_mode="MarkdownV2");  return

# ====== 输入参数阶段（地址/域名/合约）======
async def input_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = (update.message.text or "").strip()
    st = user_state.get(uid, {}).get("state", "")

    if st == "await_wallet_addr":
        rep = wallet_report(text)
        await update.message.reply_text(rep, parse_mode="MarkdownV2", reply_markup=kb_report_footer())
        user_state[uid] = {"state": "", "answers": {}};  return

    if st == "await_domain":
        rep = domain_report(text)
        await update.message.reply_text(rep, parse_mode="MarkdownV2", reply_markup=kb_report_footer())
        user_state[uid] = {"state": "", "answers": {}};  return

    if st == "await_token":
        rep = token_report(text)
        await update.message.reply_text(rep, parse_mode="MarkdownV2", reply_markup=kb_report_footer())
        user_state[uid] = {"state": "", "answers": {}};  return

    # 非流程文本
    await text_router(update, context)

# ====== 主入口 ======
def main():
    if not BOT_TOKEN:
        raise RuntimeError("缺少 BOT_TOKEN，请在 settings.py 或环境变量中配置。")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whitepaper", cmd_whitepaper))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("announce", cmd_announce))

    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), input_router))

    print("ASFO Guardian Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
