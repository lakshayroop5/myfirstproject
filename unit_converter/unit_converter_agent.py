#!/usr/bin/env python3
"""
Unit Converter Agent - Main entry point with functional composition.

Example usage:
    python unit_converter_agent.py --exp "10 meters to feet, 100 celsius to fahrenheit"
"""

import sys
import asyncio
import argparse
import logging
from pathlib import Path
from functools import partial

sys.path.insert(0, str(Path(__file__).parent))

from pipeline_executor.application.unit_converter.unit_converter_controller import UnitConverterController
from pipeline_executor.framework.models import PipelineContext
from pipeline_executor.framework.colored_logging import EmojiLogger
from pipeline_executor.framework.output_formatter import OutputFormatter

logger = EmojiLogger(__name__)


def parse_arguments():
    """Parse command line arguments using functional validation."""
    parser = argparse.ArgumentParser(
        description='Unit Converter Agent - Convert between various units',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --exp "10 meters to feet"
  %(prog)s --exp "100 celsius to fahrenheit, 5 km to miles"
  %(prog)s --exp "500 grams to pounds" --debug
  %(prog)s --exp "2 hours to minutes" --output-format json

Supported unit categories:
  - Length: meter, km, mile, foot, inch, cm, mm, yard
  - Weight: kg, gram, pound, ounce, ton
  - Temperature: celsius, fahrenheit, kelvin
  - Volume: liter, gallon, cup, quart, pint, ml
  - Time: second, minute, hour, day, week, month, year
  - Speed: m/s, km/h, mph, knots
        """
    )
    
    parser.add_argument('--exp', type=str, required=True,
                       help='Conversion expressions (comma-separated)')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Maximum execution time in seconds (default: 10)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--output-format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress stage-by-stage logging')
    
    return parser.parse_args()


def configure_logging(args):
    """Configure logging using functional predicates."""
    level_map = [
        (lambda a: a.debug, logging.DEBUG),
        (lambda a: a.quiet, logging.WARNING),
        (lambda a: True, logging.INFO)  # Default
    ]
    
    # Functional pattern matching for log level
    matched = list(filter(lambda mapping: mapping[0](args), level_map))
    log_level = matched[0][1] if matched else logging.INFO
    
    logging.basicConfig(level=log_level, format='%(message)s')


def display_banner(args):
    """Display banner using functional composition."""
    should_display = lambda: not args.quiet
    
    banner_lines = [
        "=" * 70,
        "🔄 UNIT CONVERTER AGENT",
        "=" * 70,
        f"📝 Conversions: {args.exp}",
        f"⏱️  Timeout: {args.timeout}s",
        f"🐛 Debug: {args.debug}",
        "=" * 70
    ]
    
    log_line = lambda line: logger.logger.info(line)
    _ = should_display() and list(map(log_line, banner_lines))


async def execute_pipeline(controller, context, args):
    """Execute pipeline with functional error handling."""
    logger.pipeline_start()
    result_context = await controller.execute(context)
    logger.pipeline_complete()
    
    return result_context


def display_results(result_context, args):
    """Display results using functional composition."""
    formatter = OutputFormatter(args.output_format)
    output = formatter.format(result_context)
    
    should_show_header = lambda: not args.quiet
    header_lines = ["\n" + "=" * 70, "📊 RESULTS", "=" * 70]
    
    log_line = lambda line: logger.logger.info(line)
    _ = should_show_header() and list(map(log_line, header_lines))
    
    print(output)


def calculate_exit_code(result_context):
    """Calculate exit code using functional predicates."""
    has_result = lambda ctx: ctx.result is not None
    get_success_rate = lambda ctx: ctx.result.insights.success_rate if has_result(ctx) else 0
    is_successful = lambda rate: rate > 0
    
    return 0 if is_successful(get_success_rate(result_context)) else 1


async def main():
    """Main application entry point using functional composition."""
    args = parse_arguments()
    configure_logging(args)
    display_banner(args)
    
    try:
        # Create controller and context
        controller = UnitConverterController(timeout=args.timeout, debug=args.debug)
        context = PipelineContext(input_data=args.exp, timeout=args.timeout, debug=args.debug)
        
        # Execute pipeline
        result_context = await execute_pipeline(controller, context, args)
        
        # Display results
        display_results(result_context, args)
        
        # Cleanup
        await controller.cleanup()
        
        # Exit with appropriate code
        sys.exit(calculate_exit_code(result_context))
        
    except KeyboardInterrupt:
        logger.logger.warning("\n⚠️  Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.logger.error(f"❌ Fatal error: {e}")
        _ = args.debug and __import__('traceback').print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
