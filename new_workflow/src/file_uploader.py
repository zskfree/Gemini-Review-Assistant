# file_uploader.py
"""
临时文件托管服务模块
支持多个免费文件托管平台,用于上传文件并获取可访问的URL
"""

import requests
import os
import time
from typing import Optional, Dict, Any
from enum import Enum
from .config_loader import get_config


class UploadService(Enum):
    """支持的文件上传服务"""
    CATBOX = "catbox"           # 推荐: 200MB, 永久保存
    TMPFILES = "tmpfiles"       # 1小时有效
    PIXELDRAIN = "pixeldrain"   # 24小时免费, 10GB
    FILEIO = "fileio"           # 14天, 2GB, 仅下载一次
    GOFILE = "gofile"           # 无限期, 需要获取服务器


class FileUploader:
    """
    统一的文件上传客户端,支持多个免费托管服务
    """
    
    def __init__(self, proxy_url: Optional[str] = None, use_proxy: bool = True):
        """
        初始化文件上传器
        
        Args:
            proxy_url (str, optional): 代理URL
            use_proxy (bool): 是否使用代理,默认True
        """
        self.proxy_url = proxy_url if proxy_url else get_config("proxy.url", "")
        self.use_proxy = use_proxy and bool(self.proxy_url)
        self.proxies = None
        
        if self.use_proxy:
            self.proxies = {
                'http': self.proxy_url,
                'https': self.proxy_url
            }
        else:
            self.proxies = None  # 不使用代理
    
    def upload(self, file_path: str, service: UploadService = UploadService.CATBOX,
               max_retries: int = 3) -> Dict[str, Any]:
        """
        上传文件到指定服务
        
        Args:
            file_path (str): 文件路径
            service (UploadService): 上传服务类型
            max_retries (int): 最大重试次数
            
        Returns:
            dict: {
                'success': bool,
                'url': str,
                'service': str,
                'error': str (如果失败)
            }
        """
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': f"File not found: {file_path}",
                'service': service.value
            }
        
        file_size = os.path.getsize(file_path)
        print(f"正在上传文件: {os.path.basename(file_path)} ({file_size / 1024 / 1024:.2f} MB)")
        
        for attempt in range(max_retries):
            try:
                if service == UploadService.CATBOX:
                    result = self._upload_to_catbox(file_path)
                elif service == UploadService.TMPFILES:
                    result = self._upload_to_tmpfiles(file_path)
                elif service == UploadService.PIXELDRAIN:
                    result = self._upload_to_pixeldrain(file_path)
                elif service == UploadService.FILEIO:
                    result = self._upload_to_fileio(file_path)
                elif service == UploadService.GOFILE:
                    result = self._upload_to_gofile(file_path)
                else:
                    return {
                        'success': False,
                        'error': f"Unsupported service: {service}",
                        'service': service.value
                    }
                
                if result['success']:
                    print(f"✓ 上传成功: {result['url']}")
                    return result
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"上传失败,{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    
            except requests.exceptions.ProxyError as e:
                print(f"✗ 代理错误: {e}")
                # 代理错误时尝试直连
                if self.use_proxy and attempt == 0:
                    print("→ 检测到代理错误,尝试直连...")
                    old_proxies = self.proxies
                    self.proxies = None
                    continue
                elif attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    # 恢复代理设置
                    if self.use_proxy:
                        self.proxies = old_proxies if 'old_proxies' in locals() else self.proxies
                    return {
                        'success': False,
                        'error': f"Proxy error: {str(e)}",
                        'service': service.value
                    }
            except requests.exceptions.Timeout as e:
                print(f"✗ 请求超时: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    return {
                        'success': False,
                        'error': f"Timeout: {str(e)}",
                        'service': service.value
                    }
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"上传异常: {e}, {wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'service': service.value
                    }
        
        return {
            'success': False,
            'error': f"Failed after {max_retries} attempts",
            'service': service.value
        }
    
    def _upload_to_catbox(self, file_path: str) -> Dict[str, Any]:
        """
        上传到 Catbox.moe (推荐)
        - 最大文件: 200MB
        - 保存时间: 永久
        - 无需注册
        """
        url = "https://catbox.moe/user/api.php"
        
        with open(file_path, 'rb') as f:
            files = {'fileToUpload': f}
            data = {'reqtype': 'fileupload'}
            
            response = requests.post(
                url,
                files=files,
                data=data,
                proxies=self.proxies,
                timeout=300
            )
        
        if response.status_code == 200 and response.text.startswith('http'):
            return {
                'success': True,
                'url': response.text.strip(),
                'service': 'catbox',
                'expires': 'never'
            }
        else:
            return {
                'success': False,
                'error': f"Upload failed: {response.text}",
                'service': 'catbox'
            }
    
    def _upload_to_tmpfiles(self, file_path: str) -> Dict[str, Any]:
        """
        上传到 tmpfiles.org
        - 最大文件: 100MB
        - 保存时间: 1小时
        """
        url = "https://tmpfiles.org/api/v1/upload"
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                url,
                files=files,
                proxies=self.proxies,
                timeout=300
            )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                # tmpfiles返回格式: https://tmpfiles.org/123/file.pdf
                # 需要转换为下载链接: https://tmpfiles.org/dl/123/file.pdf
                original_url = result['data']['url']
                download_url = original_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
                
                return {
                    'success': True,
                    'url': download_url,
                    'service': 'tmpfiles',
                    'expires': '1 hour'
                }
        
        return {
            'success': False,
            'error': f"Upload failed: {response.text}",
            'service': 'tmpfiles'
        }
    
    def _upload_to_pixeldrain(self, file_path: str) -> Dict[str, Any]:
        """
        上传到 Pixeldrain
        - 最大文件: 10GB (免费用户)
        - 保存时间: 24小时 (免费), 更长需要注册
        """
        url = "https://pixeldrain.com/api/file"
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                url,
                files=files,
                proxies=self.proxies,
                timeout=300
            )
        
        if response.status_code == 201:
            result = response.json()
            file_id = result['id']
            download_url = f"https://pixeldrain.com/api/file/{file_id}?download"
            
            return {
                'success': True,
                'url': download_url,
                'service': 'pixeldrain',
                'expires': '24 hours (free)'
            }
        
        return {
            'success': False,
            'error': f"Upload failed: {response.text}",
            'service': 'pixeldrain'
        }
    
    def _upload_to_fileio(self, file_path: str) -> Dict[str, Any]:
        """
        上传到 file.io
        - 最大文件: 2GB
        - 保存时间: 14天
        - 注意: 免费版仅允许下载一次!
        """
        url = "https://file.io"
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'expires': '14d'}  # 14天过期
            
            response = requests.post(
                url,
                files=files,
                data=data,
                proxies=self.proxies,
                timeout=300
            )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return {
                    'success': True,
                    'url': result['link'],
                    'service': 'fileio',
                    'expires': '14 days',
                    'warning': '免费版仅可下载一次!'
                }
        
        return {
            'success': False,
            'error': f"Upload failed: {response.text}",
            'service': 'fileio'
        }
    
    def _upload_to_gofile(self, file_path: str) -> Dict[str, Any]:
        """
        上传到 GoFile.io
        - 最大文件: 无限制
        - 保存时间: 无限期 (10天无访问后删除)
        - 需要先获取服务器地址
        """
        try:
            # 1. 获取最佳服务器
            server_response = requests.get(
                "https://api.gofile.io/getServer",
                proxies=self.proxies,
                timeout=30
            )
            
            if server_response.status_code != 200:
                return {
                    'success': False,
                    'error': "Failed to get server",
                    'service': 'gofile'
                }
            
            server = server_response.json()['data']['server']
            
            # 2. 上传文件
            upload_url = f"https://{server}.gofile.io/uploadFile"
            
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    upload_url,
                    files=files,
                    proxies=self.proxies,
                    timeout=300
                )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    return {
                        'success': True,
                        'url': result['data']['downloadPage'],
                        'direct_url': result['data'].get('directLink', ''),
                        'service': 'gofile',
                        'expires': 'permanent (10 days no access)'
                    }
        except Exception as e:
            return {
                'success': False,
                'error': f"GoFile error: {str(e)}",
                'service': 'gofile'
            }
        
        return {
            'success': False,
            'error': f"Upload failed: {response.text if 'response' in locals() else 'Unknown error'}",
            'service': 'gofile'
        }
    
    def upload_with_fallback(self, file_path: str, 
                            services: list = None) -> Dict[str, Any]:
        """
        尝试多个服务上传,自动降级
        
        Args:
            file_path (str): 文件路径
            services (list): 服务优先级列表,默认按推荐顺序
            
        Returns:
            dict: 上传结果
        """
        if services is None:
            # 默认优先级: catbox > pixeldrain > tmpfiles > gofile > fileio
            services = [
                UploadService.CATBOX,
                UploadService.PIXELDRAIN,
                UploadService.TMPFILES,
                UploadService.GOFILE,
                UploadService.FILEIO,
            ]
        
        for service in services:
            print(f"\n{'='*60}")
            print(f"尝试使用 {service.value.upper()} 上传...")
            print(f"{'='*60}")
            result = self.upload(file_path, service, max_retries=2)
            
            if result['success']:
                print(f"\n{'='*60}")
                print(f"✓✓✓ 上传成功!")
                print(f"服务: {result['service']}")
                print(f"URL: {result['url']}")
                print(f"有效期: {result.get('expires', 'N/A')}")
                if 'warning' in result:
                    print(f"⚠️  警告: {result['warning']}")
                print(f"{'='*60}\n")
                return result
            else:
                print(f"✗ {service.value} 上传失败: {result.get('error', 'Unknown error')}")
        
        return {
            'success': False,
            'error': 'All upload services failed',
            'service': 'all'
        }


# 测试代码
if __name__ == "__main__":
    # 使用代理进行测试
    uploader = FileUploader(use_proxy=True)
    
    # 测试单个服务
    test_file = "new_workflow/pdfs/巴菲特的阿尔法.pdf"
    
    if os.path.exists(test_file):
        # 方式1: 指定服务
        # result = uploader.upload(test_file, UploadService.CATBOX)
        # print(f"\n结果: {result}")
        
        # 方式2: 自动降级
        result = uploader.upload_with_fallback(test_file)
        print(f"\n最终结果: {result}")
    else:
        print(f"测试文件不存在: {test_file}")
        print(f"当前工作目录: {os.getcwd()}")
        print(f"尝试相对路径: ../pdfs/")
        
        # 尝试查找PDF文件
        pdf_dirs = ["pdfs", "new_workflow/pdfs", "../pdfs"]
        for pdf_dir in pdf_dirs:
            if os.path.exists(pdf_dir):
                files = os.listdir(pdf_dir)
                pdf_files = [f for f in files if f.endswith('.pdf')]
                if pdf_files:
                    test_file = os.path.join(pdf_dir, pdf_files[0])
                    print(f"\n找到测试文件: {test_file}")
                    result = uploader.upload_with_fallback(test_file)
                    print(f"\n最终结果: {result}")
                    break