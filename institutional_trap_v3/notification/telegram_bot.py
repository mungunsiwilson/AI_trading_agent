import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config
from utils.logger import get_logger

logger = get_logger("Telegram")

class TelegramBot:
    def __init__(self, agent):
        self.agent = agent
        self.app = None
        if not Config.TG_TOKEN: return
        
        self.app = Application.builder().token(Config.TG_TOKEN).build()
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("close", self.cmd_close))
        self.app.add_handler(CommandHandler("ml", self.cmd_ml))
        self.app.add_handler(CommandHandler("stop", self.cmd_stop))

    async def start(self):
        if not self.app: return
        await self.app.initialize()
        await self.app.start()
        if self.app.updater:
            await self.app.updater.start_polling()
        logger.info("Telegram Bot Started")

    async def stop(self):
        if not self.app: return
        if self.app.updater: await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def send_message(self, text):
        if not self.app or not Config.TG_CHAT_ID: return
        try:
            await self.app.bot.send_message(chat_id=Config.TG_CHAT_ID, text=text, parse_mode="Markdown")
        except Exception as e: logger.error(f"TG Error: {e}")

    async def send_entry_alert(self, direction, price, sl, tp, pattern):
        emoji = "🟢" if direction == "LONG" else "🔴"
        text = (
            f"{emoji} **NEW TRADE: {direction}**\n"
            f"Pattern: `{pattern}`\n"
            f"Entry: `{price}`\n"
            f"SL: `{sl}`\n"
            f"Exit: Trailing Stop\n"
            f"_Executing automatically..._"
        )
        await self.send_message(text)

    async def send_exit_alert(self, profit, reason):
        color = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪"
        text = (
            f"{color} **CLOSED**\n"
            f"PnL: `{profit:.2f} USD`\n"
            f"Reason: {reason}"
        )
        await self.send_message(text)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤖 SMC 3-TF Bot Online. Waiting for 1H Range...")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pos = self.agent.mt5.get_position(Config.SYMBOL)
        if pos:
            txt = (
                f"📊 **Active**\n"
                f"{'BUY' if pos.type == 0 else 'SELL'}\n"
                f"PnL: `{pos.profit:.2f} USD`"
            )
        else:
            txt = "✅ No active positions."
        await update.message.reply_text(txt, parse_mode="Markdown")

    async def cmd_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔄 Closing position...")
        await self.agent.close_position(reason="Manual Close")

    async def cmd_ml(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        count = self.agent.db.get_trade_count()
        status = "Active" if self.agent.ml.model else "Collecting Data..."
        await update.message.reply_text(f"🧠 **ML Status**\nTrades: `{count}`\nModel: {status}", parse_mode="Markdown")

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info("Stop command received from Telegram")
        
        # 1. Stop the main loop immediately
        self.agent.running = False
        
        # 2. Reply to user immediately
        await update.message.reply_text(
            "🛑 **STOP COMMAND RECEIVED**\n\n"
            "Bot is shutting down...\n"
            "No new trades will be opened.\n"
            "Existing positions will remain managed until closed.",
            parse_mode="Markdown"
        )
    
    async def send_trail_alert(self, direction, new_sl, current_price, profit_points):
        """Sends an alert specifically for Trailing Stop updates"""
        emoji = "🟢" if direction == "LONG" else "🔴"
        color = "🟢" if profit_points > 0 else "⚪"
        
        text = (
            f"{emoji} **TRAILING STOP UPDATED**\n"
            f"Direction: {direction}\n"
            f"Current Price: `{current_price}`\n"
            f"New Stop Loss: `{new_sl}`\n"
            f"Locked Profit: `{color} {profit_points:.2f} pts`\n"
            f"_Stop loss moved to lock in profits._"
        )
        await self.send_message(text)