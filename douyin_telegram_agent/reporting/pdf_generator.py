"""PDF Generator - Creates professional PDF reports."""
import logging
from typing import List, Dict
from datetime import datetime
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)

class PDFGenerator:
    """Generate professional PDF reports from opportunity data."""
    
    def __init__(self):
        """Initialize PDF Generator."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c5282'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Normal style with better spacing
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=6
        ))
    
    def generate_pdf(self, products: List[Dict], output_path: str) -> str:
        """
        Generate a PDF report.
        
        Args:
            products: List of scored product dictionaries
            output_path: Path to save the PDF
            
        Returns:
            Path to the generated PDF
        """
        logger.info(f"Generating PDF report for {len(products)} products...")
        
        # Sort products by score
        products = sorted(products, key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build content
        content = []
        
        # Title
        title = Paragraph("🚀 Douyin Opportunity Finder", self.styles['CustomTitle'])
        content.append(title)
        
        # Subtitle
        subtitle = Paragraph("Daily Market Gap Analysis Report", self.styles['Heading3'])
        content.append(subtitle)
        content.append(Spacer(1, 0.2*inch))
        
        # Date and metrics
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        metrics_text = f"""
        <b>Generated:</b> {report_date}<br/>
        <b>Total Opportunities:</b> {len(products)}<br/>
        <b>Top Score:</b> {products[0].get('overall_score', 0):.1f}/10 (if products else 0)<br/>
        <b>High Potential (8+):</b> {sum(1 for p in products if p.get('overall_score', 0) >= 8)} products
        """
        content.append(Paragraph(metrics_text, self.styles['CustomNormal']))
        content.append(Spacer(1, 0.3*inch))
        
        # Executive Summary
        content.append(Paragraph("Executive Summary", self.styles['CustomHeading']))
        summary_text = """
        This report identifies trending products on Douyin (Chinese TikTok) that are 
        <b>NOT yet available</b> on TikTok Shop US/UK, validated for market potential using AI analysis.
        """
        content.append(Paragraph(summary_text, self.styles['CustomNormal']))
        content.append(Spacer(1, 0.2*inch))
        
        # Top 20 Opportunities Table
        content.append(Paragraph("Top 20 Opportunities", self.styles['CustomHeading']))
        
        top_products = products[:20]
        table_data = self._create_opportunities_table(top_products)
        table = Table(table_data, colWidths=[0.4*inch, 2.5*inch, 1.2*inch, 1*inch, 2.9*inch])
        table.setStyle(self._create_table_style())
        content.append(table)
        content.append(Spacer(1, 0.3*inch))
        
        # Detailed Analysis (Top 10)
        content.append(Paragraph("Detailed Analysis - Top 10", self.styles['CustomHeading']))
        
        for i, product in enumerate(products[:10], 1):
            product_content = self._create_product_detail(i, product)
            content.extend(product_content)
            content.append(Spacer(1, 0.15*inch))
        
        # Action Items
        content.append(PageBreak())
        content.append(Paragraph("Action Items & Recommendations", self.styles['CustomHeading']))
        
        action_items = """
        <b>Priority 1 (Score 8-10):</b> Focus on creating content for top 3 products immediately<br/><br/>
        <b>Priority 2 (Score 6-7.9):</b> Research suppliers and prepare content calendar<br/><br/>
        <b>Priority 3 (Score &lt;6):</b> Monitor for trends, revisit in 1-2 weeks<br/><br/>
        <b>Important Notes:</b><br/>
        • Scores are AI-generated estimates based on available data<br/>
        • Always conduct your own market research before investing<br/>
        • Product availability and competition change rapidly<br/>
        • This report is for informational purposes only
        """
        content.append(Paragraph(action_items, self.styles['CustomNormal']))
        
        # Footer
        content.append(Spacer(1, 0.5*inch))
        footer = Paragraph("<i>Generated by Douyin Opportunity Finder v1.0 | Confidential</i>", self.styles['CustomNormal'])
        content.append(footer)
        
        # Build PDF
        doc.build(content)
        
        logger.info(f"PDF report saved to {output_path}")
        return output_path
    
    def _create_opportunities_table(self, products: List[Dict]) -> List[List]:
        """Create data for opportunities table."""
        # Header
        data = [[
            "Rank",
            "Product Name",
            "Hot Count",
            "Score",
            "Content Angle"
        ]]
        
        for i, product in enumerate(products, 1):
            name = product.get('english_title', product.get('title', 'Unknown'))[:35]
            hot_count = f"{product.get('hot_count', 0):,}"
            score = product.get('overall_score', 0)
            analysis = product.get('market_analysis', {})
            content_angle = analysis.get('content_angle', 'N/A')[:40]
            
            # Color code score
            if score >= 8:
                score_str = f"🟢 {score:.1f}"
            elif score >= 6:
                score_str = f"🟡 {score:.1f}"
            else:
                score_str = f"🔴 {score:.1f}"
            
            data.append([
                str(i),
                name,
                hot_count,
                score_str,
                content_angle
            ])
        
        return data
    
    def _create_table_style(self) -> TableStyle:
        """Create table styling."""
        style = TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            
            # Alternating row colors
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('BACKGROUND', (0, 2), (-1, -1), colors.HexColor('#f7fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            
            # Column-specific alignment
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Rank
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),   # Hot Count
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),  # Score
        ])
        
        return style
    
    def _create_product_detail(self, rank: int, product: Dict) -> list:
        """Create detailed product analysis section."""
        content = []
        
        name = product.get('english_title', product.get('title', 'Unknown'))
        score = product.get('overall_score', 0)
        hot_count = product.get('hot_count', 0)
        breakdown = product.get('score_breakdown', {})
        analysis = product.get('market_analysis', {})
        
        # Product title
        title = Paragraph(f"#{rank}: {name}", self.styles['Heading4'])
        content.append(title)
        
        # Metrics
        metrics = f"""
        <b>Overall Score:</b> {score:.1f}/10 | 
        <b>Douyin Hot Count:</b> {hot_count:,}
        """
        content.append(Paragraph(metrics, self.styles['CustomNormal']))
        
        # Score breakdown
        breakdown_text = f"""
        <b>Score Breakdown:</b><br/>
        🏆 Competition: {breakdown.get('competition', 'N/A')}/10 | 
        💬 Sentiment: {breakdown.get('sentiment', 'N/A')}/10 | 
        🌍 Cultural Fit: {breakdown.get('cultural_fit', 'N/A')}/10 | 
        📹 Visual Appeal: {breakdown.get('visual_appeal', 'N/A')}/10 | 
        💰 Price Point: {breakdown.get('price_point', 'N/A')}/10
        """
        content.append(Paragraph(breakdown_text, self.styles['CustomNormal']))
        
        # Content strategy
        content_angle = analysis.get('content_angle', 'N/A')
        content.append(Paragraph(f"<b>💡 Video Idea:</b> {content_angle}", self.styles['CustomNormal']))
        
        # Notes
        notes = analysis.get('notes', 'No additional notes.')
        content.append(Paragraph(f"<b>📝 Analysis:</b> {notes}", self.styles['CustomNormal']))
        
        return content
