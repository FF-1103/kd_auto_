from fastapi import FastAPI, UploadFile, File, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import datetime as dt
import time
import os

from models import WaybillProcess, get_db
from page.ydh_page import YdhPage
from utils.driver_utils import get_reusable_driver

app = FastAPI(title="运单号自动化服务")
templates = Jinja2Templates(directory="templates")

EXPIRE_DATE = dt.date(2026, 3, 15)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/download-template")
async def download_template():
    return FileResponse("templates/ydh.xlsx", filename="ydh.xlsx",
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


if __name__ == "__main__":
    import uvicorn
    import sys
    from configparser import ConfigParser

    # ========== 关键修改1：适配打包后路径 ==========
    if getattr(sys, 'frozen', False):
        # 打包后的根目录（PyInstaller 打包后 __file__ 指向可执行文件）
        base_path = sys._MEIPASS
        # 修正配置文件路径
        config_path = os.path.join(base_path, "config", "config.ini")
        # 修正模板目录（确保 Jinja2 能找到模板）
        templates.directory = os.path.join(base_path, "templates")
    else:
        # 开发环境路径
        base_path = os.path.dirname(__file__)
        config_path = os.path.join(base_path, "config", "config.ini")

    # 读取配置
    config = ConfigParser()
    config.read(config_path, encoding="utf-8")
    port = int(config.get("SERVER", "port", fallback=8000))

    # ========== 关键修改2：Uvicorn 启动方式适配 ==========
    if getattr(sys, 'frozen', False):
        # 打包后直接传入 app 实例，而非字符串路径
        uvicorn.run(
            app,  # 直接传app实例，避免模块查找问题
            host="0.0.0.0",
            port=port,
            log_level="warning"
        )
    else:
        # 开发环境仍用字符串形式（兼容热重载）
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=True  # 开发环境可选热重载
        )
