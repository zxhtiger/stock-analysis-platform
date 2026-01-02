# backend/app/main.py

import sys
import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.api.v1 import capital, stock, block, strategy

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# 配置CORS
if settings.DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 挂载静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 配置模板
templates = Jinja2Templates(directory="app/templates")

# 注册API路由
app.include_router(capital.router, prefix=settings.API_V1_STR)
app.include_router(stock.router, prefix=settings.API_V1_STR)
app.include_router(block.router, prefix=settings.API_V1_STR)
app.include_router(strategy.router, prefix=settings.API_V1_STR)

# Web页面路由
@app.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    """首页"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "today": datetime.now().strftime('%Y-%m-%d')}
    )

@app.get("/capital")
async def capital_page(request: Request):
    """资金流向页面"""
    return templates.TemplateResponse(
        "capital.html",
        {"request": request, "today": datetime.now().strftime('%Y-%m-%d')}
    )

@app.get("/stock")
async def stock_page(request: Request):
    """股票分析页面"""
    return templates.TemplateResponse(
        "stock.html",
        {"request": request}
    )

@app.get("/strategy")
async def strategy_page(request: Request):
    """策略页面"""
    return templates.TemplateResponse(
        "strategy.html",
        {"request": request, "today": datetime.now().strftime('%Y-%m-%d')}
    )

@app.get("/dashboard")
async def dashboard_page(request: Request):
    """仪表板页面"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "today": datetime.now().strftime('%Y-%m-%d')}
    )

@app.get("/block/{block_code}/stocks")
async def block_stocks_page(request: Request, block_code: str):
    """板块股票页面"""
    return templates.TemplateResponse(
        "block_stocks.html",
        {"request": request, "block_code": block_code}
    )

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print(f"🚀 {settings.PROJECT_NAME} v{settings.PROJECT_VERSION} 启动成功!")
    print(f"📊 数据库: {settings.DATABASE_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("👋 应用关闭")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )