# 1. 安装依赖
pip install -r requirements.txt

# 2. 确保MySQL数据库已创建
# 创建数据库：stock_analysis
# 确保stock_day_data、stock_price_distribution、stock_block_membership表已存在

# 3. 修改配置
# 编辑 config/settings.py，更新数据库连接信息

# 4. 启动Web应用
python run.py

# 5. 访问应用
# 打开浏览器访问：http://127.0.0.1:8000

# 6. （可选）启动调度器（新开终端）
python -m backend.app.scheduler