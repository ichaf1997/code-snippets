import logging

def config_log(loglevel: int = 20):
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    logging.basicConfig(
        level=loglevel,
        format=(
            "[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s -"
            " %(message)s"
        ),
        handlers=[stdout_handler],
    )

config_log(0)
logger = logging.getLogger(__name__)
logger.debug("This is a debug message")