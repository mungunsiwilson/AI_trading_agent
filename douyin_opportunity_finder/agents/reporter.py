"""
ReporterAgent - Generates daily opportunity report in markdown format.
Compiles validated products into actionable insights with content suggestions.
"""

import logging
import json
from typing import List, Dict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ReporterAgent:
    """Agent responsible for generating the final opportunity report."""
    
    def __init__(self, config):
        self.config = config
        self.report_path = config.report_output_path
    
    def generate_content_angle(self, product: Dict) -> str:
        """
        Generate a short content angle suggestion for TikTok video.
        
        Args:
            product: Validated product dictionary.
            
        Returns:
            Short content suggestion string.
        """
        product_name = product.get('title_english', '').lower()
        justifications = product.get('justifications', {})
        visual_appeal = justifications.get('visual_appeal', '')
        
        # Content angle templates based on product characteristics
        if 'light' in product_name or 'LED' in product_name:
            return "Show dramatic before/after lighting transformation with trending audio"
        elif 'organize' in product_name or 'clean' in product_name:
            return "Satisfying organization timelapse with ASMR sounds"
        elif 'hack' in product_name or 'trick' in product_name:
            return "Problem-solution format: 'I bet you didn't know this trick'"
        elif 'portable' in product_name:
            return "Show compact size vs functionality comparison"
        elif 'gift' in product_name:
            return "Gift guide format: 'Perfect gift for [target audience]'"
        else:
            return "Hook in 3 seconds → Show problem → Demonstrate solution → Call to action"
    
    def format_market_summary(self, product: Dict) -> str:
        """
        Format market analysis summary for a product.
        
        Args:
            product: Validated product dictionary.
            
        Returns:
            Formatted summary string.
        """
        amazon = product.get('amazon_summary', {})
        reddit = product.get('reddit_summary', {})
        justifications = product.get('justifications', {})
        
        notes = []
        
        # Competition level
        comp_score = product.get('component_scores', {}).get('competition', 0)
        if comp_score >= 1.8:
            notes.append("Low competition")
        elif comp_score >= 1.5:
            notes.append("Moderate competition")
        else:
            notes.append("High competition")
        
        # Price estimate
        avg_price = amazon.get('avg_price', 0)
        if avg_price > 0:
            notes.append(f"Est. price: ${avg_price:.2f}")
        else:
            notes.append("Price: Research needed")
        
        # Reddit sentiment
        mentions = reddit.get('total_mentions', 0)
        if mentions > 0:
            sentiment = reddit.get('sentiment_score', 0.5)
            if sentiment >= 0.7:
                notes.append("Positive Reddit buzz")
            elif sentiment <= 0.3:
                notes.append("Mixed Reddit reception")
        
        return "; ".join(notes)
    
    def generate_markdown_table(self, products: List[Dict]) -> str:
        """
        Generate markdown table from validated products.
        
        Args:
            products: List of validated product dictionaries.
            
        Returns:
            Markdown table string.
        """
        if not products:
            return "*No products to display*"
        
        # Table header
        table = "| Rank | Product Name (English) | Douyin Hot Count | TikTok Status | Market Fit Score | Content Angle | Additional Notes |\n"
        table += "|------|------------------------|------------------|---------------|------------------|---------------|------------------|\n"
        
        # Table rows (top 20 products)
        for i, product in enumerate(products[:20], 1):
            rank = str(i)
            name = product.get('title_english', 'Unknown')[:40]  # Truncate long names
            if len(product.get('title_english', '')) > 40:
                name += "..."
            
            hot_count = str(product.get('hot_count', 'N/A'))
            tiktok_status = "NOT FOUND ✓"
            
            score = product.get('market_fit_score', 0)
            score_display = f"{score:.1f}/10"
            
            content_angle = self.generate_content_angle(product)[:50]
            if len(self.generate_content_angle(product)) > 50:
                content_angle += "..."
            
            notes = self.format_market_summary(product)[:40]
            if len(self.format_market_summary(product)) > 40:
                notes += "..."
            
            table += f"| {rank} | {name} | {hot_count} | {tiktok_status} | {score_display} | {content_angle} | {notes} |\n"
        
        return table
    
    def generate_top_10_summary(self, products: List[Dict]) -> str:
        """
        Generate detailed summary of top 10 opportunities.
        
        Args:
            products: List of validated product dictionaries.
            
        Returns:
            Formatted summary string.
        """
        if not products:
            return "*No products to summarize*"
        
        summary = "## 🏆 Top 10 Opportunities - Detailed Analysis\n\n"
        
        for i, product in enumerate(products[:10], 1):
            name = product.get('title_english', 'Unknown')
            chinese_name = product.get('title_chinese', '')
            score = product.get('market_fit_score', 0)
            hot_count = product.get('hot_count', 0)
            
            summary += f"### #{i}: {name}\n"
            summary += f"**Chinese Title:** {chinese_name}\n\n"
            summary += f"**Market Fit Score:** {score:.1f}/10\n"
            summary += f"**Douyin Hot Count:** {hot_count:,}\n\n"
            
            # Component scores
            components = product.get('component_scores', {})
            summary += "**Score Breakdown:**\n"
            summary += f"- Competition: {components.get('competition', 0):.1f}/2\n"
            summary += f"- Sentiment: {components.get('sentiment', 0):.1f}/2\n"
            summary += f"- Cultural Fit: {components.get('cultural_fit', 0):.1f}/2\n"
            summary += f"- Visual Appeal: {components.get('visual_appeal', 0):.1f}/2\n"
            summary += f"- Price Point: {components.get('price_point', 0):.1f}/2\n\n"
            
            # Justifications
            justifications = product.get('justifications', {})
            summary += "**Key Insights:**\n"
            for key, value in justifications.items():
                summary += f"- {value}\n"
            summary += "\n"
            
            # Content angle
            content_angle = self.generate_content_angle(product)
            summary += f"**🎬 Content Suggestion:** {content_angle}\n\n"
            summary += "---\n\n"
        
        return summary
    
    def generate_report(self, validated_products_json: str) -> str:
        """
        Generate complete markdown report.
        
        Args:
            validated_products_json: JSON string containing validated products.
            
        Returns:
            Complete markdown report string.
        """
        try:
            # Parse input
            input_data = json.loads(validated_products_json)
            
            if 'error' in input_data:
                return f"# Error Report\n\n{input_data['error']}"
            
            products = input_data.get('validated_products', [])
            timestamp = input_data.get('timestamp', datetime.now().isoformat())
            
            # Generate report date
            report_date = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d")
            
            # Build report
            report = f"""# 🚀 Douyin → TikTok Shop Opportunity Report

**Report Date:** {report_date}  
**Generated At:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Total Opportunities Found:** {len(products)}

---

## 📊 Executive Summary

This report identifies trending products on Douyin (Chinese TikTok) that are **not yet available** on TikTok Shop US/UK markets. Each product has been validated using Amazon competition data and Reddit sentiment analysis.

**Key Metrics:**
- Products Analyzed: {input_data.get('total_validated', 0)}
- Average Market Fit Score: {sum(p.get('market_fit_score', 0) for p in products) / len(products):.1f}/10 (if products exist)
- Top Score: {max((p.get('market_fit_score', 0) for p in products), default=0):.1f}/10

---

## 📋 Opportunity Table

{self.generate_markdown_table(products)}

---

{self.generate_top_10_summary(products)}

## 🎯 Action Items

1. **Immediate Action:** Focus on top 3 products with scores ≥ 7.0
2. **Content Creation:** Use suggested content angles for each product
3. **Supplier Research:** Source products from Alibaba/1688 based on Chinese titles
4. **Competitive Analysis:** Deep-dive into Amazon listings for pricing strategy
5. **Test Launch:** Create TikTok videos for top 5 products within 48 hours

---

## ⚠️ Disclaimer

- Market data is based on automated analysis and should be verified manually
- TikTok Shop availability changes rapidly - verify before investing
- This report is for informational purposes only

---

*Generated by Douyin Opportunity Finder v1.0*
"""
            
            return report
            
        except Exception as e:
            logger.error(f"ReporterAgent failed: {e}")
            return f"# Error Report\n\nFailed to generate report: {str(e)}"
    
    async def run(self, validated_products_json: str) -> str:
        """
        Main execution method for the agent.
        
        Args:
            validated_products_json: JSON string containing validated products.
            
        Returns:
            Markdown report string (also saves to file).
        """
        try:
            # Generate report
            report = self.generate_report(validated_products_json)
            
            # Save to file
            self.report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"Report saved to {self.report_path}")
            
            return report
            
        except Exception as e:
            logger.error(f"ReporterAgent run failed: {e}")
            return f"# Error\n\n{str(e)}"
