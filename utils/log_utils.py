#!/usr/bin/env python 
# -*- coding: utf-8 -*-
import logging
import os
import sys
from datetime import datetime


def _get_log_dir():
    """获取日志目录（适配打包后的路径）"""
    if getattr(sys, 'frozen', False):
        # 打包后：日志目录在 dist 同级的 log 文件夹
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境：项目根目录
        base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_dir, "log")


LOG_DIR = _get_log_dir()
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, f"ydh_auto_{datetime.now().strftime('%Y%m%d')}.log")

# 配置日志（只输出到文件，不输出到控制台）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)


def get_logger(name):
    return logging.getLogger(name)
