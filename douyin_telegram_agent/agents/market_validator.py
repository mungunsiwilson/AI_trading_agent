"""Market Validator Agent - Scores products using Groq LLM and market data."""
import logging
from typing import List, Dict, Optional
from groq import Groq
import re

logger = logging.getLogger(__name__)

class MarketValidatorAgent:
    """Agent responsible for validating market potential and scoring opportunities."""
    
    def __init__(self, groq_api_key: str, config: dict = None):
        """
        Initialize the Market Validator Agent.
        
        Args:
            groq_api_key: Groq API key for LLM access
            config: Agent configuration dictionary
        """
        self.config = config or {}
        self.model = self.config.get('model', 'llama-3.3-70b-versatile')
        self.temperature = self.config.get('temperature', 0.3)
        self.max_tokens = self.config.get('max_tokens', 1000)
        
        # Initialize Groq client
        if groq_api_key:
            self.client = Groq(api_key=groq_api_key)
        else:
            self.client = None
            logger.warning("No Groq API key provided. Using rule-based scoring only.")
    
    def score_product(self, product: Dict) -> Dict:
        """
        Score a product based on multiple dimensions.
        
        Args:
            product: Product dictionary with english_title and other fields
            
        Returns:
            Product dictionary with added score and analysis
        """
        product_name = product.get('english_title', product.get('title', 'Unknown'))
        hot_count = product.get('hot_count', 0)
        
        logger.info(f"Validating market potential for: {product_name}")
        
        # Use LLM if available, otherwise use rule-based scoring
        if self.client:
            analysis = self._analyze_with_llm(product_name, hot_count)
        else:
            analysis = self._rule_based_scoring(product_name, hot_count)
        
        # Calculate overall score (weighted average)
        weights = {
            'competition': 0.25,
            'sentiment': 0.20,
            'cultural_fit': 0.25,
            'visual_appeal': 0.20,
            'price_point': 0.10
        }
        
        overall_score = sum(
            analysis.get(dim, 5) * weight 
            for dim, weight in weights.items()
        )
        
        # Round to 1 decimal place
        overall_score = round(min(10, max(1, overall_score)), 1)
        
        # Add analysis to product
        product['market_analysis'] = analysis
        product['overall_score'] = overall_score
        product['score_breakdown'] = {
            dim: analysis.get(dim, 5) for dim in weights.keys()
        }
        
        logger.info(f"Product '{product_name}' scored: {overall_score}/10")
        
        return product
    
    def _analyze_with_llm(self, product_name: str, hot_count: int) -> Dict:
        """Analyze product using Groq LLM."""
        prompt = f"""
You are an expert e-commerce analyst specializing in identifying viral product opportunities for TikTok Shop.

Analyze this product trending on Douyin: "{product_name}"
Douyin Hot Count: {hot_count}

Evaluate the following dimensions (score each 1-10):

1. **Competition** (1=highly saturated, 10=no competition):
   - Consider if similar products exist on Amazon US/UK
   - Fewer sellers = higher score
   
2. **Reddit Sentiment** (1=negative, 10=very positive):
   - Would this product be well-received in r/TikTokShop, r/dropship, r/AmazonSeller?
   - Look for indicators like "trending", "viral", "must-have"
   
3. **Cultural Fit** (1=China-specific, 10=universal Western appeal):
   - Does it solve a common Western problem?
   - Aligns with trends: ASMR, home organization, tech accessories, fitness, pet care, etc.
   
4. **Visual Appeal** (1=boring, 10=highly demonstrable in 15-30 sec video):
   - Can the product's value be shown quickly?
   - Before/after potential? Satisfying to watch?
   
5. **Price Point** (1=too expensive/cheap, 10=ideal $10-50 range):
   - Ideal impulse buy range for TikTok Shop

Respond in this EXACT format (no extra text):
COMPETITION: [1-10]
SENTIMENT: [1-10]
CULTURAL_FIT: [1-10]
VISUAL_APPEAL: [1-10]
PRICE_POINT: [1-10]
CONTENT_ANGLE: [One sentence TikTok video idea]
NOTES: [Brief explanation of scores]
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            content = response.choices[0].message.content.strip()
            return self._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._rule_based_scoring(product_name, hot_count)
    
    def _parse_llm_response(self, content: str) -> Dict:
        """Parse LLM response into structured analysis."""
        analysis = {
            'competition': 5,
            'sentiment': 5,
            'cultural_fit': 5,
            'visual_appeal': 5,
            'price_point': 5,
            'content_angle': '',
            'notes': ''
        }
        
        # Extract scores using regex
        patterns = {
            'competition': r'COMPETITION:\s*(\d+)',
            'sentiment': r'SENTIMENT:\s*(\d+)',
            'cultural_fit': r'CULTURAL_FIT:\s*(\d+)',
            'visual_appeal': r'VISUAL_APPEAL:\s*(\d+)',
            'price_point': r'PRICE_POINT:\s*(\d+)',
            'content_angle': r'CONTENT_ANGLE:\s*(.+?)(?:\n|$)',
            'notes': r'NOTES:\s*(.+?)(?:\n|$)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if key in ['competition', 'sentiment', 'cultural_fit', 'visual_appeal', 'price_point']:
                    analysis[key] = min(10, max(1, int(value)))
                else:
                    analysis[key] = value
        
        return analysis
    
    def _rule_based_scoring(self, product_name: str, hot_count: int) -> Dict:
        """Rule-based scoring fallback when LLM is unavailable."""
        # Base scores
        competition = 6  # Assume moderate competition
        sentiment = 6  # Neutral-positive
        cultural_fit = 5  # Unknown
        visual_appeal = 6  # Assume decent
        price_point = 6  # Assume reasonable
        
        # Adjust based on hot count (popularity indicator)
        if hot_count > 100000:
            sentiment += 2
            cultural_fit += 1
        elif hot_count > 50000:
            sentiment += 1
            cultural_fit += 1
        
        # Keyword-based adjustments
        name_lower = product_name.lower()
        
        # Visual appeal keywords
        visual_keywords = ['led', 'light', 'clean', 'organize', 'gadget', 'tool', 'mini', 'portable']
        if any(kw in name_lower for kw in visual_keywords):
            visual_appeal += 2
        
        # Price point keywords (assume affordable)
        price_keywords = ['mini', 'portable', 'usb', 'wireless', 'smart']
        if any(kw in name_lower for kw in price_keywords):
            price_point += 1
        
        # Cultural fit keywords (Western-friendly)
        western_keywords = ['phone', 'car', 'home', 'kitchen', 'fitness', 'pet', 'baby', 'travel']
        if any(kw in name_lower for kw in western_keywords):
            cultural_fit += 2
        
        # Content angle suggestion
        content_angle = f"Show the problem this product solves in the first 3 seconds, then demonstrate the solution."
        
        notes = f"Rule-based scoring. Hot count: {hot_count}. Product shows {'high' if hot_count > 50000 else 'moderate'} Douyin traction."
        
        return {
            'competition': min(10, competition),
            'sentiment': min(10, sentiment),
            'cultural_fit': min(10, cultural_fit),
            'visual_appeal': min(10, visual_appeal),
            'price_point': min(10, price_point),
            'content_angle': content_angle,
            'notes': notes
        }
    
    def validate_batch(self, products: List[Dict]) -> List[Dict]:
        """
        Validate and score a batch of products.
        
        Args:
            products: List of product dictionaries
            
        Returns:
            List of products with scores and analysis
        """
        logger.info(f"Validating {len(products)} products...")
        
        scored_products = []
        for i, product in enumerate(products, 1):
            logger.info(f"Processing product {i}/{len(products)}")
            scored_product = self.score_product(product)
            scored_products.append(scored_product)
        
        # Sort by overall score (descending)
        scored_products.sort(key=lambda x: x['overall_score'], reverse=True)
        
        logger.info(f"Validation complete. Top score: {scored_products[0]['overall_score'] if scored_products else 0}")
        
        return scored_products
