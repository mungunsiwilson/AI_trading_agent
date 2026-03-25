"""
Test script to verify the pipeline components work correctly.
Run this after installation to ensure everything is configured properly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from config import Config
        print("✓ Config module imported")
    except Exception as e:
        print(f"✗ Config module failed: {e}")
        return False
    
    try:
        from utils import setup_logging
        print("✓ Utils module imported")
    except Exception as e:
        print(f"✗ Utils module failed: {e}")
        return False
    
    try:
        from agents import (
            DouyinScoutAgent,
            TikTokCheckerAgent,
            MarketValidatorAgent,
            ReporterAgent
        )
        print("✓ All agent modules imported")
    except Exception as e:
        print(f"✗ Agent modules failed: {e}")
        return False
    
    return True


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from config import Config
        config = Config()
        
        # Check required properties
        assert hasattr(config, 'tikhub_api_key'), "Missing tikhub_api_key"
        assert hasattr(config, 'fuzzy_match_threshold'), "Missing fuzzy_match_threshold"
        assert hasattr(config, 'schedule_hour'), "Missing schedule_hour"
        
        print(f"✓ Configuration loaded successfully")
        print(f"  - TikHub API Key: {'Set' if config.tikhub_api_key else 'Not set (using example)'}")
        print(f"  - Fuzzy Match Threshold: {config.fuzzy_match_threshold}")
        print(f"  - Schedule: {config.schedule_hour:02d}:{config.schedule_minute:02d} {config.timezone}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_data_files():
    """Test that data files exist."""
    print("\nTesting data files...")
    
    from config import Config
    config = Config()
    
    # Check TikTok CSV files
    if config.tiktok_products_us_csv.exists():
        print(f"✓ US TikTok database found: {config.tiktok_products_us_csv}")
    else:
        print(f"⚠ US TikTok database not found: {config.tiktok_products_us_csv}")
    
    if config.tiktok_products_uk_csv.exists():
        print(f"✓ UK TikTok database found: {config.tiktok_products_uk_csv}")
    else:
        print(f"⚠ UK TikTok database not found: {config.tiktok_products_uk_csv}")
    
    # Check directories exist
    log_dir = config.log_file_path.parent
    if log_dir.exists():
        print(f"✓ Logs directory exists: {log_dir}")
    else:
        print(f"✓ Creating logs directory: {log_dir}")
        log_dir.mkdir(parents=True, exist_ok=True)
    
    return True


def test_agents_initialization():
    """Test that agents can be initialized."""
    print("\nTesting agent initialization...")
    
    try:
        from config import Config
        from agents import (
            DouyinScoutAgent,
            TikTokCheckerAgent,
            MarketValidatorAgent,
            ReporterAgent
        )
        
        config = Config()
        
        # Initialize each agent
        scout = DouyinScoutAgent(config)
        print("✓ DouyinScoutAgent initialized")
        
        checker = TikTokCheckerAgent(config)
        print("✓ TikTokCheckerAgent initialized")
        
        validator = MarketValidatorAgent(config)
        print("✓ MarketValidatorAgent initialized")
        
        reporter = ReporterAgent(config)
        print("✓ ReporterAgent initialized")
        
        return True
    except Exception as e:
        print(f"✗ Agent initialization failed: {e}")
        return False


def test_checker_agent():
    """Test TikTokCheckerAgent with sample data."""
    print("\nTesting TikTokCheckerAgent...")
    
    try:
        from config import Config
        from agents import TikTokCheckerAgent
        
        config = Config()
        checker = TikTokCheckerAgent(config)
        
        # Test translation
        chinese_title = "好物推荐 便携式LED灯"
        english_title = checker.translate_title(chinese_title)
        print(f"  Translation test: '{chinese_title}' → '{english_title}'")
        
        # Test fuzzy matching
        ratio = checker.fuzzy_match("LED light", "led desk lamp")
        print(f"  Fuzzy match test: 'LED light' vs 'led desk lamp' = {ratio:.2f}")
        
        # Load databases
        if checker.load_tiktok_databases():
            print(f"✓ Loaded {len(checker.tiktok_products)} TikTok products")
        else:
            print("⚠ No TikTok databases loaded (expected if CSV files don't exist)")
        
        return True
    except Exception as e:
        print(f"✗ Checker agent test failed: {e}")
        return False


def test_reporter_agent():
    """Test ReporterAgent with sample data."""
    print("\nTesting ReporterAgent...")
    
    try:
        from config import Config
        from agents import ReporterAgent
        import json
        
        config = Config()
        reporter = ReporterAgent(config)
        
        # Sample validated product data
        sample_products = [
            {
                'title_chinese': '神奇清洁剂',
                'title_english': 'Magic Cleaning Paste',
                'hot_count': 150000,
                'market_fit_score': 8.5,
                'component_scores': {
                    'competition': 1.8,
                    'sentiment': 1.5,
                    'cultural_fit': 1.7,
                    'visual_appeal': 1.8,
                    'price_point': 1.7
                },
                'justifications': {
                    'competition': 'Low competition',
                    'sentiment': 'Neutral sentiment',
                    'cultural_fit': 'Good cultural fit',
                    'visual_appeal': 'High visual appeal',
                    'price_point': 'Ideal price point'
                },
                'amazon_summary': {'avg_price': 19.99},
                'reddit_summary': {'total_mentions': 5}
            }
        ]
        
        # Generate report
        test_data = {
            'status': 'success',
            'total_validated': 1,
            'validated_products': sample_products,
            'timestamp': '2024-01-01T00:00:00'
        }
        
        report = reporter.generate_report(json.dumps(test_data))
        
        if report and not report.startswith('# Error'):
            print("✓ Report generated successfully")
            print(f"  Report length: {len(report)} characters")
            return True
        else:
            print(f"✗ Report generation failed: {report}")
            return False
            
    except Exception as e:
        print(f"✗ Reporter agent test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Douyin Opportunity Finder - Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Data Files", test_data_files()))
    results.append(("Agent Initialization", test_agents_initialization()))
    results.append(("Checker Agent", test_checker_agent()))
    results.append(("Reporter Agent", test_reporter_agent()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Configure your .env file with API keys")
        print("2. Update TikTok CSV files weekly")
        print("3. Run: python main.py")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")
    
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
