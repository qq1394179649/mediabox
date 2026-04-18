"""Emby管理系统 - 配置模块（支持Web端动态修改）"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

# 持久化配置文件路径
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')


def _load_settings():
    """从settings.json加载运行时配置（优先于.env）"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_settings(data):
    """保存运行时配置到settings.json"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 预置主题 — 每套主题色系统一，绝不跨色系混搭
THEMES = {
    'emby-green': {
        'name': 'Emby 经典绿',
        'primary': '#52b54b', 'primary-dark': '#3d8b38', 'primary-light': '#6fcf69',
        'primary-glow': 'rgba(82,181,75,.15)',
        'bg-body': '#0d1f10', 'bg-darker': '#091509',
        'sidebar-bg': '#0a1a0d', 'topbar-bg': 'rgba(13,31,16,.9)',
        'topbar-bg-rgb': '13,31,16', 'topbar-accent': 'rgba(82,181,75,.6)',
        'card-bg': '#122618', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(18,38,24,.7)', 'glass-border': 'rgba(82,181,75,.12)',
        'input-bg': '#0e1e12', 'input-bg-focus': '#102414',
        'text-primary': '#e8f5e9', 'text-secondary': '#81c784', 'text-muted': '#5a8a5c',
        'border-color': '#1e3a22', 'border-light': '#2a5230',
        'nav-hover-bg': 'rgba(82,181,75,.08)', 'nav-active-bg': 'rgba(82,181,75,.14)',
        'row-hover-bg': 'rgba(82,181,75,.04)',
        'btn-secondary-bg': 'rgba(82,181,75,.1)',
    },
    'ocean-blue': {
        'name': '深海蓝',
        'primary': '#4da6ff', 'primary-dark': '#2979ff', 'primary-light': '#82b1ff',
        'primary-glow': 'rgba(77,166,255,.15)',
        'bg-body': '#0a1628', 'bg-darker': '#070f1d',
        'sidebar-bg': '#0c1422', 'topbar-bg': 'rgba(10,22,40,.9)',
        'topbar-bg-rgb': '10,22,40', 'topbar-accent': 'rgba(77,166,255,.6)',
        'card-bg': '#0f1f38', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(15,31,56,.7)', 'glass-border': 'rgba(77,166,255,.12)',
        'input-bg': '#0c1828', 'input-bg-focus': '#0e1c30',
        'text-primary': '#e3f2fd', 'text-secondary': '#90caf9', 'text-muted': '#5c8ab5',
        'border-color': '#1a3050', 'border-light': '#254a70',
        'nav-hover-bg': 'rgba(77,166,255,.08)', 'nav-active-bg': 'rgba(77,166,255,.14)',
        'row-hover-bg': 'rgba(77,166,255,.04)',
        'btn-secondary-bg': 'rgba(77,166,255,.1)',
    },
    'sunset-amber': {
        'name': '琥珀日落',
        'primary': '#ffb74d', 'primary-dark': '#ff9800', 'primary-light': '#ffe0b2',
        'primary-glow': 'rgba(255,183,77,.15)',
        'bg-body': '#1a150a', 'bg-darker': '#120e06',
        'sidebar-bg': '#15100a', 'topbar-bg': 'rgba(26,21,10,.9)',
        'topbar-bg-rgb': '26,21,10', 'topbar-accent': 'rgba(255,183,77,.6)',
        'card-bg': '#221c10', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(34,28,16,.7)', 'glass-border': 'rgba(255,183,77,.12)',
        'input-bg': '#1a1508', 'input-bg-focus': '#1e180c',
        'text-primary': '#fff8e1', 'text-secondary': '#ffcc80', 'text-muted': '#a08860',
        'border-color': '#3a3018', 'border-light': '#504420',
        'nav-hover-bg': 'rgba(255,183,77,.08)', 'nav-active-bg': 'rgba(255,183,77,.14)',
        'row-hover-bg': 'rgba(255,183,77,.04)',
        'btn-secondary-bg': 'rgba(255,183,77,.1)',
    },
    'neon-purple': {
        'name': '霓虹紫',
        'primary': '#b388ff', 'primary-dark': '#7c4dff', 'primary-light': '#d1c4e9',
        'primary-glow': 'rgba(179,136,255,.15)',
        'bg-body': '#130c1e', 'bg-darker': '#0d0814',
        'sidebar-bg': '#100a1a', 'topbar-bg': 'rgba(19,12,30,.9)',
        'topbar-bg-rgb': '19,12,30', 'topbar-accent': 'rgba(179,136,255,.6)',
        'card-bg': '#1a1230', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(26,18,48,.7)', 'glass-border': 'rgba(179,136,255,.12)',
        'input-bg': '#150e24', 'input-bg-focus': '#18112a',
        'text-primary': '#f3e5f5', 'text-secondary': '#ce93d8', 'text-muted': '#8a6aa0',
        'border-color': '#2a1a42', 'border-light': '#3a2460',
        'nav-hover-bg': 'rgba(179,136,255,.08)', 'nav-active-bg': 'rgba(179,136,255,.14)',
        'row-hover-bg': 'rgba(179,136,255,.04)',
        'btn-secondary-bg': 'rgba(179,136,255,.1)',
    },
    'mint-green': {
        'name': '薄荷清新',
        'primary': '#26c6da', 'primary-dark': '#00acc1', 'primary-light': '#80deea',
        'primary-glow': 'rgba(38,198,218,.15)',
        'bg-body': '#0a1e1f', 'bg-darker': '#061416',
        'sidebar-bg': '#081a1c', 'topbar-bg': 'rgba(10,30,31,.9)',
        'topbar-bg-rgb': '10,30,31', 'topbar-accent': 'rgba(38,198,218,.6)',
        'card-bg': '#0f2628', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(15,38,40,.7)', 'glass-border': 'rgba(38,198,218,.12)',
        'input-bg': '#0b1e20', 'input-bg-focus': '#0d2224',
        'text-primary': '#e0f7fa', 'text-secondary': '#80deea', 'text-muted': '#5a9ca0',
        'border-color': '#1a383c', 'border-light': '#245050',
        'nav-hover-bg': 'rgba(38,198,218,.08)', 'nav-active-bg': 'rgba(38,198,218,.14)',
        'row-hover-bg': 'rgba(38,198,218,.04)',
        'btn-secondary-bg': 'rgba(38,198,218,.1)',
    },
    'glacier-blue': {
        'name': '冰川蓝',
        'primary': '#4fc3f7', 'primary-dark': '#0288d1', 'primary-light': '#b3e5fc',
        'primary-glow': 'rgba(79,195,247,.15)',
        'bg-body': '#0a1520', 'bg-darker': '#050d14',
        'sidebar-bg': '#081018', 'topbar-bg': 'rgba(10,21,32,.9)',
        'topbar-bg-rgb': '10,21,32', 'topbar-accent': 'rgba(79,195,247,.6)',
        'card-bg': '#0e1e2c', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(14,30,44,.7)', 'glass-border': 'rgba(79,195,247,.12)',
        'input-bg': '#0a1824', 'input-bg-focus': '#0c1c2c',
        'text-primary': '#e1f5fe', 'text-secondary': '#b3e5fc', 'text-muted': '#5a8ab0',
        'border-color': '#1a2a3a', 'border-light': '#244050',
        'nav-hover-bg': 'rgba(79,195,247,.08)', 'nav-active-bg': 'rgba(79,195,247,.14)',
        'row-hover-bg': 'rgba(79,195,247,.04)',
        'btn-secondary-bg': 'rgba(79,195,247,.1)',
    },
    'coral-orange': {
        'name': '珊瑚橙',
        'primary': '#ff8a65', 'primary-dark': '#ff5722', 'primary-light': '#ffccbc',
        'primary-glow': 'rgba(255,138,101,.15)',
        'bg-body': '#1a1208', 'bg-darker': '#120c04',
        'sidebar-bg': '#150f06', 'topbar-bg': 'rgba(26,18,8,.9)',
        'topbar-bg-rgb': '26,18,8', 'topbar-accent': 'rgba(255,138,101,.6)',
        'card-bg': '#201510', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(32,21,16,.7)', 'glass-border': 'rgba(255,138,101,.12)',
        'input-bg': '#1a1006', 'input-bg-focus': '#1e1208',
        'text-primary': '#fff3e0', 'text-secondary': '#ffccbc', 'text-muted': '#a08070',
        'border-color': '#3a2818', 'border-light': '#503a28',
        'nav-hover-bg': 'rgba(255,138,101,.08)', 'nav-active-bg': 'rgba(255,138,101,.14)',
        'row-hover-bg': 'rgba(255,138,101,.04)',
        'btn-secondary-bg': 'rgba(255,138,101,.1)',
    },
    'lavender': {
        'name': '薰衣草',
        'primary': '#9575cd', 'primary-dark': '#7e57c2', 'primary-light': '#d1c4e9',
        'primary-glow': 'rgba(149,117,205,.15)',
        'bg-body': '#12101e', 'bg-darker': '#0a0814',
        'sidebar-bg': '#0e0c18', 'topbar-bg': 'rgba(18,16,30,.9)',
        'topbar-bg-rgb': '18,16,30', 'topbar-accent': 'rgba(149,117,205,.6)',
        'card-bg': '#181428', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(24,20,40,.7)', 'glass-border': 'rgba(149,117,205,.12)',
        'input-bg': '#140e22', 'input-bg-focus': '#16102a',
        'text-primary': '#ede7f6', 'text-secondary': '#d1c4e9', 'text-muted': '#8a7aa8',
        'border-color': '#2a2040', 'border-light': '#3a2860',
        'nav-hover-bg': 'rgba(149,117,205,.08)', 'nav-active-bg': 'rgba(149,117,205,.14)',
        'row-hover-bg': 'rgba(149,117,205,.04)',
        'btn-secondary-bg': 'rgba(149,117,205,.1)',
    },
    'aurora': {
        'name': '极光',
        'primary': '#69f0ae', 'primary-dark': '#00e676', 'primary-light': '#b9f6ca',
        'primary-glow': 'rgba(105,240,174,.15)',
        'bg-body': '#0a1a14', 'bg-darker': '#06100c',
        'sidebar-bg': '#081612', 'topbar-bg': 'rgba(10,26,20,.9)',
        'topbar-bg-rgb': '10,26,20', 'topbar-accent': 'rgba(105,240,174,.6)',
        'card-bg': '#0f241c', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(15,36,28,.7)', 'glass-border': 'rgba(105,240,174,.12)',
        'input-bg': '#0b1e16', 'input-bg-focus': '#0d221a',
        'text-primary': '#e8f5e9', 'text-secondary': '#b9f6ca', 'text-muted': '#5a9a7a',
        'border-color': '#1a3830', 'border-light': '#245040',
        'nav-hover-bg': 'rgba(105,240,174,.08)', 'nav-active-bg': 'rgba(105,240,174,.14)',
        'row-hover-bg': 'rgba(105,240,174,.04)',
        'btn-secondary-bg': 'rgba(105,240,174,.1)',
    },
    'sunrise-gold': {
        'name': '日出金',
        'primary': '#ffd54f', 'primary-dark': '#ffc107', 'primary-light': '#fff9c4',
        'primary-glow': 'rgba(255,213,79,.15)',
        'bg-body': '#1a180a', 'bg-darker': '#120f04',
        'sidebar-bg': '#151206', 'topbar-bg': 'rgba(26,24,10,.9)',
        'topbar-bg-rgb': '26,24,10', 'topbar-accent': 'rgba(255,213,79,.6)',
        'card-bg': '#201e10', 'card-header-bg': 'rgba(0,0,0,.2)',
        'glass-bg': 'rgba(32,30,16,.7)', 'glass-border': 'rgba(255,213,79,.12)',
        'input-bg': '#1a1806', 'input-bg-focus': '#1e1c08',
        'text-primary': '#fffde7', 'text-secondary': '#fff9c4', 'text-muted': '#a09860',
        'border-color': '#3a3818', 'border-light': '#504a28',
        'nav-hover-bg': 'rgba(255,213,79,.08)', 'nav-active-bg': 'rgba(255,213,79,.14)',
        'row-hover-bg': 'rgba(255,213,79,.04)',
        'btn-secondary-bg': 'rgba(255,213,79,.1)',
    },
    'light-mode': {
        'name': '明亮模式',
        'primary': '#4caf50', 'primary-dark': '#388e3c', 'primary-light': '#81c784',
        'primary-glow': 'rgba(76,175,80,.1)',
        'bg-body': '#f5f7f8', 'bg-darker': '#e8eaec',
        'sidebar-bg': '#ffffff', 'topbar-bg': 'rgba(255,255,255,.98)',
        'topbar-bg-rgb': '255,255,255', 'topbar-accent': 'rgba(76,175,80,.6)',
        'card-bg': '#ffffff', 'card-header-bg': 'rgba(0,0,0,.03)',
        'glass-bg': 'rgba(255,255,255,.85)', 'glass-border': 'rgba(0,0,0,.06)',
        'input-bg': '#f0f2f4', 'input-bg-focus': '#ffffff',
        'text-primary': '#1a2e1c', 'text-secondary': '#4caf50', 'text-muted': '#7a9a7c',
        'border-color': '#dde0dc', 'border-light': '#c8ccc0',
        'nav-hover-bg': 'rgba(76,175,80,.06)', 'nav-active-bg': 'rgba(76,175,80,.1)',
        'row-hover-bg': 'rgba(76,175,80,.04)',
        'btn-secondary-bg': '#f0f4f0',
    },
    'light-pink': {
        'name': '明亮粉',
        'primary': '#e91e8c', 'primary-dark': '#c2185b', 'primary-light': '#f8bbd0',
        'primary-glow': 'rgba(233,30,140,.1)',
        'bg-body': '#fdf2f6', 'bg-darker': '#f8e4ec',
        'sidebar-bg': '#ffffff', 'topbar-bg': 'rgba(255,255,255,.98)',
        'topbar-bg-rgb': '255,255,255', 'topbar-accent': 'rgba(233,30,140,.6)',
        'card-bg': '#ffffff', 'card-header-bg': 'rgba(0,0,0,.03)',
        'glass-bg': 'rgba(255,255,255,.85)', 'glass-border': 'rgba(233,30,140,.08)',
        'input-bg': '#fceef3', 'input-bg-focus': '#ffffff',
        'text-primary': '#3a1528', 'text-secondary': '#e91e8c', 'text-muted': '#b08098',
        'border-color': '#f0d0dc', 'border-light': '#e8b8ca',
        'nav-hover-bg': 'rgba(233,30,140,.06)', 'nav-active-bg': 'rgba(233,30,140,.1)',
        'row-hover-bg': 'rgba(233,30,140,.04)',
        'btn-secondary-bg': '#fceef3',
    },
}


class Config:
    """基础配置 - 支持从settings.json动态读取"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')

    # 管理面板账户
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

    # Flask配置
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    @staticmethod
    def get_emby_url():
        """获取当前Emby服务器地址"""
        s = _load_settings()
        return s.get('emby_server_url', os.getenv('EMBY_SERVER_URL', 'http://localhost:8096')).rstrip('/')

    @staticmethod
    def get_emby_api_key():
        """获取当前Emby API密钥"""
        s = _load_settings()
        return s.get('emby_api_key', os.getenv('EMBY_API_KEY', ''))

    @staticmethod
    def get_theme():
        """获取当前主题ID"""
        s = _load_settings()
        return s.get('theme', 'light-mode')

    @staticmethod
    def get_custom_colors():
        """获取自定义颜色覆盖"""
        s = _load_settings()
        return s.get('custom_colors', {})

    @staticmethod
    def is_setup_complete():
        """检查是否已完成初始设置"""
        s = _load_settings()
        # 优先使用标记值
        if 'setup_complete' in s:
            return s.get('setup_complete', False)
        # 如果没有标记，检查是否有有效的Emby配置（兼容旧版本或数据迁移场景）
        return bool(s.get('emby_server_url') and s.get('emby_api_key'))
    
    @staticmethod
    def has_valid_config():
        """检查是否有有效的配置"""
        s = _load_settings()
        return bool(s.get('emby_server_url') and s.get('emby_api_key'))
    
    @staticmethod
    def set_setup_complete():
        """标记初始设置已完成"""
        s = _load_settings()
        s['setup_complete'] = True
        _save_settings(s)
    
    @staticmethod
    def _load_settings():
        """加载设置（供外部调用）"""
        return _load_settings()
    
    @staticmethod
    def update_emby_config(url, api_key):
        """更新Emby服务器配置"""
        s = _load_settings()
        s['emby_server_url'] = url.rstrip('/')
        s['emby_api_key'] = api_key
        _save_settings(s)

    @staticmethod
    def update_theme(theme_id, custom_colors=None):
        """更新主题配置"""
        s = _load_settings()
        s['theme'] = theme_id
        if custom_colors:
            s['custom_colors'] = custom_colors
        else:
            s.pop('custom_colors', None)
        _save_settings(s)

    @staticmethod
    def get_theme_colors():
        """获取当前主题的完整颜色变量（合并自定义覆盖）"""
        theme_id = Config.get_theme()
        base = THEMES.get(theme_id, THEMES['emby-green']).copy()
        # 移除name字段
        base.pop('name', None)
        # 合并自定义颜色覆盖
        custom = Config.get_custom_colors()
        base.update(custom)
        return base

    @staticmethod
    def get_tmdb_api_key():
        """获取TMDB API密钥"""
        s = _load_settings()
        return s.get('tmdb_api_key', '')

    @staticmethod
    def get_proxy():
        """获取代理设置"""
        s = _load_settings()
        return s.get('scraper_proxy', '')

    @staticmethod
    def get_proxy_enabled():
        """获取是否启用代理"""
        s = _load_settings()
        return s.get('scraper_proxy_enabled', True)

    @staticmethod
    def get_douban_fallback():
        """获取是否启用豆瓣备选刮削"""
        s = _load_settings()
        return s.get('douban_fallback', True)

    @staticmethod
    def get_emby_proxy_enabled():
        """获取是否启用Emby反向代理"""
        s = _load_settings()
        return s.get('emby_proxy_enabled', False)

    @staticmethod
    def get_emby_proxy_port():
        """获取Emby反向代理端口"""
        s = _load_settings()
        return s.get('emby_proxy_port', 8097)

    @staticmethod
    def update_emby_proxy_config(enabled=None, port=None):
        """更新Emby反向代理配置"""
        s = _load_settings()
        if enabled is not None:
            s['emby_proxy_enabled'] = enabled
        if port is not None:
            s['emby_proxy_port'] = port
        _save_settings(s)

    @staticmethod
    def update_scraper_config(tmdb_api_key=None, proxy=None, proxy_enabled=None, douban_fallback=None):
        """更新刮削配置"""
        s = _load_settings()
        if tmdb_api_key is not None:
            s['tmdb_api_key'] = tmdb_api_key
        if proxy is not None:
            s['scraper_proxy'] = proxy
        if proxy_enabled is not None:
            s['scraper_proxy_enabled'] = proxy_enabled
        if douban_fallback is not None:
            s['douban_fallback'] = douban_fallback
        _save_settings(s)

    @staticmethod
    def update_proxy_config(emby_proxy_enabled=None, emby_proxy_port=None):
        """更新反向代理配置"""
        s = _load_settings()
        if emby_proxy_enabled is not None:
            s['emby_proxy_enabled'] = emby_proxy_enabled
        if emby_proxy_port is not None:
            s['emby_proxy_port'] = emby_proxy_port
        _save_settings(s)

    # 兼容旧代码
    EMBY_SERVER_URL = property(lambda self: Config.get_emby_url())
    EMBY_API_KEY = property(lambda self: Config.get_emby_api_key())
