# 🎬 MediaBox - Emby 媒体库管理系统

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

### Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/qq1394179649/mediabox.git
cd mediabox

# 启动服务
docker-compose up -d
```

访问 `http://localhost:5000`，首次登录需要配置 Emby 服务器信息。

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

### Docker Run

```bash
docker run -d \
  --name mediabox \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e EMBY_SERVER_URL=http://your-emby-server:8096 \
  -e EMBY_API_KEY=your-api-key \
  ghcr.io/qq1394179649/mediabox:latest
```





### Docker compose
```bash
  services:
  mediabox:
    image: ghcr.io/qq1394179649/mediabox:latest
    container_name: mediabox
    restart: unless-stopped
    
    ports:
      - "15000:5000"    # 正常访问端口

    volumes:
      - /vol1/1000/docker/mediabox/data:/app/data
      - /vol1/1000/docker/mediabox/logs:/app/logs

    environment:
      - TZ=Asia/Shanghai
      - EMBY_SERVER_URL=http://10.0.0.10:8096    # 你的 Emby 地址
      - EMBY_API_KEY=XXXXXXXXXXX                # 把这里改成你的真实API密钥
      - SECRET_KEY=mediabox_2025_random_key     # 随便填一串随机字符

    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

networks:
  default:
    driver: bridge
```    


## 📦 技术栈

- **后端**: Python 3.11 / Flask / Flask-Login
- **前端**: HTML5 / CSS3 / JavaScript
- **数据库**: SQLite
- **部署**: Docker / Gunicorn

## 🔧 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `FLASK_ENV` | 运行环境 | `production` |
| `EMBY_SERVER_URL` | Emby 服务器地址 | - |
| `EMBY_API_KEY` | Emby API Key | - |
| `SECRET_KEY` | Flask 密钥 | 随机生成 |

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

- 🌙 深色主题，专为媒体管理场景设计
- 🪟 玻璃态效果
- ✨ 流畅动画与微交互
- 📱 响应式布局

## ⚠️ 注意事项

1. **API 密钥安全**：不要将 settings.json 提交到公开仓库
2. **网络访问**：确保可访问 Emby 服务器
3. **生产部署**：建议使用 Docker 部署，配置 HTTPS

## 📄 许可证

MIT License
