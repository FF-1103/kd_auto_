#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2026/2/8 11:19
# @Author  : fzs
# @Site    :
# @File    : ydh_page.py
# @Software: PyCharm
import random
import time

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from page.base_page import BasePage
from utils.phone_utils import get_valid_phone
from utils.log_utils import get_logger
from utils.excel_utils import read_config

logger = get_logger("ydh_page")


class YdhPage(BasePage):
    # 元素定位
    # 取货码第一位
    SHELF_NUM_INPUT = (By.XPATH, '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div['
                                 '1]/form/div/div[1]/div[2]/div/div/div[1]/div[1]/div/div/div/input')
    # 序号
    SN_NUM_INPUT = (By.XPATH, '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div['
                              '1]/form/div/div[1]/div[2]/div/div/div[1]/div[1]/div/div/div/input')
    #  运单号
    YDH_INPUT = (By.XPATH, '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div[1]/form/div/div['
                           '1]/div[3]/div/div/div/input')
    # 手机号
    MOBILE_INPUT = (By.XPATH,
                    '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div[1]/form/div/div[1]/div['
                    '4]/div/div/div[1]/div[1]/input')
    # 提交
    SUBMIT_BTN = (By.XPATH,
                  '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div[1]/form/div/div[1]/div['
                  '6]/div/div/button')
    FORM_TAG = (By.TAG_NAME, "form")

    def __init__(self, driver):
        super().__init__(driver)
        self.login_url = read_config("ENV", "login_url")
        self.shelf_num = read_config("ENV", "shelf_num")

    def open_ydh_page(self):
        """打开运单号处理页"""
        if self.login_url not in self.driver.current_url:
            logger.info(f"访问目标页面：{self.login_url}")
            self.driver.get(self.login_url)
            self.wait_element_presence(self.FORM_TAG)
        else:
            logger.info("已在目标页面，跳过访问")

    def input_shelf_num(self):
        """输入货架号"""
        logger.info("输入货架号")
        try:
            shelf_elem = self.wait_element_clickable(self.SHELF_NUM_INPUT)
            self.force_clear_input(shelf_elem)
            self.shelf_num = random.randint(100, 9998)
            shelf_elem.send_keys(self.shelf_num)
            logger.info("货架号输入完成")
        except Exception as e:
            logger.error(f"输入货架号失败：{str(e)}", exc_info=True)
            raise

    def process_single_ydh(self, ydh):
        """处理单个运单号（整合try/except，异常时刷新页面）"""
        # 先校验入参，避免空值报错
        if not ydh or not isinstance(ydh, str):
            logger.error(f"运单号格式错误：{ydh}（必须是非空字符串）")
            raise ValueError(f"无效的运单号：{ydh}")

        try:
            mobile = get_valid_phone()
            logger.info(f"处理运单号：{ydh}（手机号：{mobile}）")

            # 运单号输入（移除原有try/except，整合到顶层）
            ydh_elem = self.wait_element_clickable(self.YDH_INPUT)
            time.sleep(0.2)  # 短等待，避免页面未加载完
            ydh_elem.clear()
            ydh_elem.send_keys(ydh)
            time.sleep(0.2)
            logger.info("运单号输入完成")
            # 手机号输入 + 提交（移除原有try/except，整合到顶层）
            mobile_elem = self.wait_element_clickable(self.MOBILE_INPUT)
            mobile_elem.clear()
            time.sleep(1)
            mobile_elem.clear()
            # 判断 mobile_elem 是否有值，有值则再次 clear
            if mobile_elem.get_attribute("value"):
                mobile_elem.clear()
                time.sleep(0.2)
            mobile_elem.send_keys(mobile)
            logger.info("手机号输入完成")
            self.random_sleep()
            # 提交
            submit_elem = self.wait_element_clickable(self.SUBMIT_BTN)
            submit_elem.click()
            self.random_sleep()
            logger.info("提交按钮已点击")

            # 额外等待
            time.sleep(0.2)

        except Exception as e:
            # 统一捕获所有异常，执行刷新页面逻辑
            logger.error(f"处理运单号{ydh}失败，执行页面刷新：{str(e)}", exc_info=True)
            self.save_screenshot(f"ydh_error_{ydh}.png")  # 保留截图
            # 刷新当前页面（核心新增逻辑）
            logger.info("开始刷新当前页面...")
            self.driver.get(self.login_url)
            self.wait_element_presence(self.FORM_TAG)
            # 抛出异常（可选，根据业务是否需要上层感知）
            raise
