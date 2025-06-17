import logging.config

def setup_logging():
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters":{
            "default":{
                "format":"[%(asctime)s [%(levelname)s] %(name)s: %(message)s]",
                "datefmt": "%Y-%m-%d %H-%M-%S"
            },
        },
        "handlers":{
            "console":{
                "class":"logging.StreamHandler",
                "formatter": "default",
            },
            "file":{
                "class": "logging.FileHandler",
                "filename":"app.log",
                "encoding": "utf-8",
                "formatter": "default",
            }

        },
        "root":{
            "level": "INFO",
            "handlers": ["console","file"]
        }
    }
    logging.config.dictConfig(config=config)