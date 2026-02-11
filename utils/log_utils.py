#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @Time    : 2026/2/8 11:22
# @Author  : fzs
# @Site    : 
# @File    : log_utils.py
# @Software: PyCharm
import logging
import os
from datetime import datetime
from configparser import ConfigParser  # 新增：直接导入ConfigParser


def _read_config(section, key):
    """内部函数：读取配置（避免循环导入）"""
    config = ConfigParser()
    # 确认配置文件路径是 项目根目录/config/config.ini
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.ini")
    # 新增：打印路径，便于排查
    print(f"读取配置文件路径：{config_path}")
    config.read(config_path, encoding="utf-8")
    return config.get(section, key)


# 读取日志目录配置（用内部函数）
LOG_DIR = _read_config("PATH", "log_dir")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, f"ydh_auto_{datetime.now().strftime('%Y%m%d')}.log")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)


def get_logger(name):
    return logging.getLogger(name)
