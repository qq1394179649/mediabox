"""Emby管理系统 - Flask应用主入口（性能优化版）"""
import os
import re
import sys
import time
import json
import uuid
import secrets
import string
import logging
import socket
import sqlite3
import threading
from pathlib import Path
from functools import wraps
from datetime import datetime, timedelta
import flask
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response, Response, stream_with_context, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config, THEMES, _save_settings
from emby_client import EmbyClient
from scraper import MediaScraper
import requests as http_requests

# ========== 数据库配置 ==========
DATABASE = Path(__file__).parent / 'data.db'
DATA_DIR = Path(__file__).parent
DATA_DIR.mkdir(exist_ok=True)

def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """初始化数据库表"""
    db = get_db()
    # 用户表
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    # 权限模板表
    db.execute('''
        CREATE TABLE IF NOT EXISTS permission_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            permissions TEXT,  -- JSON格式存储权限
            is_default INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    # 邀请码表
    db.execute('''
        CREATE TABLE IF NOT EXISTS invite_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            max_uses INTEGER DEFAULT 1,
            use_count INTEGER DEFAULT 0,
            used_by INTEGER,
            used_at TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            template_id INTEGER,
            FOREIGN KEY (created_by) REFERENCES users(id),
            FOREIGN KEY (used_by) REFERENCES users(id),
            FOREIGN KEY (template_id) REFERENCES permission_templates(id)
        )
    ''')
    db.commit()
    
    # 迁移：为旧数据库添加缺失的列
    try:
        cursor = db.execute("PRAGMA table_info(invite_codes)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'template_id' not in columns:
            db.execute("ALTER TABLE invite_codes ADD COLUMN template_id INTEGER REFERENCES permission_templates(id)")
            db.commit()
    except Exception:
        pass
    
    # 如果没有默认模板，创建一个
    cursor = db.execute('SELECT id FROM permission_templates WHERE is_default = 1')
    if not cursor.fetchone():
        import json as json_module
        # 创建普通用户模板
        perms_normal = {
            "can_view": True, "can_download": False, "can_manage": False, "can_admin": False,
            "emby": {
                "is_admin": False, "is_hidden": False, "is_disabled": False,
                "video_transcoding": True, "audio_transcoding": True, "remuxing": True, "media_conversion": False,
                "remote_access": True, "live_tv": False, "media_playback": True,
                "content_downloading": False, "subtitle_download": True, "content_deletion": False,
                "bitrate_limit": 0
            }
        }
        db.execute('''
            INSERT INTO permission_templates (name, description, permissions, is_default, created_by)
            VALUES (?, ?, ?, 1, ?)
        ''', ('普通用户', '默认权限，允许转码但禁止下载', json_module.dumps(perms_normal), None))
        
        # 创建高级用户模板
        perms_advanced = {
            "can_view": True, "can_download": True, "can_manage": False, "can_admin": False,
            "emby": {
                "is_admin": False, "is_hidden": False, "is_disabled": False,
                "video_transcoding": True, "audio_transcoding": True, "remuxing": True, "media_conversion": True,
                "remote_access": True, "live_tv": True, "media_playback": True,
                "content_downloading": True, "subtitle_download": True, "content_deletion": False,
                "bitrate_limit": 0
            }
        }
        db.execute('''
            INSERT INTO permission_templates (name, description, permissions, is_default, created_by)
            VALUES (?, ?, ?, 0, ?)
        ''', ('高级用户', '可下载媒体，允许转码和直播', json_module.dumps(perms_advanced), None))
        
        # 创建管理员模板
        perms_admin = {
            "can_view": True, "can_download": True, "can_manage": True, "can_admin": True,
            "emby": {
                "is_admin": True, "is_hidden": False, "is_disabled": False,
                "video_transcoding": True, "audio_transcoding": True, "remuxing": True, "media_conversion": True,
                "remote_access": True, "live_tv": True, "media_playback": True,
                "content_downloading": True, "subtitle_download": True, "content_deletion": True,
                "bitrate_limit": 0
            }
        }
        db.execute('''
            INSERT INTO permission_templates (name, description, permissions, is_default, created_by)
            VALUES (?, ?, ?, 0, ?)
        ''', ('管理员', '完整访问权限', json_module.dumps(perms_admin), None))
        
        # 创建限制用户模板（仅Remuxing，不允许转码）
        perms_restricted = {
            "can_view": True, "can_download": False, "can_manage": False, "can_admin": False,
            "emby": {
                "is_admin": False, "is_hidden": False, "is_disabled": False,
                "video_transcoding": False, "audio_transcoding": False, "remuxing": True, "media_conversion": False,
                "remote_access": True, "live_tv": False, "media_playback": True,
                "content_downloading": False, "subtitle_download": False, "content_deletion": False,
                "bitrate_limit": 5000
            }
        }
        db.execute('''
            INSERT INTO permission_templates (name, description, permissions, is_default, created_by)
            VALUES (?, ?, ?, 0, ?)
        ''', ('限制用户', '仅允许直接播放，限制码率', json_module.dumps(perms_restricted), None))
        
        db.commit()
    
    # 迁移：更新现有模板，添加Emby权限字段（如果缺少的话）
    import json as json_module
    cursor = db.execute('SELECT id, permissions FROM permission_templates')
    for row in cursor.fetchall():
        perms = json_module.loads(row['permissions']) if row['permissions'] else {}
        if 'emby' not in perms:
            # 为旧模板添加默认的Emby权限
            perms['emby'] = {
                "is_admin": perms.get('can_admin', False),
                "is_hidden": False, "is_disabled": False,
                "video_transcoding": True, "audio_transcoding": True, "remuxing": True, "media_conversion": False,
                "remote_access": True, "live_tv": False, "media_playback": True,
                "content_downloading": perms.get('can_download', False), 
                "subtitle_download": True, "content_deletion": False,
                "bitrate_limit": 0
            }
            db.execute('UPDATE permission_templates SET permissions = ? WHERE id = ?', 
                       (json_module.dumps(perms), row['id']))
    db.commit()
    
    # 不再自动创建默认管理员用户
    # 登录时直接调用 Emby API 认证，首次登录会自动同步到本地 users 表

# Flask 版本号
FLASK_VERSION = flask.__version__

# ========== 获取本机网络IP ==========
def get_local_ips():
    """获取本机所有网络接口的IP地址"""
    ips = []
    hostname = socket.gethostname()
    try:
        # 获取本机主机名对应的所有IP
        addrs = socket.getaddrinfo(hostname, None)
        for addr in addrs:
            ip = addr[4][0]
            if ip not in ips and not ip.startswith('::'):  # 排除IPv6
                ips.append(ip)
    except Exception:
        pass
    
    # 如果上面的方法获取不到，尝试通过连接外部DNS获取
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            if local_ip:
                ips.append(local_ip)
        except Exception:
            pass
    
    # 始终添加 127.0.0.1
    if '127.0.0.1' not in ips:
        ips.insert(0, '127.0.0.1')
    
    return hostname, ips

# ========== 应用日志配置 ==========
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)
APP_LOG_FILE = LOG_DIR / 'mediabox.log'

# 配置日志
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(APP_LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('mediabox')

logger = setup_logging()

def log_info(msg):
    logger.info(msg)

def log_error(msg):
    logger.error(msg)

def log_warning(msg):
    logger.warning(msg)

def log_debug(msg):
    logger.debug(msg)

app = Flask(__name__)
app.config.from_object(Config)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 静态文件缓存1天

# 注册数据库 teardown
@app.teardown_appcontext
def close_db(error):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# 初始化数据库
with app.app_context():
    init_db()


# 自定义Jinja2过滤器
@app.template_filter('format_number')
def format_number(value):
    """格式化数字：添加千分位逗号"""
    try:
        n = int(value)
        if n >= 10000:
            return f'{n:,}'
        return str(n)
    except (ValueError, TypeError):
        return str(value)

@app.template_filter('from_json')
def from_json(value):
    """解析JSON字符串"""
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except:
        return {}

# Flask-Login配置
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ========== 简易内存缓存 ==========
_cache = {}
_CACHE_TTL = 30  # 默认缓存30秒


def cached(ttl=_CACHE_TTL):
    """API结果缓存装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = f.__name__
            now = time.time()
            if key in _cache:
                data, expire_at = _cache[key]
                if now < expire_at:
                    return data
            result = f(*args, **kwargs)
            _cache[key] = (result, now + ttl)
            return result
        return wrapper
    return decorator


def clear_cache():
    """清空缓存"""
    _cache.clear()


def get_emby_client():
    """获取Emby客户端实例（每次读取最新配置）"""
    return EmbyClient(Config.get_emby_url(), Config.get_emby_api_key())


class MediaBoxUser(UserMixin):
    """MediaBox用户模型"""
    def __init__(self, user_id, username, is_admin=False, is_enabled=True, display_name=None):
        self.id = user_id
        self.username = username
        self.is_admin = is_admin
        self._is_enabled = is_enabled  # 用 _is_enabled 避免与 UserMixin 的 is_active 冲突
        self.display_name = display_name or username
    
    def is_enabled(self):
        """用户是否启用"""
        return self._is_enabled


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.execute(
        'SELECT id, username, is_admin, is_active, display_name FROM users WHERE id = ? AND is_active = 1',
        (user_id,)
    )
    row = cursor.fetchone()
    if row:
        return MediaBoxUser(row['id'], row['username'], row['is_admin'], row['is_active'], row['display_name'])
    return None


def is_admin_user(user_id):
    """检查用户是否为管理员"""
    db = get_db()
    cursor = db.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    return row and row['is_admin'] == 1


def permissions_to_emby_policy(permissions: dict) -> dict:
    """将权限模板转换为Emby用户策略"""
    emby_perms = permissions.get('emby', {})
    
    policy = {
        # 用户状态
        'IsAdministrator': emby_perms.get('is_admin', False),
        'IsHidden': emby_perms.get('is_hidden', False),
        'IsDisabled': emby_perms.get('is_disabled', False),
        
        # 访问权限
        'EnableRemoteAccess': emby_perms.get('remote_access', True),
        'EnableLiveTvAccess': emby_perms.get('live_tv', False),
        'EnableLiveTvManagement': emby_perms.get('live_tv', False),
        
        # 播放权限
        'EnableMediaPlayback': emby_perms.get('media_playback', True),
        'EnableAudioPlaybackTranscoding': emby_perms.get('audio_transcoding', True),
        'EnableVideoPlaybackTranscoding': emby_perms.get('video_transcoding', True),
        'EnablePlaybackRemuxing': emby_perms.get('remuxing', True),
        'EnableMediaConversion': emby_perms.get('media_conversion', False),
        'EnableSyncTranscoding': emby_perms.get('media_conversion', False),
        
        # 内容权限
        'EnableContentDeletion': emby_perms.get('content_deletion', False),
        'EnableContentDownloading': emby_perms.get('content_downloading', False),
        'EnableSubtitleDownloading': emby_perms.get('subtitle_download', True),
        'EnableSubtitleManagement': emby_perms.get('subtitle_download', False),
        
        # 设备权限
        'EnableAllDevices': True,
        'EnableSharedDeviceControl': True,
        'EnableRemoteControlOfOtherUsers': False,
        
        # 码率限制
        'RemoteClientBitrateLimit': emby_perms.get('bitrate_limit', 0),
    }
    
    return policy


# ========== 启动向导检查 ==========

@app.before_request
def check_setup():
    """检查是否需要显示启动向导"""
    # 跳过静态文件和API
    if request.path.startswith('/static/') or \
       request.path.startswith('/api/') or \
       request.path == '/favicon.ico':
        return
    
    # 跳过登录、登出和静态资源
    if request.path in ['/login', '/logout', '/register', '/setup-wizard']:
        return
    
    # 检查是否已完成设置
    if not Config.is_setup_complete():
        return redirect(url_for('setup_wizard'))


# ========== 启动向导路由 ==========

@app.route('/setup-wizard')
def setup_wizard():
    """启动向导页面"""
    # 如果已完成设置，重定向到首页
    if Config.is_setup_complete():
        return redirect(url_for('dashboard'))
    return render_template('setup_wizard.html')


@app.route('/api/setup/test-emby', methods=['POST'])
def api_test_emby():
    """测试Emby服务器连接"""
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    api_key = data.get('api_key', '').strip()
    
    if not url or not api_key:
        return jsonify({'success': False, 'error': '请提供服务器地址和API密钥'})
    
    try:
        # 临时使用传入的配置测试
        test_config = {
            'emby_server_url': url.rstrip('/'),
            'emby_api_key': api_key
        }
        import requests
        session = requests.Session()
        session.trust_env = False
        
        # 测试连接
        resp = session.get(
            f"{url.rstrip('/')}/System/Info",
            params={'api_key': api_key},
            timeout=10
        )
        
        if resp.status_code == 200:
            info = resp.json()
            return jsonify({
                'success': True,
                'server_name': info.get('ServerName', 'Emby Server'),
                'version': info.get('Version', 'Unknown')
            })
        elif resp.status_code == 401:
            return jsonify({'success': False, 'error': 'API密钥无效'})
        else:
            return jsonify({'success': False, 'error': f'服务器返回错误: {resp.status_code}'})
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': '连接超时，请检查服务器地址是否正确'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': '无法连接到服务器，请检查地址是否正确'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'连接失败: {str(e)}'})


@app.route('/api/setup/complete', methods=['POST'])
def api_setup_complete():
    """完成启动向导配置"""
    data = request.get_json() or {}
    
    emby_url = data.get('emby_url', '').strip()
    emby_api_key = data.get('emby_api_key', '').strip()
    admin_username = data.get('admin_username', '').strip()
    admin_password = data.get('admin_password', '')
    tmdb_api_key = data.get('tmdb_api_key', '').strip()
    proxy_enabled = data.get('proxy_enabled', False)
    proxy_url = data.get('proxy_url', '').strip()
    douban_fallback = data.get('douban_fallback', True)
    
    # 验证必填项
    if not emby_url or not emby_api_key:
        return jsonify({'success': False, 'error': '请填写Emby服务器配置'})
    
    if not admin_username or len(admin_password) < 1:
        return jsonify({'success': False, 'error': '请填写Emby管理员账户和密码'})
    
    try:
        # 先保存Emby配置（后续认证需要）
        Config.update_emby_config(emby_url, emby_api_key)
        
        # 验证管理员账户在Emby中能否登录
        try:
            emby = get_emby_client()
            auth_result = emby.authenticate_by_name(admin_username, admin_password)
            emby_user = auth_result.get('User', {}) or auth_result
            
            # 检查是否为Emby管理员
            if not emby_user.get('Policy', {}).get('IsAdministrator', False):
                return jsonify({'success': False, 'error': '该Emby账户不是管理员，请使用管理员账户'})
        except Exception as e:
            error_msg = str(e)
            if '401' in error_msg or 'Unauthorized' in error_msg:
                return jsonify({'success': False, 'error': 'Emby用户名或密码错误'})
            return jsonify({'success': False, 'error': f'Emby认证失败: {error_msg}'})
        
        # 保存刮削配置
        Config.update_scraper_config(
            tmdb_api_key=tmdb_api_key if tmdb_api_key else None,
            proxy=proxy_url if proxy_enabled and proxy_url else None,
            proxy_enabled=proxy_enabled,
            douban_fallback=douban_fallback
        )
        
        # 同步管理员信息到本地数据库（不存储密码，登录走 Emby 认证）
        db = get_db()
        
        # 检查管理员用户是否存在
        cursor = db.execute('SELECT id FROM users WHERE username = ?', (admin_username,))
        existing = cursor.fetchone()
        
        if existing:
            db.execute(
                'UPDATE users SET is_admin = 1, display_name = ? WHERE username = ?',
                (admin_username, admin_username)
            )
        else:
            db.execute(
                'INSERT INTO users (username, password_hash, display_name, is_admin) VALUES (?, ?, ?, 1)',
                (admin_username, '', admin_username)
            )
        
        # 清除可能残留的默认admin账户（兼容旧版本升级）
        db.execute('DELETE FROM users WHERE username = ? AND username != ?', 
                   ('admin', admin_username))
        
        db.commit()
        
        # 标记设置完成
        Config.set_setup_complete()
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f'设置保存失败: {e}')
        return jsonify({'success': False, 'error': f'保存失败: {str(e)}'})


# ========== 模板上下文处理 ==========

@app.context_processor
def inject_globals():
    """向所有模板注入全局变量（含主题颜色）"""
    emby = get_emby_client()
    theme_colors = Config.get_theme_colors()
    theme_id = Config.get_theme()
    return {
        'emby_online': emby.ping(),
        'emby_url': Config.get_emby_url(),
        'emby_api_key': Config.get_emby_api_key(),
        'theme_colors': theme_colors,
        'theme_id': theme_id,
        'themes': THEMES,
        'config': Config,
    }


@app.after_request
def add_cache_headers(response):
    """为静态资源添加缓存头"""
    if request.path.startswith('/static/'):
        response.cache_control.max_age = 86400
        response.cache_control.public = True
    return response


# ========== 认证路由 ==========

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # 直接使用 Emby API 认证
        try:
            emby = get_emby_client()
            auth_result = emby.authenticate_by_name(username, password)
            
            emby_user = auth_result.get('User', {}) or auth_result
            emby_user_id = emby_user.get('Id', '')
            is_admin = emby_user.get('Policy', {}).get('IsAdministrator', False)
            is_disabled = emby_user.get('Policy', {}).get('IsDisabled', False)
            display_name = emby_user.get('Name', username)
            
            if is_disabled:
                flash('该账户已被禁用', 'danger')
                return render_template('login.html')
            
            # 同步到本地数据库（保持本地用户记录用于邀请码等功能）
            db = get_db()
            cursor = db.execute('SELECT id FROM users WHERE username = ?', (username,))
            local_user = cursor.fetchone()
            
            if local_user:
                # 更新本地用户的管理员状态和最后登录
                db.execute('UPDATE users SET is_admin = ?, last_login = CURRENT_TIMESTAMP, display_name = ? WHERE username = ?',
                          (1 if is_admin else 0, display_name, username))
            else:
                # 本地不存在则自动创建（不存储密码，登录走 Emby 认证）
                db.execute(
                    'INSERT OR IGNORE INTO users (username, password_hash, display_name, is_admin, is_active) VALUES (?, ?, ?, ?, 1)',
                    (username, '', display_name, 1 if is_admin else 0)
                )
            db.commit()
            
            # 重新获取本地用户ID
            cursor = db.execute('SELECT id, is_admin, display_name FROM users WHERE username = ?', (username,))
            local_user = cursor.fetchone()
            
            # 存储 Emby 用户信息到 session
            session['emby_user_id'] = emby_user_id
            session['emby_access_token'] = auth_result.get('AccessToken', '')
            
            login_user(MediaBoxUser(
                local_user['id'], username, local_user['is_admin'], True, local_user['display_name']
            ))
            flash('登录成功！', 'success')
            next_page = request.args.get('next', url_for('dashboard'))
            return redirect(next_page)
            
        except Exception as e:
            error_msg = str(e)
            if '401' in error_msg or 'Unauthorized' in error_msg:
                flash('用户名或密码错误', 'danger')
            elif 'ConnectionError' in error_msg or '连接' in error_msg:
                flash('无法连接到 Emby 服务器，请检查配置', 'danger')
            else:
                flash(f'登录失败：{error_msg}', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))


# ========== 邀请码管理 ==========

def generate_invite_code(length=8):
    """生成随机邀请码"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


# ========== 权限模板管理 ==========

@app.route('/permission-templates')
@login_required
def permission_templates_page():
    """权限模板管理页面"""
    if not current_user.is_admin:
        flash('需要管理员权限', 'danger')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    cursor = db.execute('''
        SELECT pt.*, u.username as creator_name
        FROM permission_templates pt
        LEFT JOIN users u ON pt.created_by = u.id
        ORDER BY pt.is_default DESC, pt.created_at DESC
    ''')
    templates = [dict(row) for row in cursor.fetchall()]
    
    return render_template('permission_templates.html', templates=templates)


@app.route('/api/templates', methods=['GET'])
@login_required
def api_get_templates():
    """获取所有权限模板"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    db = get_db()
    cursor = db.execute('''
        SELECT * FROM permission_templates ORDER BY is_default DESC, created_at DESC
    ''')
    templates = [dict(row) for row in cursor.fetchall()]
    return jsonify({'templates': templates})


@app.route('/api/templates/<int:template_id>/set-default', methods=['POST'])
@login_required
def api_set_default_template(template_id):
    """设置默认模板"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    db = get_db()
    
    # 取消所有默认
    db.execute('UPDATE permission_templates SET is_default = 0')
    
    # 设置新的默认
    db.execute('UPDATE permission_templates SET is_default = 1 WHERE id = ?', (template_id,))
    db.commit()
    
    return jsonify({'success': True})


@app.route('/api/templates', methods=['POST'])
@login_required
def api_create_template():
    """创建权限模板"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    permissions = data.get('permissions', {})
    
    if not name:
        return jsonify({'error': '模板名称不能为空'}), 400
    
    db = get_db()
    cursor = db.execute('''
        INSERT INTO permission_templates (name, description, permissions, created_by)
        VALUES (?, ?, ?, ?)
    ''', (name, description, json.dumps(permissions), current_user.id))
    db.commit()
    
    return jsonify({
        'success': True,
        'template_id': cursor.lastrowid
    })


@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
@login_required
def api_delete_template(template_id):
    """删除权限模板"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    db = get_db()
    
    # 检查是否是默认模板
    cursor = db.execute('SELECT is_default FROM permission_templates WHERE id = ?', (template_id,))
    row = cursor.fetchone()
    if row and row['is_default']:
        return jsonify({'error': '不能删除默认模板'}), 400
    
    # 检查是否有邀请码使用此模板
    cursor = db.execute('SELECT COUNT(*) as cnt FROM invite_codes WHERE template_id = ?', (template_id,))
    if cursor.fetchone()['cnt'] > 0:
        return jsonify({'error': '有邀请码正在使用此模板'}), 400
    
    db.execute('DELETE FROM permission_templates WHERE id = ?', (template_id,))
    db.commit()
    
    return jsonify({'success': True})


@app.route('/api/templates/<int:template_id>', methods=['PUT'])
@login_required
def api_update_template(template_id):
    """更新权限模板"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    permissions = data.get('permissions', {})
    
    db = get_db()
    db.execute('''
        UPDATE permission_templates SET name = ?, description = ?, permissions = ?
        WHERE id = ?
    ''', (name, description, json.dumps(permissions), template_id))
    db.commit()
    
    return jsonify({'success': True})


@app.route('/api/templates/default')
@login_required
def api_get_default_template():
    """获取默认模板（公开接口，注册页面使用）"""
    db = get_db()
    cursor = db.execute('SELECT * FROM permission_templates WHERE is_default = 1 LIMIT 1')
    row = cursor.fetchone()
    if row:
        return jsonify({'template': dict(row)})
    return jsonify({'template': None})


@app.route('/invite-codes')
@login_required
def invite_codes_page():
    """邀请码管理页面"""
    if not current_user.is_admin:
        flash('需要管理员权限', 'danger')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    # 获取所有邀请码
    cursor = db.execute('''
        SELECT ic.*, u.username as creator_name, u2.username as used_by_name, pt.name as template_name
        FROM invite_codes ic
        LEFT JOIN users u ON ic.created_by = u.id
        LEFT JOIN users u2 ON ic.used_by = u2.id
        LEFT JOIN permission_templates pt ON ic.template_id = pt.id
        ORDER BY ic.created_at DESC
    ''')
    codes = [dict(row) for row in cursor.fetchall()]
    
    # 获取所有用户（用于分配邀请码）
    cursor = db.execute('SELECT id, username, display_name FROM users ORDER BY created_at DESC')
    users = [dict(row) for row in cursor.fetchall()]
    
    # 获取所有权限模板
    cursor = db.execute('SELECT * FROM permission_templates ORDER BY is_default DESC, created_at DESC')
    templates = [dict(row) for row in cursor.fetchall()]
    
    return render_template('invite_codes.html', codes=codes, users=users, templates=templates, now=datetime.now())


@app.route('/api/invite-codes', methods=['GET'])
@login_required
def api_get_invite_codes():
    """获取邀请码列表API"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    db = get_db()
    cursor = db.execute('''
        SELECT ic.*, u.username as creator_name, u2.username as used_by_name
        FROM invite_codes ic
        LEFT JOIN users u ON ic.created_by = u.id
        LEFT JOIN users u2 ON ic.used_by = u2.id
        ORDER BY ic.created_at DESC
    ''')
    codes = [dict(row) for row in cursor.fetchall()]
    
    # 转换日期时间对象为字符串
    for code in codes:
        if code['created_at']:
            code['created_at'] = code['created_at'].isoformat() if hasattr(code['created_at'], 'isoformat') else str(code['created_at'])
        if code['expires_at']:
            code['expires_at'] = code['expires_at'].isoformat() if hasattr(code['expires_at'], 'isoformat') else str(code['expires_at'])
        if code['used_at']:
            code['used_at'] = code['used_at'].isoformat() if hasattr(code['used_at'], 'isoformat') else str(code['used_at'])
    
    return jsonify({'codes': codes})


@app.route('/api/invite-codes', methods=['POST'])
@login_required
def api_create_invite_code():
    """创建邀请码API"""
    log_info(f'[邀请码] 用户 {current_user.username} 请求创建邀请码')
    
    if not current_user.is_admin:
        log_warning(f'[邀请码] 用户 {current_user.username} 无管理员权限')
        return jsonify({'error': '需要管理员权限'}), 403
    
    data = request.get_json() or {}
    max_uses = data.get('max_uses', 1)
    expires_days = data.get('expires_days', 7)  # 默认7天过期
    template_id = data.get('template_id')  # 权限模板ID
    
    code = generate_invite_code()
    expires_at = datetime.now() + timedelta(days=expires_days) if expires_days else None
    
    db = get_db()
    
    # 如果没有指定模板，使用默认模板
    if not template_id:
        cursor = db.execute('SELECT id FROM permission_templates WHERE is_default = 1 LIMIT 1')
        row = cursor.fetchone()
        if row:
            template_id = row['id']
    
    try:
        cursor = db.execute('''
            INSERT INTO invite_codes (code, created_by, max_uses, expires_at, template_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, current_user.id, max_uses, expires_at, template_id))
        db.commit()
        
        # 获取模板名称
        template_name = ''
        if template_id:
            cursor = db.execute('SELECT name FROM permission_templates WHERE id = ?', (template_id,))
            row = cursor.fetchone()
            if row:
                template_name = row['name']
        
        log_info(f'[邀请码] 创建成功: {code}, 有效期: {expires_days}天, 最大使用: {max_uses}次, 模板: {template_name}')
        
        return jsonify({
            'success': True,
            'code': code,
            'max_uses': max_uses,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'template_id': template_id,
            'template_name': template_name
        })
    except sqlite3.IntegrityError:
        log_error(f'[邀请码] 创建失败: 邀请码已存在')
        return jsonify({'error': '邀请码已存在'}), 400
    except Exception as e:
        log_error(f'[邀请码] 创建失败: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/invite-codes/<int:code_id>', methods=['DELETE'])
@login_required
def api_delete_invite_code(code_id):
    """删除邀请码API"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    db = get_db()
    db.execute('DELETE FROM invite_codes WHERE id = ?', (code_id,))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/invite-codes/validate', methods=['POST'])
def api_validate_invite_code():
    """验证邀请码是否有效（用于注册页面）"""
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    
    if not code:
        return jsonify({'valid': False, 'message': '请输入邀请码'})
    
    db = get_db()
    cursor = db.execute('''
        SELECT * FROM invite_codes 
        WHERE code = ? AND is_active = 1 AND use_count < max_uses
    ''', (code,))
    row = cursor.fetchone()
    
    if not row:
        return jsonify({'valid': False, 'message': '邀请码无效或已用完'})
    
    # 检查是否过期
    if row['expires_at'] and row['expires_at'] < datetime.now():
        return jsonify({'valid': False, 'message': '邀请码已过期'})
    
    remaining = row['max_uses'] - row['use_count']
    return jsonify({
        'valid': True,
        'remaining': remaining,
        'expires_at': row['expires_at'].strftime('%Y-%m-%d') if row['expires_at'] else None
    })


# ========== 用户管理 ==========

@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册页面"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        invite_code = request.form.get('invite_code', '').strip().upper()
        display_name = request.form.get('display_name', '').strip()
        
        # 验证输入
        if not username or len(username) < 3:
            flash('用户名至少需要3个字符', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('密码至少需要6个字符', 'danger')
            return render_template('register.html', username=username, display_name=display_name, invite_code=invite_code)
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('register.html', username=username, display_name=display_name, invite_code=invite_code)
        
        # 验证邀请码
        if not invite_code:
            flash('请输入邀请码', 'danger')
            return render_template('register.html', username=username, display_name=display_name)
        
        db = get_db()
        
        # 检查邀请码是否有效
        cursor = db.execute('''
            SELECT * FROM invite_codes 
            WHERE code = ? AND is_active = 1 AND use_count < max_uses
        ''', (invite_code,))
        code_row = cursor.fetchone()
        
        if not code_row:
            flash('邀请码无效或已过期', 'danger')
            return render_template('register.html', username=username, display_name=display_name, invite_code=invite_code)
        
        # 检查邀请码是否过期
        if code_row['expires_at'] and code_row['expires_at'] < datetime.now():
            flash('邀请码已过期', 'danger')
            return render_template('register.html', username=username, display_name=display_name, invite_code=invite_code)
        
        # 检查用户名是否已存在
        cursor = db.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            flash('用户名已存在', 'danger')
            return render_template('register.html', display_name=display_name, invite_code=invite_code)
        
        # 创建本地用户记录（密码由 Emby 管理，本地不存储）
        cursor = db.execute('''
            INSERT INTO users (username, password_hash, display_name, is_admin)
            VALUES (?, ?, ?, 0)
        ''', (username, '', display_name or username))
        user_id = cursor.lastrowid
        
        # 更新邀请码使用次数
        db.execute('''
            UPDATE invite_codes 
            SET use_count = use_count + 1, used_by = ?, used_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id, code_row['id']))
        
        # 如果邀请码使用次数已达上限，禁用它
        db.execute('UPDATE invite_codes SET is_active = 0 WHERE id = ? AND use_count >= max_uses', (code_row['id'],))
        
        # 如果邀请码关联了权限模板，获取模板权限
        emby_policy = {}
        template_id = code_row['template_id']
        if template_id:
            cursor = db.execute('SELECT permissions FROM permission_templates WHERE id = ?', (template_id,))
            template_row = cursor.fetchone()
            if template_row and template_row['permissions']:
                import json
                perms = json.loads(template_row['permissions'])
                emby_policy = permissions_to_emby_policy(perms)
        else:
            # 使用默认模板
            cursor = db.execute('SELECT permissions FROM permission_templates WHERE is_default = 1 LIMIT 1')
            template_row = cursor.fetchone()
            if template_row and template_row['permissions']:
                import json
                perms = json.loads(template_row['permissions'])
                emby_policy = permissions_to_emby_policy(perms)
        
        # 同步创建Emby用户并应用权限
        try:
            emby = get_emby_client()
            emby_user = emby.create_user(username, has_password=bool(password))
            emby_user_id = emby_user.get('Id')
            if emby_user_id and password:
                emby.update_user_password(emby_user_id, '', password)
            if emby_user_id and emby_policy:
                emby.update_user_policy(emby_user_id, emby_policy)
        except Exception as e:
            app.logger.error(f'创建Emby用户失败: {e}')
        
        db.commit()
        
        flash('注册成功！请使用 Emby 账号登录', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/api/users/<user_id>/toggle-admin', methods=['POST'])
@login_required
def api_toggle_admin(user_id):
    """切换Emby用户管理员状态"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    # 不能修改自己的管理员状态
    if user_id == session.get('emby_user_id'):
        return jsonify({'error': '不能修改自己的管理员状态'}), 400
    
    try:
        emby = get_emby_client()
        user = emby.get_user_by_id(user_id)
        policy = user.get('Policy', {})
        policy['IsAdministrator'] = not policy.get('IsAdministrator', False)
        emby.update_user_policy(user_id, policy)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'操作失败: {e}'}), 500


@app.route('/api/users/check-username', methods=['POST'])
def api_check_username():
    """检查用户名是否可用（本地+Emby双检查）"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    
    if not username or len(username) < 3:
        return jsonify({'available': False, 'message': '用户名至少需要3个字符'})
    
    # 检查格式
    import re
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return jsonify({'available': False, 'message': '仅支持字母、数字和下划线'})
    
    # 检查本地数据库
    db = get_db()
    cursor = db.execute('SELECT id FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        return jsonify({'available': False, 'message': '用户名已被占用'})
    
    # 检查Emby端
    try:
        emby = get_emby_client()
        emby_users = emby.get_users()
        for u in emby_users:
            if u.get('Name', '').lower() == username.lower():
                return jsonify({'available': False, 'message': '用户名已被占用'})
    except Exception:
        pass  # Emby不可用时不阻止注册
    
    return jsonify({'available': True, 'message': '用户名可用'})


@app.route('/api/users/<user_id>/toggle-active', methods=['POST'])
@login_required
def api_toggle_active(user_id):
    """切换Emby用户激活状态"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    # 不能禁用自己
    if user_id == session.get('emby_user_id'):
        return jsonify({'error': '不能禁用自己的账户'}), 400
    
    try:
        emby = get_emby_client()
        user = emby.get_user_by_id(user_id)
        policy = user.get('Policy', {})
        policy['IsDisabled'] = not policy.get('IsDisabled', False)
        emby.update_user_policy(user_id, policy)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'操作失败: {e}'}), 500


@app.route('/api/users/<user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    """删除Emby用户"""
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    # 不能删除自己
    if user_id == session.get('emby_user_id'):
        return jsonify({'error': '不能删除自己的账户'}), 400
    
    try:
        emby = get_emby_client()
        emby.delete_user(user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'删除失败: {e}'}), 500


# ========== 仪表盘（使用缓存加速） ==========

@app.route('/')
@login_required
def dashboard():
    emby = get_emby_client()
    system_info = {}
    item_counts = {}
    users = []
    sessions = []
    media_folders = []
    folder_counts = {}

    try:
        system_info = emby.get_system_info()
    except Exception:
        pass
    try:
        item_counts = emby.get_item_counts()
    except Exception:
        pass
    try:
        users = emby.get_users()
    except Exception:
        pass
    try:
        sessions = emby.get_sessions()
    except Exception:
        pass
    try:
        media_folders = emby.get_library_media_folders()
    except Exception:
        pass

    # 获取每个媒体库文件夹的项目数
    admin_user_id = None
    try:
        if users:
            admin_user_id = users[0].get('Id')
    except Exception:
        pass

    for folder in media_folders:
        fid = folder.get('Id')
        # 优先使用ChildCount
        cc = folder.get('ChildCount')
        if cc is not None:
            folder_counts[fid] = cc
        elif fid:
            try:
                data = emby.get_items(
                    parent_id=fid,
                    limit=1,
                    user_id=admin_user_id
                )
                folder_counts[fid] = data.get('TotalRecordCount', 0)
            except Exception:
                pass

    # 过滤活动会话
    active_sessions = [s for s in sessions if s.get('UserName')]

    # 最近添加的内容
    latest_items = []
    try:
        if admin_user_id:
            latest_items = emby.get_latest_items(admin_user_id, limit=16)
    except Exception:
        pass

    # 正在播放的会话
    playing_sessions = [s for s in active_sessions if s.get('NowPlayingItem')]

    # 计算媒体分布（用于饼图）
    media_distribution = []
    total_media = 0
    for key, label, color in [
        ('MovieCount', '电影', '#4da6ff'),
        ('SeriesCount', '剧集', '#66bb6a'),
        ('EpisodeCount', '集数', '#ffa726'),
        ('MusicAlbumCount', '专辑', '#ab47bc'),
        ('BookCount', '书籍', '#ef5350'),
        ('SongCount', '歌曲', '#29b6f6'),
    ]:
        count = item_counts.get(key, 0)
        if count > 0:
            media_distribution.append({'label': label, 'count': count, 'color': color})
            total_media += count

    # 用户统计
    admin_count = sum(1 for u in users if u.get('Policy', {}).get('IsAdministrator', False))
    disabled_count = sum(1 for u in users if u.get('Policy', {}).get('IsDisabled', False))
    active_user_count = len(users) - disabled_count

    # 媒体库总大小估算（从文件夹汇总）
    total_items_in_folders = sum(folder_counts.values())

    # 获取应用配置信息
    emby_server_url = Config.get_emby_url()
    emby_api_key = Config.get_emby_api_key()

    # 启动向导状态（检查是否已完成配置）
    setup_wizard_complete = bool(emby_server_url and emby_api_key)

    return render_template('dashboard.html',
                           system_info=system_info,
                           item_counts=item_counts,
                           users=users,
                           media_folders=media_folders,
                           folder_counts=folder_counts,
                           latest_items=latest_items,
                           playing_sessions=playing_sessions,
                           media_distribution=media_distribution,
                           total_media=total_media,
                           admin_count=admin_count,
                           active_user_count=active_user_count,
                           disabled_user_count=disabled_count,
                           total_items_in_folders=total_items_in_folders,
                           emby_server_url=emby_server_url,
                           emby_api_key=emby_api_key,
                           setup_wizard_complete=setup_wizard_complete)


# ========== 程序日志 ==========

@app.route('/logs')
@login_required
def app_logs():
    """程序日志页面"""
    lines = []
    total_size = 0
    if APP_LOG_FILE.exists():
        total_size = APP_LOG_FILE.stat().st_size
        try:
            with open(APP_LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # 只保留最后500行
            if len(lines) > 500:
                lines = lines[-500:]
                lines.insert(0, f'... (省略了前 {total_size - sum(len(l) for l in lines[-500:]) - 200} 字符)\n')
        except Exception as e:
            lines = [f'读取日志失败: {e}']

    return render_template('logs.html',
                           log_lines=lines,
                           log_file=str(APP_LOG_FILE),
                           total_lines=len(lines),
                           total_size=total_size)


# ========== 用户管理 ==========

@app.route('/users')
@login_required
def users_list():
    """Emby用户管理页面 - 直接对接Emby API"""
    if not current_user.is_admin:
        flash('需要管理员权限', 'danger')
        return redirect(url_for('dashboard'))
    
    emby_users = []
    try:
        emby = get_emby_client()
        emby_users = emby.get_users()
    except Exception as e:
        flash(f'获取Emby用户列表失败: {e}', 'danger')
    
    return render_template('users.html', emby_users=emby_users)


@app.route('/users/create', methods=['GET', 'POST'])
@login_required
def user_create():
    if not current_user.is_admin:
        flash('需要管理员权限', 'danger')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    
    # 获取所有权限模板
    cursor = db.execute('SELECT id, name, permissions, is_default FROM permission_templates ORDER BY is_default DESC, name')
    templates = [dict(row) for row in cursor.fetchall()]
    
    # 获取默认模板ID
    default_template_id = None
    for t in templates:
        if t.get('is_default'):
            default_template_id = t['id']
            break
    if not default_template_id and templates:
        default_template_id = templates[0]['id']
    
    if request.method == 'POST':
        emby = get_emby_client()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        template_id = request.form.get('template_id', '')
        
        if not name:
            flash('用户名不能为空', 'danger')
            return redirect(url_for('user_create'))
        
        try:
            user = emby.create_user(name, has_password=bool(password))
            user_id = user.get('Id')
            if password and user_id:
                emby.update_user_password(user_id, '', password)
            
            # 应用权限模板
            if user_id:
                if template_id:
                    cursor = db.execute('SELECT permissions FROM permission_templates WHERE id = ?', (int(template_id),))
                else:
                    cursor = db.execute('SELECT permissions FROM permission_templates WHERE is_default = 1 LIMIT 1')
                
                template_row = cursor.fetchone()
                if template_row and template_row['permissions']:
                    import json
                    perms = json.loads(template_row['permissions'])
                    emby_policy = permissions_to_emby_policy(perms)
                    emby.update_user_policy(user_id, emby_policy)
            
            flash(f'用户 "{name}" 创建成功', 'success')
            clear_cache()
            return redirect(url_for('users_list'))
        except Exception as e:
            flash(f'创建用户失败: {e}', 'danger')
    
    return render_template('user_create.html', templates=templates, default_template_id=default_template_id)


@app.route('/users/<user_id>')
@login_required
def user_detail(user_id):
    emby = get_emby_client()
    user = {}
    try:
        user = emby.get_user_by_id(user_id)
    except Exception as e:
        flash(f'获取用户信息失败: {e}', 'danger')
    return render_template('user_detail.html', user=user)


@app.route('/users/<user_id>/policy', methods=['GET', 'POST'])
@login_required
def user_policy(user_id):
    if request.method == 'POST':
        emby = get_emby_client()
        policy = {}
        bool_fields = [
            'IsAdministrator', 'IsHidden', 'IsDisabled',
            'EnableRemoteAccess', 'EnableLiveTvManagement', 'EnableLiveTvAccess',
            'EnableMediaPlayback', 'EnableAudioPlaybackTranscoding',
            'EnableVideoPlaybackTranscoding', 'EnablePlaybackRemuxing',
            'EnableContentDeletion', 'EnableContentDownloading',
            'EnableSubtitleDownloading', 'EnableSubtitleManagement',
            'EnableSyncTranscoding', 'EnableMediaConversion',
            'EnableAllDevices', 'EnableSharedDeviceControl',
            'EnableRemoteControlOfOtherUsers'
        ]
        for field in bool_fields:
            policy[field] = request.form.get(field) == 'on'
        int_fields = ['RemoteClientBitrateLimit']
        for field in int_fields:
            val = request.form.get(field, '0')
            try:
                policy[field] = int(val)
            except ValueError:
                policy[field] = 0
        try:
            success = emby.update_user_policy(user_id, policy)
            if success:
                flash('用户策略更新成功', 'success')
            else:
                flash('策略更新可能未生效', 'warning')
        except Exception as e:
            flash(f'更新策略失败: {e}', 'danger')
        clear_cache()
        return redirect(url_for('user_detail', user_id=user_id))

    emby = get_emby_client()
    user = {}
    try:
        user = emby.get_user_by_id(user_id)
    except Exception as e:
        flash(f'获取用户信息失败: {e}', 'danger')
    return render_template('user_policy.html', user=user)


@app.route('/users/<user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    emby = get_emby_client()
    try:
        success = emby.delete_user(user_id)
        if success:
            flash('用户已删除', 'success')
        else:
            flash('删除用户可能未成功', 'warning')
    except Exception as e:
        flash(f'删除用户失败: {e}', 'danger')
    clear_cache()
    return redirect(url_for('users_list'))


@app.route('/users/<user_id>/password', methods=['POST'])
@login_required
def user_password(user_id):
    emby = get_emby_client()
    new_password = request.form.get('new_password', '')
    try:
        emby.update_user_password(user_id, '', new_password)
        flash('密码已重置', 'success')
    except Exception as e:
        flash(f'重置密码失败: {e}', 'danger')
    return redirect(url_for('user_detail', user_id=user_id))


# ========== 媒体库管理 ==========

@app.route('/library')
@login_required
def library_list():
    emby = get_emby_client()
    media_folders = []
    folder_counts = {}
    try:
        media_folders = emby.get_library_media_folders()
    except Exception as e:
        flash(f'获取媒体库列表失败: {e}', 'danger')

    # 获取每个文件夹的项目数
    admin_user_id = None
    try:
        users = emby.get_users()
        if users:
            admin_user_id = users[0].get('Id')
    except Exception:
        pass

    for folder in media_folders:
        fid = folder.get('Id')
        cc = folder.get('ChildCount')
        if cc is not None:
            folder_counts[fid] = cc
        elif fid:
            try:
                data = emby.get_items(
                    parent_id=fid,
                    limit=1,
                    user_id=admin_user_id
                )
                folder_counts[fid] = data.get('TotalRecordCount', 0)
            except Exception:
                pass

    return render_template('library.html', media_folders=media_folders, folder_counts=folder_counts)


@app.route('/library/items')
@login_required
def library_items():
    emby = get_emby_client()
    parent_id = request.args.get('parent_id')
    item_type = request.args.get('item_type', '')
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page_arg = request.args.get('per_page', '24')

    # 处理每页数量
    if per_page_arg == 'all':
        per_page = 999999  # 使用大数字代表"全部"
    else:
        per_page = int(per_page_arg) if per_page_arg.isdigit() else 24

    # 获取管理员用户ID
    admin_user_id = None
    try:
        users = emby.get_users()
        if users:
            admin_user_id = users[0].get('Id')
    except Exception:
        pass

    items_data = {}
    try:
        # 如果没有指定类型，默认只显示媒体文件类型（排除Folder）
        item_types = item_type if item_type else 'Movie,Series,Episode,MusicAlbum,Audio,Book,Video'

        items_data = emby.get_items(
            parent_id=parent_id if parent_id else None,
            item_types=item_types,
            search_term=search if search else None,
            start_index=(page - 1) * per_page if per_page != 999999 else 0,
            limit=per_page,
            fields='Overview,Genres,CommunityRating,OfficialRating,DateCreated',
            sort_by='SortName',
            sort_order='Ascending',
            user_id=admin_user_id
        )
    except Exception as e:
        flash(f'获取媒体项目失败: {e}', 'danger')

    total = items_data.get('TotalRecordCount', 0)
    items = items_data.get('Items', [])
    total_pages = 1 if per_page == 999999 else (total + per_page - 1) // per_page

    return render_template('library_items.html',
                           items=items, total=total, page=page,
                           total_pages=total_pages, parent_id=parent_id,
                           item_type=item_type, search=search,
                           per_page=per_page if per_page != 999999 else 'all')


@app.route('/library/items/<item_id>')
@login_required
def library_item_detail(item_id):
    emby = get_emby_client()
    item = {}
    similar = {}
    # 获取管理员用户ID用于API调用（部分Emby接口需要UserId）
    admin_user_id = None
    try:
        users = emby.get_users()
        if users:
            admin_user_id = users[0].get('Id')
    except Exception:
        pass
    try:
        item = emby.get_item_by_id(item_id, user_id=admin_user_id)
    except Exception as e:
        flash(f'获取项目详情失败: {e}', 'danger')
    try:
        similar = emby.get_similar_items(item_id, limit=6, user_id=admin_user_id)
    except Exception:
        pass
    return render_template('library_item_detail.html',
                           item=item,
                           similar_items=similar.get('Items', []))


@app.route('/library/refresh', methods=['POST'])
@login_required
def library_refresh():
    emby = get_emby_client()
    try:
        emby.refresh_library()
        flash('媒体库刷新已开始', 'success')
    except Exception as e:
        flash(f'刷新媒体库失败: {e}', 'danger')
    clear_cache()
    return redirect(url_for('library_list'))


# ========== STRM 媒体有效性检查 ==========

@app.route('/strm-check')
@login_required
def strm_check():
    """STRM媒体有效性检查页面"""
    emby = get_emby_client()
    media_folders = []
    try:
        media_folders = emby.get_library_media_folders()
    except Exception as e:
        flash(f'获取媒体库列表失败: {e}', 'danger')
    return render_template('strm_check.html', media_folders=media_folders)


@app.route('/api/strm/items')
@login_required
def api_strm_items():
    """获取STRM项目列表（AJAX分页）"""
    emby = get_emby_client()
    parent_id = request.args.get('parent_id', '')
    item_types = request.args.get('item_types', 'Movie,Episode')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 100))
    start_index = (page - 1) * limit

    # 获取管理员用户ID
    admin_user_id = None
    try:
        users = emby.get_users()
        if users:
            admin_user_id = users[0].get('Id')
    except Exception:
        pass

    if not admin_user_id:
        return jsonify({'error': '无法获取用户ID'}), 500

    try:
        result = emby.get_strm_items(
            user_id=admin_user_id,
            parent_id=parent_id if parent_id else None,
            item_types=item_types,
            start_index=start_index,
            limit=limit
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/strm/check-url', methods=['POST'])
@login_required
def api_strm_check_url():
    """检查单个STRM URL的有效性"""
    emby = get_emby_client()
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    item_id = data.get('item_id', '').strip()
    if not url:
        return jsonify({'error': 'URL不能为空'}), 400
    try:
        result = emby.check_strm_url(url, item_id=item_id if item_id else None)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/strm/check-batch', methods=['POST'])
@login_required
def api_strm_check_batch():
    """批量检查STRM URL有效性"""
    emby = get_emby_client()
    data = request.get_json() or {}
    items = data.get('items', [])  # [{url, item_id}]
    timeout = int(data.get('timeout', 15))

    if not items:
        return jsonify({'error': '列表不能为空'}), 400
    if len(items) > 200:
        return jsonify({'error': '单次最多检查200个'}), 400

    results = []
    for item in items:
        url = item.get('url', '')
        item_id = item.get('item_id', '')
        if not url:
            continue
        try:
            result = emby.check_strm_url(url, timeout=timeout, item_id=item_id if item_id else None)
            results.append({'url': url, **result})
        except Exception as e:
            results.append({'url': url, 'status': 'error', 'http_code': 0, 'reason': str(e)[:80]})

    return jsonify({
        'total': len(results),
        'ok': sum(1 for r in results if r['status'] == 'ok'),
        'fail': sum(1 for r in results if r['status'] in ('fail', 'timeout', 'error')),
        'results': results
    })


# ========== Emby 反向代理页面 ==========

@app.route('/emby-proxy', methods=['GET', 'POST'])
@login_required
def emby_proxy_page():
    """Emby反向代理页面"""
    if request.method == 'POST':
        emby_proxy_enabled = request.form.get('emby_proxy_enabled') == 'on'
        emby_proxy_port = request.form.get('emby_proxy_port', '8097').strip()
        try:
            port = int(emby_proxy_port)
            if port < 1 or port > 65535:
                raise ValueError
        except ValueError:
            flash('端口号无效，请输入 1-65535 之间的数字', 'danger')
            return redirect(url_for('emby_proxy_page'))
        
        Config.update_proxy_config(
            emby_proxy_enabled=emby_proxy_enabled,
            emby_proxy_port=port
        )
        restart_proxy_server()
        flash(f'Emby反向代理已{"启用" if emby_proxy_enabled else "关闭"}，端口: {port}', 'success')
        return redirect(url_for('emby_proxy_page'))
    
    return render_template('emby_proxy.html',
                           emby_proxy_enabled=Config.get_emby_proxy_enabled(),
                           emby_proxy_port=Config.get_emby_proxy_port(),
                           proxy_host=request.host.split(':')[0],
                           emby_server_url=Config.get_emby_url())


# ========== 媒体刮削 ==========

# 批量刮削状态（全局变量）
_batch_scrape_state = {
    'running': False,
    'total': 0,
    'completed': 0,
    'success': 0,
    'failed': 0,
    'results': [],
    'stop_flag': False,
}


def get_scraper():
    """获取刮削器实例"""
    tmdb_key = Config.get_tmdb_api_key()
    proxy = Config.get_proxy()
    proxy_enabled = Config.get_proxy_enabled()
    douban = Config.get_douban_fallback()
    return MediaScraper(tmdb_key, proxy, proxy_enabled, douban)


@app.route('/scraper')
@login_required
def media_scraper():
    """媒体刮削页面"""
    emby = get_emby_client()
    media_folders = []
    try:
        media_folders = emby.get_library_media_folders()
    except Exception as e:
        flash(f'获取媒体库列表失败: {e}', 'danger')

    return render_template('scraper.html',
                          media_folders=media_folders,
                          tmdb_api_key=Config.get_tmdb_api_key())


@app.route('/api/scraper/network-test', methods=['POST'])
@login_required
def api_scraper_network_test():
    """测试网络连接"""
    import requests
    data = request.get_json() or {}
    proxy = data.get('proxy', '').strip()
    proxy_enabled = data.get('proxy_enabled', True)
    api_key = data.get('api_key', '').strip()
    target = data.get('target', 'tmdb')  # tmdb / douban

    # 如果代理未启用，不使用代理
    if not proxy_enabled:
        proxy = ''

    results = {
        'proxy_configured': bool(proxy),
        'proxy_enabled': proxy_enabled,
        'proxy_url': proxy if proxy else '未配置（将使用直连）',
        'tests': []
    }

    # 测试目标URL
    if target == 'tmdb':
        test_url = 'https://api.themoviedb.org/3/movie/27205'
        test_name = 'TMDB API'
    else:
        test_url = 'https://www.douban.com'
        test_name = '豆瓣'

    # 准备session
    session = requests.Session()
    session.trust_env = False  # 不使用环境代理
    session.headers.update({
        'User-Agent': 'EmbyManager/1.0',
        'Accept': 'application/json'
    })

    if proxy:
        proxy = proxy if proxy.startswith('http') else 'http://' + proxy
        session.proxies = {'http': proxy, 'https': proxy}

    # 测试1: 代理连接
    if proxy:
        try:
            resp = session.get(proxy.split('://')[0] + '://' + proxy.split('://')[1] if '://' in proxy else proxy,
                             timeout=5)
            results['tests'].append({
                'name': '代理服务器',
                'status': 'success',
                'message': f'代理可达 (HTTP {resp.status_code})'
            })
        except Exception as e:
            results['tests'].append({
                'name': '代理服务器',
                'status': 'error',
                'message': f'无法连接代理: {str(e)}'
            })
            return jsonify(results)

    # 测试2: 目标API
    try:
        params = {'api_key': api_key} if target == 'tmdb' else {}
        resp = session.get(test_url, params=params, timeout=15)
        if resp.status_code == 200:
            results['tests'].append({
                'name': test_name,
                'status': 'success',
                'message': f'连接成功'
            })
            if target == 'tmdb' and api_key:
                # 验证API Key
                data = resp.json()
                if 'status_code' in data and data['status_code'] != 1:
                    results['tests'].append({
                        'name': 'API Key验证',
                        'status': 'error',
                        'message': 'API Key无效'
                    })
                else:
                    results['tests'].append({
                        'name': 'API Key验证',
                        'status': 'success',
                        'message': 'API Key有效'
                    })
        elif resp.status_code == 401:
            results['tests'].append({
                'name': test_name,
                'status': 'warning',
                'message': '连接成功但API Key无效或已过期'
            })
        elif resp.status_code == 429:
            results['tests'].append({
                'name': test_name,
                'status': 'warning',
                'message': '请求过于频繁，请稍后重试'
            })
        else:
            results['tests'].append({
                'name': test_name,
                'status': 'error',
                'message': f'HTTP {resp.status_code}'
            })
    except requests.exceptions.Timeout:
        results['tests'].append({
            'name': test_name,
            'status': 'error',
            'message': '连接超时，请检查代理设置'
        })
    except requests.exceptions.ConnectionError as e:
        results['tests'].append({
            'name': test_name,
            'status': 'error',
            'message': f'连接失败: 无法到达服务器'
        })
    except Exception as e:
        results['tests'].append({
            'name': test_name,
            'status': 'error',
            'message': f'错误: {str(e)}'
        })

    return jsonify(results)


@app.route('/api/scraper/search')
@login_required
def api_scraper_search():
    """搜索刮削媒体信息"""
    title = request.args.get('title', '').strip()
    item_type = request.args.get('type', 'movie')
    year = request.args.get('year', '')
    tmdb_id = request.args.get('tmdb_id', '')

    scraper = get_scraper()

    # 如果提供了TMDB ID，直接获取详情
    if tmdb_id:
        try:
            tmdb_int = int(tmdb_id)
            if item_type == 'movie':
                result = scraper.get_movie_by_id(tmdb_int)
            else:
                result = scraper.get_tv_by_id(tmdb_int)
        except (ValueError, TypeError):
            return jsonify({'error': '无效的TMDB ID'}), 400
    else:
        # 否则按标题搜索
        if not title:
            return jsonify({'error': '请输入搜索标题或TMDB ID'}), 400

        try:
            year_int = int(year) if year else None
        except ValueError:
            year_int = None

        if item_type == 'movie':
            result = scraper.scrape_movie(title, year_int)
        else:
            result = scraper.scrape_tv(title, year_int)

    if result:
        # 检查是否是错误响应
        if 'error' in result:
            return jsonify({
                'error': result['message'] if 'message' in result else '刮削失败',
                'error_code': result.get('error', 'UNKNOWN'),
                'details': '请检查：1. TMDB API Key是否有效 2. 代理设置是否正确 3. 网络连接是否正常'
            }), 400
        return jsonify(result)
    else:
        return jsonify({
            'error': '未找到匹配结果',
            'details': 'TMDB和豆瓣都未找到该媒体，请尝试：1. 使用更精确的标题 2. 提供年份信息 3. 手动在TMDB网站搜索确认是否存在'
        }), 404


@app.route('/api/scraper/library-items')
@login_required
def api_scraper_library_items():
    """获取媒体库项目列表"""
    emby = get_emby_client()
    folder_id = request.args.get('folder_id', '')
    item_type = request.args.get('type', 'Movie,Series')

    # 获取管理员用户ID
    admin_user_id = None
    try:
        users = emby.get_users()
        if users:
            admin_user_id = users[0].get('Id')
    except Exception:
        pass

    if not admin_user_id:
        return jsonify({'error': '无法获取用户ID'}), 500

    try:
        result = emby.get_items(
            user_id=admin_user_id,
            parent_id=folder_id if folder_id else None,
            item_types=item_type,
            recursive=True,
            start_index=0,
            limit=100,
            fields='PrimaryImageAspectRatio,ProductionYear,PremiereDate'
        )

        items = []
        for item in result.get('Items', []):
            items.append({
                'id': item.get('Id'),
                'name': item.get('Name', '未知'),
                'type': item.get('Type', 'Unknown'),
                'year': item.get('ProductionYear', ''),
                'image': emby.get_item_image_url(item.get('Id'), 'Primary', 200) if item.get('Id') else None,
            })

        return jsonify({'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scraper/scrape-item', methods=['POST'])
@login_required
def api_scraper_scrape_item():
    """刮削单个媒体项目"""
    data = request.get_json() or {}
    item_id = data.get('item_id', '')
    auto_apply = data.get('apply', False)  # 是否自动应用到Emby

    if not item_id:
        return jsonify({'error': '请提供项目ID'}), 400

    emby = get_emby_client()
    scraper = get_scraper()

    try:
        # 获取项目信息
        users = emby.get_users()
        admin_user_id = users[0].get('Id') if users else None
        item = emby.get_item_by_id(item_id, admin_user_id)

        title = item.get('Name', '')
        item_type = 'movie' if item.get('Type') == 'Movie' else 'series'
        year = item.get('ProductionYear')

        # 执行刮削
        result = scraper.scrape(title, item_type, year)

        if result:
            # 检查是否是错误响应
            if 'error' in result:
                return jsonify({
                    'error': result.get('message', '刮削失败'),
                    'error_code': result.get('error', 'UNKNOWN'),
                    'title': title,
                    'details': '请检查：1. TMDB API Key是否有效 2. 代理设置是否正确 3. 网络连接是否正常'
                }), 400

            # 如果需要自动应用，记录详细日志
            poster_uploaded = False
            backdrop_uploaded = False
            poster_error = None
            backdrop_error = None
            
            if auto_apply:
                # 获取刮削来源的 TMDB ID
                tmdb_id = result.get('tmdb_id')
                source = result.get('source', '未知')
                
                # 方案1: 如果有 TMDB ID，设置 Provider ID 让 Emby 自动刮削
                if tmdb_id and source == 'TMDB':
                    try:
                        print(f"[刮削应用] 方案1: 设置 TMDB ID {tmdb_id} 让 Emby 自动刮削")
                        provider_set = emby.set_provider_id(item_id, 'Tmdb', str(tmdb_id))
                        
                        if provider_set:
                            print(f"[刮削应用] TMDB ID 设置成功，触发元数据刷新（含图片替换）")
                            # 触发完全刷新让 Emby 自动下载图片
                            refresh_success = emby.refresh_item(
                                item_id,
                                replace_images=True,
                                replace_metadata=True
                            )
                            print(f"[刮削应用] 元数据刷新{'成功' if refresh_success else '失败'}")
                            
                            if refresh_success:
                                # 刷新是异步的，等待 Emby 下载图片
                                print(f"[刮削应用] 等待 Emby 下载图片...")
                                import time as _time
                                has_image = False
                                for attempt in range(6):  # 最多等30秒
                                    _time.sleep(5)
                                    if emby.check_item_has_image(item_id, 'Primary'):
                                        has_image = True
                                        print(f"[刮削应用] 第{attempt+1}次检查：图片已就绪")
                                        break
                                    print(f"[刮削应用] 第{attempt+1}次检查：图片尚未就绪，继续等待...")
                                
                                if has_image:
                                    poster_uploaded = True
                                    backdrop_uploaded = True
                                else:
                                    # 图片还没下载完，但任务已提交
                                    poster_uploaded = True
                                    backdrop_uploaded = True
                                    poster_error = 'TMDB ID 已设置，图片正在后台下载中，请稍后刷新页面查看'
                                    print(f"[刮削应用] 图片仍在下载中，返回异步状态")
                            else:
                                poster_error = 'TMDB ID 已设置，但元数据刷新失败，请手动刷新'
                        else:
                            poster_error = 'TMDB ID 设置失败'
                    except Exception as e:
                        poster_error = f'自动刮削异常: {str(e)}'
                        print(f"[刮削应用] 自动刮削异常: {e}")
                else:
                    # 方案2: 如果没有 TMDB ID 或来源不是 TMDB，尝试手动下载上传
                    print(f"[刮削应用] 无 TMDB ID 或非 TMDB 来源，尝试手动上传")
                    poster_url = result.get('poster_url')
                    
                    if poster_url:
                        try:
                            poster_data = scraper.download_image(poster_url)
                            if poster_data:
                                print(f"[刮削应用] 海报下载成功，大小: {len(poster_data)} bytes")
                                print(f"[刮削应用] 尝试上传到 Emby")
                                poster_uploaded = emby.set_item_poster(item_id, poster_data)
                                print(f"[刮削应用] 二进制上传{'成功' if poster_uploaded else '失败'}")
                                
                                if not poster_uploaded:
                                    poster_error = '海报下载成功但上传失败，可能是 Emby 服务器配置问题'
                            else:
                                poster_error = '海报下载失败，请检查网络连接和代理设置'
                        except Exception as e:
                            poster_error = f'海报应用异常: {str(e)}'
                            print(f"[刮削应用] 海报上传异常: {e}")
                    
                    # 处理背景图
                    if result.get('backdrop_url'):
                        backdrop_url = result.get('backdrop_url')
                        try:
                            backdrop_data = scraper.download_image(backdrop_url)
                            if backdrop_data:
                                backdrop_uploaded = emby.set_item_backdrop(item_id, backdrop_data)
                                print(f"[刮削应用] 背景图{'成功' if backdrop_uploaded else '失败'}")
                                if not backdrop_uploaded:
                                    backdrop_error = '背景图下载成功但上传失败'
                            else:
                                backdrop_error = '背景图下载失败'
                        except Exception as e:
                            backdrop_error = f'背景图异常: {str(e)}'
                            print(f"[刮削应用] 背景图异常: {e}")

            response_data = {
                'success': True,
                'source': result.get('source', '未知'),
                'title': result.get('title', title),
                'poster_url': result.get('poster_url'),
                'overview': result.get('overview'),
                'applied': {
                    'poster': poster_uploaded,
                    'backdrop': backdrop_uploaded,
                }
            }
            
            # 如果有错误，添加到响应中
            if poster_error:
                response_data['poster_error'] = poster_error
            if backdrop_error:
                response_data['backdrop_error'] = backdrop_error
            if poster_error or backdrop_error:
                response_data['manual_guide'] = '请手动在Emby中设置封面：点击媒体库 -> 找到该影片 -> 编辑 -> 海报/背景图'
            
            return jsonify(response_data)
        else:
            return jsonify({
                'error': '未找到匹配结果',
                'title': title,
                'details': 'TMDB和豆瓣都未找到该媒体，建议：1. 检查媒体名称是否正确 2. 确认TMDB收录了该媒体'
            }), 404

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/scraper/batch', methods=['POST'])
@login_required
def api_scraper_batch():
    """启动批量刮削任务"""
    global _batch_scrape_state

    if _batch_scrape_state['running']:
        return jsonify({'error': '已有批量刮削任务在运行'}), 409

    data = request.get_json() or {}
    folder_id = data.get('folder_id', '')
    item_type = data.get('item_type', 'Movie,Series')
    limit = min(int(data.get('limit', 20)), 100)

    # 重置状态
    _batch_scrape_state = {
        'running': True,
        'total': 0,
        'completed': 0,
        'success': 0,
        'failed': 0,
        'results': [],
        'stop_flag': False,
        'folder_id': folder_id,
        'item_type': item_type,
        'limit': limit,
    }

    # 后台执行
    def run_batch():
        global _batch_scrape_state
        emby = get_emby_client()
        scraper = get_scraper()

        try:
            # 获取用户ID
            users = emby.get_users()
            admin_user_id = users[0].get('Id') if users else None
            if not admin_user_id:
                _batch_scrape_state['error'] = '无法获取用户ID'
                return

            # 获取项目列表
            result = emby.get_items(
                user_id=admin_user_id,
                parent_id=folder_id if folder_id else None,
                item_types=item_type,
                recursive=True,
                start_index=0,
                limit=limit,
            )

            items = result.get('Items', [])
            _batch_scrape_state['total'] = len(items)

            for item in items:
                if _batch_scrape_state['stop_flag']:
                    break

                try:
                    title = item.get('Name', '')
                    itype = 'movie' if item.get('Type') == 'Movie' else 'series'
                    year = item.get('ProductionYear')

                    scraped = scraper.scrape(title, itype, year)

                    _batch_scrape_state['completed'] += 1

                    if scraped:
                        _batch_scrape_state['success'] += 1
                        _batch_scrape_state['results'].append({
                            'id': item.get('Id'),
                            'name': title,
                            'type': itype,
                            'source': scraped.get('source', ''),
                            'status': 'success',
                        })
                    else:
                        _batch_scrape_state['failed'] += 1
                        _batch_scrape_state['results'].append({
                            'id': item.get('Id'),
                            'name': title,
                            'type': itype,
                            'source': '',
                            'status': 'failed',
                        })

                except Exception as e:
                    _batch_scrape_state['completed'] += 1
                    _batch_scrape_state['failed'] += 1
                    _batch_scrape_state['results'].append({
                        'name': item.get('Name', ''),
                        'status': 'error',
                        'error': str(e)[:50],
                    })

        except Exception as e:
            _batch_scrape_state['error'] = str(e)
        finally:
            _batch_scrape_state['running'] = False

    thread = threading.Thread(target=run_batch)
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})


@app.route('/api/scraper/batch/status')
@login_required
def api_scraper_batch_status():
    """获取批量刮削状态"""
    global _batch_scrape_state
    return jsonify(_batch_scrape_state)


@app.route('/api/scraper/batch/stop', methods=['POST'])
@login_required
def api_scraper_batch_stop():
    """停止批量刮削"""
    global _batch_scrape_state
    _batch_scrape_state['stop_flag'] = True
    return jsonify({'status': 'stopping'})


@app.route('/library/item/<item_id>/refresh', methods=['POST'])
@login_required
def library_item_refresh(item_id):
    emby = get_emby_client()
    try:
        emby.refresh_item(item_id)
        flash('项目刷新已开始', 'success')
    except Exception as e:
        flash(f'刷新项目失败: {e}', 'danger')
    return redirect(request.referrer or url_for('library_items'))




# ========== 关于页面 ==========

@app.route('/about')
@login_required
def about():
    """关于页面"""
    return render_template('about.html')


# ========== 系统设置 ==========

@app.route('/system')
@login_required
def system_info():
    emby = get_emby_client()
    info = {}
    logs = []
    # 获取本机网络信息
    hostname, local_ips = get_local_ips()
    # 获取应用运行端口
    app_port = request.host.split(':')[-1] if ':' in request.host else '5000'
    
    try:
        info = emby.get_system_info()
    except Exception as e:
        flash(f'获取系统信息失败: {e}', 'danger')
    try:
        logs = emby.get_server_logs()
    except Exception:
        pass
    return render_template('system.html', info=info, logs=logs, 
                           hostname=hostname, local_ips=local_ips, app_port=app_port,
                           sys=sys, flask_version=FLASK_VERSION)


@app.route('/system/restart', methods=['POST'])
@login_required
def system_restart():
    emby = get_emby_client()
    try:
        emby.restart_server()
        flash('重启指令已发送，服务器将在稍后重启', 'warning')
    except Exception as e:
        flash(f'重启失败: {e}', 'danger')
    return redirect(url_for('system_info'))


# ========== 在线设备 ==========

@app.route('/devices')
@login_required
def devices_page():
    """在线设备页面 - 显示所有活动设备和播放状态"""
    emby = get_emby_client()
    sessions = []
    try:
        sessions = emby.get_sessions()
    except Exception as e:
        flash(f'获取设备列表失败: {e}', 'danger')

    # 过滤有用户名的活动会话（在线设备）
    active_devices = [s for s in sessions if s.get('UserName')]

    # 按播放状态分组
    playing = [d for d in active_devices if d.get('NowPlayingItem')]
    idle = [d for d in active_devices if not d.get('NowPlayingItem')]

    return render_template('devices.html',
                          playing_devices=playing,
                          idle_devices=idle,
                          total_devices=len(active_devices))


# ========== 应用设置（Web端配置Emby服务器 + 主题） ==========

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def app_settings():
    """应用设置页面 - Emby服务器配置 + 主题自定义"""
    if request.method == 'POST':
        form_type = request.form.get('form_type', '')

        if form_type == 'emby_config':
            # 更新Emby服务器配置
            server_url = request.form.get('emby_server_url', '').strip()
            api_key = request.form.get('emby_api_key', '').strip()
            if not server_url:
                flash('服务器地址不能为空', 'danger')
            else:
                Config.update_emby_config(server_url, api_key)
                clear_cache()
                flash('Emby服务器配置已更新', 'success')

        elif form_type == 'theme_config':
            # 更新主题
            theme_id = request.form.get('theme_id', 'emby-green')
            custom_colors = {}
            color_fields = ['primary', 'primary-dark', 'primary-light', 'bg-body', 'card-bg', 'text-primary', 'text-secondary', 'border-color']
            for field in color_fields:
                val = request.form.get(f'color_{field}', '').strip()
                if val and val.startswith('#'):
                    custom_colors[field] = val
            Config.update_theme(theme_id, custom_colors if custom_colors else None)
            flash(f'主题已切换为「{THEMES.get(theme_id, {}).get("name", theme_id)}」', 'success')

        elif form_type == 'scraper_config':
            # 更新刮削配置
            tmdb_api_key = request.form.get('tmdb_api_key', '').strip()
            proxy = request.form.get('scraper_proxy', '').strip()
            proxy_enabled = request.form.get('scraper_proxy_enabled') == 'on'
            douban_fallback = request.form.get('douban_fallback') == 'on'
            Config.update_scraper_config(
                tmdb_api_key=tmdb_api_key if tmdb_api_key else None,
                proxy=proxy if proxy else None,
                proxy_enabled=proxy_enabled,
                douban_fallback=douban_fallback
            )
            flash('刮削配置已更新', 'success')

        elif form_type == 'emby_proxy_config':
            # 更新Emby反向代理配置
            proxy_enabled = request.form.get('emby_proxy_enabled') == 'on'
            proxy_port = request.form.get('emby_proxy_port', '8097').strip()
            try:
                proxy_port = int(proxy_port)
                if proxy_port < 1024 or proxy_port > 65535:
                    raise ValueError()
            except:
                flash('端口号无效，请输入 1024-65535 之间的数字', 'danger')
                return redirect(url_for('app_settings'))
            
            Config.update_emby_proxy_config(enabled=proxy_enabled, port=proxy_port)
            # 动态更新反代服务
            update_emby_proxy(enabled=proxy_enabled, port=proxy_port)
            flash('Emby反向代理配置已更新', 'success')

        return redirect(url_for('app_settings'))

    current_url = Config.get_emby_url()
    current_key = Config.get_emby_api_key()
    current_theme = Config.get_theme()
    custom_colors = Config.get_custom_colors()

    # 测试连接
    emby = get_emby_client()
    emby_online = emby.ping()

    return render_template('settings.html',
                           current_url=current_url,
                           current_key=current_key,
                           current_theme=current_theme,
                           custom_colors=custom_colors,
                           theme_colors=Config.get_theme_colors(),
                           themes=THEMES,
                           emby_online=emby_online,
                           tmdb_api_key=Config.get_tmdb_api_key(),
                           scraper_proxy=Config.get_proxy(),
                           scraper_proxy_enabled=Config.get_proxy_enabled(),
                           douban_fallback=Config.get_douban_fallback(),
                           emby_proxy_enabled=Config.get_emby_proxy_enabled(),
                           emby_proxy_port=Config.get_emby_proxy_port())


# ========== API接口（AJAX） ==========

@app.route('/api/status')
@login_required
def api_status():
    emby = get_emby_client()
    return jsonify({
        'online': emby.ping(),
        'server_url': Config.get_emby_url()
    })


@app.route('/api/stats')
@login_required
def api_stats():
    emby = get_emby_client()
    try:
        counts = emby.get_item_counts()
        users = emby.get_users()
        sessions = emby.get_sessions()
        active = [s for s in sessions if s.get('UserName')]
        return jsonify({
            'movies': counts.get('MovieCount', 0),
            'series': counts.get('SeriesCount', 0),
            'episodes': counts.get('EpisodeCount', 0),
            'albums': counts.get('MusicAlbumCount', 0),
            'songs': counts.get('SongCount', 0),
            'books': counts.get('BookCount', 0),
            'users': len(users),
            'active_sessions': len(active)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users')
@login_required
def api_users():
    emby = get_emby_client()
    try:
        users = emby.get_users()
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/library/folders')
@login_required
def api_library_folders():
    emby = get_emby_client()
    try:
        folders = emby.get_library_media_folders()
        return jsonify(folders)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-connection', methods=['POST'])
@login_required
def api_test_connection():
    """测试Emby服务器连接"""
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    key = data.get('api_key', '').strip()
    if not url:
        return jsonify({'success': False, 'message': '地址不能为空'}), 400
    try:
        test_client = EmbyClient(url, key)
        online = test_client.ping()
        if online:
            info = test_client.get_system_info()
            return jsonify({
                'success': True,
                'message': f'连接成功！服务器: {info.get("ServerName", "Unknown")}',
                'server_name': info.get('ServerName', ''),
                'version': info.get('Version', '')
            })
        else:
            return jsonify({'success': False, 'message': '服务器无响应'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'连接失败: {str(e)}'})


@app.route('/api/theme', methods=['POST'])
@login_required
def api_set_theme():
    """AJAX切换主题"""
    data = request.get_json() or {}
    theme_id = data.get('theme_id', 'emby-green')
    custom = data.get('custom_colors', {})
    Config.update_theme(theme_id, custom if custom else None)
    return jsonify({'success': True, 'theme': theme_id})


# ========== Emby 反向代理（独立端口透明代理） ==========

_proxy_server = None  # 全局反代服务器实例
_proxy_thread = None  # 反代线程
_proxy_shutdown_event = None  # 优雅关闭事件


def _start_proxy_server():
    """启动独立端口的 Emby 反向代理服务器"""
    global _proxy_server, _proxy_thread, _proxy_shutdown_event
    
    if not Config.get_emby_proxy_enabled():
        return
    
    port = Config.get_emby_proxy_port()
    emby_url = Config.get_emby_url()
    
    if not emby_url:
        print("[Emby反代] 未配置 Emby 服务器地址，不启动反代")
        return
    
    # 使用独立 Session，不走系统代理
    proxy_session = http_requests.Session()
    proxy_session.trust_env = False
    
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from socketserver import ThreadingMixIn
    from urllib.parse import urlparse, urlencode
    
    # 创建关闭事件，用于优雅停止
    _proxy_shutdown_event = threading.Event()
    
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        """多线程 HTTP 服务器"""
        daemon_threads = True
        allow_reuse_address = True  # 允许地址复用，快速重启
    
    class EmbyProxyHandler(BaseHTTPRequestHandler):
        """透明反向代理 Handler"""
        
        # 需要302直连的路径模式（这些请求由Emby直接处理，不走代理中转）
        REDIRECT_PATTERNS = (
            '/Videos/',      # 视频流/下载
            '/Audio/',       # 音频流
            '/Download/',    # 下载
            '/Videos',       # 视频相关（如 /videos/xxx/stream）
        )
        
        def _should_redirect(self, path):
            """检查是否需要302直连到Emby服务器"""
            path_lower = path.lower()
            for pattern in self.REDIRECT_PATTERNS:
                if pattern.lower() in path_lower:
                    return True
            return False
        
        def _send_redirect(self, target_url):
            """发送302重定向"""
            self.send_response(302)
            self.send_header('Location', target_url)
            self.send_header('Content-Length', '0')
            self.end_headers()
        
        def _proxy_request(self):
            emby = Config.get_emby_url()
            api_key = Config.get_emby_api_key()
            
            # ========== 302直连：视频流、下载等请求直接重定向到Emby ==========
            if self._should_redirect(self.path):
                parsed = urlparse(self.path)
                query = parsed.query
                if api_key and 'api_key' not in query:
                    separator = '&' if query else ''
                    query = query + separator + f'api_key={api_key}'
                target_url = f"{emby}{parsed.path}"
                if query:
                    target_url = f"{target_url}?{query}"
                self._send_redirect(target_url)
                return
            # ==========================================================================
            
            # 构建目标 URL - 透明转发，避免双重编码
            parsed = urlparse(self.path)
            
            # 如果需要注入 api_key，追加到查询字符串末尾
            # 关键：不重新编码已有参数，避免 %2C → %252C 双重编码
            query = parsed.query
            if api_key and 'api_key' not in query:
                separator = '&' if query else ''
                query = query + separator + f'api_key={api_key}'
            
            target_url = f"{emby}{parsed.path}"
            if query:
                target_url = f"{target_url}?{query}"
            
            # 准备转发 headers
            fwd_headers = {}
            # 遍历所有 header 行（保留重复 key 如 Set-Cookie）
            for key, value in self.headers.items():
                key_lower = key.lower()
                # 跳过 hop-by-hop headers
                if key_lower in ('host', 'connection', 'keep-alive',
                                 'proxy-authenticate', 'proxy-authorization',
                                 'te', 'trailers', 'transfer-encoding', 'upgrade',
                                 'accept-encoding'):
                    continue
                # 重写 Origin/Referer 为 Emby 服务器地址，避免 CORS 问题
                if key_lower == 'origin':
                    fwd_headers['Origin'] = emby
                    continue
                if key_lower == 'referer':
                    fwd_headers['Referer'] = f"{emby}/web/index.html"
                    continue
                # 保留其他 header（可能重复 key，用逗号连接）
                if key in fwd_headers:
                    fwd_headers[key] = fwd_headers[key] + ', ' + value
                else:
                    fwd_headers[key] = value
            
            # 设置正确的 Host
            emby_parsed = urlparse(emby)
            fwd_headers['Host'] = emby_parsed.netloc
            # 不请求压缩
            fwd_headers['Accept-Encoding'] = 'identity'
            
            # 读取请求体
            content_length = self.headers.get('Content-Length')
            body = None
            if content_length:
                body = self.rfile.read(int(content_length))
            
            try:
                resp = proxy_session.request(
                    method=self.command,
                    url=target_url,
                    headers=fwd_headers,
                    data=body,
                    allow_redirects=False,
                    timeout=30,
                )
                
                # 处理重定向
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get('Location', '')
                    self.send_response(resp.status_code)
                    self.send_header('Location', location)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                
                # 转发响应
                self.send_response(resp.status_code)
                
                # 转发 headers
                skip_headers = {'transfer-encoding', 'connection', 'keep-alive',
                                'content-encoding', 'content-length',
                                'server', 'date'}
                for key, value in resp.headers.items():
                    if key.lower() not in skip_headers:
                        self.send_header(key, value)
                
                # 发送内容（resp.content 已自动解压）
                content = resp.content
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                
            except http_requests.Timeout:
                self.send_response(504)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Emby server timeout"}')
            except http_requests.ConnectionError:
                self.send_response(502)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Cannot connect to Emby server"}')
            except Exception as e:
                print(f"[Emby反代] 代理错误: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                msg = str(e)[:100].encode('utf-8', errors='replace')
                self.wfile.write(b'{"error": "' + msg + b'"}')
        
        def do_GET(self): self._proxy_request()
        def do_POST(self): self._proxy_request()
        def do_PUT(self): self._proxy_request()
        def do_DELETE(self): self._proxy_request()
        def do_PATCH(self): self._proxy_request()
        def do_HEAD(self): self._proxy_request()
        def do_OPTIONS(self): self._proxy_request()
        
        def log_message(self, format, *args):
            """静默日志，避免刷屏"""
            pass
    
    try:
        _proxy_server = ThreadingHTTPServer(('0.0.0.0', port), EmbyProxyHandler)
        
        def _run():
            print(f"[Emby反代] 透明代理已启动: 0.0.0.0:{port} → {emby_url}")
            # 使用 poll_interval 让 shutdown 事件能及时响应
            _proxy_server.serve_forever(poll_interval=0.5)
            print("[Emby反代] 代理服务器已停止")
        
        _proxy_thread = threading.Thread(target=_run, daemon=True)
        _proxy_thread.start()
        
    except OSError as e:
        if '10048' in str(e) or 'Address already in use' in str(e):
            print(f"[Emby反代] 端口 {port} 已被占用，请更换端口")
        else:
            print(f"[Emby反代] 启动失败: {e}")


def _stop_proxy_server():
    """停止反代服务器"""
    global _proxy_server, _proxy_thread, _proxy_shutdown_event
    
    if _proxy_server:
        # 通知 serve_forever 退出
        _proxy_server.shutdown()
        _proxy_server.server_close()
        _proxy_server = None
    
    # 等待线程结束（最多5秒）
    if _proxy_thread and _proxy_thread.is_alive():
        _proxy_thread.join(timeout=5)
        if _proxy_thread.is_alive():
            print("[Emby反代] 线程未能在5秒内停止")
    _proxy_thread = None
    
    if _proxy_shutdown_event:
        _proxy_shutdown_event.set()
        _proxy_shutdown_event = None
    
    print("[Emby反代] 已停止")


def restart_proxy_server():
    """重启反代服务器（配置变更后调用）"""
    _stop_proxy_server()
    if Config.get_emby_proxy_enabled():
        _start_proxy_server()


def update_emby_proxy(enabled=None, port=None):
    """更新反代服务（供设置页面调用）"""
    if enabled is False:
        # 关闭反代
        _stop_proxy_server()
    elif enabled is True:
        # 启用反代
        if port:
            _stop_proxy_server()
        if not _proxy_server:
            _start_proxy_server()
    elif port is not None:
        # 端口变更需要重启
        if _proxy_server:
            _stop_proxy_server()
            _start_proxy_server()


# ========== 错误处理 ==========

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    import os
    # ========== 单实例保护：启动前杀死旧进程 ==========
    pid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.app.pid')
    old_pid = None
    try:
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
    except (ValueError, IOError):
        old_pid = None
    
    # 杀掉旧进程
    if old_pid:
        try:
            import signal
            os.kill(old_pid, signal.SIGTERM)
            time.sleep(1)
        except (OSError, ProcessLookupError, ValueError):
            pass  # 进程不存在或已结束
    
    # 写入当前PID
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    
    # 启动 Emby 反代服务器
    _start_proxy_server()
    
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
