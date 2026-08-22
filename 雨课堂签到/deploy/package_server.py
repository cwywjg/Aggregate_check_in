#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键服务器迁移打包工具 (Server Migration Packager)
用于将雨课堂签到与AI答题后台服务的全部运行文件打包为 tar.gz 与 zip 压缩包，方便快速拷贝到新 VPS 部署。
"""

import os
import tarfile
import zipfile
import shutil
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT_DIR, 'deploy_dist')

SERVER_FILES = [
    'api_server.py',
    'ai_solver.py',
    'ykt_monitor.py',
    'ykt_ws_engine.py',
    'safe_json_store.py',
    'requirements.txt',
    'ecosystem.config.cjs',
    'server_config.json',
    'SERVER_MIGRATION_GUIDE.md'
]

SERVER_DIRS = [
    'deploy'
]

def build_package():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    tar_path = os.path.join(OUTPUT_DIR, f'ykt_server_deploy_{timestamp}.tar.gz')
    latest_tar_path = os.path.join(OUTPUT_DIR, 'ykt_server_deploy_latest.tar.gz')
    zip_path = os.path.join(OUTPUT_DIR, f'ykt_server_deploy_{timestamp}.zip')
    latest_zip_path = os.path.join(OUTPUT_DIR, 'ykt_server_deploy_latest.zip')

    print('[*] 开始构建服务器极速部署包...')

    # 1. 构建 tar.gz
    with tarfile.open(tar_path, 'w:gz') as tar:
        for f in SERVER_FILES:
            full_path = os.path.join(ROOT_DIR, f)
            if os.path.exists(full_path):
                tar.add(full_path, arcname=f)
                print(f'  + 归档文件: {f}')
            else:
                print(f'  ! 提示: 可选文件未找到: {f}')
        
        for d in SERVER_DIRS:
            full_path = os.path.join(ROOT_DIR, d)
            if os.path.exists(full_path):
                for root, _, files in os.walk(full_path):
                    for file in files:
                        if file.endswith(('.pyc', '.git', '.DS_Store')) or file == 'package_server.py':
                            continue
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, ROOT_DIR)
                        tar.add(file_path, arcname=arcname)
                        print(f'  + 归档目录文件: {arcname}')

    shutil.copyfile(tar_path, latest_tar_path)
    print(f'[OK] tar.gz 打包完成: {tar_path}')
    print(f'[OK] 最新版本软链副本: {latest_tar_path}')

    # 2. 构建 zip
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in SERVER_FILES:
            full_path = os.path.join(ROOT_DIR, f)
            if os.path.exists(full_path):
                zf.write(full_path, arcname=f)
        
        for d in SERVER_DIRS:
            full_path = os.path.join(ROOT_DIR, d)
            if os.path.exists(full_path):
                for root, _, files in os.walk(full_path):
                    for file in files:
                        if file.endswith(('.pyc', '.git', '.DS_Store')) or file == 'package_server.py':
                            continue
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, ROOT_DIR)
                        zf.write(file_path, arcname=arcname)

    shutil.copyfile(zip_path, latest_zip_path)
    print(f'[OK] zip 打包完成: {zip_path}')
    print(f'[OK] 最新版本软链副本: {latest_zip_path}')
    print('\n[SUCCESS] 全部打包完成！上传 ykt_server_deploy_latest.tar.gz 到新服务器即可直接部署。')

if __name__ == '__main__':
    build_package()
