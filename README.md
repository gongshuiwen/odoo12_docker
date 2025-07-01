# README

## 1. Docker 镜像

该仓库为基于 odoo 12.0 的自定义镜像构建文件，相较于官方镜像做出了如下的一些修改：

- 基础镜像使用 python:3.7-slim-bullseye
- 支持切换 debian, postgresql, pypi 源
- 改为从本地文件安装 wkhtmltox
- 添加 Windows 系统中的宋体和 TimesNewRoman 字体
- 镜像中默认安装 celery, redis, minio 模块，并支持作为 celery worker 运行
- 额外的第三方模块可在 requirements.txt 中添加，例如 paramiko 等
- 添加等待 RabbitMQ Server 和 Redis Server 启动的脚本，因此 RabbitMQ, Redis 和 PostgreSQL 都是必须依赖且要优先启动的服务
- 添加基于 redis 的会话存储
- 添加基于 minio 的附件存储

### 镜像构建

```sh
git clone --depth=1 -b 12.0 https://github.com/odoo/odoo.git
docker build -t odoo12:latest .
```

### 运行 celery worker

使用如下命令示例可以将镜像容器作为 celery worker 运行，不用添加 `-A app worker`，其余参数可直接追加在后面：

```sh
docker run -d \
-v /host/path/data/:/var/lib/odoo/ \
-v /host/path/odoo.conf:/etc/odoo/odoo.conf \
odoo12 celery -l INFO [celery args]
```

> 注意：作为 celery worker 运行容器时，只能添加 celery worker 相关的命令行参数，odoo 参数只能填写在 `odoo.conf` 配置文件中，且必须挂载至 `/etc/odoo/` 目录下。

### 启动等待

Odoo12 镜像运行的容器启动时会等待 RabbitMQ Server 和 Redis Server 启动成功, RabbitMQ 和 Redis 连接信息需按如下方式在 `odoo.conf` 文件中配置：

```conf
; RabbitMQ
rabbit_host = rabbitmq
rabbit_port = 5672
rabbit_user = guest
rabbit_password = guest

; Redis
redis_host = redis
redis_port = 6379
redis_password = redis
redis_db = 0
redis_maxconn = 32
```

> 配置项缺省情况下将使用默认配置，连接超时后容器会自动退出

## 2. Docker Compose

> 该 docker-compose.yml 仅用于开发和测试环境，请勿直接用于生产环境！

### Compose 启动

```sh
cp odoo.conf compose/odoo.conf
cd compose
docker compose up -d
```

docker compose 中的默认服务及镜像如下：

- nginx(nginx)
- web(odoo12)
- chat(odoo12)
- cron(odoo12)
- celery(odoo12)
- db(postgres:13)
- rabbitmq(rabbitmq:3-management)
- redis(redis)
- minio(minio/minio)

## 3. 构建项目镜像

本镜像是 Odoo12 的基础镜像，如果需要从该镜像构建项目镜像，可参考如下 Dockerfile：

```dockerfile
FROM odoo12:latest

# Install project requirements
COPY requirements.txt /requirements-project.txt
RUN pip3 install --no-cache-dir -r /requirements-project.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Add project's addons
COPY addons_project /mnt/extra-addons/

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["odoo"]
```
