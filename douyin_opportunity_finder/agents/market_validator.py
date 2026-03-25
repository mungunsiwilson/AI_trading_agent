"""
MarketValidatorAgent - Validates market potential using Amazon and Reddit data.
Scores each gap product based on competition, sentiment, cultural fit, and visual appeal.
Uses Groq API for free, fast LLM inference.
"""

import logging
import json
import os
from typing import List, Dict, Optional
from datetime import datetime

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq library not installed. Install with: pip install groq")

logger = logging.getLogger(__name__)


class MarketValidatorAgent:
    """Agent responsible for validating market potential of gap products."""
    
    def __init__(self, config, llm_client=None):
        self.config = config
        self.llm_client = llm_client
        
        # Initialize Groq client if available
        groq_api_key = config.get('GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
        self.groq_model = config.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
        
        if GROQ_AVAILABLE and groq_api_key:
            self.client = Groq(api_key=groq_api_key)
            logger.info(f"Groq client initialized with model: {self.groq_model}")
        else:
            self.client = None
            logger.warning("Groq client not initialized. Using rule-based scoring only.")
        
        self.amazon_api_key = config.get('AMAZON_SEARCH_API_KEY', '')
        self.reddit_config = {
            'client_id': config.get('REDDIT_CLIENT_ID', ''),
            'client_secret': config.get('REDDIT_CLIENT_SECRET', ''),
            'user_agent': config.get('REDDIT_USER_AGENT', 'douyin_opportunity_finder')
        }
    
    def search_amazon(self, product_name: str) -> Dict:
        """
        Search Amazon for similar products.
        
        In production, this would use OpenClaw's amazon-search skill or Amazon Product API.
        For now, returns mock data structure.
        
        Args:
            product_name: Product name to search.
            
        Returns:
            Dictionary with Amazon search results.
        """
        # TODO: Integrate with OpenClaw amazon-search skill
        # Example: result = openclaw.skills.amazon_search(query=product_name)
        
        logger.info(f"Searching Amazon for: {product_name}")
        
        # Mock response (replace with actual API call)
        return {
            'query': product_name,
            'total_results': 0,  # Would come from API
            'num_sellers': 0,
            'avg_price': 0.0,
            'avg_rating': 0.0,
            'bestseller_exists': False,
            'competition_level': 'unknown'
        }
    
    def search_reddit(self, product_name: str) -> Dict:
        """
        Search Reddit for product mentions and sentiment.
        
        Uses PRAW or OpenClaw's reddit-readonly skill.
        
        Args:
            product_name: Product name to search.
            
        Returns:
            Dictionary with Reddit search results and sentiment.
        """
        # TODO: Integrate with OpenClaw reddit-readonly skill or PRAW
        # Example: posts = openclaw.skills.reddit_readonly.search(subreddit='dropship', query=product_name)
        
        logger.info(f"Searching Reddit for: {product_name}")
        
        subreddits = ['r/AmazonSeller', 'r/dropship', 'r/TikTokShop', 'r/ecommerce']
        
        # Mock response (replace with actual API call)
        return {
            'query': product_name,
            'subreddits_searched': subreddits,
            'total_mentions': 0,
            'positive_mentions': 0,
            'negative_mentions': 0,
            'sentiment_score': 0.5,  # 0-1 scale
            'trending_keywords': []
        }
    
    def score_product(self, product: Dict, amazon_data: Dict, reddit_data: Dict) -> Dict:
        """
        Calculate market fit score (1-10) for a product.
        
        Scoring criteria:
        - Competition level (fewer sellers = higher score): 0-2 points
        - Reddit sentiment (positive = higher score): 0-2 points
        - Cultural fit (Western market alignment): 0-2 points
        - Visual appeal (video potential): 0-2 points
        - Price point ($10-50 ideal): 0-2 points
        
        Args:
            product: Gap product dictionary.
            amazon_data: Amazon search results.
            reddit_data: Reddit search results.
            
        Returns:
            Dictionary with scores and justification.
        """
        scores = {}
        justifications = {}
        
        # 1. Competition Score (0-2)
        num_sellers = amazon_data.get('num_sellers', 0)
        if num_sellers == 0:
            scores['competition'] = 2.0
            justifications['competition'] = "No direct competition found on Amazon"
        elif num_sellers < 10:
            scores['competition'] = 1.8
            justifications['competition'] = f"Low competition ({num_sellers} sellers)"
        elif num_sellers < 50:
            scores['competition'] = 1.5
            justifications['competition'] = f"Moderate competition ({num_sellers} sellers)"
        elif num_sellers < 100:
            scores['competition'] = 1.0
            justifications['competition'] = f"High competition ({num_sellers} sellers)"
        else:
            scores['competition'] = 0.5
            justifications['competition'] = f"Very saturated market ({num_sellers} sellers)"
        
        # 2. Reddit Sentiment Score (0-2)
        sentiment = reddit_data.get('sentiment_score', 0.5)
        mentions = reddit_data.get('total_mentions', 0)
        
        if mentions == 0:
            scores['sentiment'] = 1.5  # Neutral - untapped potential
            justifications['sentiment'] = "No Reddit mentions yet (untapped opportunity)"
        elif sentiment >= 0.7:
            scores['sentiment'] = 2.0
            justifications['sentiment'] = f"Positive sentiment ({mentions} mentions)"
        elif sentiment >= 0.4:
            scores['sentiment'] = 1.5
            justifications['sentiment'] = f"Neutral sentiment ({mentions} mentions)"
        else:
            scores['sentiment'] = 0.5
            justifications['sentiment'] = f"Negative sentiment ({mentions} mentions)"
        
        # 3. Cultural Fit Score (0-2) - Use LLM for evaluation
        scores['cultural_fit'], justifications['cultural_fit'] = self._evaluate_cultural_fit(product)
        
        # 4. Visual Appeal Score (0-2) - Can it be demonstrated in 15-30s video?
        scores['visual_appeal'], justifications['visual_appeal'] = self._evaluate_visual_appeal(product)
        
        # 5. Price Point Score (0-2) - Ideal range $10-50
        avg_price = amazon_data.get('avg_price', 25.0)  # Default to ideal midpoint
        if 10 <= avg_price <= 50:
            scores['price_point'] = 2.0
            justifications['price_point'] = f"Ideal price point (${avg_price:.2f})"
        elif 5 <= avg_price < 10 or 50 < avg_price <= 75:
            scores['price_point'] = 1.5
            justifications['price_point'] = f"Acceptable price point (${avg_price:.2f})"
        else:
            scores['price_point'] = 1.0
            justifications['price_point'] = f"Suboptimal price point (${avg_price:.2f})"
        
        # Calculate total score
        total_score = sum(scores.values())
        
        return {
            'total_score': min(10.0, total_score),  # Cap at 10
            'component_scores': scores,
            'justifications': justifications,
            'amazon_data': amazon_data,
            'reddit_data': reddit_data
        }
    
    def _evaluate_cultural_fit(self, product: Dict) -> tuple:
        """
        Evaluate if product fits Western market trends.
        
        Uses Groq LLM to analyze product description for cultural relevance.
        
        Returns:
            Tuple of (score, justification).
        """
        product_name = product.get('title_english', '')
        product_desc = product.get('description', '') or product_name
        
        # If Groq client is available, use LLM for evaluation
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.groq_model,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert at evaluating product-market fit for Western markets (US/UK).
Evaluate if a product from Douyin (Chinese TikTok) would succeed on TikTok Shop US/UK.
Consider: trending categories (ASMR, fitness, home organization, tech accessories, aesthetic products),
seasonal relevance, price sensitivity ($10-50 ideal), and visual demonstration potential.
Respond with ONLY a JSON object: {"score": 1.0-2.0, "reason": "brief explanation"}"""
                        },
                        {
                            "role": "user",
                            "content": f"Product: {product_desc}\n\nEvaluate cultural fit for US/UK market."
                        }
                    ],
                    temperature=0.3,
                    max_tokens=150,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                score = float(result.get('score', 1.5))
                reason = result.get('reason', 'LLM evaluation completed')
                
                # Clamp score between 0.5 and 2.0
                score = max(0.5, min(2.0, score))
                
                return score, f"LLM analysis: {reason}"
                
            except Exception as e:
                logger.warning(f"Groq LLM evaluation failed: {e}. Falling back to rule-based.")
        
        # Fallback to rule-based evaluation
        # Keywords that indicate good cultural fit
        positive_keywords = [
            'ASMR', 'summer', 'winter', 'Apple', 'iPhone', 'Android',
            'fitness', 'gym', 'yoga', 'kitchen', 'home', 'organization',
            'LED', 'RGB', 'gaming', 'portable', 'wireless', 'USB',
            'eco-friendly', 'sustainable', 'minimalist', 'aesthetic'
        ]
        
        score = 1.0  # Base score
        reasons = []
        
        for keyword in positive_keywords:
            if keyword.lower() in product_name.lower():
                score += 0.2
                reasons.append(f"Contains '{keyword}' trend")
        
        if score > 2.0:
            score = 2.0
        
        if not reasons:
            justification = "Neutral cultural fit - requires market testing"
        else:
            justification = f"Good cultural fit: {', '.join(reasons[:3])}"
        
        return score, justification
    
    def _evaluate_visual_appeal(self, product: Dict) -> tuple:
        """
        Evaluate if product can be demonstrated in short video.
        
        Uses Groq LLM to analyze product type for video potential.
        
        Returns:
            Tuple of (score, justification).
        """
        product_name = product.get('title_english', '').lower()
        product_desc = product.get('description', '') or product_name
        
        # If Groq client is available, use LLM for evaluation
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.groq_model,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert at evaluating products for TikTok video potential.
Determine if a product can be effectively demonstrated in a 15-30 second vertical video.
Consider: transformation effects, before/after, satisfying actions, visual effects, curiosity factor.
Respond with ONLY a JSON object: {"score": 1.0-2.0, "reason": "brief explanation", "video_idea": "suggested content angle"}"""
                        },
                        {
                            "role": "user",
                            "content": f"Product: {product_desc}\n\nEvaluate visual appeal for TikTok videos."
                        }
                    ],
                    temperature=0.3,
                    max_tokens=200,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                score = float(result.get('score', 1.5))
                reason = result.get('reason', 'LLM evaluation completed')
                video_idea = result.get('video_idea', '')
                
                # Clamp score between 0.5 and 2.0
                score = max(0.5, min(2.0, score))
                
                justification = f"LLM analysis: {reason}"
                if video_idea:
                    justification += f" | Video idea: {video_idea}"
                
                return score, justification
                
            except Exception as e:
                logger.warning(f"Groq LLM evaluation failed: {e}. Falling back to rule-based.")
        
        # Fallback to rule-based evaluation
        # Categories with high visual appeal
        visual_categories = [
            ('light', 'LED', 'glow', 'neon'),  # Lighting effects
            ('transform', 'fold', 'expand', 'convert'),  # Transformation
            ('before', 'after', 'clean', 'organize'),  # Before/after
            ('satisfying', 'ASMR', 'texture'),  # Sensory appeal
            ('magic', 'trick', 'hack', 'secret'),  # Curiosity
            ('instant', 'quick', 'fast', 'easy')  # Quick results
        ]
        
        score = 1.0  # Base score
        reasons = []
        
        for category, *keywords in visual_categories:
            if any(kw in product_name for kw in keywords):
                score += 0.3
                reasons.append(f"{category} visual potential")
        
        if score > 2.0:
            score = 2.0
        
        if not reasons:
            justification = "Standard visual appeal - depends on content execution"
        else:
            justification = f"High visual appeal: {', '.join(reasons[:3])}"
        
        return score, justification
    
    async def run(self, gap_products_json: str) -> str:
        """
        Main execution method for the agent.
        
        Args:
            gap_products_json: JSON string containing gap products.
            
        Returns:
            JSON string containing validated products with scores.
        """
        try:
            # Parse input
            input_data = json.loads(gap_products_json)
            
            if 'error' in input_data:
                return json.dumps({'error': input_data['error']})
            
            gap_products = input_data.get('gap_products', [])
            
            if not gap_products:
                return json.dumps({'error': 'No gap products to validate'})
            
            validated_products = []
            
            for product in gap_products:
                product_name = product.get('title_english', '')
                
                # Search Amazon and Reddit
                amazon_data = self.search_amazon(product_name)
                reddit_data = self.search_reddit(product_name)
                
                # Score the product
                scoring_result = self.score_product(product, amazon_data, reddit_data)
                
                # Combine all data
                validated_product = {
                    **product,
                    'market_fit_score': scoring_result['total_score'],
                    'component_scores': scoring_result['component_scores'],
                    'justifications': scoring_result['justifications'],
                    'amazon_summary': amazon_data,
                    'reddit_summary': reddit_data
                }
                
                validated_products.append(validated_product)
                logger.info(f"Validated: {product_name} - Score: {scoring_result['total_score']:.1f}/10")
            
            # Sort by score (highest first)
            validated_products.sort(key=lambda x: x['market_fit_score'], reverse=True)
            
            result = {
                'status': 'success',
                'total_validated': len(validated_products),
                'validated_products': validated_products,
                'timestamp': input_data.get('timestamp', datetime.now().isoformat())
            }
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"MarketValidatorAgent failed: {e}")
            return json.dumps({'error': str(e)})
