#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @Time    : 2026/2/8 11:22
# @Author  : fzs
# @Site    : 
# @File    : phone_utils.py
# @Software: PyCharm
import random
import re
from utils.log_utils import get_logger

logger = get_logger("phone_utils")


def generate_random_phone_number():
    mobile_prefixes = ['142']
    prefix = random.choice(mobile_prefixes)
    suffix = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    return prefix + suffix


def get_valid_phone():
    pattern = r'^1[3-9]\d{9}$'
    while True:
        phone = generate_random_phone_number()
        if re.match(pattern, phone):
            logger.debug(f"生成有效手机号：{phone}")
            return phone
