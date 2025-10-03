import logging
import sys
import os

# Create and export the main project logger instance for easy import
# Note: It's best practice to call setup_logger once in the main entry point
# of your application to ensure all configuration is done after parsing CLI args.
log = logging.getLogger('cse140l')
log.setLevel(logging.INFO)

def setup_logger(log_file: str = None, level=logging.INFO):
    """
    Sets up a project-wide logger, outputting to a file if provided,
    otherwise defaulting to stdout.

    Args:
        log_file (str, optional): Path to the log file. If None, logs to stdout.
        level (int): The minimum logging level (e.g., logging.DEBUG, logging.INFO).
    """
    # Get the existing logger instance
    logger = logging.getLogger('cse140l')
    logger.setLevel(level)

    # 1. Clear any existing handlers to prevent duplicates on re-configuration
    if logger.handlers:
        logger.handlers.clear()

    # 2. Define the Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s | %(name)s.%(module)s.%(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 3. Define the Handler (File or Stream)
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Use FileHandler for disk output (appends to file)
        handler = logging.FileHandler(log_file, mode='a')
    else:
        # Default to StreamHandler for stdout output
        handler = logging.StreamHandler(sys.stdout)

    handler.setLevel(level)
    handler.setFormatter(formatter)

    # 4. Add the handler to the logger
    logger.addHandler(handler)


# Initial setup to ensure a logger exists, even before CLI args are parsed
if not log.handlers:
    setup_logger()