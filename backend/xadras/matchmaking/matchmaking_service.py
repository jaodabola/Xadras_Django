import os
import sys
import time
import logging
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), 'logs')
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'matchmaking_service.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('matchmaking_service')

# Matchmaking interval in seconds
MATCHMAKING_INTERVAL = 10


def log_matchmaking_result(result):
    """Log the result of a matchmaking run"""
    if not result or not result.stdout:
        return

    try:
        # Parse the JSON output from the management command
        output = json.loads(result.stdout)
        if 'matches' in output:
            for match in output['matches']:
                logger.info(
                    "Match created",
                    extra={
                        'event': 'match_created',
                        'game_id': match.get('game_id'),
                        'white_player': match.get('white_player'),
                        'black_player': match.get('black_player'),
                        'status': 'success'
                    }
                )
        elif 'message' in output:
            logger.info(
                output['message'],
                extra={'event': 'matchmaking_status'}
            )
    except json.JSONDecodeError:
        logger.warning(
            "Failed to parse matchmaking output",
            extra={
                'event': 'parse_error',
                # Log first 200 chars to avoid huge logs
                'output': result.stdout[:200]
            }
        )


def run_matchmaking():
    """Run the matchmaking command with enhanced logging"""
    logger.info("Starting matchmaking service",
                extra={'event': 'service_start'})

    while True:
        try:
            logger.debug("Running matchmaking cycle",
                         extra={'event': 'cycle_start'})

            # Run the matchmake command with JSON output
            result = subprocess.run(
                ['python3', 'manage.py', 'matchmake', '--format=json'],
                capture_output=True,
                text=True
            )

            # Log the result if there was output
            if result.stdout.strip():
                log_matchmaking_result(result)

            # Log errors if any
            if result.stderr:
                err = result.stderr.strip()
                if 'Not enough players in queue' in err or 'not enough players in queue' in err:
                    logger.info(err, extra={'event': 'matchmaking_status'})
                else:
                    logger.error(
                        "Error in matchmaking command",
                        extra={
                            'event': 'command_error',
                            'error': err
                        }
                    )

            # Wait for the next interval
            time.sleep(MATCHMAKING_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Matchmaking service stopped by user",
                        extra={'event': 'service_stop'})
            break

        except Exception as e:
            logger.error(
                "Unexpected error in matchmaking service",
                extra={
                    'event': 'service_error',
                    'error': str(e),
                    'exception_type': type(e).__name__
                },
                exc_info=True
            )
            time.sleep(5)  # Wait before retrying on error


if __name__ == "__main__":
    try:
        logger.info("Starting matchmaking service",
                    extra={'event': 'service_startup'})
        run_matchmaking()
    except Exception as e:
        logger.critical(
            "Fatal error in matchmaking service",
            extra={
                'event': 'fatal_error',
                'error': str(e),
                'exception_type': type(e).__name__
            },
            exc_info=True
        )
        sys.exit(1)
