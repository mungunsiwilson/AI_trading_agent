"""Telegram Sender - Sends PDF reports to Telegram channels/groups."""
import logging
import httpx
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class TelegramSender:
    """Send reports and files to Telegram via Bot API."""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram Sender.
        
        Args:
            bot_token: Telegram Bot Token from @BotFather
            chat_id: Target chat ID (channel, group, or private chat)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        if not bot_token or not chat_id:
            logger.error("Telegram bot token or chat ID not configured")
    
    async def send_document(self, file_path: str, caption: str = "") -> bool:
        """
        Send a document (PDF) to Telegram.
        
        Args:
            file_path: Path to the PDF file
            caption: Optional caption for the document
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Sending PDF to Telegram: {file_path}")
        
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            # Prepare the file
            with open(file_path_obj, 'rb') as f:
                file_content = f.read()
            
            # Send via Telegram Bot API
            url = f"{self.base_url}/sendDocument"
            
            data = {
                'chat_id': self.chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            
            files = {
                'document': (file_path_obj.name, file_content, 'application/pdf')
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, data=data, files=files)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get('ok'):
                    logger.info(f"Successfully sent PDF to Telegram chat {self.chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API error: {result}")
                    return False
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending to Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send PDF to Telegram: {e}")
            return False
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a text message to Telegram.
        
        Args:
            text: Message text (supports HTML/Markdown)
            parse_mode: Parse mode ('HTML' or 'Markdown')
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Sending message to Telegram: {text[:100]}...")
        
        try:
            url = f"{self.base_url}/sendMessage"
            
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, data=data)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get('ok'):
                    logger.info(f"Successfully sent message to Telegram chat {self.chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API error: {result}")
                    return False
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending message: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send message to Telegram: {e}")
            return False
    
    async def send_report(self, pdf_path: str, summary_text: str) -> bool:
        """
        Send a complete report (summary message + PDF attachment).
        
        Args:
            pdf_path: Path to the PDF report
            summary_text: Summary text to send with the PDF
            
        Returns:
            True if both message and PDF sent successfully
        """
        # First send the summary message
        message_sent = await self.send_message(summary_text)
        
        if not message_sent:
            logger.warning("Failed to send summary message, but will try sending PDF")
        
        # Then send the PDF
        caption = "📊 <b>Daily Opportunity Report</b>\n\nSee attached PDF for full analysis."
        pdf_sent = await self.send_document(pdf_path, caption)
        
        return message_sent and pdf_sent
    
    def test_connection(self) -> bool:
        """
        Test the Telegram bot connection.
        
        Returns:
            True if connection successful
        """
        import requests
        
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                bot_name = result['result']['first_name']
                logger.info(f"Telegram bot connected: @{bot_name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
