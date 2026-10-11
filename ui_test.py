"""UI 自动化最小示例：Selenium + 显式等待。

⚠️ 为什么不参与 CI：UI 测试需要本地浏览器 + 匹配版本的 ChromeDriver，
   在无头容器里默认跑不了。所以本文件**默认跳过**，本地手动跑时设置环境变量：

       PowerShell:  $env:RUN_UI=1; pytest ui_test.py -v
       或直接运行:   python ui_test.py

前置（一次性）：
   1. 安装 selenium：      pip install selenium
   2. 查 Chrome 版本：     浏览器地址栏输入 chrome://version
   3. 下载匹配主版本的 chromedriver，解压出 chromedriver.exe 放到本项目目录

面试要点（三类等待）：
   强制 time.sleep()  → 写死时间，慢则浪费、快则易挂（最差）
   隐式 implicitly_wait() → 全局设一次，省事但不精准
   显式 WebDriverWait().until(条件) → 只等特定条件，条件一到立刻继续（最稳）
   —— 一句话：「显式等待 = 等条件，不等时间。」
"""
import os
import sys

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_UI") != "1",
    reason="UI 测试需本地浏览器与 ChromeDriver；设置 RUN_UI=1 后再运行",
)


def test_python_org_has_search_box():
    """打开 python.org，显式等待搜索框出现，并断言页面标题。"""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = webdriver.Chrome()
    try:
        driver.get("https://www.python.org")
        # 显式等待：最多 10 秒，直到搜索框元素出现（而非固定 sleep）
        search = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        assert search is not None
        assert "Python" in driver.title
    finally:
        driver.quit()   # 无论成败都关浏览器，避免残留进程


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-s"]))
