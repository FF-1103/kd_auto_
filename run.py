# import pytest
# import os
# from utils.log_utils import get_logger
#
# logger = get_logger("run")
#
# # 报告目录（可选，若用allure）
# REPORT_DIR = "reports"
# if not os.path.exists(REPORT_DIR):
#     os.makedirs(REPORT_DIR)
#
# if __name__ == "__main__":
#     logger.info("========== 开始执行运单号自动化处理 ==========")
#     # 运行pytest用例
#     pytest.main([
#         "-v",
#         "-s",
#         "test_cases/test_ydh_process.py",
#         f"--tb=short",  # 简化异常输出
#         # 如需生成allure报告，取消下面注释（需安装allure-pytest）
#         # f"--alluredir={REPORT_DIR}/allure-results",
#         # "--clean-alluredir"
#     ])
#     logger.info("========== 执行结束 ==========")
import datetime
import os
import time
import traceback
from utils.log_utils import get_logger
from utils.driver_utils import get_reusable_driver
from page.ydh_page import YdhPage
from utils.excel_utils import read_ydh_from_excel

# 初始化日志
logger = get_logger("run")

# 报告目录（保留，无需修改）
REPORT_DIR = "reports"
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)


def main():
    # 定义过期日期和当前日期
    expire_date = datetime.date(2026, 3, 15)
    current_date = datetime.date.today()

    # 输出日期信息到日志
    # logger.info(f"当前日期：{current_date}，程序截止日期：{expire_date}")

    # 判断是否超过截止日期
    if current_date > expire_date:
        logger.warning("程序已过期，停止执行")
        print("❌ 程序已过期（截止日期：2026年3月1日），请更新程序后重试")
        return  # 直接退出函数

    """核心执行函数（直接运行，不依赖pytest）"""
    driver = None
    try:
        logger.info("========== 开始执行运单号自动化处理 ==========")

        # 1. 读取运单号
        ydh_list = read_ydh_from_excel()
        if not ydh_list:
            logger.warning("未读取到有效运单号，程序结束")
            return

        # 2. 获取Chrome驱动
        driver = get_reusable_driver()

        # 3. 初始化页面并处理运单号
        ydh_page = YdhPage(driver)
        ydh_page.open_ydh_page()
        ydh_page.input_shelf_num()

        # 4. 批量处理运单号

        for idx, ydh in enumerate(ydh_list, 1):
            logger.info(f"\n========== 处理第 {idx}/{len(ydh_list)} 个运单号 ==========")
            try:
                ydh_page.process_single_ydh(ydh)
            except Exception as e:
                # 记录异常信息，但不中断循环
                logger.error(f"处理运单号 {ydh} 时发生异常：{str(e)}", exc_info=True)
                ydh_page.input_shelf_num()
                time.sleep(2)
                continue  # 继续处理下一个运单号

        logger.info("\n🎉 所有运单号处理完成！")

    except Exception as e:
        # 打印详细报错
        logger.error(f"程序执行失败：{str(e)}", exc_info=True)
        print("\n❌ 程序执行出错：")
        print(traceback.format_exc())
        # 错误截图（如果驱动已初始化）
        if driver:
            try:
                ydh_page = YdhPage(driver)
                ydh_page.save_screenshot("main_error.png")
            except:
                pass
    finally:
        # 关闭驱动
        if driver:
            logger.info("断开Chrome驱动连接")
            driver.quit()
        logger.info("========== 执行结束 ==========")
        input("\n按Enter键关闭窗口...")  # 强制暂停


if __name__ == "__main__":
    main()  # 直接执行核心函数，无需pytest
