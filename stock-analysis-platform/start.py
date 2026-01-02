# simple_app.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
import os

# 数据库连接
DATABASE_URL = "mysql+pymysql://stock:stock%401234@localhost:3306/stock"
engine = create_engine(DATABASE_URL)

# 创建应用
app = FastAPI(title="股票分析平台", version="1.0.0")

# 模板和静态文件
templates = Jinja2Templates(directory="backend/app/templates")
app.mount("/static", StaticFiles(directory="backend/app/static"), name="static")

# API路由
@app.get("/api/test")
async def test_db():
    """测试数据库连接"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) as count FROM stock_day_data"))
            count = result.fetchone()[0]
        return {"code": 0, "message": "success", "data": {"count": count}}
    except Exception as e:
        return {"code": 1, "message": str(e)}

# 页面路由
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/capital")
async def capital(request: Request):
    return templates.TemplateResponse("capital.html", {"request": request})

@app.get("/stock")
async def stock(request: Request):
    return templates.TemplateResponse("stock.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)