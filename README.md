<img width="1920" height="1080" alt="00_setup_wizard" src="https://github.com/user-attachments/assets/fe038dfd-2565-4ff1-a467-073f156562b1" /># 🎬 MediaBox - Emby 媒体库管理系统

基于 Python Flask 开发的 Emby 服务器管理系统，提供完整的 Web 管理面板。

## ✨ 功能特性

### 📊 仪表盘
- 服务器状态实时监控
- 媒体统计概览（电影、剧集、音乐、书籍等）
- 媒体分布可视化
- 媒体库概览

### 📁 STRM 媒体检查
- 批量检查 STRM 媒体文件可用性
- 支持分页、批量检查、导出
- 快速定位无效媒体链接

### 🔍 智能刮削
- TMDb + 豆瓣双数据源
- 支持代理设置
- 自动下载海报和背景图

### 👥 用户管理
- 用户列表查看
- 创建/编辑/删除用户
- 用户策略配置
- 在线设备监控

### 📚 媒体库管理
- 媒体库列表与概览
- 媒体项目浏览（网格视图）
- 按类型筛选和搜索
- 媒体详情与刮削

### 🎭 Emby 反代
- 内置透明反向代理
- 无缝访问 Emby Web 界面

### 🎨 主题定制
- 12+ 精选主题
- 亮色/暗色模式切换

## 🚀 快速开始

### FNOS 部署（推荐）

FNOS（飞牛 NAS）内置 Docker 支持，通过以下步骤即可快速部署 MediaBox：

#### 1. 创建存储目录

打开 FNOS 文件管理器，在 Docker 共享文件夹下创建 mediabox 目录：

```
/docker/mediabox/
├── data/          # 数据库存储
└── logs/          # 应用日志
```

或通过 SSH 执行：
```bash
mkdir -p /vol1/docker/mediabox/data /vol1/docker/mediabox/logs
```

> 💡 FNOS 的存储路径通常为 `/vol1/docker/`，请根据实际情况调整

#### 2. 拉取镜像

打开 FNOS 的 **Docker 管理** → **镜像管理** → **仓库**，搜索并拉取：
```
ghcr.io/qq1394179649/mediabox:latest
```

或通过 SSH 命令行拉取：
```bash
docker pull ghcr.io/qq1394179649/mediabox:latest
```

#### 3. 创建容器

在 FNOS Docker 管理界面 → **Compose** → **新增**，粘贴以下配置：

```yaml
services:
  mediabox:
    image: ghcr.io/qq1394179649/mediabox:latest
    container_name: mediabox
    restart: unless-stopped

    ports:
      - "15000:5000"    # MediaBox 访问端口（外部端口可自行修改）

    volumes:
      - /vol1/docker/mediabox/data:/app/data        # 数据持久化
      - /vol1/docker/mediabox/logs:/app/logs         # 日志持久化

    environment:
      - TZ=Asia/Shanghai
```

点击 **部署** 启动容器。

> ⚠️ **首次启动不需要配置环境变量**，直接访问 Web 界面通过向导完成初始化即可

#### 4. 访问初始化

浏览器打开 `http://FNOS的IP:15000`，进入设置向导：

1. **连接 Emby** — 填写 Emby 服务器地址（如 `http://10.0.0.10:8096`）和 API 密钥
2. **创建管理员** — 设置 MediaBox 管理员账户（与 Emby 账户无关）
3. **完成** — 自动跳转到仪表盘

#### 5. Emby API 密钥获取

1. 登录 Emby Web 界面（管理员账户）
2. 进入 **设置**（齿轮图标） → **控制台**
3. 找到 **API 密钥** 选项
4. 点击 **新建 API 密钥**，应用名填 `MediaBox`
5. 复制生成的密钥

#### 6. （可选）启用 Emby 反向代理

MediaBox 内置了 Emby 反向代理功能，可以在不暴露 Emby 地址的情况下访问 Emby 界面：

1. 登录 MediaBox → 侧边栏点击 **Emby 反代**
2. 打开 **启用反向代理** 开关
3. 端口默认 `8097`，如需外部访问需在 FNOS 防火墙放行该端口
4. 点击 **保存并应用**

> 💡 反向代理默认关闭，按需开启即可

---

### Docker Compose 部署

适用于任何支持 Docker 的系统（群晖、unraid、Linux 服务器等）：

```bash
# 创建目录
mkdir -p mediabox/data mediabox/logs

# 创建 docker-compose.yml 并粘贴下方配置
cat > mediabox/docker-compose.yml << 'EOF'
services:
  mediabox:
    image: ghcr.io/qq1394179649/mediabox:latest
    container_name: mediabox
    restart: unless-stopped
    ports:
      - "15000:5000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - TZ=Asia/Shanghai
EOF

# 启动
cd mediabox && docker-compose up -d
```

访问 `http://服务器IP:15000` 完成初始化设置。

### Docker Run

```bash
docker run -d \
  --name mediabox \
  --restart unless-stopped \
  -p 15000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e TZ=Asia/Shanghai \
  ghcr.io/qq1394179649/mediabox:latest
```

### 手动部署

```bash
# 克隆项目
git clone https://github.com/qq1394179649/mediabox.git
cd mediabox

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

访问 `http://localhost:5000`

### 🔄 更新镜像

```bash
# 拉取最新镜像
docker pull ghcr.io/qq1394179649/mediabox:latest

# 重建容器（数据不会丢失，data 和 logs 目录已挂载持久化）
docker-compose down && docker-compose up -d
```

> FNOS 用户也可以在 Docker 管理 → 镜像中点击「更新」，然后重建容器

## 📦 技术栈

- **后端**: Python 3.11 / Flask / Flask-Login
- **前端**: HTML5 / CSS3 / JavaScript
- **数据库**: SQLite
- **部署**: Docker / Gunicorn

## 🔧 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `TZ` | 时区 | `Asia/Shanghai` |
| `EMBY_SERVER_URL` | Emby 服务器地址（也可在向导中配置） | - |
| `EMBY_API_KEY` | Emby API Key（也可在向导中配置） | - |
| `SECRET_KEY` | Flask 密钥 | 随机生成 |

> 💡 推荐通过 Web 向导配置 Emby 连接，无需手动设置环境变量

## 📁 项目结构

```
.
├── app.py                  # Flask 应用主入口
├── config.py               # 配置模块
├── emby_client.py          # Emby API 客户端
├── scraper.py              # 媒体刮削模块
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 配置
├── docker-compose.yml      # Docker Compose 配置
├── static/
│   ├── css/style.css      # 样式文件
│   └── images/            # 静态图片
└── templates/             # Jinja2 模板
    ├── base.html           # 基础布局
    ├── login.html          # 登录页
    ├── dashboard.html      # 仪表盘
    ├── library.html        # 媒体库
    ├── strm_check.html     # STRM 检查
    └── ...
```

## 🔑 Emby API 密钥获取

1. 登录 Emby Web 界面
2. 进入 **设置** → **控制台**
3. 找到 **API 密钥**
4. 点击 **新建** 创建密钥
5. 复制密钥并配置到系统

## 🎨 界面预览

<img width="1920" height="1080" alt="00_setup_wizard" src="https://github.com/user-attachments/assets/d882b5a3-d000-4413-ae63-f94846623f77" />
<img width="1920" height="1048" alt="01_setup_wizard" src="https://github.com/user-attachments/assets/5c58f9e7-3318-4d9b-b9c4-d0c48a7ba270" />
<img width="1920" height="1048" alt="user" src="https://github.com/user-attachments/assets/12fe916d-bb33-4e77-9d7d-3b3b5b3e1835" />
<img width="1920" height="1048" alt="tmdb" src="https://github.com/user-attachments/assets/26afa484-66cf-4df8-b7a4-95f383d09f46" />
<img width="1920" height="1048" alt="system" src="https://github.com/user-attachments/assets/10401788-2617-46ee-a1be-eb5b14ae6a0f" />
<img width="1920" height="1048" alt="strm" src="https://github.com/user-attachments/assets/a06587f9-71bb-487a-85ec-b750aa29218c" />
<img width="1920" height="1048" alt="set1" src="https://github.com/user-attachments/assets/8f46f695-be0f-4aba-bfd1-d0d2cc9f3d4b" />
<img width="1920" height="1048" alt="set" src="https://github.com/user-attachments/assets/024c212c-c148-4179-bad5-dd71ef5d67ba" />
<img width="1920" height="1048" alt="quanxian" src="https://github.com/user-attachments/assets/692e57f6-232b-49a9-a668-d54690400180" />
<img width="1920" height="1048" alt="new" src="https://github.com/user-attachments/assets/c2497e3b-7def-42d0-9b30-dbfef8b1b8ea" />
<img width="1920" height="1048" alt="media" src="https://github.com/user-attachments/assets/4691b07e-a88d-4068-932e-65cd70186ced" />
<img width="1920" height="1048" alt="login" src="https://github.com/user-attachments/assets/78b78b8c-4753-4c15-8633-b6bab647a813" />
<img width="1920" height="1048" alt="line" src="https://github.com/user-attachments/assets/29b2f511-54fb-4ade-8f66-8d54ece27824" />
<img width="1920" height="1048" alt="index" src="https://github.com/user-attachments/assets/23190ab3-1497-4cdf-a3cc-4676887b919a" />
<img width="1920" height="1048" alt="about" src="https://github.com/user-attachments/assets/01f01062-53b1-4924-a641-5a229510a69d" />
<img width="1920" height="1048" alt="03_setup_wizard" src="https://github.com/user-attachments/assets/2d7e6c16-2b50-4808-b9fd-bffbed104188" />
<img width="1920" height="1048" alt="02_setup_wizard" src="https://github.com/user-attachments/assets/1b3f0671-b291-4bba-a384-af847004e16e" />



## ⚠️ 注意事项

1. **数据持久化**：`data` 和 `logs` 目录必须挂载到宿主机，否则容器重建后数据丢失
2. **网络访问**：确保 MediaBox 容器可访问 Emby 服务器
3. **反向代理**：默认关闭，如需启用请在 Web 界面中手动开启
4. **更新容器**：拉取新镜像后需重建容器（`docker-compose down && up -d`），数据不会丢失

## 📄 许可证

MIT License
