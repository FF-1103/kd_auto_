chcp 65001
pyinstaller -F main.py --add-data "config;config" --add-binary "chromedriver.exe;." --console --name "运单号自动化工具" --clean --distpath D:\dist