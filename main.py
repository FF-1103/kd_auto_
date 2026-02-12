from fastapi import FastAPI, UploadFile, File, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import datetime as dt
import time

from models import WaybillProcess, get_db
from page.ydh_page import YdhPage
from utils.driver_utils import get_reusable_driver

app = FastAPI(title="运单号自动化服务")
templates = Jinja2Templates(directory="templates")

EXPIRE_DATE = dt.date(2026, 3, 15)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ------------------------------
# 导入Excel
# ------------------------------
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


# ------------------------------
# 处理 pending
# ------------------------------
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


# ------------------------------
# 重试 failed
# ------------------------------
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
