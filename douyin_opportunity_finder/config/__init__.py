"""
Configuration loader for the Douyin Opportunity Finder system.
Loads environment variables and YAML configuration files.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Centralized configuration management."""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.load_env()
        self.load_config()
    
    def load_env(self):
        """Load environment variables from .env file."""
        env_path = self.base_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Try loading example as fallback
            env_example = self.base_dir / ".env.example"
            if env_example.exists():
                load_dotenv(env_example)
    
    def load_config(self):
        """Load YAML configuration."""
        config_path = self.base_dir / "config" / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
    
    def get(self, key: str, default=None):
        """Get environment variable."""
        return os.getenv(key, default)
    
    def get_llm_config(self):
        """Get LLM configuration for AG2 agents."""
        llm_config = self.config.get('llm_config', {})
        
        # Replace environment variable placeholders
        config_list = llm_config.get('config_list', [])
        for config in config_list:
            if 'api_key' in config and config['api_key'].startswith('${'):
                env_var = config['api_key'][2:-1]  # Extract var name from ${VAR}
                config['api_key'] = self.get(env_var, '')
        
        return {
            'config_list': config_list,
            'temperature': llm_config.get('temperature', 0.7),
            'max_tokens': llm_config.get('max_tokens', 2048),
            'timeout': llm_config.get('timeout', 60)
        }
    
    def get_agent_config(self, agent_name: str):
        """Get specific agent configuration."""
        agents = self.config.get('agents', {})
        return agents.get(agent_name, {})
    
    @property
    def tikhub_api_key(self):
        return self.get('TIKHUB_API_KEY', '')
    
    @property
    def tikhub_base_url(self):
        return self.get('TIKHUB_BASE_URL', 'https://api.tikhub.io/api/v1')
    
    @property
    def openai_api_key(self):
        return self.get('OPENAI_API_KEY', '')
    
    @property
    def openai_model(self):
        return self.get('OPENAI_MODEL', 'gpt-4o')
    
    @property
    def fuzzy_match_threshold(self):
        return float(self.get('FUZZY_MATCH_THRESHOLD', '0.8'))
    
    @property
    def tiktok_products_us_csv(self):
        return self.base_dir / self.get('TIKTOK_PRODUCTS_US_CSV', 'data/tiktok_products_us.csv')
    
    @property
    def tiktok_products_uk_csv(self):
        return self.base_dir / self.get('TIKTOK_PRODUCTS_UK_CSV', 'data/tiktok_products_uk.csv')
    
    @property
    def report_output_path(self):
        return self.base_dir / self.get('REPORT_OUTPUT_PATH', 'data/daily_report.md')
    
    @property
    def log_file_path(self):
        return self.base_dir / self.get('LOG_FILE_PATH', 'logs/scan.log')
    
    @property
    def cache_file_path(self):
        return self.base_dir / self.get('CACHE_FILE_PATH', 'data/cache.json')
    
    @property
    def schedule_hour(self):
        return int(self.get('SCHEDULE_HOUR', '9'))
    
    @property
    def schedule_minute(self):
        return int(self.get('SCHEDULE_MINUTE', '0'))
    
    @property
    def timezone(self):
        return self.get('TIMEZONE', 'Asia/Shanghai')
    
    @property
    def openclaw_enabled(self):
        return self.get('OPENCLAW_ENABLED', 'false').lower() == 'true'
    
    @property
    def openclaw_api_key(self):
        return self.get('OPENCLAW_API_KEY', '')
