#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @Time    : 2026/2/8 11:21
# @Author  : fzs
# @Site    : 
# @File    : driver_utils.py
# @Software: PyCharm
import os
import sys
import time
import subprocess
import psutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from utils.log_utils import get_logger
from utils.excel_utils import read_config

logger = get_logger("driver_utils")


def is_chrome_debug_running():
    """检查调试端口Chrome是否运行"""
    debug_port = read_config("ENV", "chrome_debug_port")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'chrome' in proc.name().lower() and f'{debug_port}' in ' '.join(proc.cmdline()):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def start_chrome_with_debug():
    """启动带调试端口的Chrome"""
    debug_port = read_config("ENV", "chrome_debug_port")
    chrome_profile_dir = read_config("PATH", "chrome_profile_dir")
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    chrome_path = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_path = path
            break
    if not chrome_path:
        raise Exception("未找到Chrome浏览器！")

    # 启动Chrome
    try:
        subprocess.Popen([
            chrome_path,
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={os.path.join(os.path.dirname(os.path.dirname(__file__)), chrome_profile_dir)}",
            "--start-maximized"
        ])
        logger.info(f"启动Chrome（调试端口{debug_port}），等待5秒...")
        time.sleep(5)
    except Exception as e:
        logger.error(f"启动Chrome失败：{str(e)}", exc_info=True)
        raise


def get_reusable_driver():
    """获取复用的Chrome驱动（重构后）"""
    debug_port = read_config("ENV", "chrome_debug_port")
    # 启动Chrome（若未运行）
    if not is_chrome_debug_running():
        start_chrome_with_debug()

    # 驱动路径
    if hasattr(sys, '_MEIPASS'):
        driver_path = os.path.join(os.path.dirname(sys.executable), "chromedriver.exe")
    else:
        driver_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chromedriver.exe")
    if not os.path.exists(driver_path):
        raise Exception(f"未找到ChromeDriver！路径：{driver_path}")

    # 连接Chrome
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    service = Service(executable_path=driver_path)

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(5)
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
        logger.info("成功连接Chrome实例")
        return driver
    except Exception as e:
        logger.error(f"连接Chrome失败：{str(e)}", exc_info=True)
        raise
