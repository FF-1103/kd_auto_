#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2026/2/8 11:19
# @Author  : fzs
# @Site    :
# @File    : base_page.py
# @Software: PyCharm
import time
import random
import os
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from utils.log_utils import get_logger
from utils.excel_utils import read_config

logger = get_logger("base_page")


class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.sleep_min = float(read_config("SLEEP", "sleep_min"))
        self.sleep_max = float(read_config("SLEEP", "sleep_max"))
        
        # 根据是否打包确定截图目录（支持相对路径）
        import sys
        screenshot_dir = read_config("PATH", "screenshot_dir")
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(__file__))
        self.screenshot_dir = os.path.join(base_dir, screenshot_dir)
        
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)

    def wait_element_clickable(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(locator))

    def wait_element_presence(self, locator, timeout=15):
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))

    def force_clear_input(self, input_elem):
        input_elem.send_keys(Keys.CONTROL, 'a')
        input_elem.send_keys(Keys.BACKSPACE)
        time.sleep(0.2)
        logger.debug("强制清空输入框完成")

    def random_sleep(self):
        sleep_t = random.uniform(self.sleep_min, self.sleep_max)
        logger.info(f"随机睡眠 {sleep_t:.2f} 秒")
        time.sleep(sleep_t)

    def save_screenshot(self, filename):
        screenshot_path = os.path.join(self.screenshot_dir, filename)
        self.driver.save_screenshot(screenshot_path)
        logger.info(f"错误截图已保存：{screenshot_path}")
        return screenshot_path
