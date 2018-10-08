
# Author: Adam Kobi <AdamKobi@Gmail.Com>

from lib.gpssport_crawler import GPSSportCrawler
from lib.data_sorter import DataSorter
from lib.utils import *


if __name__ == "__main__":
    logger = init_logging('dataSorter')
    cfg = get_cfg('config.yml')
    sorter = DataSorter(cfg, logger)
    # days_to_download = sorter.get_last_date()
    # if days_to_download is not None:
        # crawler = GPSSportCrawler(cfg, logger, days_to_download)
    sorter.load_from_csv('injuries')
    sorter.load_from_csv('players')
    sorter.load_from_csv('gps_data')
        # data = crawler.download()
        # sorter.load_from_crawler(data)