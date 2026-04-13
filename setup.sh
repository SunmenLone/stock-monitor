#!/bin/bash
# 股票均线交叉检测系统环境初始化脚本

echo "创建虚拟环境..."
python3 -m venv venv

echo "激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install -r requirements.txt

echo "创建数据目录..."
mkdir -p data/klines_cache

echo "复制环境变量模板..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "请编辑 .env 文件配置钉钉Webhook URL"
fi

echo "初始化完成！"
echo "运行方式: source venv/bin/activate && python main.py"