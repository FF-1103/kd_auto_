#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @Time    : 2026/2/8 11:22
# @Author  : fzs
# @Site    : 
# @File    : excel_utils.py
# @Software: PyCharm
import os
import sys
import pandas as pd
from configparser import ConfigParser


# ========== 修复：移除顶部的get_logger导入 ==========
# 原代码：from utils.log_utils import get_logger  → 删掉这行

def read_config(section, key):
    """读取config.ini配置"""
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.ini")
    config.read(config_path, encoding="utf-8")
    return config.get(section, key)


def get_excel_path():
    """获取Excel文件路径（适配exe/脚本运行）"""
    # ========== 修复：在函数内导入logger ==========
    from utils.log_utils import get_logger
    logger = get_logger("excel_utils")

    if hasattr(sys, '_MEIPASS'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(__file__))
    excel_path = os.path.join(base_dir, "data", "dh.xlsx")
    if not os.path.exists(excel_path):
        logger.error(f"未找到dh.xlsx！路径：{excel_path}")
        raise FileNotFoundError(f"❌ 未找到dh.xlsx！请将文件放在：{excel_path}")
    return excel_path


def read_ydh_from_excel():
    """读取运单号（重构后）"""
    # ========== 修复：在函数内导入logger ==========
    from utils.log_utils import get_logger
    logger = get_logger("excel_utils")

    try:
        excel_path = get_excel_path()
        df = pd.read_excel(excel_path)

        # 检查核心列
        target_cols = ["运单号", "YD", "ydh", "单号"]
        waybill_col = None
        for col in target_cols:
            if col in df.columns:
                waybill_col = col
                break
        if not waybill_col:
            raise ValueError(f"Excel中未找到运单号相关列（支持：{', '.join(target_cols)}）")

        # 清洗数据
        df_clean = df.dropna(subset=[waybill_col]).dropna(how='all')
        ydh_list = df_clean[waybill_col].unique().tolist()

        if not ydh_list:
            raise ValueError("Excel中无有效运单号")

        logger.info(f"成功读取Excel，共{len(ydh_list)}个唯一运单号")
        return ydh_list
    except Exception as e:
        logger.error(f"读取Excel失败：{str(e)}", exc_info=True)
        raise
