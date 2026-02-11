#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @Time    : 2026/2/8 11:20
# @Author  : fzs
# @Site    : 
# @File    : conftest.py
# @Software: PyCharm
import pytest
from utils.driver_utils import get_reusable_driver
from utils.log_utils import get_logger

logger = get_logger("conftest")


@pytest.fixture(scope="session")
def driver():
    """全局驱动夹具"""
    driver = get_reusable_driver()
    yield driver
    logger.info("断开驱动连接")
    driver.quit()
