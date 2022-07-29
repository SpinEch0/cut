import json
import logging
from logging import config
import os


# The logging leaves can be accesses without
# importing the logging module in other modules.
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
NOTSET = logging.NOTSET

CMDLINE_LOG_LEVELS = ["info", "debug"]

DEBUG_ANALYZER = logging.DEBUG_ANALYZER = 15  # type: ignore
logging.addLevelName(DEBUG_ANALYZER, "DEBUG_ANALYZER")


class CCLogger(logging.Logger):
    def __init__(self, name, level=NOTSET):
        super(CCLogger, self).__init__(name, level)

    def debug_analyzer(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.DEBUG_ANALYZER):
            self._log(logging.DEBUG_ANALYZER, msg, args, **kwargs)


logging.setLoggerClass(CCLogger)

data_files_dir_path = os.environ.get("CC_DATA_FILES_DIR", "")
DEFAULT_LOG_CFG_FILE = os.path.join(data_files_dir_path, "config", "logger.conf")


# Default config which can be used if reading log config from a
# file fails.
DEFAULT_LOG_CONFIG = """{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "brief": {
      "format": "[%(asctime)s][%(levelname)s] - %(message)s",
      "datefmt": "%Y-%m-%d %H:%M"
    },
    "precise": {
      "format": "[%(levelname)s] [%(asctime)s] {%(name)s} [%(process)d] \
<%(thread)d> - %(filename)s:%(lineno)d %(funcName)s() - %(message)s",
      "datefmt": "%Y-%m-%d %H:%M"
    }
  },
  "handlers": {
    "default": {
      "level": "INFO",
      "formatter": "brief",
      "class": "logging.StreamHandler"
    }
  },
  "loggers": {
    "": {
      "handlers": ["default"],
      "level": "INFO",
      "propagate": true
    }
  }
}"""


try:
    with open(DEFAULT_LOG_CFG_FILE, "r", encoding="utf-8", errors="ignore") as dlc:
        DEFAULT_LOG_CONFIG = dlc.read()
except IOError as ex:
    print(ex)
    print("Failed to load logger configuration. Using built-in config.")


def get_logger(name):
    """
    Return a logger instance if already exists with the given name.
    """
    return logging.getLogger(name)


def validate_loglvl(log_level):
    """
    Should return a valid log level name
    """
    log_level = log_level.upper()

    if log_level not in {lev.upper() for lev in CMDLINE_LOG_LEVELS}:
        return "INFO"

    return log_level


def setup_logger(log_level=None, stream=None):
    """
    Modifies the log configuration.
    Overwrites the log levels for the loggers and handlers in the
    configuration.
    Redirects the output of all handlers to the given stream. Short names can
    be given (stderr -> ext://sys.stderr, 'stdout' -> ext://sys.stdout).
    """

    LOG_CONFIG = json.loads(DEFAULT_LOG_CONFIG)
    if log_level:
        log_level = validate_loglvl(log_level)

        print("loglevel ", log_level)
        loggers = LOG_CONFIG.get("loggers", {})
        for k in loggers.keys():
            LOG_CONFIG["loggers"][k]["level"] = log_level

        handlers = LOG_CONFIG.get("handlers", {})
        for k in handlers.keys():
            LOG_CONFIG["handlers"][k]["level"] = log_level
            if log_level == "DEBUG" or log_level == "DEBUG_ANALYZER":
                LOG_CONFIG["handlers"][k]["formatter"] = "precise"

    if stream:
        if stream == "stderr":
            stream = "ext://sys.stderr"
        elif stream == "stdout":
            stream = "ext://sys.stdout"

        handlers = LOG_CONFIG.get("handlers", {})
        for k in handlers.keys():
            handler = LOG_CONFIG["handlers"][k]
            if "stream" in handler:
                handler["stream"] = stream

    config.dictConfig(LOG_CONFIG)
