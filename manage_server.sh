#!/bin/bash

# 油品检测记录系统 - 服务器管理脚本
# 类似本地管理方式

set -e

DEPLOY_DIR="/opt/oil-inspection"
source "$DEPLOY_DIR/venv/bin/activate"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

show_help() {
    echo "油品检测记录系统 - 服务器管理"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start           启动服务"
    echo "  stop            停止服务"
    echo "  restart         重启服务"
    echo "  status          查看服务状态"
    echo "  logs            查看日志"
    echo "  migrate         执行数据库迁移"
    echo "  collectstatic   收集静态文件"
    echo "  createsuperuser 创建管理员"
    echo "  shell           Django shell"
    echo "  update          更新代码和重启"
    echo "  backup          备份数据库"
    echo "  help            显示帮助"
    echo ""
}

start_service() {
    echo -e "${GREEN}🚀 启动服务...${NC}"
    sudo systemctl start oil-inspection
    sudo systemctl status oil-inspection --no-pager
}

stop_service() {
    echo -e "${YELLOW}🛑 停止服务...${NC}"
    sudo systemctl stop oil-inspection
}

restart_service() {
    echo -e "${YELLOW}🔄 重启服务...${NC}"
    sudo systemctl restart oil-inspection
    sudo systemctl status oil-inspection --no-pager
}

show_status() {
    echo -e "${GREEN}📊 服务状态:${NC}"
    sudo systemctl status oil-inspection --no-pager

    echo ""
    echo -e "${GREEN}📱 网络访问:${NC}"
    echo "本地访问: http://localhost:8000"
    echo "内网访问: http://$(hostname -I | awk '{print $1}'):8000"
    echo "外网访问: http://$(curl -s ifconfig.me 2>/dev/null || echo '需要手动检查IP'):8000"
}

show_logs() {
    echo -e "${GREEN}📋 服务日志:${NC}"
    sudo journalctl -u oil-inspection -f
}

migrate_db() {
    echo -e "${GREEN}🔄 执行数据库迁移...${NC}"
    cd "$DEPLOY_DIR"
    python manage.py migrate
}

collect_static() {
    echo -e "${GREEN}📁 收集静态文件...${NC}"
    cd "$DEPLOY_DIR"
    python manage.py collectstatic --noinput
}

create_superuser() {
    echo -e "${GREEN}👤 创建管理员账户...${NC}"
    cd "$DEPLOY_DIR"
    python manage.py createsuperuser
}

django_shell() {
    echo -e "${GREEN}🐍 进入Django Shell...${NC}"
    cd "$DEPLOY_DIR"
    python manage.py shell
}

update_code() {
    echo -e "${GREEN}🔄 更新代码...${NC}"
    cd "$DEPLOY_DIR"

    # 拉取最新代码（如果使用git）
    if [ -d ".git" ]; then
        git pull
    fi

    # 更新依赖
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

    # 执行迁移
    python manage.py migrate

    # 收集静态文件
    python manage.py collectstatic --noinput

    # 重启服务
    restart_service
}

backup_db() {
    echo -e "${GREEN}💾 备份数据库...${NC}"
    cd "$DEPLOY_DIR"

    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"

    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"

    # 如果是PostgreSQL
    if grep -q "postgresql" oil_inspection/settings.py; then
        PGPASSWORD=$(grep DB_PASSWORD .env | cut -d'=' -f2) pg_dump -h localhost -U oil_user oil_inspection_db > "$BACKUP_FILE"
    else
        # 如果是SQLite
        cp db.sqlite3 "$BACKUP_FILE"
    fi

    gzip "$BACKUP_FILE"
    echo -e "${GREEN}✅ 备份完成: ${BACKUP_FILE}.gz${NC}"
}

case "${1:-help}" in
    "start")
        start_service
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "migrate")
        migrate_db
        ;;
    "collectstatic")
        collect_static
        ;;
    "createsuperuser")
        create_superuser
        ;;
    "shell")
        django_shell
        ;;
    "update")
        update_code
        ;;
    "backup")
        backup_db
        ;;
    "help"|*)
        show_help
        ;;
esac