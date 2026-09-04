import logging.handlers

class botLogger:
    def __init__(self, parent=None):
        self.logger = logging.getLogger('[trBit]')
        self.filename = 'log/trBit.log'
        self.fileMaxByte = 1024 * 1024 * 100 #100MB
        self.fileHandler = logging.handlers.RotatingFileHandler(self.filename, maxBytes=self.fileMaxByte, backupCount=10)
        self.fomatter = logging.Formatter('[%(levelname)s|[trBit]:%(lineno)s] %(asctime)s > %(message)s')

        self.fileHandler.setFormatter(self.fomatter)
        self.logger.addHandler(self.fileHandler)

        self.logger.setLevel(logging.DEBUG)

    def debug(self, str):
        self.logger.debug(str)

    def info(self, str):
        self.logger.info(str)

    def warning(self, str):
        self.logger.warning(str)

    def error(self, str):
        self.logger.error(str)

    def critical(self, str):
        self.logger.critical(str)


if __name__ == '__main__':
    log = botLogger()

    log.error("메롱")