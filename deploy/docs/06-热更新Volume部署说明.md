# 06 - 热更新 Volume 部署说明

## 目的

通过 **Volume 挂载** 将宿主机代码目录挂入容器（只读），使：

- 宿主机 `git pull` 后，容器内**立即看到新代码**，无需 `docker cp`
- 热更新系统能检测到文件变化，触发热更新即可生效
- 容器内 `/app` 仍为只读（挂载为 `:ro`），符合生产安全要求

## 使用方式

### 生产环境（推荐）

启动时叠加 `docker-compose.hotreload.yml`：

```bash
cd /opt/HiFate-bazi

# 若使用 deploy/docker 下的编排（双机）
cd deploy/docker
docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml -f ../../docker-compose.hotreload.yml up -d

# 若在项目根目录使用基础编排
docker-compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.hotreload.yml up -d
```

**首次启用**：需要**重新创建**容器一次（`up -d` 会应用新的 volume，通常会自动重建相关服务）。

### 增量部署流程（启用 Volume 后）

1. 本地提交并推送：`git push origin master`
2. 执行增量部署脚本：`bash deploy/scripts/incremental_deploy_production.sh`
3. 脚本在宿主机执行 `git pull` 后，容器内通过挂载**自动看到新代码**
4. 脚本触发热更新 API，热更新检测到变化并完成重载

**无需**再在容器内执行 `docker cp` 或 `git pull`。

## 挂载目录说明

| 宿主机目录（相对项目根） | 容器内路径 | 说明 |
|-------------------------|------------|------|
| `./server`              | `/app/server`   | Web 与热更新逻辑 |
| `./src`                 | `/app/src`      | 核心计算与工具 |
| `./services`            | `/app/services` | 各微服务代码 |
| `./core`                | `/app/core`     | 八字核心等 |

挂载均为**只读**（`:ro`），容器内不可修改这些目录。

## 未启用 Volume 时

若**未**使用 `docker-compose.hotreload.yml`：

- 容器内代码为镜像构建时的版本，宿主机 `git pull` 不会改变容器内文件
- 热更新检测的是容器内文件，因此**不会**检测到变化，热更新不生效
- 此时如需热更新生效，需改用 Volume 挂载（本文档方式）或重建镜像并重新部署

## 相关文件

- `docker-compose.hotreload.yml`：热更新 Volume 配置（项目根目录）
- `deploy/scripts/incremental_deploy_production.sh`：增量部署脚本（内含热更新触发）
- `standards/hot-reload.md`：热更新规范与 API 说明
