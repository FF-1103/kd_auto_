#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import io
import traceback

# ========== 启动诊断日志 ==========
startup_log_path = os.path.join(
    os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__),
    "startup_error.log"
)


def log_startup(msg):
    try:
        with open(startup_log_path, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
            f.flush()
    except:
        pass


try:
    log_startup("=" * 50)
    log_startup(f"启动时间: {__import__('datetime').datetime.now()}")
    log_startup(f"Python: {sys.version}")
    log_startup(f"Frozen: {getattr(sys, 'frozen', False)}")
    log_startup(f"Executable: {sys.executable}")
    log_startup(f"CWD: {os.getcwd()}")

    # Windows服务兼容：无控制台时创建虚拟stdout
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')

    log_startup("✓ stdout/stderr 设置完成")

    # 导入主要模块
    log_startup("正在导入模块...")

    try:
        from fastapi import FastAPI, UploadFile, File, Depends, Request, Response, status
        from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
        from fastapi.templating import Jinja2Templates
        from fastapi.exceptions import HTTPException
        from starlette.middleware.sessions import SessionMiddleware

        log_startup("✓ FastAPI 导入成功")
    except Exception as e:
        log_startup(f"✗ FastAPI 导入失败: {str(e)}")
        raise

    try:
        import pandas as pd

        log_startup("✓ pandas 导入成功")
    except Exception as e:
        log_startup(f"✗ pandas 导入失败: {str(e)}")
        raise

    try:
        import uvicorn

        log_startup(f"✓ uvicorn 导入成功 (版本: {uvicorn.__version__})")
    except Exception as e:
        log_startup(f"✗ uvicorn 导入失败: {str(e)}")
        raise

    try:
        from models import WaybillProcess, User, get_db, get_password_hash, verify_password

        log_startup("✓ models 导入成功")
    except Exception as e:
        log_startup(f"✗ models 导入失败: {str(e)}")
        log_startup(traceback.format_exc())
        raise

    try:
        from page.ydh_page import YdhPage

        log_startup("✓ ydh_page 导入成功")
    except Exception as e:
        log_startup(f"✗ ydh_page 导入失败: {str(e)}")
        log_startup(traceback.format_exc())
        raise

    try:
        from utils.driver_utils import get_reusable_driver

        log_startup("✓ driver_utils 导入成功")
    except Exception as e:
        log_startup(f"✗ driver_utils 导入失败: {str(e)}")
        log_startup(traceback.format_exc())
        raise

    log_startup("✓ 所有模块导入完成")

    import datetime as dt
    import time
    from datetime import datetime
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import IntegrityError
    from configparser import ConfigParser
    from typing import Optional

    # 创建应用
    app = FastAPI(title="运单号自动化服务")
    log_startup("✓ FastAPI 应用创建成功")

    # 添加 Session 中间件（用于登录状态管理）
    app.add_middleware(SessionMiddleware, secret_key="your-secret-key-change-this-in-production")
    log_startup("✓ Session 中间件添加成功")

    # 全局状态变量
    processing_status = {"running": False, "processed": 0, "total": 0}


    # 登录验证依赖
    async def require_login(request: Request):
        """验证用户是否已登录"""
        if not request.session.get("user_id"):
            raise HTTPException(status_code=401, detail="请先登录")


    # 根据是否打包设置模板目录
    if getattr(sys, 'frozen', False):
        template_dir = os.path.join(os.path.dirname(sys.executable), "templates")
    else:
        template_dir = "templates"

    log_startup(f"模板目录: {template_dir}")
    log_startup(f"模板目录存在: {os.path.exists(template_dir)}")

    templates = Jinja2Templates(directory=template_dir)
    log_startup("✓ Jinja2 模板设置完成")

    EXPIRE_DATE = dt.date(2026, 3, 15)


    # 全局配置读取函数
    def get_config():
        """读取配置文件"""
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            config_path = os.path.join(base_path, "config", "config.ini")
        else:
            base_path = os.path.dirname(__file__)
            config_path = os.path.join(base_path, "config", "config.ini")

        config = ConfigParser()
        config.read(config_path, encoding="utf-8")
        return config


    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        try:
            # 检查是否已登录
            if not request.session.get("user_id"):
                return RedirectResponse(url="/login", status_code=302)
            return templates.TemplateResponse("index.html", {"request": request})
        except Exception as e:
            log_startup(f"模板渲染错误: {str(e)}")
            raise


    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """登录页面"""
        try:
            # 如果已登录，跳转到首页
            if request.session.get("user_id"):
                return RedirectResponse(url="/", status_code=302)
            return templates.TemplateResponse("login.html", {"request": request})
        except Exception as e:
            log_startup(f"登录页面渲染错误: {str(e)}")
            raise


    @app.post("/login")
    async def login(request: Request, db: Session = Depends(get_db)):
        """用户登录接口"""
        try:
            data = await request.json()
            phone = data.get("phone", "").strip()
            password = data.get("password", "")

            if not phone or not password:
                return {"code": 400, "msg": "请输入手机号和密码"}

            # 查询用户
            user = db.query(User).filter(User.phone == phone).first()
            if not user:
                return {"code": 400, "msg": "手机号或密码错误"}

            if user.is_active != '1':
                return {"code": 400, "msg": "账号已被禁用"}

            # 验证密码
            if not verify_password(password, user.password_hash):
                return {"code": 400, "msg": "手机号或密码错误"}

            # 设置登录状态
            request.session["user_id"] = user.id
            request.session["phone"] = user.phone
            request.session["nickname"] = user.nickname or user.phone

            return {"code": 200, "msg": "登录成功"}
        except Exception as e:
            return {"code": 500, "msg": f"登录失败：{str(e)}"}


    @app.post("/register")
    async def register(request: Request, db: Session = Depends(get_db)):
        """用户注册接口"""
        try:
            data = await request.json()
            phone = data.get("phone", "").strip()
            password = data.get("password", "")
            nickname = data.get("nickname", "").strip()

            if not phone or not password:
                return {"code": 400, "msg": "请填写完整信息"}

            # 验证手机号格式
            import re
            if not re.match(r'^1[3-9]\d{9}$', phone):
                return {"code": 400, "msg": "请输入正确的手机号"}

            if len(password) < 6:
                return {"code": 400, "msg": "密码至少6位"}

            # 检查手机号是否已注册
            existing = db.query(User).filter(User.phone == phone).first()
            if existing:
                return {"code": 400, "msg": "该手机号已注册"}

            # 创建新用户
            new_user = User(
                phone=phone,
                password_hash=get_password_hash(password),
                nickname=nickname,
                is_active='1'
            )
            db.add(new_user)
            db.commit()

            return {"code": 200, "msg": "注册成功"}
        except Exception as e:
            db.rollback()
            return {"code": 500, "msg": f"注册失败：{str(e)}"}


    @app.get("/logout")
    async def logout(request: Request):
        """退出登录"""
        request.session.clear()
        return RedirectResponse(url="/login", status_code=302)


    # 获取模板文件路径
    def get_template_path(filename):
        if getattr(sys, 'frozen', False):
            return os.path.join(os.path.dirname(sys.executable), "templates", filename)
        return os.path.join("templates", filename)


    @app.get("/download-template")
    async def download_template():
        template_path = get_template_path("ydh.xlsx")
        return FileResponse(template_path, filename="ydh.xlsx",
                            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


    @app.post("/import-excel")
    async def import_excel(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db),
                           user=Depends(require_login)):
        """导入Excel文件到数据库"""
        try:
            if not file.filename.endswith(('.xlsx', '.xls')):
                return {"code": 400, "msg": "仅支持Excel文件"}

            df = pd.read_excel(file.file)
            if df.empty:
                return {"code": 400, "msg": "Excel无数据"}

            # 获取当前登录用户的手机号
            phone = request.session.get("phone", "")

            # 导入数据到数据库
            count = 0
            for _, row in df.iterrows():
                try:
                    # 获取运单号（支持多个常见列名）
                    waybill_no = None
                    for col in ['运单号', 'ydh', 'YDH', 'waybill_no', 'WaybillNo']:
                        if col in row and pd.notna(row[col]):
                            waybill_no = str(row[col]).strip()
                            break

                    if not waybill_no:
                        continue

                    # 检查是否已存在
                    existing = db.query(WaybillProcess).filter(
                        WaybillProcess.waybill_no == waybill_no,
                        WaybillProcess.phone == phone
                    ).first()

                    if not existing:
                        # 创建新记录
                        new_record = WaybillProcess(
                            waybill_no=waybill_no,
                            phone=phone,
                            process_status="pending"
                        )
                        db.add(new_record)
                        count += 1

                except Exception as e:
                    logger.error(f"导入行失败: {e}")
                    continue

            db.commit()
            return {"code": 200, "msg": f"导入完成，共导入 {count} 条运单号"}

        except Exception as e:
            return {"code": 500, "msg": f"导入异常：{str(e)}"}


    @app.post("/process-waybills")
    async def process_waybills(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
        """执行处理待处理运单"""
        try:
            if dt.date.today() > EXPIRE_DATE:
                return {"code": 403, "msg": "已过期"}

            # 检查是否已在处理中
            if processing_status["running"]:
                return {"code": 400, "msg": "已有任务正在处理中，请先停止当前任务"}

            # 获取当前登录用户的手机号
            phone = request.session.get("phone", "")

            # 获取时间范围参数
            data = await request.json()
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            # 构建查询条件 - 只查询当前用户的数据
            query = db.query(WaybillProcess).filter(
                WaybillProcess.process_status == "pending",
                WaybillProcess.phone == phone
            )

            if start_date:
                query = query.filter(WaybillProcess.create_time >= start_date)
            if end_date:
                # 结束日期加一天，包含当天所有数据
                from datetime import timedelta
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                end_date_next = (end_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                query = query.filter(WaybillProcess.create_time < end_date_next)

            # 读取配置
            config = get_config()
            max_batch_size = int(config.get("PROCESS", "max_batch_size", fallback=10000))

            # 限制最大条数
            items = query.order_by(WaybillProcess.create_time.asc()).limit(max_batch_size).all()

            if not items:
                return {"code": 200, "msg": "暂无待处理运单号"}

            # 初始化状态
            processing_status["running"] = True
            processing_status["processed"] = 0
            processing_status["total"] = len(items)

            driver = None
            try:
                driver = get_reusable_driver()
                ydh = YdhPage(driver)
                ydh.open_ydh_page()
                ydh.input_shelf_num()

                ok = 0
                ng = 0

                for w in items:
                    try:
                        w.process_status = "processing"
                        db.commit()

                        ydh.process_single_ydh(w.waybill_no)

                        w.process_status = "completed"
                        db.commit()
                        ok += 1
                        processing_status["processed"] = ok + ng
                    except Exception as e:
                        w.process_status = "failed"
                        db.commit()
                        ng += 1
                        processing_status["processed"] = ok + ng
                        ydh.input_shelf_num()
                        time.sleep(1)

                processing_status["running"] = False
                return {"code": 200, "msg": f"处理完成 成功:{ok} 失败:{ng}"}

            except Exception as e:
                processing_status["running"] = False
                return {"code": 500, "msg": f"执行异常：{str(e)}"}

        except Exception as e:
            processing_status["running"] = False
            return {"code": 500, "msg": f"系统异常：{str(e)}"}


    @app.post("/retry-failed-waybills")
    async def retry_failed_waybills(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
        try:
            if dt.date.today() > EXPIRE_DATE:
                return {"code": 403, "msg": "已过期"}

            # 检查是否已在处理中
            if processing_status["running"]:
                return {"code": 400, "msg": "已有任务正在处理中，请先停止当前任务"}

            # 获取当前登录用户的手机号
            phone = request.session.get("phone", "")

            # 获取时间范围参数
            data = await request.json()
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            # 构建查询条件 - 只查询当前用户的数据
            query = db.query(WaybillProcess).filter(
                WaybillProcess.process_status == "failed",
                WaybillProcess.phone == phone
            )

            if start_date:
                query = query.filter(WaybillProcess.create_time >= start_date)
            if end_date:
                # 结束日期加一天，包含当天所有数据
                from datetime import timedelta
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                end_date_next = (end_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                query = query.filter(WaybillProcess.create_time < end_date_next)

            # 读取配置
            config = get_config()
            max_batch_size = int(config.get("PROCESS", "max_batch_size", fallback=10000))

            # 限制最大条数
            items = query.order_by(WaybillProcess.create_time.asc()).limit(max_batch_size).all()

            if not items:
                return {"code": 200, "msg": "暂无失败数据"}

            # 初始化状态
            processing_status["running"] = True
            processing_status["processed"] = 0
            processing_status["total"] = len(items)

            driver = None
            try:
                driver = get_reusable_driver()
                ydh = YdhPage(driver)
                ydh.open_ydh_page()
                ydh.input_shelf_num()
                ydh.input_sn_num()

                ok = 0
                ng = 0

                for w in items:
                    try:
                        w.process_status = "processing"
                        db.commit()

                        ydh.process_single_ydh(w.waybill_no)

                        w.process_status = "completed"
                        db.commit()
                        ok += 1
                        processing_status["processed"] = ok + ng
                    except Exception as e:
                        w.process_status = "failed"
                        db.commit()
                        ng += 1
                        processing_status["processed"] = ok + ng
                        ydh.input_shelf_num()
                        time.sleep(1)

                processing_status["running"] = False
                return {"code": 200, "msg": f"重试完成 成功:{ok} 失败:{ng}"}

            except Exception as e:
                processing_status["running"] = False
                return {"code": 500, "msg": f"重试异常：{str(e)}"}

        except Exception as e:
            processing_status["running"] = False
            return {"code": 500, "msg": f"系统异常：{str(e)}"}


    @app.get("/processing-status")
    async def get_processing_status():
        """获取当前处理状态"""
        return {
            "code": 200,
            "data": {
                "running": processing_status["running"],
                "processed": processing_status["processed"],
                "total": processing_status["total"],
                "progress": f"{processing_status['processed']}/{processing_status['total']}" if processing_status[
                                                                                                    "total"] > 0 else "0/0"
            }
        }


    @app.get("/export-completed")
    async def export_completed(
            request: Request,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            db: Session = Depends(get_db),
            user=Depends(require_login)
    ):
        try:
            # 获取当前登录用户的手机号
            phone = request.session.get("phone", "")

            # 构建查询条件 - 只查询当前用户的数据
            query = db.query(WaybillProcess).filter(
                WaybillProcess.process_status == "completed",
                WaybillProcess.phone == phone
            )

            if start_date:
                query = query.filter(WaybillProcess.create_time >= start_date)
            if end_date:
                # 结束日期加一天，包含当天所有数据
                from datetime import timedelta
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                end_date_next = (end_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                query = query.filter(WaybillProcess.create_time < end_date_next)

            # 读取配置
            config = get_config()
            max_batch_size = int(config.get("PROCESS", "max_batch_size", fallback=10000))

            # 限制最大条数
            items = query.order_by(WaybillProcess.create_time.desc()).limit(max_batch_size).all()

            if not items:
                return {"code": 200, "msg": "暂无成功数据"}

            status_map = {
                "pending": "待处理",
                "processing": "处理中",
                "completed": "处理完成",
                "failed": "处理失败"
            }

            data = [{
                "运单号": w.waybill_no,
                "状态": status_map.get(w.process_status, w.process_status),
                "创建时间": w.create_time.strftime("%Y-%m-%d %H:%M:%S") if w.create_time else "",
                "更新时间": w.update_time.strftime("%Y-%m-%d %H:%M:%S") if w.update_time else "",
                "备注": w.remark or ""
            } for w in items]

            df = pd.DataFrame(data)
            file_path = "reports/completed_data.xlsx"
            os.makedirs("reports", exist_ok=True)
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)

            return FileResponse(file_path, filename="成功数据.xlsx",
                                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except Exception as e:
            return {"code": 500, "msg": f"导出异常：{str(e)}"}


    @app.get("/export-failed")
    async def export_failed(
            request: Request,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            db: Session = Depends(get_db),
            user=Depends(require_login)
    ):
        try:
            # 获取当前登录用户的手机号
            phone = request.session.get("phone", "")

            # 构建查询条件 - 只查询当前用户的数据
            query = db.query(WaybillProcess).filter(
                WaybillProcess.process_status == "failed",
                WaybillProcess.phone == phone
            )

            if start_date:
                query = query.filter(WaybillProcess.create_time >= start_date)
            if end_date:
                # 结束日期加一天，包含当天所有数据
                from datetime import timedelta
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                end_date_next = (end_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                query = query.filter(WaybillProcess.create_time < end_date_next)

            # 读取配置
            config = get_config()
            max_batch_size = int(config.get("PROCESS", "max_batch_size", fallback=10000))

            # 限制最大条数
            items = query.order_by(WaybillProcess.create_time.desc()).limit(max_batch_size).all()

            if not items:
                return {"code": 200, "msg": "暂无失败数据"}

            status_map = {
                "pending": "待处理",
                "processing": "处理中",
                "completed": "处理完成",
                "failed": "处理失败"
            }

            data = [{
                "运单号": w.waybill_no,
                "状态": status_map.get(w.process_status, w.process_status),
                "创建时间": w.create_time.strftime("%Y-%m-%d %H:%M:%S") if w.create_time else "",
                "更新时间": w.update_time.strftime("%Y-%m-%d %H:%M:%S") if w.update_time else "",
                "备注": w.remark or ""
            } for w in items]

            df = pd.DataFrame(data)
            file_path = "reports/failed_data.xlsx"
            os.makedirs("reports", exist_ok=True)
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)

            return FileResponse(file_path, filename="失败数据.xlsx",
                                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except Exception as e:
            return {"code": 500, "msg": f"导出异常：{str(e)}"}


    log_startup("✓ 所有路由定义完成")
    log_startup("=" * 50)

except Exception as e:
    log_startup(f"\n!!! 启动失败: {str(e)}")
    log_startup(traceback.format_exc())
    log_startup("=" * 50)
    raise


def kill_port_process(port):
    """杀掉占用指定端口的进程"""
    try:
        import subprocess
        # 使用PowerShell查找并关闭占用端口的进程
        result = subprocess.run(
            ['powershell', '-Command',
             f"$conn = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue; "
             f"if ($conn) {{ "
             f"  $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue; "
             f"  if ($proc -and $proc.ProcessName -ne 'Idle') {{ "
             f"    Stop-Process -Id $conn.OwningProcess -Force; "
             f"    Write-Host \"已关闭占用端口 {port} 的进程: $($proc.ProcessName) (PID: $($conn.OwningProcess))\"; "
             f"  }}"
             f"}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            log_startup(result.stdout.strip())
        return True
    except Exception as e:
        log_startup(f"关闭端口进程失败: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        log_startup("正在启动服务...")

        # 读取配置
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            config_path = os.path.join(base_path, "config", "config.ini")
        else:
            base_path = os.path.dirname(__file__)
            config_path = os.path.join(base_path, "config", "config.ini")

        log_startup(f"配置文件路径: {config_path}")
        log_startup(f"配置文件存在: {os.path.exists(config_path)}")

        config = ConfigParser()
        config.read(config_path, encoding="utf-8")
        port = int(config.get("SERVER", "port", fallback=8000))
        max_batch_size = int(config.get("PROCESS", "max_batch_size", fallback=10000))

        log_startup(f"服务端口: {port}")
        log_startup(f"批量处理大小: {max_batch_size}")

        # 先杀掉占用该端口的进程
        log_startup(f"正在检查端口 {port} 占用情况...")
        kill_port_process(port)

        # 等待一下确保端口释放
        time.sleep(1)

        log_startup("正在启动 uvicorn...")

        # 检查端口是否被占用
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                log_startup(f"警告：端口 {port} 已被占用！")
            else:
                log_startup(f"端口 {port} 可用")
            sock.close()
        except Exception as e:
            log_startup(f"端口检查失败: {str(e)}")

        # 启动服务
        try:
            log_startup("调用 uvicorn.run...")
            if getattr(sys, 'frozen', False):
                uvicorn.run(
                    app,
                    host="0.0.0.0",
                    port=port,
                    log_level="error",
                    access_log=False,
                )
            else:
                uvicorn.run(
                    "main:app",
                    host="0.0.0.0",
                    port=port,
                    reload=True
                )
            log_startup("uvicorn.run 返回")
        except Exception as e:
            log_startup(f"uvicorn 启动失败: {str(e)}")
            log_startup(traceback.format_exc())
            raise
    except Exception as e:
        log_startup(f"\n!!! 服务启动失败: {str(e)}")
        log_startup(traceback.format_exc())
