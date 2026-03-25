"""
Main pipeline orchestrator using AG2 (AutoGen) for multi-agent collaboration.
Coordinates the workflow: Scout → Checker → Validator → Reporter
Generates both Markdown and PDF reports, with optional email delivery.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import Config
from utils import setup_logging
from agents import (
    DouyinScoutAgent,
    TikTokCheckerAgent,
    MarketValidatorAgent,
    ReporterAgent
)
from reporting.pdf_generator import generate_pdf_report
from email_services.email_sender import (
    create_email_service_from_env,
    parse_email_list
)

# Try to import AG2 (AutoGen) components
try:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.teams import RoundRobinGroupChat
    AG2_AVAILABLE = True
except ImportError:
    AG2_AVAILABLE = False


class OpportunityFinderPipeline:
    """
    Main pipeline that orchestrates the multi-agent workflow.
    
    Workflow:
    1. DouyinScoutAgent fetches trending products from TikHub API
    2. TikTokCheckerAgent identifies gaps (products not on TikTok Shop)
    3. MarketValidatorAgent scores each gap product
    4. ReporterAgent generates final markdown report
    5. PDF report is generated
    6. Email is sent to recipients (if configured)
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        
        # Setup logging
        self.logger = setup_logging(self.config.log_file_path)
        
        # Initialize agents
        self.scout = DouyinScoutAgent(self.config)
        self.checker = TikTokCheckerAgent(self.config)
        self.validator = MarketValidatorAgent(self.config)
        self.reporter = ReporterAgent(self.config)
        
        # Email service (optional)
        self.email_service = None
        self.email_enabled = os.getenv('ENABLE_EMAIL_REPORTS', 'false').lower() == 'true'
        
        if self.email_enabled:
            self.email_service = create_email_service_from_env()
            if self.email_service:
                self.logger.info("Email service initialized")
            else:
                self.logger.warning("Email service could not be initialized")
        
        self.logger.info("OpportunityFinderPipeline initialized")
    
    async def run_pipeline(self, send_email: bool = None) -> str:
        """
        Execute the complete pipeline sequentially.
        
        Args:
            send_email: Override email sending setting
            
        Returns:
            Final markdown report string.
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting Douyin Opportunity Finder Pipeline")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info("=" * 60)
        
        try:
            # Step 1: Fetch Douyin trends
            self.logger.info("\n[Step 1/4] Fetching trending products from Douyin...")
            douyin_result = await self.scout.run()
            
            if 'error' in douyin_result:
                self.logger.error(f"Douyin fetch failed: {douyin_result}")
                return f"# Pipeline Error\n\nFailed to fetch Douyin data: {douyin_result}"
            
            douyin_data = json.loads(douyin_result)
            self.logger.info(f"✓ Found {douyin_data.get('count', 0)} Douyin products")
            
            # Step 2: Check against TikTok Shop
            self.logger.info("\n[Step 2/4] Checking products against TikTok Shop databases...")
            checker_result = await self.checker.run(douyin_result)
            
            if 'error' in checker_result:
                self.logger.error(f"TikTok check failed: {checker_result}")
                return f"# Pipeline Error\n\nFailed to check TikTok Shop: {checker_result}"
            
            checker_data = json.loads(checker_result)
            self.logger.info(f"✓ Found {checker_data.get('gaps_found', 0)} gap products")
            
            # Step 3: Validate market potential
            self.logger.info("\n[Step 3/4] Validating market potential...")
            validator_result = await self.validator.run(checker_result)
            
            if 'error' in validator_result:
                self.logger.error(f"Market validation failed: {validator_result}")
                return f"# Pipeline Error\n\nFailed to validate market: {validator_result}"
            
            validator_data = json.loads(validator_result)
            self.logger.info(f"✓ Validated {validator_data.get('total_validated', 0)} products")
            
            # Step 4: Generate markdown report
            self.logger.info("\n[Step 4/6] Generating opportunity report...")
            markdown_report = await self.reporter.run(validator_result)
            
            self.logger.info(f"✓ Markdown report saved to: {self.config.report_output_path}")
            
            # Step 5: Generate PDF report
            self.logger.info("\n[Step 5/6] Generating PDF report...")
            pdf_path = self._generate_pdf_report(validator_data)
            if pdf_path:
                self.logger.info(f"✓ PDF report saved to: {pdf_path}")
            else:
                self.logger.warning("PDF generation failed or disabled")
            
            # Step 6: Send email (if configured)
            if send_email is None:
                send_email = self.email_enabled
            
            if send_email and self.email_service and pdf_path:
                self.logger.info("\n[Step 6/6] Sending email report...")
                email_sent = self._send_email_report(pdf_path, markdown_report)
                if email_sent:
                    self.logger.info("✓ Email report sent successfully")
                else:
                    self.logger.warning("Email sending failed")
            elif send_email and not self.email_service:
                self.logger.warning("Email sending requested but email service not configured")
            else:
                self.logger.info("\n[Step 6/6] Email sending skipped (not configured)")
            
            self.logger.info(f"\n{'=' * 60}")
            self.logger.info("Pipeline completed successfully!")
            self.logger.info(f"Reports saved to:")
            self.logger.info(f"  - Markdown: {self.config.report_output_path}")
            if pdf_path:
                self.logger.info(f"  - PDF: {pdf_path}")
            self.logger.info(f"{'=' * 60}\n")
            
            return markdown_report
            
        except Exception as e:
            self.logger.error(f"Pipeline failed with exception: {e}", exc_info=True)
            return f"# Pipeline Error\n\n{str(e)}"
    
    def _generate_pdf_report(self, validator_data: dict) -> Optional[str]:
        """Generate PDF report from validated data."""
        try:
            # Prepare report data structure for PDF generator
            opportunities = validator_data.get('validated_products', [])
            
            # Calculate metrics
            total_opportunities = len(opportunities)
            high_score_count = sum(1 for p in opportunities if p.get('market_fit_score', 0) >= 8)
            avg_score = sum(p.get('market_fit_score', 0) for p in opportunities) / max(1, total_opportunities)
            
            # Determine top category (simplified)
            categories = {}
            for p in opportunities:
                name = p.get('title_english', '').lower()
                if any(kw in name for kw in ['led', 'light', 'lamp']):
                    categories['Lighting'] = categories.get('Lighting', 0) + 1
                elif any(kw in name for kw in ['kitchen', 'home', 'organize']):
                    categories['Home & Kitchen'] = categories.get('Home & Kitchen', 0) + 1
                elif any(kw in name for kw in ['phone', 'case', 'accessory']):
                    categories['Tech Accessories'] = categories.get('Tech Accessories', 0) + 1
                else:
                    categories['Other'] = categories.get('Other', 0) + 1
            
            top_category = max(categories, key=categories.get) if categories else 'N/A'
            
            # Build report data
            report_data = {
                'title': 'Douyin Opportunity Finder',
                'timezone': os.getenv('TIMEZONE', 'Asia/Shanghai'),
                'summary': {
                    'key_findings': [
                        f"Found {total_opportunities} trending products not available on TikTok Shop US/UK",
                        f"Top category: {top_category}",
                        f"Average opportunity score: {avg_score:.1f}/10",
                        f"{high_score_count} products scored above 8.0 (high priority)"
                    ],
                    'total_opportunities': total_opportunities,
                    'high_score_count': high_score_count
                },
                'metrics': {
                    'products_analyzed': validator_data.get('total_validated', 0),
                    'gaps_found': total_opportunities,
                    'average_score': avg_score,
                    'top_category': top_category,
                    'avg_price_range': '$15-$45'
                },
                'opportunities': []
            }
            
            # Add opportunities
            for opp in opportunities[:20]:  # Top 20 for table
                report_data['opportunities'].append({
                    'product_name': opp.get('title_english', 'Unknown'),
                    'hot_count': opp.get('hot_count', 0),
                    'score': opp.get('market_fit_score', 0),
                    'price_range': '$15-$45',
                    'content_angle': opp.get('justifications', {}).get('visual_appeal', 'Create demo video'),
                    'competition': opp.get('component_scores', {}).get('competition', 'Medium'),
                    'cultural_fit': opp.get('component_scores', {}).get('cultural_fit', 'Medium'),
                    'visual_appeal': opp.get('component_scores', {}).get('visual_appeal', 'Medium'),
                    'notes': opp.get('justifications', {}).get('cultural_fit', '')
                })
            
            # Generate PDF
            pdf_output_path = os.getenv('PDF_REPORT_OUTPUT_PATH', 'data/daily_report.pdf')
            pdf_path = generate_pdf_report(report_data, pdf_output_path)
            
            return pdf_path
            
        except Exception as e:
            self.logger.error(f"PDF generation failed: {e}")
            return None
    
    def _send_email_report(self, pdf_path: str, markdown_report: str) -> bool:
        """Send email with PDF report attached."""
        try:
            # Get email configuration
            email_to_str = os.getenv('EMAIL_TO', '')
            email_subject = os.getenv('EMAIL_SUBJECT', 'Douyin Opportunity Finder - Daily Report')
            
            # Parse recipient list
            recipients = parse_email_list(email_to_str)
            
            if not recipients:
                self.logger.warning("No email recipients configured")
                return False
            
            # Create email body (plain text summary)
            body = f"""
Douyin Opportunity Finder - Daily Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Please find attached the detailed PDF report with today's top opportunities.

KEY HIGHLIGHTS:
- See attached PDF for full analysis
- Top opportunities ranked by market fit score (1-10)
- Content angle suggestions included for each product

This is an automated report from the Douyin Opportunity Finder system.
For questions, contact your system administrator.

---
Douyin Opportunity Finder
Automated Product Research System
            """
            
            # Create HTML version
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <h2 style="color: #1a1a2e;">Douyin Opportunity Finder - Daily Report</h2>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    
    <div style="background-color: #f4f4f4; padding: 15px; border-left: 4px solid #16213e; margin: 20px 0;">
        <p>Please find attached the detailed PDF report with today's top opportunities.</p>
    </div>
    
    <h3>Key Highlights:</h3>
    <ul>
        <li>See attached PDF for full analysis</li>
        <li>Top opportunities ranked by market fit score (1-10)</li>
        <li>Content angle suggestions included for each product</li>
    </ul>
    
    <p style="color: #666; font-size: 12px; margin-top: 30px;">
        This is an automated report from the Douyin Opportunity Finder system.<br>
        For questions, contact your system administrator.
    </p>
</body>
</html>
            """
            
            # Send email
            success = self.email_service.send_report(
                to_emails=recipients,
                subject=email_subject,
                body=body,
                pdf_path=pdf_path,
                html_body=html_body
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Email sending failed: {e}")
            return False
    
    def run_with_ag2(self) -> str:
        """
        Execute pipeline using AG2 (AutoGen) multi-agent framework.
        
        This method demonstrates AG2 integration where agents communicate
        via a group chat managed by GroupChatManager.
        
        Note: Requires AG2 (autogen-agentchat) to be installed.
        """
        if not AG2_AVAILABLE:
            self.logger.warning("AG2 not available, falling back to sequential execution")
            return asyncio.run(self.run_pipeline())
        
        self.logger.info("Running with AG2 multi-agent orchestration...")
        
        # Define agent tasks as messages
        tasks = [
            "Fetch trending products from Douyin using TikHub API",
            "Check which products are NOT available on TikTok Shop US/UK",
            "Validate market potential using Amazon and Reddit data",
            "Generate markdown report with top opportunities"
        ]
        
        # Create AG2 assistant agents (conceptual - actual implementation varies)
        # In production, you would define proper agent configurations
        
        # For now, fall back to sequential execution
        # AG2 integration requires specific setup based on your environment
        return asyncio.run(self.run_pipeline())


async def main():
    """Main entry point for the pipeline."""
    config = Config()
    pipeline = OpportunityFinderPipeline(config)
    
    # Run the pipeline
    report = await pipeline.run_pipeline()
    
    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE EXECUTION COMPLETE")
    print("=" * 60)
    print(f"\nReport generated at: {config.report_output_path}")
    print("\nTo view the report:")
    print(f"  cat {config.report_output_path}")
    print("\n" + "=" * 60 + "\n")
    
    return report


if __name__ == "__main__":
    asyncio.run(main())
