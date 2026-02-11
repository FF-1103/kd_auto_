#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @Time    : 2026/2/8 11:20
# @Author  : fzs
# @Site    : 
# @File    : test_ydh_process.py
# @Software: PyCharm
import pytest
from page.ydh_page import YdhPage
from utils.excel_utils import read_ydh_from_excel
from utils.log_utils import get_logger

logger = get_logger("test_ydh_process")


class TestYdhProcess:
    def test_ydh_batch_process(self, driver):
        """批量处理运单号用例"""
        # 读取运单号
        ydh_list = read_ydh_from_excel()
        # 初始化页面
        ydh_page = YdhPage(driver)

        try:
            # 打开页面+输入货架号
            ydh_page.open_ydh_page()
            ydh_page.input_shelf_num()

            # 批量处理
            for idx, ydh in enumerate(ydh_list, 1):
                logger.info(f"\n========== 处理第 {idx}/{len(ydh_list)} 个运单号 ==========")
                ydh_page.process_single_ydh(ydh)

            logger.info("\n🎉 所有运单号处理完成！")
        except Exception as e:
            logger.error(f"批量处理失败：{str(e)}", exc_info=True)
            ydh_page.save_screenshot("main_error.png")
            raise

        # 交互提示
        input("按Enter键断开驱动连接（Chrome窗口可保留）...")
