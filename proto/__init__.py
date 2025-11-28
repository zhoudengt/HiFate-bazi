# Proto 模块 - 使用延迟导入避免循环依赖
import sys
import importlib

def __getattr__(name):
    """延迟导入 generated 目录中的模块"""
    if name.endswith('_pb2') or name.endswith('_pb2_grpc'):
        module = importlib.import_module(f'proto.generated.{name}')
        globals()[name] = module
        return module
    raise AttributeError(f"module 'proto' has no attribute '{name}'")
