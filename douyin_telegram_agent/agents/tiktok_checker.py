"""TikTok Checker Agent - Validates products against TikTok Shop database."""
import logging
import pandas as pd
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

class TikTokCheckerAgent:
    """Agent responsible for checking if Douyin products exist on TikTok Shop."""
    
    def __init__(self, us_csv_path: str, uk_csv_path: str, config: dict = None):
        """
        Initialize the TikTok Checker Agent.
        
        Args:
            us_csv_path: Path to US TikTok products CSV
            uk_csv_path: Path to UK TikTok products CSV
            config: Agent configuration dictionary
        """
        self.config = config or {}
        self.similarity_threshold = self.config.get('similarity_threshold', 0.8)
        self.translator = GoogleTranslator(source='zh-CN', target='en')
        
        # Load TikTok product databases
        self.us_products = self._load_csv(us_csv_path)
        self.uk_products = self._load_csv(uk_csv_path)
        self.all_tiktok_products = self.us_products + self.uk_products
        
        logger.info(f"Loaded {len(self.us_products)} US and {len(self.uk_products)} UK TikTok products")
    
    def _load_csv(self, filepath: str) -> List[Dict]:
        """Load products from CSV file."""
        try:
            df = pd.read_csv(filepath)
            # Normalize column names
            df.columns = df.columns.str.lower().str.strip()
            
            products = []
            for _, row in df.iterrows():
                product = {
                    'title': str(row.get('title', '') or row.get('product_name', '')),
                    'price': row.get('price', ''),
                    'category': row.get('category', ''),
                    'market': row.get('market', 'US' if 'us' in filepath.lower() else 'UK')
                }
                if product['title']:
                    products.append(product)
            
            return products
        except Exception as e:
            logger.error(f"Failed to load CSV {filepath}: {e}")
            return []
    
    def translate_title(self, chinese_title: str) -> str:
        """Translate Chinese title to English."""
        try:
            if not chinese_title or all(ord(c) < 128 for c in chinese_title):
                return chinese_title  # Already English or empty
            
            translated = self.translator.translate(chinese_title)
            return translated
        except Exception as e:
            logger.warning(f"Translation failed for '{chinese_title}': {e}")
            return chinese_title
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings."""
        # Normalize strings
        str1_clean = str1.lower().strip()
        str2_clean = str2.lower().strip()
        
        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, str1_clean, str2_clean).ratio()
    
    def check_product_exists(self, douyin_product: Dict) -> Tuple[bool, float, str]:
        """
        Check if a Douyin product exists in TikTok Shop databases.
        
        Args:
            douyin_product: Dictionary with 'title' (Chinese) and other fields
            
        Returns:
            Tuple of (exists: bool, max_similarity: float, matched_title: str)
        """
        # Translate title to English
        english_title = self.translate_title(douyin_product['title'])
        douyin_product['english_title'] = english_title
        
        max_similarity = 0.0
        matched_title = ""
        
        # Check against all TikTok products
        for tiktok_product in self.all_tiktok_products:
            similarity = self.calculate_similarity(english_title, tiktok_product['title'])
            
            if similarity > max_similarity:
                max_similarity = similarity
                matched_title = tiktok_product['title']
                
                # Early exit if above threshold
                if similarity >= self.similarity_threshold:
                    break
        
        exists = max_similarity >= self.similarity_threshold
        
        if exists:
            logger.debug(f"Product '{english_title}' exists (similarity: {max_similarity:.2f}) - Matched: '{matched_title}'")
        else:
            logger.debug(f"Product '{english_title}' NOT found (max similarity: {max_similarity:.2f})")
        
        return exists, max_similarity, matched_title
    
    def find_gaps(self, douyin_products: List[Dict]) -> List[Dict]:
        """
        Find Douyin products that don't exist on TikTok Shop.
        
        Args:
            douyin_products: List of Douyin product dictionaries
            
        Returns:
            List of gap products with additional metadata
        """
        logger.info(f"Checking {len(douyin_products)} Douyin products against TikTok Shop...")
        
        gaps = []
        for product in douyin_products:
            exists, similarity, matched_title = self.check_product_exists(product)
            
            if not exists:
                gap_product = {
                    **product,
                    'exists_on_tiktok': False,
                    'max_similarity': similarity,
                    'closest_match': matched_title
                }
                gaps.append(gap_product)
        
        logger.info(f"Found {len(gaps)} opportunity gaps (products not on TikTok Shop)")
        return gaps
    
    def get_summary(self, douyin_products: List[Dict]) -> str:
        """Get summary of gap analysis."""
        gaps = self.find_gaps(douyin_products)
        
        summary = f"Gap Analysis Results:\n"
        summary += f"- Total Douyin products: {len(douyin_products)}\n"
        summary += f"- Products already on TikTok Shop: {len(douyin_products) - len(gaps)}\n"
        summary += f"- Opportunity gaps: {len(gaps)}\n\n"
        
        if gaps:
            summary += "Top 5 Opportunities:\n"
            for i, gap in enumerate(gaps[:5], 1):
                summary += f"{i}. {gap.get('english_title', gap['title'])} "
                summary += f"(Similarity: {gap['max_similarity']:.2f})\n"
        
        return summary
