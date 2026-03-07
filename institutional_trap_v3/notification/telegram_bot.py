"""
Async Telegram bot for notifications and command handling.
Uses python-telegram-bot v20+ with async application.
"""

import asyncio
from typing import Optional, Dict, Any
import logging

try:
    from telegram import Update, Bot
    from telegram.ext import Application, CommandHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
    ContextTypes_DEFAULT_TYPE = ContextTypes.DEFAULT_TYPE
except ImportError:
    TELEGRAM_AVAILABLE = False
    # Create dummy types for when telegram is not available
    class Update: pass
    class Bot: pass
    class Application: pass
    class CommandHandler: pass
    class ContextTypes: 
        DEFAULT_TYPE = None
    ContextTypes_DEFAULT_TYPE = None

from config import Config


logger = logging.getLogger("institutional_trap_v3")


class TelegramBot:
    """
    Async Telegram bot for trading notifications.
    Supports commands: /start, /stop, /status, /balance, /help
    """
    
    def __init__(self, config: Config):
        """
        Initialize Telegram bot.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.application: Optional[Application] = None
        self._running = False
        
        # State callbacks (set by main app)
        self._get_status_callback = None
        self._get_balance_callback = None
        self._stop_callback = None
    
    async def initialize(self) -> None:
        """Initialize the bot application."""
        if not TELEGRAM_AVAILABLE:
            logger.warning("python-telegram-bot not available, notifications disabled")
            return
        
        if not self.config.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram bot token not configured, notifications disabled")
            return
        
        try:
            # Build application
            self.application = Application.builder().token(
                self.config.TELEGRAM_BOT_TOKEN
            ).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("stop", self.cmd_stop))
            self.application.add_handler(CommandHandler("close", self.cmd_close))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CommandHandler("balance", self.cmd_balance))
            self.application.add_handler(CommandHandler("help", self.cmd_help))
            
            logger.info("Telegram bot initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
    
    async def start(self) -> None:
        """Start the bot polling."""
        if not TELEGRAM_AVAILABLE or not self.application:
            return
        
        self._running = True
        
        # Start polling in background
        await self.application.initialize()
        await self.application.start()
        
        # Run updater with polling
        if self.application.updater:
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        
        logger.info("Telegram bot started polling")
    
    async def stop(self) -> None:
        """Stop the bot."""
        self._running = False
        
        if self.application:
            if self.application.updater:
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        logger.info("Telegram bot stopped")
    
    async def cmd_start(self, update: Update, context: ContextTypes_DEFAULT_TYPE) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 Institutional Trap v3.0 Bot Started\n\n"
            "Commands:\n"
            "/status - Show current position and PnL\n"
            "/close - Close current position manually\n"
            "/balance - Show account balance\n"
            "/ml - Show ML analysis and performance stats\n"
            "/stop - Emergency stop (closes all positions)\n"
            "/help - Show this help message"
        )
    
    async def cmd_stop(self, update: Update, context: ContextTypes_DEFAULT_TYPE) -> None:
        """Handle /stop command - emergency stop."""
        await update.message.reply_text("🛑 Emergency stop initiated...")
        
        if self._stop_callback:
            try:
                await self._stop_callback()
                await update.message.reply_text("✅ All positions closed successfully")
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {e}")
        else:
            await update.message.reply_text("⚠️ Stop callback not configured")
    
    async def cmd_close(self, update: Update, context: ContextTypes_DEFAULT_TYPE) -> None:
        """Handle /close command - close current position manually."""
        if not self._close_position_callback:
            await update.message.reply_text("⚠️ Close position functionality not configured")
            return
            
        try:
            await update.message.reply_text("🔄 Closing current position...")
            result = await self._close_position_callback()
            await update.message.reply_text(result)
        except Exception as e:
            logger.error(f"Error in /close command: {e}")
            await update.message.reply_text(f"❌ Error closing position: {e}")
    
    async def cmd_status(self, update: Update, context: ContextTypes_DEFAULT_TYPE) -> None:
        """Handle /status command."""
        if self._get_status_callback:
            try:
                status = await self._get_status_callback()
                await update.message.reply_text(status)
            except Exception as e:
                await update.message.reply_text(f"❌ Error getting status: {e}")
        else:
            await update.message.reply_text("⚠️ Status callback not configured")
    
    async def cmd_balance(self, update: Update, context: ContextTypes_DEFAULT_TYPE) -> None:
        """Handle /balance command."""
        if self._get_balance_callback:
            try:
                balance = await self._get_balance_callback()
                await update.message.reply_text(balance)
            except Exception as e:
                await update.message.reply_text(f"❌ Error getting balance: {e}")
        else:
            await update.message.reply_text("⚠️ Balance callback not configured")
    
    async def cmd_help(self, update: Update, context: ContextTypes_DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "📖 Institutional Trap v3.0 Help\n\n"
            "This bot trades the 'Institutional Trap v3.0' strategy:\n"
            "- Detects liquidity sweeps with delta divergence\n"
            "- Confirms absorption via cumulative delta\n"
            "- Enters on micro-structure triggers\n"
            "- Uses intelligent ATR-based trailing stops\n"
            "- ML-powered trade selection (learns from past trades)\n"
            "- Exits on: Stop Loss, Trailing Stop, or Opposite Signal\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/status - Show current position and PnL\n"
            "/close - Close current position manually\n"
            "/balance - Show account balance\n"
            "/ml - Show ML analysis and performance stats\n"
            "/stop - Emergency stop (closes all positions)\n"
            "/help - Show this help message\n\n"
            "Risk Warning: Trading involves substantial risk."
        )
    
    async def cmd_ml(self, update: Update, context: ContextTypes_DEFAULT_TYPE) -> None:
        """Handle /ml command - show ML analysis."""
        if self._get_ml_analysis_callback:
            try:
                analysis = await self._get_ml_analysis_callback()
                await update.message.reply_text(analysis, parse_mode='HTML')
            except Exception as e:
                await update.message.reply_text(f"❌ Error getting ML analysis: {e}")
        else:
            await update.message.reply_text("⚠️ ML analysis not configured")
    
    def set_callbacks(
        self,
        get_status: callable,
        get_balance: callable,
        stop_trading: callable,
        get_ml_analysis: callable = None,
        close_position: callable = None
    ) -> None:
        """
        Set callback functions for commands.
        
        Args:
            get_status: Async function returning status string
            get_balance: Async function returning balance string
            stop_trading: Async function to emergency stop
            get_ml_analysis: Optional async function for ML analysis
            close_position: Optional async function to close current position
        """
        self._get_status_callback = get_status
        self._get_balance_callback = get_balance
        self._stop_callback = stop_trading
        self._get_ml_analysis_callback = get_ml_analysis
        self._close_position_callback = close_position
        
        # Add ML analysis command handler if callback provided
        if get_ml_analysis and self.application:
            self.application.add_handler(CommandHandler("ml", self.cmd_ml))
    
    async def send_message(self, message: str) -> None:
        """
        Send generic message to chat (alias for send_notification).
        
        Args:
            message: Message to send
        """
        await self.send_notification(message)
    
    async def send_notification(self, message: str) -> None:
        """
        Send notification message to chat.
        
        Args:
            message: Message to send
        """
        if not TELEGRAM_AVAILABLE or not self.application:
            return
        
        if not self.config.TELEGRAM_CHAT_ID:
            return
        
        try:
            await self.application.bot.send_message(
                chat_id=self.config.TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
    
    async def send_entry_notification(self, signal: Dict[str, Any]) -> None:
        """Send entry signal notification."""
        direction_emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
        message = (
            f"{direction_emoji} <b>ENTRY SIGNAL</b>\n\n"
            f"Direction: {signal['direction']}\n"
            f"Entry Price: {signal['entry_price']:.2f}\n"
            f"Signal Type: {signal['signal_type']}\n"
            f"Confidence: {signal['confidence']:.0%}"
        )
        await self.send_notification(message)
    
    async def send_exit_notification(
        self,
        direction: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        reason: str
    ) -> None:
        """Send position exit notification."""
        direction_emoji = "🟢" if direction == 'LONG' else "🔴"
        pnl_emoji = "💰" if pnl >= 0 else "💸"
        pnl_sign = "+" if pnl >= 0 else ""
        
        message = (
            f"{direction_emoji} <b>POSITION CLOSED</b>\n\n"
            f"Direction: {direction}\n"
            f"Entry: {entry_price:.2f}\n"
            f"Exit: {exit_price:.2f}\n"
            f"PnL: {pnl_emoji} {pnl_sign}{pnl:.2f} USDT\n"
            f"Reason: {reason}"
        )
        await self.send_notification(message)
    
    async def send_error_notification(self, error: str) -> None:
        """Send error notification."""
        message = f"❌ <b>ERROR</b>\n\n{error}"
        await self.send_notification(message)
