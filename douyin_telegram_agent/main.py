"""Main Pipeline - Orchestrates the complete Douyin Opportunity Finder workflow."""
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from agents import DouyinScoutAgent, TikTokCheckerAgent, MarketValidatorAgent, ReporterAgent
from reporting import PDFGenerator
from telegram_services import TelegramSender

# Setup logging
def setup_logging():
    """Configure logging."""
    log_config = config.get_logging_config()
    log_dir = Path(log_config['file']).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        handlers=[
            logging.FileHandler(log_config['file'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class DouyinOpportunityPipeline:
    """Main pipeline orchestrating all agents."""
    
    def __init__(self):
        """Initialize the pipeline with all agents."""
        logger.info("Initializing Douyin Opportunity Pipeline...")
        
        paths = config.get_paths()
        
        # Initialize agents
        self.scout = DouyinScoutAgent(
            api_key=config.tikhub_api_key,
            config=config.get_agent_config('douyin_scout')
        )
        
        self.checker = TikTokCheckerAgent(
            us_csv_path=paths['us_csv'],
            uk_csv_path=paths['uk_csv'],
            config=config.get_agent_config('tiktok_checker')
        )
        
        self.validator = MarketValidatorAgent(
            groq_api_key=config.groq_api_key,
            config=config.get_agent_config('market_validator')
        )
        
        self.reporter = ReporterAgent(
            config=config.get_agent_config('reporter')
        )
        
        self.pdf_generator = PDFGenerator()
        
        # Telegram sender (optional)
        if config.enable_telegram and config.telegram_bot_token and config.telegram_chat_id:
            self.telegram_sender = TelegramSender(
                bot_token=config.telegram_bot_token,
                chat_id=config.telegram_chat_id
            )
        else:
            self.telegram_sender = None
            logger.warning("Telegram not configured. Reports will be generated locally only.")
        
        logger.info("Pipeline initialized successfully")
    
    def run(self) -> dict:
        """
        Execute the complete pipeline.
        
        Returns:
            Dictionary with pipeline results
        """
        logger.info("=" * 60)
        logger.info("Starting Douyin Opportunity Pipeline")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        results = {
            'success': False,
            'products_found': 0,
            'gaps_identified': 0,
            'products_validated': 0,
            'report_generated': False,
            'pdf_generated': False,
            'telegram_sent': False,
            'errors': []
        }
        
        try:
            # Step 1: Fetch trending products from Douyin
            logger.info("\n[STEP 1/5] Fetching trending products from Douyin...")
            douyin_products = self.scout.fetch_trending_products()
            
            if not douyin_products:
                logger.error("No products fetched from Douyin")
                results['errors'].append("Failed to fetch products from Douyin")
                return results
            
            results['products_found'] = len(douyin_products)
            logger.info(f"✓ Found {len(douyin_products)} trending products")
            
            # Step 2: Identify gaps (products not on TikTok Shop)
            logger.info("\n[STEP 2/5] Checking against TikTok Shop database...")
            gap_products = self.checker.find_gaps(douyin_products)
            
            if not gap_products:
                logger.info("No opportunity gaps found (all products exist on TikTok Shop)")
                results['gaps_identified'] = 0
                results['success'] = True
                return results
            
            results['gaps_identified'] = len(gap_products)
            logger.info(f"✓ Identified {len(gap_products)} opportunity gaps")
            
            # Step 3: Validate and score market potential
            logger.info("\n[STEP 3/5] Validating market potential...")
            scored_products = self.validator.validate_batch(gap_products)
            
            results['products_validated'] = len(scored_products)
            logger.info(f"✓ Validated {len(scored_products)} products")
            
            # Step 4: Generate markdown report
            logger.info("\n[STEP 4/5] Generating reports...")
            paths = config.get_paths()
            report_date = datetime.now().strftime("%Y%m%d")
            
            # Markdown report
            if config.enable_markdown:
                markdown_path = Path(paths['reports_dir']) / f"daily_report_{report_date}.md"
                self.reporter.generate_markdown_report(scored_products, str(markdown_path))
                logger.info(f"✓ Markdown report: {markdown_path}")
            
            # PDF report
            pdf_path = Path(paths['reports_dir']) / f"daily_report_{report_date}.pdf"
            self.pdf_generator.generate_pdf(scored_products, str(pdf_path))
            results['pdf_generated'] = True
            logger.info(f"✓ PDF report: {pdf_path}")
            results['report_generated'] = True
            
            # Step 5: Send to Telegram (if configured)
            if self.telegram_sender and config.enable_telegram:
                logger.info("\n[STEP 5/5] Sending report to Telegram...")
                
                # Get summary for message
                summary = self.reporter.get_report_summary(scored_products)
                
                # Send asynchronously
                success = asyncio.run(
                    self.telegram_sender.send_report(str(pdf_path), summary)
                )
                
                results['telegram_sent'] = success
                
                if success:
                    logger.info("✓ Report sent to Telegram")
                else:
                    logger.warning("Failed to send report to Telegram")
                    results['errors'].append("Telegram delivery failed")
            else:
                logger.info("\n[STEP 5/5] Skipping Telegram (not configured)")
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            results['errors'].append(str(e))
        
        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("\n" + "=" * 60)
            logger.info("Pipeline Execution Summary")
            logger.info("=" * 60)
            logger.info(f"Status: {'✓ SUCCESS' if results['success'] else '✗ FAILED'}")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Products Found: {results['products_found']}")
            logger.info(f"Gaps Identified: {results['gaps_identified']}")
            logger.info(f"Products Validated: {results['products_validated']}")
            logger.info(f"Report Generated: {results['report_generated']}")
            logger.info(f"PDF Generated: {results['pdf_generated']}")
            logger.info(f"Telegram Sent: {results['telegram_sent']}")
            
            if results['errors']:
                logger.warning(f"Errors: {', '.join(results['errors'])}")
            
            logger.info("=" * 60)
        
        return results


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("🚀 DOUYIN OPPORTUNITY FINDER")
    print("=" * 60 + "\n")
    
    # Check configuration - allow demo mode if API key is missing
    use_demo = os.getenv("USE_DEMO_DATA", "false").lower() == "true"
    
    if not config.tikhub_api_key or config.tikhub_api_key == 'your_tikhub_api_key_here':
        if use_demo:
            print("⚠️  TIKHUB_API_KEY not set - Running in DEMO MODE")
            print("   Using simulated data for testing (no API calls)")
            print("   Set USE_DEMO_DATA=false and add real API key for production")
            print()
        else:
            print("❌ ERROR: TikHub API key not configured!")
            print("   Please set TIKHUB_API_KEY in your .env file")
            print("   Get your key at: https://tikhub.io/")
            print("   OR set USE_DEMO_DATA=true to test with demo data")
            sys.exit(1)
    
    if not config.groq_api_key or config.groq_api_key == 'your_groq_api_key_here':
        print("⚠️  WARNING: Groq API key not configured!")
        print("   Using rule-based scoring only (no LLM analysis)")
        print("   Get FREE key at: https://console.groq.com/")
        print()
    
    # Run pipeline
    pipeline = DouyinOpportunityPipeline()
    results = pipeline.run()
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)


if __name__ == "__main__":
    main()
