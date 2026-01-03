#!/bin/bash
# 杀掉阻塞 MySQL 导入的连接

CONTAINER=$(docker ps --format '{{.Names}}' | grep -E "(hifate-mysql-master|hifate-mysql-slave)" | head -1)
MYSQL_PASSWORD=$(grep MYSQL_PASSWORD /opt/HiFate-bazi/.env 2>/dev/null | cut -d'=' -f2 || echo "Yuanqizhan@163")

echo "杀掉阻塞的连接..."

# 杀掉所有非系统进程（除了 event_scheduler 和 repl）
docker exec $CONTAINER mysql -uroot -p"$MYSQL_PASSWORD" -e "
SELECT CONCAT('KILL ', id, ';') 
FROM information_schema.processlist 
WHERE user != 'event_scheduler' 
  AND user != 'repl' 
  AND command != 'Daemon'
  AND id != CONNECTION_ID();
" -N | while read kill_cmd; do
    if [ -n "$kill_cmd" ]; then
        echo "执行: $kill_cmd"
        docker exec $CONTAINER mysql -uroot -p"$MYSQL_PASSWORD" -e "$kill_cmd" 2>/dev/null
    fi
done

echo "完成"

