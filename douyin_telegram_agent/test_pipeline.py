"""Test script to verify installation and basic functionality."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all imports."""
    print("Testing imports...")
    
    try:
        from config import config
        print("✓ Config loaded")
    except Exception as e:
        print(f"✗ Config failed: {e}")
        return False
    
    try:
        from agents.douyin_scout import DouyinScoutAgent
        from agents.tiktok_checker import TikTokCheckerAgent
        from agents.market_validator import MarketValidatorAgent
        from agents.reporter import ReporterAgent
        print("✓ All agents imported")
    except Exception as e:
        print(f"✗ Agent imports failed: {e}")
        return False
    
    try:
        from reporting.pdf_generator import PDFGenerator
        print("✓ PDF Generator imported")
    except Exception as e:
        print(f"✗ PDF Generator failed: {e}")
        return False
    
    try:
        from telegram_services.telegram_sender import TelegramSender
        print("✓ Telegram Sender imported")
    except Exception as e:
        print(f"✗ Telegram Sender failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    from config import config
    
    if not config.tikhub_api_key or config.tikhub_api_key == 'your_tikhub_api_key_here':
        print("⚠️  TikHub API key not configured (expected for testing)")
    else:
        print("✓ TikHub API key configured")
    
    if not config.groq_api_key or config.groq_api_key == 'your_groq_api_key_here':
        print("⚠️  Groq API key not configured (will use rule-based scoring)")
    else:
        print("✓ Groq API key configured")
    
    if config.telegram_bot_token and config.telegram_chat_id:
        if config.telegram_bot_token != 'your_telegram_bot_token_here':
            print("✓ Telegram configured")
        else:
            print("⚠️  Telegram not fully configured")
    else:
        print("⚠️  Telegram not configured")
    
    return True

def test_data_files():
    """Test data files exist."""
    print("\nTesting data files...")
    
    us_csv = Path(__file__).parent / "data" / "tiktok_products_us.csv"
    uk_csv = Path(__file__).parent / "data" / "tiktok_products_uk.csv"
    
    if us_csv.exists():
        print(f"✓ US products CSV exists ({us_csv})")
    else:
        print(f"✗ US products CSV missing: {us_csv}")
        return False
    
    if uk_csv.exists():
        print(f"✓ UK products CSV exists ({uk_csv})")
    else:
        print(f"✗ UK products CSV missing: {uk_csv}")
        return False
    
    return True

def test_checker_agent():
    """Test TikTok Checker Agent functionality."""
    print("\nTesting TikTok Checker Agent...")
    
    from agents.tiktok_checker import TikTokCheckerAgent
    from config import config
    
    paths = config.get_paths()
    
    try:
        checker = TikTokCheckerAgent(
            us_csv_path=paths['us_csv'],
            uk_csv_path=paths['uk_csv']
        )
        print(f"✓ Checker initialized with {len(checker.all_tiktok_products)} products")
        
        # Test translation
        test_title = "智能保温杯"
        translated = checker.translate_title(test_title)
        print(f"✓ Translation test: '{test_title}' → '{translated}'")
        
        # Test similarity
        sim = checker.calculate_similarity("wireless earbuds", "wireless earbuds pro")
        print(f"✓ Similarity test: {sim:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Checker test failed: {e}")
        return False

def test_reporter_agent():
    """Test Reporter Agent functionality."""
    print("\nTesting Reporter Agent...")
    
    from agents.reporter import ReporterAgent
    
    try:
        reporter = ReporterAgent()
        
        # Create sample product data
        sample_products = [
            {
                'english_title': 'Test Product 1',
                'hot_count': 50000,
                'overall_score': 8.5,
                'market_analysis': {
                    'content_angle': 'Show before/after transformation',
                    'notes': 'Great potential'
                },
                'score_breakdown': {
                    'competition': 8,
                    'sentiment': 9,
                    'cultural_fit': 8,
                    'visual_appeal': 9,
                    'price_point': 8
                }
            }
        ]
        
        # Generate test report
        report = reporter.generate_markdown_report(sample_products)
        
        if report and len(report) > 100:
            print(f"✓ Report generated ({len(report)} chars)")
            return True
        else:
            print("✗ Report generation failed")
            return False
            
    except Exception as e:
        print(f"✗ Reporter test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("DOUYIN OPPORTUNITY FINDER - INSTALLATION TEST")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Data Files", test_data_files),
        ("Checker Agent", test_checker_agent),
        ("Reporter Agent", test_reporter_agent),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Configure .env with your API keys")
        print("2. Run: python main.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
