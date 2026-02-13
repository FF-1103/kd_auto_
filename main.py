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
        from fastapi import FastAPI, UploadFile, File, Depends, Request
        from fastapi.responses import HTMLResponse, FileResponse
        from fastapi.templating import Jinja2Templates
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
        from models import WaybillProcess, get_db
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
    
    # 创建应用
    app = FastAPI(title="运单号自动化服务")
    log_startup("✓ FastAPI 应用创建成功")
    
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
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        try:
            return templates.TemplateResponse("index.html", {"request": request})
        except Exception as e:
            log_startup(f"模板渲染错误: {str(e)}")
            raise
    
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
    async def import_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
        try:
            if not file.filename.endswith(('.xlsx', '.xls')):
                return {"code": 400, "msg": "仅支持Excel文件"}
    
            df = pd.read_excel(file.file)
            if df.empty:
                return {"code": 400, "msg": "Excel无数据"}
    
            success = 0
            fail = 0
            for v in df.iloc[:, 0].dropna():
                no = str(v).strip()
                if not no:
                    fail += 1
                    continue
                try:
                    w = WaybillProcess(waybill_no=no, process_status="pending")
                    db.add(w)
                    db.commit()
                    success += 1
                except IntegrityError:
                    db.rollback()
                    fail += 1
                except:
                    db.rollback()
                    fail += 1
    
            return {"code": 200, "msg": f"导入完成 成功:{success} 失败:{fail}"}
        except Exception as e:
            return {"code": 500, "msg": f"导入异常：{str(e)}"}
    
    @app.post("/process-waybills")
    async def process_waybills(db: Session = Depends(get_db)):
        try:
            if dt.date.today() > EXPIRE_DATE:
                return {"code": 403, "msg": "已过期"}
    
            items = db.query(WaybillProcess).filter(WaybillProcess.process_status == "pending").all()
            if not items:
                return {"code": 200, "msg": "暂无待处理运单号"}
    
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
                    except Exception as e:
                        w.process_status = "failed"
                        db.commit()
                        ng += 1
                        ydh.input_shelf_num()
                        time.sleep(1)
    
                return {"code": 200, "msg": f"处理完成 成功:{ok} 失败:{ng}"}
    
            except Exception as e:
                return {"code": 500, "msg": f"执行异常：{str(e)}"}
    
        except Exception as e:
            return {"code": 500, "msg": f"系统异常：{str(e)}"}
    
    @app.post("/retry-failed-waybills")
    async def retry_failed_waybills(db: Session = Depends(get_db)):
        try:
            if dt.date.today() > EXPIRE_DATE:
                return {"code": 403, "msg": "已过期"}
    
            items = db.query(WaybillProcess).filter(WaybillProcess.process_status == "failed").all()
            if not items:
                return {"code": 200, "msg": "暂无失败数据"}
    
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
                    except Exception as e:
                        w.process_status = "failed"
                        db.commit()
                        ng += 1
                        ydh.input_shelf_num()
                        time.sleep(1)
    
                return {"code": 200, "msg": f"重试完成 成功:{ok} 失败:{ng}"}
    
            except Exception as e:
                return {"code": 500, "msg": f"重试异常：{str(e)}"}
    
        except Exception as e:
            return {"code": 500, "msg": f"系统异常：{str(e)}"}
    
    @app.get("/export-completed")
    async def export_completed(db: Session = Depends(get_db)):
        try:
            items = db.query(WaybillProcess).filter(
                WaybillProcess.process_status == "completed"
            ).order_by(WaybillProcess.update_time.desc()).all()
    
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
    async def export_failed(db: Session = Depends(get_db)):
        try:
            items = db.query(WaybillProcess).filter(
                WaybillProcess.process_status == "failed"
            ).order_by(WaybillProcess.update_time.desc()).all()
    
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
        
        log_startup(f"服务端口: {port}")
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
