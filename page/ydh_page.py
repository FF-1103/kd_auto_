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
    SHELF_NUM_INPUT = (By.XPATH, '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div['
                                 '1]/form/div/div[1]/div[2]/div/div/div[1]/div[1]/div/div/div/input')
    SN_NUM_INPUT = (By.XPATH,
                    '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div[1]/form/div/div[1]/div['
                    '2]/div/div/div[1]/div[3]/div/div/div/input')
    YDH_INPUT = (By.XPATH, '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div[1]/form/div/div['
                           '1]/div[3]/div/div/div/input')
    MOBILE_INPUT = (By.XPATH,
                    '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div[1]/form/div/div[1]/div['
                    '4]/div/div/div[1]/div[1]/input')
    SUBMIT_BTN = (By.XPATH,
                  '/html/body/div[1]/section/section/section/div/div[1]/div/main/div/div[1]/form/div/div[1]/div['
                  '6]/div/div/button')
    FORM_TAG = (By.TAG_NAME, "form")

    def __init__(self, driver):
        super().__init__(driver)
        self.sn_num = read_config("ENV", "sn_num")
        self.login_url = read_config("ENV", "login_url")
        self.shelf_num = read_config("ENV", "shelf_num")

    def open_ydh_page(self):
        if self.login_url not in self.driver.current_url:
            logger.info(f"访问目标页面：{self.login_url}")
            self.driver.get(self.login_url)
            self.wait_element_presence(self.FORM_TAG)
        else:
            logger.info("已在目标页面，跳过访问")

    def input_shelf_num(self):
        logger.info("输入货架号")
        try:
            shelf_elem = self.wait_element_clickable(self.SHELF_NUM_INPUT)
            self.force_clear_input(shelf_elem)
            self.shelf_num = random.randint(100, 9998)
            shelf_elem.send_keys(str(self.shelf_num))
            logger.info("货架号输入完成")
        except Exception as e:
            logger.error(f"输入货架号失败：{str(e)}", exc_info=True)
            raise

    def input_sn_num(self):
        logger.info("输入序号")
        try:
            sn_elem = self.wait_element_clickable(self.SN_NUM_INPUT)
            self.force_clear_input(sn_elem)
            self.sn_num = random.randint(100, 9998)
            sn_elem.send_keys(str(self.sn_num))
            logger.info("序号输入完成")
        except Exception as e:
            logger.error(f"输入序号失败：{str(e)}", exc_info=True)
            raise

    def process_single_ydh(self, ydh):
        if not ydh or not isinstance(ydh, str):
            logger.error(f"运单号格式错误：{ydh}（必须是非空字符串）")
            raise ValueError(f"无效的运单号：{ydh}")

        try:
            mobile = get_valid_phone()
            logger.info(f"处理运单号：{ydh}（手机号：{mobile}）")

            ydh_elem = self.wait_element_clickable(self.YDH_INPUT)
            time.sleep(0.2)
            ydh_elem.clear()
            ydh_elem.send_keys(ydh)
            time.sleep(0.2)
            logger.info("运单号输入完成")

            mobile_elem = self.wait_element_clickable(self.MOBILE_INPUT)
            mobile_elem.clear()
            time.sleep(1)
            mobile_elem.clear()
            if mobile_elem.get_attribute("value"):
                mobile_elem.clear()
                time.sleep(0.2)
            mobile_elem.send_keys(mobile)
            logger.info("手机号输入完成")
            self.random_sleep()

            # 验证页面上输入的值是否与预期一致
            actual_ydh = ydh_elem.get_attribute("value")
            actual_mobile = mobile_elem.get_attribute("value")
            
            if actual_ydh != ydh:
                logger.error(f"运单号验证失败：预期[{ydh}]，实际[{actual_ydh}]")
                raise ValueError(f"运单号输入验证失败：预期[{ydh}]，实际[{actual_ydh}]")
            
            if actual_mobile != mobile:
                logger.error(f"手机号验证失败：预期[{mobile}]，实际[{actual_mobile}]")
                raise ValueError(f"手机号输入验证失败：预期[{mobile}]，实际[{actual_mobile}]")
            
            logger.info("输入验证通过，准备点击提交")

            submit_elem = self.wait_element_clickable(self.SUBMIT_BTN)
            submit_elem.click()
            self.random_sleep()
            logger.info("提交按钮已点击")

            time.sleep(0.2)

        except Exception as e:
            logger.error(f"处理运单号{ydh}失败，执行页面刷新：{str(e)}", exc_info=True)
            self.save_screenshot(f"ydh_error_{ydh}.png")
            logger.info("开始刷新当前页面...")
            self.driver.get(self.login_url)
            self.wait_element_presence(self.FORM_TAG)
            raise
