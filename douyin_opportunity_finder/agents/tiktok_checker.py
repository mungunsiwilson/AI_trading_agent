"""
TikTokCheckerAgent - Cross-references Douyin products against TikTok Shop databases.
Uses fuzzy matching to identify products not yet available on TikTok Shop US/UK.
"""

import logging
import pandas as pd
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)


class TikTokCheckerAgent:
    """Agent responsible for checking if products exist on TikTok Shop."""
    
    def __init__(self, config):
        self.config = config
        self.us_csv_path = config.tiktok_products_us_csv
        self.uk_csv_path = config.tiktok_products_uk_csv
        self.threshold = config.fuzzy_match_threshold
        self.tiktok_products = []
    
    def load_tiktok_databases(self) -> bool:
        """
        Load TikTok product databases from CSV files.
        
        Returns:
            True if at least one database loaded successfully.
        """
        all_products = []
        
        # Load US database
        if self.us_csv_path.exists():
            try:
                df_us = pd.read_csv(self.us_csv_path)
                logger.info(f"Loaded {len(df_us)} products from US database")
                
                # Extract product names (adjust column name based on actual CSV structure)
                if 'product_name' in df_us.columns:
                    all_products.extend(df_us['product_name'].dropna().tolist())
                elif 'title' in df_us.columns:
                    all_products.extend(df_us['title'].dropna().tolist())
                elif 'name' in df_us.columns:
                    all_products.extend(df_us['name'].dropna().tolist())
                else:
                    logger.warning("Unknown column structure in US CSV")
                    
            except Exception as e:
                logger.error(f"Failed to load US database: {e}")
        else:
            logger.warning(f"US database not found: {self.us_csv_path}")
        
        # Load UK database
        if self.uk_csv_path.exists():
            try:
                df_uk = pd.read_csv(self.uk_csv_path)
                logger.info(f"Loaded {len(df_uk)} products from UK database")
                
                if 'product_name' in df_uk.columns:
                    all_products.extend(df_uk['product_name'].dropna().tolist())
                elif 'title' in df_uk.columns:
                    all_products.extend(df_uk['title'].dropna().tolist())
                elif 'name' in df_uk.columns:
                    all_products.extend(df_uk['name'].dropna().tolist())
                else:
                    logger.warning("Unknown column structure in UK CSV")
                    
            except Exception as e:
                logger.error(f"Failed to load UK database: {e}")
        else:
            logger.warning(f"UK database not found: {self.uk_csv_path}")
        
        self.tiktok_products = [str(p).lower().strip() for p in all_products]
        logger.info(f"Total TikTok products loaded: {len(self.tiktok_products)}")
        
        return len(self.tiktok_products) > 0
    
    def translate_title(self, chinese_title: str) -> str:
        """
        Translate Chinese title to English.
        Uses googletrans library with fallback to simple keyword extraction.
        
        Args:
            chinese_title: Product title in Chinese.
            
        Returns:
            Translated English title or simplified version.
        """
        try:
            from googletrans import Translator
            translator = Translator()
            result = translator.translate(chinese_title, src='zh-cn', dest='en')
            return result.text
        except Exception as e:
            logger.warning(f"Translation failed: {e}, using fallback")
            # Fallback: remove common Chinese keywords and return remaining
            keywords_to_remove = ['好物', '推荐', '爆款', '热销', '必备', '神器', '种草']
            title = chinese_title
            for kw in keywords_to_remove:
                title = title.replace(kw, '')
            return title.strip()
    
    def fuzzy_match(self, title1: str, title2: str) -> float:
        """
        Calculate similarity ratio between two strings.
        
        Args:
            title1: First string.
            title2: Second string.
            
        Returns:
            Similarity ratio (0.0 - 1.0).
        """
        return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()
    
    def check_product_exists(self, english_title: str) -> Tuple[bool, float, str]:
        """
        Check if a product exists in TikTok Shop databases.
        
        Args:
            english_title: Product title in English.
            
        Returns:
            Tuple of (exists, best_match_ratio, matched_product_name).
        """
        best_ratio = 0.0
        best_match = ""
        
        for tiktok_product in self.tiktok_products:
            ratio = self.fuzzy_match(english_title, tiktok_product)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = tiktok_product
        
        exists = best_ratio >= self.threshold
        
        if exists:
            logger.info(f"Product '{english_title}' exists (match: {best_match}, ratio: {best_ratio:.2f})")
        else:
            logger.debug(f"Product '{english_title}' not found (best ratio: {best_ratio:.2f})")
        
        return exists, best_ratio, best_match
    
    async def run(self, douyin_products_json: str) -> str:
        """
        Main execution method for the agent.
        
        Args:
            douyin_products_json: JSON string containing Douyin products.
            
        Returns:
            JSON string containing gap products (not found on TikTok Shop).
        """
        import json
        
        try:
            # Parse input
            input_data = json.loads(douyin_products_json)
            
            if 'error' in input_data:
                return json.dumps({'error': input_data['error']})
            
            products = input_data.get('products', [])
            
            if not products:
                return json.dumps({'error': 'No products to check'})
            
            # Load TikTok databases
            if not self.load_tiktok_databases():
                logger.warning("No TikTok databases loaded, treating all as gaps")
            
            # Check each product
            gap_products = []
            
            for product in products:
                chinese_title = product.get('title', '')
                english_title = self.translate_title(chinese_title)
                
                exists, ratio, matched = self.check_product_exists(english_title)
                
                if not exists:
                    gap_product = {
                        'title_chinese': chinese_title,
                        'title_english': english_title,
                        'hot_count': product.get('hot_count', 0),
                        'item_id': product.get('item_id', ''),
                        'url': product.get('url', ''),
                        'best_match_ratio': ratio,
                        'closest_match': matched,
                        'exists_on_tiktok': False
                    }
                    gap_products.append(gap_product)
            
            result = {
                'status': 'success',
                'total_checked': len(products),
                'gaps_found': len(gap_products),
                'gap_products': gap_products,
                'timestamp': input_data.get('timestamp', '')
            }
            
            logger.info(f"Found {len(gap_products)} gap products out of {len(products)} checked")
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"TikTokCheckerAgent failed: {e}")
            import json
            return json.dumps({'error': str(e)})
