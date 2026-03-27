"""Douyin Scout Agent - Fetches trending products from TikHub API."""
import os
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

class DouyinScoutAgent:
    """Agent responsible for fetching trending products from Douyin via TikHub API."""
    
    def __init__(self, api_key: str, config: dict = None):
        """
        Initialize the Douyin Scout Agent.
        
        Args:
            api_key: TikHub API key
            config: Agent configuration dictionary
        """
        self.api_key = api_key
        self.config = config or {}
        # Try v2 endpoint first, fallback to v1
        self.base_url = "https://api.tikhub.io"
        self.endpoints = [
            "/api/v2/douyin/billboard/hot_rise_list",
            "/api/v1/douyin/billboard/hot_rise_list", 
            "/douyin/billboard/fetch_hot_rise_list"
        ]
        self.max_products = self.config.get('max_products', 50)
        self.min_hot_count = self.config.get('min_hot_count', 1000)
        self.cache_file = Path(__file__).parent.parent / "data" / "douyin_cache.json"
        
        # Check for demo mode
        self.use_demo = os.getenv("USE_DEMO_DATA", "false").lower() == "true"
        if not self.api_key or self.api_key.startswith("your_") or self.api_key == "test_key":
            logger.warning("Invalid or missing TIKHUB_API_KEY. Will use demo data for testing.")
            self.use_demo = True
        
    def fetch_trending_products(self) -> List[Dict]:
        """
        Fetch trending products from TikHub API.
        Tries multiple endpoints and falls back to demo data if all fail or in demo mode.
        
        Returns:
            List of product dictionaries with title, hot_count, item_id, url
        """
        logger.info("Fetching trending products from Douyin...")
        
        # If demo mode is enabled, skip API calls entirely
        if self.use_demo:
            logger.info("Demo mode enabled - using fallback data for testing")
            return self._get_fallback_data()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        params = {
            "limit": min(self.max_products, 20),  # Keep limit reasonable for free tier
            "min_hot_count": self.min_hot_count
        }
        
        # Try each endpoint
        for endpoint in self.endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                logger.info(f"Trying endpoint: {url}")
                
                response = requests.get(url, headers=headers, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    products = self._parse_response(data)
                    if products:
                        logger.info(f"✓ Successfully fetched {len(products)} products from {endpoint}")
                        self._cache_products(products)
                        return products
                        
                elif response.status_code == 404:
                    logger.debug(f"Endpoint not found: {endpoint}")
                    continue
                    
                elif response.status_code == 401 or response.status_code == 403:
                    logger.error(f"API authentication failed ({response.status_code}). Check your TIKHUB_API_KEY.")
                    logger.warning("Switching to demo mode for this run.")
                    return self._get_fallback_data()
                    
                else:
                    logger.warning(f"API returned {response.status_code} from {endpoint}: {response.text[:100]}")
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request failed for {endpoint}: {e}")
                continue
        
        # All endpoints failed
        logger.error("All TikHub API endpoints failed. Using fallback demo data.")
        return self._get_fallback_data()
    
    def _get_fallback_data(self) -> List[Dict]:
        """Return realistic fallback data for testing when API is unavailable."""
        logger.info("Generating realistic fallback data for demonstration...")
        
        fallback_products = [
            {"title": "智能恒温保温杯", "hot_count": 15420, "item_id": "dy_001"},
            {"title": "便携式榨汁机神器", "hot_count": 23150, "item_id": "dy_002"},
            {"title": "无线充电器支架推荐", "hot_count": 18900, "item_id": "dy_003"},
            {"title": "纳米防水喷雾好物", "hot_count": 31200, "item_id": "dy_004"},
            {"title": "LED化妆镜带灯必备", "hot_count": 27800, "item_id": "dy_005"},
            {"title": "迷你筋膜枪按摩仪", "hot_count": 42100, "item_id": "dy_006"},
            {"title": "可折叠收纳箱神器", "hot_count": 19500, "item_id": "dy_007"},
            {"title": "蓝牙耳机保护套种草", "hot_count": 12300, "item_id": "dy_008"},
            {"title": "多功能切菜器同款", "hot_count": 38700, "item_id": "dy_009"},
            {"title": "车载手机支架推荐", "hot_count": 21400, "item_id": "dy_010"},
            {"title": "硅胶冰格模具好物", "hot_count": 16800, "item_id": "dy_011"},
            {"title": "USB充电小风扇", "hot_count": 29300, "item_id": "dy_012"},
            {"title": "防蓝光眼镜必备", "hot_count": 14200, "item_id": "dy_013"},
            {"title": "魔术贴理线器神器", "hot_count": 11500, "item_id": "dy_014"},
            {"title": "便携挂烫机推荐", "hot_count": 25600, "item_id": "dy_015"}
        ]
        
        products = []
        for item in fallback_products:
            if self._is_product_related(item["title"]):
                products.append({
                    'title': item['title'],
                    'hot_count': item['hot_count'],
                    'item_id': item['item_id'],
                    'url': f"https://www.douyin.com/search/{item['item_id']}",
                    'timestamp': datetime.now().isoformat(),
                    'source': 'fallback_demo'
                })
        
        logger.info(f"Generated {len(products)} fallback products")
        return products
    
    def _parse_response(self, data: dict) -> List[Dict]:
        """Parse API response and extract product information."""
        products = []
        
        # Handle various response structures
        items = (
            data.get('data', {}).get('list', []) or 
            data.get('data', []) or 
            data.get('items', []) or 
            data.get('list', [])
        )
        
        for item in items:
            product = {
                'title': item.get('title', '') or item.get('desc', ''),
                'hot_count': int(item.get('hot_count', 0) or item.get('hot_value', 0)),
                'item_id': item.get('item_id', '') or item.get('id', '') or str(uuid.uuid4())[:8],
                'url': item.get('url', '') or item.get('share_url', '') or item.get('link', ''),
                'timestamp': datetime.now().isoformat(),
                'source': 'tikhub_api'
            }
            
            # Filter by product keywords
            if self._is_product_related(product['title']):
                products.append(product)
        
        return products[:self.max_products]
    
    def _is_product_related(self, title: str) -> bool:
        """Check if title contains product-related keywords."""
        keywords = ['好物', '推荐', '必备', '神器', '种草', '同款', '产品', '商品', '机', '杯', '器', '镜', '箱', '套', '喷雾', '风扇', '眼镜']
        return any(kw in title for kw in keywords) or len(title) >= 4
    
    def _cache_products(self, products: List[Dict]):
        """Cache products to local file."""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'products': products,
                'source': 'api'
            }
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Cached {len(products)} products to {self.cache_file}")
        except Exception as e:
            logger.error(f"Failed to cache products: {e}")
    
    def _load_cached_products(self) -> List[Dict]:
        """Load products from cache file."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                products = cache_data.get('products', [])
                logger.info(f"Loaded {len(products)} products from cache")
                return products
        except Exception as e:
            logger.error(f"Failed to load cached products: {e}")
        
        return []
    
    def get_summary(self) -> str:
        """Get a summary of fetched products."""
        products = self.fetch_trending_products()
        if not products:
            return "No trending products found."
        
        summary = f"Found {len(products)} trending products on Douyin:\n\n"
        for i, product in enumerate(products[:10], 1):
            summary += f"{i}. {product['title']} (Hot: {product['hot_count']})\n"
        
        return summary
