"""Configuration loader for the Douyin Opportunity Finder."""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Central configuration manager."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.config_file = self.base_dir / "config" / "config.yaml"
        self._load_config()
        self._load_env_vars()
    
    def _load_config(self):
        """Load YAML configuration."""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def _load_env_vars(self):
        """Load environment variables."""
        # TikHub API
        self.tikhub_api_key = os.getenv('TIKHUB_API_KEY', '')
        
        # Groq LLM
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')
        self.groq_model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        self.llm_provider = os.getenv('LLM_PROVIDER', 'groq')
        
        # Telegram
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.enable_telegram = os.getenv('ENABLE_TELEGRAM_REPORTS', 'true').lower() == 'true'
        
        # Features
        self.enable_markdown = os.getenv('ENABLE_MARKDOWN_REPORTS', 'true').lower() == 'true'
        
        # Scheduling
        self.timezone = os.getenv('TIMEZONE', 'Asia/Shanghai')
        self.schedule_time = os.getenv('SCHEDULE_TIME', '09:00')
    
    def get_agent_config(self, agent_name: str) -> dict:
        """Get configuration for a specific agent."""
        return self.config.get('agents', {}).get(agent_name, {})
    
    def get_tikhub_config(self) -> dict:
        """Get TikHub API configuration."""
        return self.config.get('tikhub', {})
    
    def get_paths(self) -> dict:
        """Get file paths configuration."""
        paths = self.config.get('paths', {})
        # Convert to absolute paths
        return {k: str(self.base_dir / v) if not os.path.isabs(v) else v 
                for k, v in paths.items()}
    
    def get_logging_config(self) -> dict:
        """Get logging configuration."""
        log_config = self.config.get('logging', {})
        paths = self.get_paths()
        log_config['file'] = paths.get('logs_dir', 'logs') + '/' + log_config.get('file', 'scan.log').split('/')[-1]
        return log_config

# Global config instance
config = Config()
