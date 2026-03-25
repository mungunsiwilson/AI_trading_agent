"""
PDF Report Generator Module

Generates professional PDF reports from opportunity data
with charts, tables, and formatted sections.
"""

import os
from datetime import datetime
from typing import List, Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


class PDFReportGenerator:
    """Generate professional PDF reports from opportunity data."""
    
    def __init__(self, output_path: str = "data/daily_report.pdf"):
        self.output_path = output_path
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Create custom paragraph styles for the report."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#16213e'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Normal text with justification
        self.styles.add(ParagraphStyle(
            name='JustifiedText',
            parent=self.styles['Normal'],
            alignment=TA_JUSTIFY,
            fontSize=10,
            leading=12
        ))
        
        # Score highlight style
        self.styles.add(ParagraphStyle(
            name='ScoreHighlight',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#e94560'),
            fontName='Helvetica-Bold'
        ))
    
    def generate_pdf(self, report_data: Dict[str, Any], markdown_content: str = None) -> str:
        """
        Generate a PDF report from structured data.
        
        Args:
            report_data: Dictionary containing report sections
            markdown_content: Optional raw markdown to parse
            
        Returns:
            Path to generated PDF file
        """
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Add header with date
        story.extend(self._create_header(report_data))
        
        # Add executive summary
        if 'summary' in report_data:
            story.extend(self._create_summary_section(report_data['summary']))
        
        # Add key metrics table
        if 'metrics' in report_data:
            story.extend(self._create_metrics_section(report_data['metrics']))
        
        # Add opportunities table (top 20)
        if 'opportunities' in report_data:
            story.extend(self._create_opportunities_table(report_data['opportunities'][:20]))
        
        # Add detailed analysis for top 10
        if 'opportunities' in report_data:
            story.extend(self._create_detailed_analysis(report_data['opportunities'][:10]))
        
        # Add footer
        story.extend(self._create_footer())
        
        # Build PDF
        doc.build(story)
        
        return self.output_path
    
    def _create_header(self, report_data: Dict[str, Any]) -> List:
        """Create report header with title and date."""
        elements = []
        
        # Title
        title = report_data.get('title', 'Douyin Opportunity Finder')
        elements.append(Paragraph(title, self.styles['CustomTitle']))
        
        # Date
        date_str = datetime.now().strftime('%B %d, %Y')
        elements.append(Paragraph(f"Daily Report - {date_str}", self.styles['Subtitle']))
        
        # Timezone info
        tz = report_data.get('timezone', 'Asia/Shanghai')
        elements.append(Paragraph(
            f"Generated at 9:00 AM {tz} | Market Analysis: US & UK TikTok Shop",
            self.styles['JustifiedText']
        ))
        
        elements.append(Spacer(1, 0.3*inch))
        return elements
    
    def _create_summary_section(self, summary: Dict[str, Any]) -> List:
        """Create executive summary section."""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Key findings
        findings = summary.get('key_findings', [])
        for finding in findings:
            p = Paragraph(f"• {finding}", self.styles['JustifiedText'])
            elements.append(p)
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Total opportunities
        total = summary.get('total_opportunities', 0)
        high_score = summary.get('high_score_count', 0)
        
        elements.append(Paragraph(
            f"Total Opportunities Identified: <b>{total}</b> | High-Priority (Score ≥8): <b>{high_score}</b>",
            self.styles['ScoreHighlight']
        ))
        
        elements.append(Spacer(1, 0.3*inch))
        return elements
    
    def _create_metrics_section(self, metrics: Dict[str, Any]) -> List:
        """Create key metrics table."""
        elements = []
        
        elements.append(Paragraph("Key Metrics", self.styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Create metrics table
        data = [
            ['Metric', 'Value'],
            ['Products Analyzed', str(metrics.get('products_analyzed', 0))],
            ['Gaps Found', str(metrics.get('gaps_found', 0))],
            ['Average Score', f"{metrics.get('average_score', 0):.1f}/10"],
            ['Top Category', metrics.get('top_category', 'N/A')],
            ['Avg Price Range', metrics.get('avg_price_range', '$10-$50')],
        ]
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        return elements
    
    def _create_opportunities_table(self, opportunities: List[Dict[str, Any]]) -> List:
        """Create main opportunities table."""
        elements = []
        
        elements.append(Paragraph("Top Opportunities (Top 20)", self.styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Table headers
        data = [[
            'Rank',
            'Product Name',
            'Hot Count',
            'Score',
            'Price Range',
            'Content Angle'
        ]]
        
        # Add rows
        for i, opp in enumerate(opportunities, 1):
            row = [
                str(i),
                opp.get('product_name', 'N/A')[:40],
                f"{opp.get('hot_count', 0):,}",
                f"{opp.get('score', 0):.1f}",
                opp.get('price_range', '$10-$50'),
                opp.get('content_angle', 'N/A')[:30]
            ]
            data.append(row)
        
        # Create table
        table = Table(data, colWidths=[0.5*inch, 2*inch, 1*inch, 0.7*inch, 1*inch, 1.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Highlight high scores
            ('BACKGROUND', (3, 1), (3, -1), colors.Color(1, 0, 0, alpha=0.1)),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        return elements
    
    def _create_detailed_analysis(self, opportunities: List[Dict[str, Any]]) -> List:
        """Create detailed analysis for top 10 products."""
        elements = []
        
        elements.append(Paragraph("Detailed Analysis - Top 10", self.styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        for i, opp in enumerate(opportunities, 1):
            # Product header
            elements.append(Paragraph(
                f"#{i}: {opp.get('product_name', 'Unknown Product')}",
                self.styles['Heading3']
            ))
            
            # Score breakdown
            score = opp.get('score', 0)
            score_color = colors.green if score >= 8 else (colors.orange if score >= 6 else colors.red)
            
            elements.append(Paragraph(
                f"<b>Overall Score:</b> <font color='{score_color.hexval()}'>{score:.1f}/10</font>",
                self.styles['Normal']
            ))
            
            # Details
            details = [
                f"• Douyin Hot Count: {opp.get('hot_count', 0):,}",
                f"• Price Range: {opp.get('price_range', 'N/A')}",
                f"• Competition Level: {opp.get('competition', 'Medium')}",
                f"• Cultural Fit: {opp.get('cultural_fit', 'Medium')}",
                f"• Visual Appeal: {opp.get('visual_appeal', 'Medium')}",
            ]
            
            for detail in details:
                elements.append(Paragraph(detail, self.styles['JustifiedText']))
            
            # Content angle
            elements.append(Paragraph(
                f"<b>Content Angle:</b> {opp.get('content_angle', 'N/A')}",
                self.styles['Normal']
            ))
            
            # Notes
            if opp.get('notes'):
                elements.append(Paragraph(
                    f"<b>Notes:</b> {opp.get('notes')}",
                    self.styles['JustifiedText']
                ))
            
            elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_footer(self) -> List:
        """Create report footer."""
        elements = []
        
        elements.append(PageBreak())
        
        # Disclaimer
        elements.append(Paragraph("Disclaimer", self.styles['Heading3']))
        elements.append(Paragraph(
            "This report is generated automatically based on available data. "
            "Market conditions change rapidly. Always conduct additional research before making business decisions.",
            self.styles['JustifiedText']
        ))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Contact info placeholder
        elements.append(Paragraph(
            "For questions or support, contact your system administrator.",
            self.styles['JustifiedText']
        ))
        
        return elements


def generate_pdf_report(report_data: Dict[str, Any], output_path: str = None) -> str:
    """
    Convenience function to generate PDF report.
    
    Args:
        report_data: Report data dictionary
        output_path: Optional custom output path
        
    Returns:
        Path to generated PDF
    """
    if output_path:
        generator = PDFReportGenerator(output_path)
    else:
        generator = PDFReportGenerator()
    
    return generator.generate_pdf(report_data)


if __name__ == "__main__":
    # Test PDF generation
    test_data = {
        'title': 'Douyin Opportunity Finder',
        'timezone': 'Asia/Shanghai',
        'summary': {
            'key_findings': [
                'Found 25 trending products not available on TikTok Shop US/UK',
                'Top category: Home & Kitchen gadgets',
                'Average opportunity score: 7.2/10',
                '3 products scored above 8.5 (high priority)'
            ],
            'total_opportunities': 25,
            'high_score_count': 3
        },
        'metrics': {
            'products_analyzed': 100,
            'gaps_found': 25,
            'average_score': 7.2,
            'top_category': 'Home & Kitchen',
            'avg_price_range': '$15-$45'
        },
        'opportunities': [
            {
                'product_name': 'Smart LED Desk Lamp with Wireless Charging',
                'hot_count': 125000,
                'score': 9.2,
                'price_range': '$25-$35',
                'content_angle': 'Show transformation from cluttered to organized desk',
                'competition': 'Low',
                'cultural_fit': 'High',
                'visual_appeal': 'High',
                'notes': 'Perfect for WFH trend, multiple use cases'
            },
        ]
    }
    
    pdf_path = generate_pdf_report(test_data)
    print(f"PDF report generated: {pdf_path}")
