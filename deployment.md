# 智能法律助手项目部署方案

## 一、PostgreSQL数据库安装（Docker部署）

- 拉取已包含 vector 扩展的镜像
  
  *docker pull ankane/pgvector*

- 运行容器
  
  *docker run -d --name pgvector -p 5432:5432 -e POSTGRES_PASSWORD=password ankane/pgvector*

- 运行之后，PostgreSQL数据库已经启动了，运行端口5432，用户名：postgres，密码：password




## 二、Milvus向量数据库安装(Docker部署)

### 以管理员模式运行Powershell，运行命令：

- 下载docker-compose.yml配置文件

    *C:\>Invoke-WebRequest https://github.com/milvus-io/milvus/releases/download/v2.6.8/milvus-standalone-docker-compose.yml -OutFile docker-compose.yml*

- 启动Milvus

    *C:\>docker compose up -d*

- 启动之后，Milvus已经启动了，运行端口19530。
- 本地MinIO控制台页面地址：http://localhost:9001 (用户名: minioadmin, 密码: minioadmin)