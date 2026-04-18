"""Emby管理系统 - Emby API客户端封装"""
import requests
from typing import Optional, Dict, List, Any


class EmbyClient:
    """Emby服务器API客户端，封装所有REST API调用"""

    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })

    def _url(self, path: str) -> str:
        """构建完整的API URL"""
        return f"{self.server_url}/emby{path}"

    def _params(self, extra: Optional[Dict] = None) -> Dict:
        """构建请求参数，自动附加api_key"""
        params = {'api_key': self.api_key}
        if extra:
            params.update(extra)
        return params

    # ========== 认证相关 ==========

    def authenticate_by_name(self, username: str, password: str) -> Dict:
        """用户名密码认证，返回用户信息和token"""
        resp = self.session.post(
            self._url('/Users/AuthenticateByName'),
            params=self._params(),
            json={'Username': username, 'Pw': password}
        )
        resp.raise_for_status()
        return resp.json()

    def get_public_users(self) -> List[Dict]:
        """获取公开用户列表（无需认证）"""
        resp = self.session.get(
            self._url('/Users/Public'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    # ========== 用户管理 ==========

    def get_users(self) -> List[Dict]:
        """获取所有用户列表"""
        resp = self.session.get(
            self._url('/Users'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def get_user_by_id(self, user_id: str) -> Dict:
        """根据ID获取用户信息"""
        resp = self.session.get(
            self._url(f'/Users/{user_id}'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def create_user(self, name: str, has_password: bool = True) -> Dict:
        """创建新用户"""
        resp = self.session.post(
            self._url('/Users/New'),
            params=self._params(),
            json={'Name': name, 'HasPassword': has_password}
        )
        resp.raise_for_status()
        return resp.json()

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        resp = self.session.delete(
            self._url(f'/Users/{user_id}'),
            params=self._params()
        )
        return resp.status_code == 204

    def update_user_password(self, user_id: str, current_pw: str, new_pw: str) -> bool:
        """更新用户密码"""
        resp = self.session.post(
            self._url(f'/Users/{user_id}/Password'),
            params=self._params(),
            json={'CurrentPw': current_pw, 'NewPw': new_pw}
        )
        return resp.status_code == 204

    def update_user_policy(self, user_id: str, policy: Dict) -> bool:
        """更新用户策略（权限配置）"""
        resp = self.session.post(
            self._url(f'/Users/{user_id}/Policy'),
            params=self._params(),
            json=policy
        )
        return resp.status_code == 204

    def update_user_configuration(self, user_id: str, config: Dict) -> bool:
        """更新用户配置"""
        resp = self.session.post(
            self._url(f'/Users/{user_id}/Configuration'),
            params=self._params(),
            json=config
        )
        return resp.status_code == 204

    def get_user_policy(self, user_id: str) -> Dict:
        """获取用户策略"""
        user = self.get_user_by_id(user_id)
        return user.get('Policy', {})

    # ========== 媒体库管理 ==========

    def get_items(self, parent_id: Optional[str] = None,
                  item_types: Optional[str] = None,
                  recursive: bool = True,
                  start_index: int = 0,
                  limit: int = 100,
                  search_term: Optional[str] = None,
                  fields: Optional[str] = None,
                  sort_by: Optional[str] = None,
                  sort_order: Optional[str] = None,
                  user_id: Optional[str] = None) -> Dict:
        """获取媒体项目列表"""
        params = self._params({
            'Recursive': str(recursive).lower(),
            'StartIndex': start_index,
            'Limit': limit,
        })
        if parent_id:
            params['ParentId'] = parent_id
        if item_types:
            params['IncludeItemTypes'] = item_types
        if search_term:
            params['SearchTerm'] = search_term
        if fields:
            params['Fields'] = fields
        if sort_by:
            params['SortBy'] = sort_by
        if sort_order:
            params['SortOrder'] = sort_order
        if user_id:
            resp = self.session.get(self._url(f'/Users/{user_id}/Items'), params=params)
        else:
            resp = self.session.get(self._url('/Items'), params=params)
        resp.raise_for_status()
        return resp.json()

    def get_item_by_id(self, item_id: str, user_id: Optional[str] = None) -> Dict:
        """根据ID获取媒体项目详情
        
        注意：Emby服务器通常要求通过用户上下文访问项目，
        格式为 /Users/{UserId}/Items/{ItemId}，而非 /Items/{ItemId}
        
        Args:
            item_id: 媒体项目ID
            user_id: 用户ID（强烈建议提供，否则很多Emby配置下会返回404）
        """
        params = self._params()
        if user_id:
            # 使用用户上下文路径：/Users/{userId}/Items/{itemId}
            resp = self.session.get(
                self._url(f'/Users/{user_id}/Items/{item_id}'),
                params=params
            )
        else:
            # fallback：不带用户上下文
            resp = self.session.get(
                self._url(f'/Items/{item_id}'),
                params=params
            )
        resp.raise_for_status()
        return resp.json()

    def get_item_counts(self) -> Dict:
        """获取媒体项目计数统计"""
        resp = self.session.get(
            self._url('/Items/Counts'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def get_physical_paths(self, item_id: str) -> Dict:
        """获取媒体项目的物理路径"""
        resp = self.session.get(
            self._url(f'/Items/{item_id}/PhysicalPaths'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def get_similar_items(self, item_id: str, limit: int = 12, user_id: Optional[str] = None) -> Dict:
        """获取相似媒体项目
        
        Args:
            item_id: 媒体项目ID
            limit: 返回数量
            user_id: 用户ID（推荐提供）
        """
        params = self._params({'Limit': limit})
        if user_id:
            params['UserId'] = user_id
        resp = self.session.get(
            self._url(f'/Items/{item_id}/Similar'),
            params=params
        )
        resp.raise_for_status()
        return resp.json()

    # ========== 媒体库文件夹 ==========

    def get_library_media_folders(self) -> List[Dict]:
        """获取媒体库文件夹列表"""
        resp = self.session.get(
            self._url('/Library/MediaFolders'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json().get('Items', [])

    def refresh_library(self) -> bool:
        """刷新整个媒体库"""
        resp = self.session.post(
            self._url('/Library/Refresh'),
            params=self._params()
        )
        return resp.status_code == 204

    def refresh_item(self, item_id: str) -> bool:
        """刷新单个媒体项目"""
        resp = self.session.post(
            self._url(f'/Items/{item_id}/Refresh'),
            params=self._params()
        )
        return resp.status_code == 204

    def get_library_virtual_folders(self) -> List[Dict]:
        """获取虚拟文件夹列表"""
        resp = self.session.get(
            self._url('/Library/VirtualFolders'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def add_virtual_folder(self, name: str, collection_type: str,
                           paths: List[str], item_type: Optional[str] = None) -> bool:
        """添加虚拟文件夹（媒体库）"""
        params = self._params({
            'name': name,
            'collectionType': collection_type,
        })
        if item_type:
            params['itemType'] = item_type
        resp = self.session.post(
            self._url('/Library/VirtualFolders'),
            params=params,
            json={'LibraryMonitors': paths}
        )
        return resp.status_code == 204

    def remove_virtual_folder(self, name: str) -> bool:
        """移除虚拟文件夹"""
        resp = self.session.delete(
            self._url('/Library/VirtualFolders'),
            params=self._params({'name': name})
        )
        return resp.status_code == 204

    # ========== 系统信息 ==========

    def get_system_info(self) -> Dict:
        """获取系统信息"""
        resp = self.session.get(
            self._url('/System/Info'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def get_system_configuration(self) -> Dict:
        """获取系统配置"""
        resp = self.session.get(
            self._url('/System/Configuration'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def update_system_configuration(self, config: Dict) -> bool:
        """更新系统配置"""
        resp = self.session.post(
            self._url('/System/Configuration'),
            params=self._params(),
            json=config
        )
        return resp.status_code == 204

    def get_server_logs(self) -> List[Dict]:
        """获取服务器日志列表"""
        resp = self.session.get(
            self._url('/System/Logs'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def restart_server(self) -> bool:
        """重启Emby服务器"""
        resp = self.session.post(
            self._url('/System/Restart'),
            params=self._params()
        )
        return resp.status_code == 204

    def shutdown_server(self) -> bool:
        """关闭Emby服务器"""
        resp = self.session.post(
            self._url('/System/Shutdown'),
            params=self._params()
        )
        return resp.status_code == 204

    # ========== 会话管理 ==========

    def get_sessions(self) -> List[Dict]:
        """获取所有活动会话"""
        resp = self.session.get(
            self._url('/Sessions'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def send_session_message(self, session_id: str, header: str, message: str) -> bool:
        """向会话发送消息"""
        resp = self.session.post(
            self._url(f'/Sessions/{session_id}/Message'),
            params=self._params(),
            json={'Header': header, 'Text': message}
        )
        return resp.status_code == 204

    def send_session_command(self, session_id: str, command: str,
                             params: Optional[Dict] = None) -> bool:
        """向会话发送命令"""
        data = {'Command': command}
        if params:
            data.update(params)
        resp = self.session.post(
            self._url(f'/Sessions/{session_id}/Command'),
            params=self._params(),
            json=data
        )
        return resp.status_code == 204

    # ========== 播放信息 ==========

    def get_playback_info(self, item_id: str, user_id: str) -> Dict:
        """获取播放信息"""
        resp = self.session.post(
            self._url(f'/Items/{item_id}/PlaybackInfo'),
            params=self._params({'UserId': user_id})
        )
        resp.raise_for_status()
        return resp.json()

    # ========== 图片 ==========

    def get_item_image_url(self, item_id: str, image_type: str = 'Primary',
                           max_width: int = 300) -> str:
        """获取媒体项目图片URL"""
        return f"{self._url(f'/Items/{item_id}/Images/{image_type}')}" \
               f"?api_key={self.api_key}&maxWidth={max_width}"

    def upload_item_image(self, item_id: str, image_type: str,
                         image_data: bytes, index: int = 0) -> bool:
        """上传图片到媒体项目

        Args:
            item_id: 媒体项目ID
            image_type: 图片类型 (Primary, Backdrop, Logo, Thumb, etc.)
            image_data: 图片二进制数据
            index: 图片索引（用于多张图片）

        Returns:
            是否上传成功
        """
        print(f"[Emby上传] item_id={item_id}, image_type={image_type}, data_size={len(image_data) if image_data else 0}")
        
        params = self._params({'Index': index})
        url = self._url(f'/Items/{item_id}/Images/{image_type}')
        print(f"[Emby上传] URL: {url}")
        print(f"[Emby上传] Params: {params}")
        
        # 检测图片类型
        content_type = 'image/jpeg'
        if image_data and len(image_data) >= 4:
            if image_data[:4] == b'\x89PNG':
                content_type = 'image/png'
            elif image_data[:4] == b'GIF8':
                content_type = 'image/gif'
            elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
                content_type = 'image/webp'
        print(f"[Emby上传] 检测到的类型: {content_type}")
        
        resp = self.session.post(
            url,
            params=params,
            data=image_data,
            headers={'Content-Type': content_type}
        )
        print(f"[Emby上传] 状态码: {resp.status_code}")
        print(f"[Emby上传] 响应: {resp.text[:200] if resp.text else '空'}")
        
        return resp.status_code in (200, 204)

    def set_item_poster(self, item_id: str, image_data: bytes) -> bool:
        """设置项目封面图"""
        return self.upload_item_image(item_id, 'Primary', image_data)

    def set_item_backdrop(self, item_id: str, image_data: bytes) -> bool:
        """设置项目背景图"""
        return self.upload_item_image(item_id, 'Backdrop', image_data)

    def set_item_image_by_url(self, item_id: str, image_type: str, url: str) -> bool:
        """通过URL设置项目图片
        
        Args:
            item_id: 媒体项目ID
            image_type: 图片类型 (Primary, Backdrop, etc.)
            url: 图片URL
            
        Returns:
            是否成功
        """
        print(f"[Emby URL设置] item_id={item_id}, type={image_type}, url={url}")
        params = self._params()
        resp = self.session.post(
            self._url(f'/Items/{item_id}/Images/{image_type}'),
            params=params,
            json={'ImageUrl': url}
        )
        print(f"[Emby URL设置] 状态码: {resp.status_code}")
        print(f"[Emby URL设置] 响应: {resp.text[:200] if resp.text else '空'}")
        return resp.status_code in (200, 204)

    def set_provider_id(self, item_id: str, provider: str, provider_id: str) -> bool:
        """设置媒体提供商标识符，让Emby自动刮削图片
        
        Args:
            item_id: 媒体项目ID
            provider: 提供商名称 (Tmdb, Tvdb, Imdb 等)
            provider_id: 提供商ID
            
        Returns:
            是否成功
        """
        print(f"[Emby ProviderID] item_id={item_id}, provider={provider}, id={provider_id}")
        params = self._params()
        resp = self.session.post(
            self._url(f'/Items/{item_id}'),
            params=params,
            json={'ProviderIds': {provider: provider_id}}
        )
        print(f"[Emby ProviderID] 状态码: {resp.status_code}")
        print(f"[Emby ProviderID] 响应: {resp.text[:200] if resp.text else '空'}")
        return resp.status_code == 204

    def refresh_item(self, item_id: str, replace_images: bool = True,
                     replace_metadata: bool = True) -> bool:
        """刷新项目元数据和图片
        
        Args:
            item_id: 媒体项目ID
            replace_images: 是否替换所有图片（从Provider下载新图片）
            replace_metadata: 是否替换所有元数据
            
        Returns:
            是否成功提交刷新任务（注意：刷新是异步的）
        """
        print(f"[Emby Refresh] item_id={item_id}, replace_images={replace_images}, replace_metadata={replace_metadata}")
        params = self._params({
            'Recursive': 'true',
            'ImageRefreshMode': 'FullRefresh',
            'MetadataRefreshMode': 'FullRefresh',
        })
        if replace_images:
            params['ReplaceAllImages'] = 'true'
        if replace_metadata:
            params['ReplaceAllMetadata'] = 'true'
        
        resp = self.session.post(
            self._url(f'/Items/{item_id}/Refresh'),
            params=params
        )
        print(f"[Emby Refresh] 状态码: {resp.status_code}, 参数: {params}")
        return resp.status_code in (200, 204)
    
    def check_item_has_image(self, item_id: str, image_type: str = 'Primary') -> bool:
        """检查项目是否已有指定类型的图片
        
        Args:
            item_id: 媒体项目ID
            image_type: 图片类型 (Primary, Backdrop, etc.)
            
        Returns:
            是否存在图片
        """
        try:
            resp = self.session.head(
                self._url(f'/Items/{item_id}/Images/{image_type}'),
                params=self._params(),
                timeout=5
            )
            return resp.status_code == 200
        except Exception:
            return False

    # ========== 任务调度 ==========

    def get_scheduled_tasks(self) -> List[Dict]:
        """获取计划任务列表"""
        resp = self.session.get(
            self._url('/ScheduledTasks'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def run_scheduled_task(self, task_id: str) -> bool:
        """执行计划任务"""
        resp = self.session.post(
            self._url(f'/ScheduledTasks/Running/{task_id}'),
            params=self._params()
        )
        return resp.status_code == 204

    # ========== 通知 ==========

    def get_notifications(self, user_id: str) -> Dict:
        """获取用户通知"""
        resp = self.session.get(
            self._url(f'/Notifications/{user_id}'),
            params=self._params()
        )
        resp.raise_for_status()
        return resp.json()

    def send_notification(self, user_id: str, name: str, description: str, url: str = '') -> bool:
        """发送通知给用户"""
        resp = self.session.post(
            self._url(f'/Notifications/{user_id}'),
            params=self._params(),
            json={'Name': name, 'Description': description, 'Url': url}
        )
        return resp.status_code == 204

    # ========== 最近添加 ==========

    def get_latest_items(self, user_id: str, limit: int = 16,
                         item_types: Optional[str] = None) -> List[Dict]:
        """获取最近添加的媒体项目
        
        Args:
            user_id: 用户ID（必须）
            limit: 返回数量
            item_types: 类型过滤，如 'Movie' 或 'Series'
        """
        params = self._params({'Limit': limit, 'Fields': 'Overview,DateCreated,ProductionYear,CommunityRating,OfficialRating'})
        if item_types:
            params['IncludeItemTypes'] = item_types
        resp = self.session.get(
            self._url(f'/Users/{user_id}/Items/Latest'),
            params=params
        )
        resp.raise_for_status()
        return resp.json()

    # ========== STRM 媒体有效性检查 ==========

    def get_strm_items(self, user_id: str, parent_id: Optional[str] = None,
                       item_types: str = 'Movie,Episode',
                       start_index: int = 0, limit: int = 100) -> Dict:
        """获取 .strm 类型的媒体项目列表
        
        Args:
            user_id: 用户ID
            parent_id: 媒体库文件夹ID（可选，不传则查全部）
            item_types: 项目类型过滤，默认 Movie+Episode
            start_index: 分页起始
            limit: 每页数量
        """
        params = self._params({
            'IncludeItemTypes': item_types,
            'Recursive': 'true',
            'StartIndex': start_index,
            'Limit': limit,
            'Fields': 'Path,MediaSources,ParentId',
            'SortBy': 'DateCreated',
            'SortOrder': 'Descending',
        })
        if parent_id:
            params['ParentId'] = parent_id
        resp = self.session.get(
            self._url(f'/Users/{user_id}/Items'),
            params=params
        )
        resp.raise_for_status()
        data = resp.json()
        
        # 筛选 .strm 后缀的项目
        items = []
        for i in data.get('Items', []):
            path = i.get('Path', '')
            # 检查Path是否以.strm结尾
            if path.endswith('.strm'):
                # 从MediaSources获取实际的播放URL
                media_sources = i.get('MediaSources', [])
                if media_sources:
                    ms = media_sources[0]
                    play_url = ms.get('Path', '')
                    protocol = ms.get('Protocol', '')
                    # 将播放URL存到item中，供前端使用
                    i['_play_url'] = play_url
                    i['_protocol'] = protocol
                items.append(i)
        
        return {
            'Items': items,
            'TotalRecordCount': len(items),
        }

    def check_strm_url(self, url: str, timeout: int = 15, item_id: str = None) -> Dict:
        """检查单个 .strm URL 的有效性
        
        优先通过Emby服务器直接检测文件是否存在（使用 /videos/{id}/ 路径）。
        如果无法通过这种方式检测，则使用Range请求检测原始URL。
        
        Args:
            url: MediaSources中的播放URL
            timeout: 超时时间（秒）
            item_id: Emby项目ID（可选，用于直接通过Emby检测）
        
        Returns:
            dict: {'status': 'ok'|'fail'|'timeout'|'error', 'http_code': int, 'reason': str}
        """
        # 优先尝试通过Emby服务器检测
        if item_id:
            try:
                # 获取播放信息得到DirectStreamUrl
                users = self.get_users()
                user_id = users[0]['Id'] if users else None
                
                if user_id:
                    resp = self.session.post(
                        self._url(f'/Items/{item_id}/PlaybackInfo'),
                        params=self._params({'UserId': user_id}),
                        json={'MediaSourceId': '', 'DeviceProfile': {}},
                        timeout=timeout
                    )
                    if resp.ok:
                        sources = resp.json().get('MediaSources', [])
                        for source in sources:
                            # 检查是否是本地文件（DirectStreamUrl指向/videos/路径）
                            ds_url = source.get('DirectStreamUrl', '')
                            if ds_url and ds_url.startswith('/videos/'):
                                # 通过Emby服务器检测
                                video_url = f"{self.server_url}{ds_url.split('?')[0]}?api_key={self.api_key}"
                                try:
                                    head_resp = self.session.head(video_url, timeout=timeout)
                                    if head_resp.status_code == 200:
                                        return {'status': 'ok', 'http_code': 200, 'reason': 'Emby直链'}
                                    elif head_resp.status_code == 404:
                                        return {'status': 'fail', 'http_code': 404, 'reason': '文件不存在'}
                                except Exception:
                                    pass
            except Exception:
                pass
        
        # 回退方案：直接检测原始URL
        return self._check_url_direct(url, timeout)
    
    def _check_url_direct(self, url: str, timeout: int = 15) -> Dict:
        """直接检测URL有效性（使用Range请求避免下载大文件）"""
        try:
            headers = {
                'Range': 'bytes=0-1023',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            resp = self.session.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
            
            if resp.status_code < 400:
                return {'status': 'ok', 'http_code': resp.status_code, 'reason': ''}
            elif resp.status_code == 416:
                return {'status': 'ok', 'http_code': resp.status_code, 'reason': '文件过小'}
            else:
                return {'status': 'fail', 'http_code': resp.status_code,
                        'reason': f'HTTP {resp.status_code}'}
                
        except requests.Timeout:
            return {'status': 'timeout', 'http_code': 0, 'reason': f'超时({timeout}s)'}
        except requests.ConnectionError as e:
            err_str = str(e)
            if 'Max retries' in err_str:
                return {'status': 'fail', 'http_code': 0, 
                        'reason': '连接失败: 服务器无响应'}
            elif 'Connection refused' in err_str:
                return {'status': 'fail', 'http_code': 0, 'reason': '连接被拒绝'}
            elif 'Name or service not known' in err_str:
                return {'status': 'fail', 'http_code': 0, 'reason': '域名解析失败'}
            else:
                return {'status': 'fail', 'http_code': 0, 'reason': f'连接失败: {err_str[:50]}'}
        except Exception as e:
            return {'status': 'error', 'http_code': 0,
                    'reason': f'异常: {str(e)[:60]}'}

    # ========== 健康检查 ==========

    def ping(self) -> bool:
        """检查Emby服务器是否在线"""
        try:
            resp = self.session.get(
                self._url('/System/Ping'),
                params=self._params(),
                timeout=5
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False
