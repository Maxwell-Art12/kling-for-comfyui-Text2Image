# custom_nodes/kling_ai/__init__.py

import sys
import importlib
from .kling_t2i import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# 自动安装依赖（可选）
REQUIRED_PACKAGES = ["requests"]
try:
    import requests
except ImportError:
    print("\033[1;31m检测到缺少依赖，正在自动安装...\033[0m")
    from pip._internal import main as pipmain
    pipmain(['install'] + REQUIRED_PACKAGES)
    importlib.reload(sys.modules[__name__])  # 重新加载模块

# 版本声明
__version__ = "1.0.5"
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

# 启动时显示加载信息
print(f"\033[1;32m✅ 可灵AI节点 v{__version__} 已加载 | 支持文生图/图生图功能\033[0m")
