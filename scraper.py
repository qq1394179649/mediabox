"""媒体刮削客户端 - 支持TMDB和豆瓣"""
import requests
import time
from typing import Optional, Dict, List, Any


class TMDbScraper:
    """TMDB刮削器"""

    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str, proxy: str = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.trust_env = False  # 不使用环境变量中的代理
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'EmbyManager/1.0',
        })
        if proxy:
            # 确保使用HTTP代理协议
            proxy = proxy.strip()
            if not proxy.startswith('http'):
                proxy = 'http://' + proxy
            self.session.proxies = {
                'http': proxy,
                'https': proxy,
            }
        # 禁用SSL警告
        requests.packages.urllib3.disable_warnings()

    def search_movie(self, title: str, year: int = None, language: str = 'zh-CN') -> Optional[Dict]:
        """搜索电影

        Args:
            title: 电影标题
            year: 上映年份（可选）
            language: 语言设置

        Returns:
            搜索结果列表或错误信息
        """
        if not self.api_key:
            return {'error': 'TMDB_API_KEY_MISSING', 'message': 'TMDB API Key未配置'}

        params = {
            'api_key': self.api_key,
            'query': title,
            'language': language,
        }
        if year:
            params['primary_release_year'] = year

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/search/movie",
                params=params,
                timeout=15
            )
            if resp.status_code == 401:
                return {'error': 'TMDB_API_INVALID', 'message': 'TMDB API Key无效或已过期'}
            if resp.status_code == 429:
                return {'error': 'TMDB_API_RATE_LIMIT', 'message': 'TMDB API请求过于频繁，请稍后重试'}
            if resp.status_code != 200:
                return {'error': 'TMDB_API_ERROR', 'message': f'TMDB API错误: HTTP {resp.status_code}'}

            data = resp.json()
            results = data.get('results', [])
            if results:
                # 返回最相关的结果
                return {'result': results[0]}
            return None
        except requests.exceptions.Timeout:
            return {'error': 'TIMEOUT', 'message': '请求超时，请检查网络或代理设置'}
        except requests.exceptions.ConnectionError as e:
            return {'error': 'CONNECTION_ERROR', 'message': f'网络连接失败: 无法连接到TMDB，请检查代理设置'}
        except Exception as e:
            return {'error': 'UNKNOWN', 'message': f'未知错误: {str(e)}'}

    def search_tv(self, title: str, year: int = None, language: str = 'zh-CN') -> Optional[Dict]:
        """搜索电视剧

        Args:
            title: 电视剧标题
            year: 首播年份（可选）
            language: 语言设置

        Returns:
            搜索结果或错误信息
        """
        if not self.api_key:
            return {'error': 'TMDB_API_KEY_MISSING', 'message': 'TMDB API Key未配置'}

        params = {
            'api_key': self.api_key,
            'query': title,
            'language': language,
        }
        if year:
            params['first_air_date_year'] = year

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/search/tv",
                params=params,
                timeout=15
            )
            if resp.status_code == 401:
                return {'error': 'TMDB_API_INVALID', 'message': 'TMDB API Key无效或已过期'}
            if resp.status_code == 429:
                return {'error': 'TMDB_API_RATE_LIMIT', 'message': 'TMDB API请求过于频繁，请稍后重试'}
            if resp.status_code != 200:
                return {'error': 'TMDB_API_ERROR', 'message': f'TMDB API错误: HTTP {resp.status_code}'}

            data = resp.json()
            results = data.get('results', [])
            if results:
                return {'result': results[0]}
            return None
        except requests.exceptions.Timeout:
            return {'error': 'TIMEOUT', 'message': '请求超时，请检查网络或代理设置'}
        except requests.exceptions.ConnectionError:
            return {'error': 'CONNECTION_ERROR', 'message': '网络连接失败，无法连接到TMDB，请检查代理设置'}
        except Exception as e:
            return {'error': 'UNKNOWN', 'message': f'未知错误: {str(e)}'}

    def get_movie_details(self, tmdb_id: int, language: str = 'zh-CN') -> Optional[Dict]:
        """获取电影详情

        Args:
            tmdb_id: TMDB电影ID
            language: 语言设置

        Returns:
            电影详情
        """
        if not self.api_key:
            return None

        params = {
            'api_key': self.api_key,
            'language': language,
            'append_to_response': 'credits,images',
        }

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/movie/{tmdb_id}",
                params=params,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                # 添加tmdb_id字段
                data['tmdb_id'] = tmdb_id
                # 格式化返回数据
                return self._format_movie_result(data)
            return None
        except Exception:
            return None

    def get_tv_details(self, tmdb_id: int, language: str = 'zh-CN') -> Optional[Dict]:
        """获取电视剧详情

        Args:
            tmdb_id: TMDB电视剧ID
            language: 语言设置

        Returns:
            电视剧详情
        """
        if not self.api_key:
            return None

        params = {
            'api_key': self.api_key,
            'language': language,
            'append_to_response': 'credits,images,external_ids',
        }

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/tv/{tmdb_id}",
                params=params,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                # 添加tmdb_id字段
                data['tmdb_id'] = tmdb_id
                # 格式化返回数据
                return self._format_tv_result(data)
            return None
        except Exception:
            return None

    def get_tv_season(self, tmdb_id: int, season_number: int, language: str = 'zh-CN') -> Optional[Dict]:
        """获取电视剧季详情

        Args:
            tmdb_id: TMDB电视剧ID
            season_number: 季号
            language: 语言设置

        Returns:
            季详情
        """
        if not self.api_key:
            return None

        params = {
            'api_key': self.api_key,
            'language': language,
        }

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/tv/{tmdb_id}/season/{season_number}",
                params=params,
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def get_image_url(self, path: str, size: str = 'w500') -> str:
        """获取TMDB图片URL

        Args:
            path: 图片路径
            size: 图片尺寸

        Returns:
            完整图片URL
        """
        if not path:
            return ''
        return f"https://image.tmdb.org/t/p/{size}{path}"

    def scrape_movie(self, title: str, year: int = None) -> Optional[Dict]:
        """刮削电影信息

        Args:
            title: 电影标题
            year: 上映年份（可选）

        Returns:
            刮削结果
        """
        result = self.search_movie(title, year)
        if not result:
            return None

        tmdb_id = result.get('id')
        details = self.get_movie_details(tmdb_id)
        if not details:
            return None

        return details  # get_movie_details已经格式化了结果

    def _format_movie_result(self, details: Dict) -> Dict:
        """格式化电影详情结果"""
        tmdb_id = details.get('id')
        scraped = {
            'source': 'TMDB',
            'title': details.get('title', ''),
            'original_title': details.get('original_title', ''),
            'overview': details.get('overview', ''),
            'poster_url': self.get_image_url(details.get('poster_path')),
            'backdrop_url': self.get_image_url(details.get('backdrop_path'), 'w1280'),
            'release_date': details.get('release_date', ''),
            'runtime': details.get('runtime', 0),
            'vote_average': details.get('vote_average', 0),
            'genres': [g.get('name', '') for g in details.get('genres', [])],
            'tmdb_id': tmdb_id,
            'imdb_id': details.get('imdb_id', ''),
            'tagline': details.get('tagline', ''),
            'budget': details.get('budget', 0),
            'revenue': details.get('revenue', 0),
            'status': details.get('status', ''),
        }

        # 添加导演信息
        credits = details.get('credits', {})
        directors = [c.get('name') for c in credits.get('crew', []) if c.get('job') == 'Director']
        scraped['director'] = directors[0] if directors else ''

        return scraped

    def scrape_tv(self, title: str, year: int = None) -> Optional[Dict]:
        """刮削电视剧信息

        Args:
            title: 电视剧标题
            year: 首播年份（可选）

        Returns:
            刮削结果
        """
        result = self.search_tv(title, year)
        if not result:
            return None

        tmdb_id = result.get('id')
        details = self.get_tv_details(tmdb_id)
        if not details:
            return None

        return details  # get_tv_details已经格式化了结果

    def _format_tv_result(self, details: Dict) -> Dict:
        """格式化电视剧详情结果"""
        scraped = {
            'source': 'TMDB',
            'title': details.get('name', ''),
            'original_title': details.get('original_name', ''),
            'overview': details.get('overview', ''),
            'poster_url': self.get_image_url(details.get('poster_path')),
            'backdrop_url': self.get_image_url(details.get('backdrop_path'), 'w1280'),
            'first_air_date': details.get('first_air_date', ''),
            'last_air_date': details.get('last_air_date', ''),
            'episode_run_time': details.get('episode_run_time', []),
            'vote_average': details.get('vote_average', 0),
            'genres': [g.get('name', '') for g in details.get('genres', [])],
            'tmdb_id': details.get('id'),
            'imdb_id': details.get('external_ids', {}).get('imdb_id', ''),
            'number_of_seasons': details.get('number_of_seasons', 0),
            'number_of_episodes': details.get('number_of_episodes', 0),
            'status': details.get('status', ''),
        }

        # 添加创作者信息
        credits = details.get('credits', {})
        creators = [c.get('name') for c in credits.get('created_by', [])]
        scraped['creator'] = creators[0] if creators else ''

        return scraped


class DoubanScraper:
    """豆瓣刮削器（备选）"""

    BASE_URL = "https://www.douban.com"

    def __init__(self, proxy: str = None):
        self.session = requests.Session()
        self.session.trust_env = False  # 不使用环境变量中的代理
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })
        if proxy:
            # 确保使用HTTP代理协议
            proxy = proxy.strip()
            if not proxy.startswith('http'):
                proxy = 'http://' + proxy
            self.session.proxies = {
                'http': proxy,
                'https': proxy,
            }
        requests.packages.urllib3.disable_warnings()

    def search(self, keyword: str, item_type: str = 'movie') -> Optional[Dict]:
        """搜索电影或电视剧

        Args:
            keyword: 搜索关键词
            item_type: 类型 'movie' 或 'tv'

        Returns:
            搜索结果
        """
        search_url = f"{self.BASE_URL}/search/"
        params = {
            'q': keyword,
            'cat': '1002' if item_type == 'movie' else '1003',
        }

        try:
            resp = self.session.get(search_url, params=params, timeout=15)
            if resp.status_code != 200:
                return None

            # 解析搜索结果（简化版，实际可能需要更复杂的解析）
            text = resp.text
            # 寻找第一个结果
            import re
            pattern = r'href="(https://movie\.douban\.com/subject/(\d+)/)"[^>]*>([^<]+)'
            matches = re.findall(pattern, text)
            if matches:
                url, douban_id, title = matches[0]
                return {
                    'id': douban_id,
                    'url': url,
                    'title': title.strip(),
                }
            return None
        except Exception:
            return None

    def get_details(self, douban_id: str) -> Optional[Dict]:
        """获取详情页信息

        Args:
            douban_id: 豆瓣ID

        Returns:
            详细信息
        """
        url = f"{self.BASE_URL}/subject/{douban_id}/"

        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return None

            text = resp.text
            import re

            scraped = {
                'source': '豆瓣',
                'douban_id': douban_id,
            }

            # 提取标题
            title_match = re.search(r'<title>([^<]+)</title>', text)
            if title_match:
                scraped['title'] = title_match.group(1).replace('(豆瓣)', '').strip()

            # 提取简介
            summary_match = re.search(r'<span class="short">(.*?)</span>', text, re.DOTALL)
            if summary_match:
                scraped['overview'] = summary_match.group(1).strip()
            else:
                overview_match = re.search(r'"description"\s*:\s*"([^"]+)"', text)
                if overview_match:
                    scraped['overview'] = overview_match.group(1)

            # 提取评分
            rating_match = re.search(r'class="ll rating_num"[^>]*>([^<]+)</span>', text)
            if rating_match:
                scraped['vote_average'] = float(rating_match.group(1))

            # 提取年份
            year_match = re.search(r'(\d{4})</span>', text)
            if year_match:
                scraped['year'] = year_match.group(1)

            # 提取海报
            poster_match = re.search(r'"image"\s*:\s*"([^"]+)"', text)
            if poster_match:
                scraped['poster_url'] = poster_match.group(1)

            return scraped
        except Exception:
            return None

    def scrape(self, keyword: str, item_type: str = 'movie') -> Optional[Dict]:
        """刮削信息

        Args:
            keyword: 搜索关键词
            item_type: 类型

        Returns:
            刮削结果
        """
        search_result = self.search(keyword, item_type)
        if not search_result:
            return None

        return self.get_details(search_result['id'])


class MediaScraper:
    """统一的媒体刮削器，优先TMDB，失败时使用豆瓣"""

    def __init__(self, tmdb_api_key: str = None, proxy: str = None, proxy_enabled: bool = True, use_douban: bool = True):
        # 只有启用代理时才传递 proxy
        actual_proxy = proxy if proxy_enabled and proxy else None
        self.tmdb = TMDbScraper(tmdb_api_key, actual_proxy) if tmdb_api_key else None
        self.douban = DoubanScraper(actual_proxy) if use_douban else None
        self.use_douban = use_douban
        print(f"[MediaScraper] 初始化 - proxy_enabled={proxy_enabled}, actual_proxy={actual_proxy}")

    def scrape_movie(self, title: str, year: int = None) -> Optional[Dict]:
        """刮削电影

        Args:
            title: 电影标题
            year: 上映年份

        Returns:
            刮削结果或错误信息
        """
        last_error = None
        
        # 优先TMDB - 尝试多种策略
        if self.tmdb:
            # 策略1: 中文搜索
            search_result = self.tmdb.search_movie(title, year, 'zh-CN')
            if search_result:
                if 'error' in search_result:
                    last_error = search_result
                    # 如果是API配置问题，直接返回错误
                    if search_result['error'] in ('TMDB_API_KEY_MISSING', 'TMDB_API_INVALID', 'TMDB_API_RATE_LIMIT'):
                        return search_result
                else:
                    # 找到结果，获取详情
                    tmdb_id = search_result['result'].get('id')
                    details = self.tmdb.get_movie_details(tmdb_id)
                    if details:
                        return details
                    last_error = {'error': 'DETAILS_FETCH_FAILED', 'message': '获取电影详情失败'}

            # 策略2: 英文搜索（如果中文没找到）
            if not search_result or (isinstance(search_result, dict) and 'error' in search_result):
                search_result_en = self.tmdb.search_movie(title, year, 'en-US')
                if search_result_en and 'result' in search_result_en:
                    tmdb_id = search_result_en['result'].get('id')
                    details = self.tmdb.get_movie_details(tmdb_id)
                    if details:
                        return details

        # 回退豆瓣
        if self.douban:
            try:
                result = self.douban.scrape(title, 'movie')
                if result:
                    return result
            except Exception:
                pass

        # 如果有详细错误信息，返回它
        if last_error:
            return last_error
        
        return None

    def scrape_tv(self, title: str, year: int = None) -> Optional[Dict]:
        """刮削电视剧

        Args:
            title: 电视剧标题
            year: 首播年份

        Returns:
            刮削结果或错误信息
        """
        last_error = None
        
        # 优先TMDB - 尝试多种策略
        if self.tmdb:
            # 策略1: 中文搜索
            search_result = self.tmdb.search_tv(title, year, 'zh-CN')
            if search_result:
                if 'error' in search_result:
                    last_error = search_result
                    # 如果是API配置问题，直接返回错误
                    if search_result['error'] in ('TMDB_API_KEY_MISSING', 'TMDB_API_INVALID', 'TMDB_API_RATE_LIMIT'):
                        return search_result
                else:
                    # 找到结果，获取详情
                    tmdb_id = search_result['result'].get('id')
                    details = self.tmdb.get_tv_details(tmdb_id)
                    if details:
                        return details
                    last_error = {'error': 'DETAILS_FETCH_FAILED', 'message': '获取电视剧详情失败'}

            # 策略2: 英文搜索（如果中文没找到）
            if not search_result or (isinstance(search_result, dict) and 'error' in search_result):
                search_result_en = self.tmdb.search_tv(title, year, 'en-US')
                if search_result_en and 'result' in search_result_en:
                    tmdb_id = search_result_en['result'].get('id')
                    details = self.tmdb.get_tv_details(tmdb_id)
                    if details:
                        return details

        # 回退豆瓣
        if self.douban:
            try:
                result = self.douban.scrape(title, 'tv')
                if result:
                    return result
            except Exception:
                pass

        # 如果有详细错误信息，返回它
        if last_error:
            return last_error
        
        return None

    def scrape(self, title: str, item_type: str = 'movie', year: int = None) -> Optional[Dict]:
        """通用刮削方法

        Args:
            title: 标题
            item_type: 类型 'movie' 或 'series'
            year: 年份

        Returns:
            刮削结果
        """
        if item_type == 'movie':
            return self.scrape_movie(title, year)
        else:
            return self.scrape_tv(title, year)

    def get_movie_by_id(self, tmdb_id: int) -> Optional[Dict]:
        """通过TMDB ID获取电影详情

        Args:
            tmdb_id: TMDB电影ID

        Returns:
            电影详情
        """
        if self.tmdb:
            try:
                return self.tmdb.get_movie_details(tmdb_id)
            except Exception:
                pass
        return None

    def get_tv_by_id(self, tmdb_id: int) -> Optional[Dict]:
        """通过TMDB ID获取电视剧详情

        Args:
            tmdb_id: TMDB电视剧ID

        Returns:
            电视剧详情
        """
        if self.tmdb:
            try:
                return self.tmdb.get_tv_details(tmdb_id)
            except Exception:
                pass
        return None

    def download_image(self, url: str) -> Optional[bytes]:
        """下载图片

        Args:
            url: 图片URL

        Returns:
            图片二进制数据，失败返回None
        """
        if not url:
            print(f"[图片下载] URL为空")
            return None

        print(f"[图片下载] 正在下载: {url}")

        # 优先使用代理下载（通过TMDB的session）
        session = None
        if self.tmdb:
            session = self.tmdb.session
        elif self.douban:
            session = self.douban.session

        if not session:
            session = requests.Session()

        try:
            print(f"[图片下载] 尝试通过代理下载...")
            resp = session.get(url, timeout=30, stream=True)
            if resp.status_code == 200:
                data = resp.content
                print(f"[图片下载] 代理下载成功，大小: {len(data)} bytes")
                return data
            else:
                print(f"[图片下载] 代理下载失败，状态码: {resp.status_code}")
        except Exception as e:
            print(f"[图片下载] 代理下载异常: {e}")

        # 如果使用代理下载失败，尝试不使用代理
        try:
            print(f"[图片下载] 尝试直连下载...")
            session2 = requests.Session()
            session2.trust_env = False
            resp = session2.get(url, timeout=30, stream=True)
            if resp.status_code == 200:
                data = resp.content
                print(f"[图片下载] 直连下载成功，大小: {len(data)} bytes")
                return data
            else:
                print(f"[图片下载] 直连下载失败，状态码: {resp.status_code}")
        except Exception as e:
            print(f"[图片下载] 直连下载异常: {e}")

        print(f"[图片下载] 所有下载方式均失败")
        return None
