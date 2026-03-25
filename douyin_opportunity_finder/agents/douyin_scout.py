"""
DouyinScoutAgent - Fetches trending products from Douyin using TikHub API.
"""

import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DouyinScoutAgent:
    """Agent responsible for fetching trending products from Douyin."""
    
    def __init__(self, config):
        self.config = config
        self.api_key = config.tikhub_api_key
        self.base_url = config.tikhub_base_url
        self.cache_file = config.cache_file_path
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def fetch_hot_rise_list(self) -> Optional[List[Dict]]:
        """
        Fetch the hot-rising product list from TikHub API.
        
        Returns:
            List of product dictionaries or None if request fails.
        """
        endpoint = f"{self.base_url}/douyin/billboard/fetch_hot_rise_list"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        params = {
            "limit": 50,  # Get top 50 trending products
            "offset": 0
        }
        
        try:
            logger.info(f"Fetching trending products from TikHub API: {endpoint}")
            response = requests.get(endpoint, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract products from response (adjust based on actual API structure)
            products = data.get('data', [])
            
            if not products:
                logger.warning("No products returned from TikHub API")
                return None
            
            logger.info(f"Successfully fetched {len(products)} products from Douyin")
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch from TikHub API: {e}")
            raise
    
    def filter_product_titles(self, products: List[Dict]) -> List[Dict]:
        """
        Filter products by relevant keywords in titles.
        
        Args:
            products: List of product dictionaries from TikHub API.
            
        Returns:
            Filtered list with only product-related entries.
        """
        keywords = ['好物', '推荐', '爆款', '热销', '必备', '神器', '种草']
        
        filtered = []
        for product in products:
            title = product.get('title', '')
            # Check if any keyword appears in the title
            if any(keyword in title for keyword in keywords):
                filtered.append(product)
        
        logger.info(f"Filtered {len(filtered)} product-related entries from {len(products)} total")
        return filtered
    
    def extract_product_info(self, products: List[Dict]) -> List[Dict]:
        """
        Extract relevant information from product data.
        
        Args:
            products: List of product dictionaries.
            
        Returns:
            List of extracted product info with standardized fields.
        """
        extracted = []
        
        for product in products:
            info = {
                'title': product.get('title', ''),
                'hot_count': product.get('hot_value', 0) or product.get('hot_count', 0),
                'item_id': product.get('item_id', ''),
                'url': product.get('url', ''),
                'timestamp': datetime.now().isoformat()
            }
            extracted.append(info)
        
        return extracted
    
    def save_cache(self, data: List[Dict]):
        """Save fetched data to cache file."""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'products': data
            }
            
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Cache saved to {self.cache_file}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def load_cache(self) -> Optional[List[Dict]]:
        """Load cached data if available."""
        if not self.cache_file.exists():
            return None
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            logger.info(f"Loaded cache from {self.cache_file}")
            return cache_data.get('products', [])
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return None
    
    async def run(self) -> str:
        """
        Main execution method for the agent.
        
        Returns:
            JSON string containing list of Douyin products.
        """
        try:
            # Try to fetch from API
            products = self.fetch_hot_rise_list()
            
            if products is None:
                # Fallback to cache
                logger.warning("API fetch failed, using cached data")
                products = self.load_cache()
                
                if products is None:
                    return json.dumps({'error': 'No data available from API or cache'})
            else:
                # Save successful fetch to cache
                self.save_cache(products)
            
            # Filter and extract
            filtered = self.filter_product_titles(products)
            extracted = self.extract_product_info(filtered)
            
            result = {
                'status': 'success',
                'count': len(extracted),
                'products': extracted,
                'timestamp': datetime.now().isoformat()
            }
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"DouyinScoutAgent failed: {e}")
            return json.dumps({'error': str(e)})
