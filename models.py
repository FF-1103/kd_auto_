#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @Time    : 2026/2/11 17:44
# @Author  : fzs
# @Site    : 
# @File    : models.py
# @Software: PyCharm
from sqlalchemy import create_engine, Column, BigInteger, String, Enum, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os
import sys
from configparser import ConfigParser
from passlib.context import CryptContext


def read_config(section, key):
    """读取config.ini配置（适配打包后的路径）"""
    config = ConfigParser()
    if getattr(sys, 'frozen', False):
        # 打包后：exe所在目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境：当前文件所在目录
        base_dir = os.path.dirname(__file__)
    config_path = os.path.join(base_dir, "config", "config.ini")
    config.read(config_path, encoding="utf-8")
    return config.get(section, key)


db_url = read_config("DATABASE", "db_url")
engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 密码加密上下文 - 当前使用明文存储
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    """存储明文密码"""
    return password

def verify_password(plain_password, hashed_password):
    """验证明文密码"""
    return plain_password == hashed_password


# 用户表模型
class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), default='')
    is_active = Column(String(1), default='1')  # '1'启用 '0'禁用
    create_time = Column(DateTime, nullable=False, default=func.now())
    update_time = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


# 运单处理表模型
class WaybillProcess(Base):
    __tablename__ = "waybill_process"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    waybill_no = Column(String(50), nullable=False, unique=True)
    phone = Column(String(20), nullable=False, index=True)
    process_status = Column(Enum('pending', 'processing', 'completed', 'failed'),
                            nullable=False, default='pending')
    create_time = Column(DateTime, nullable=False, default=func.now())
    update_time = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    remark = Column(String(500), default='')

    # 索引
    __table_args__ = (
        Index("idx_status_create_time", "process_status", "create_time"),
        Index("idx_status_update_time", "process_status", "update_time"),
        Index("idx_phone_status", "phone", "process_status"),
    )


# 创建表（首次运行执行）
Base.metadata.create_all(bind=engine)


# 数据库依赖（FastAPI使用）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
