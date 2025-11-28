# Proto 模块导出
# 从 generated 目录导出所有 pb2 模块

from proto.generated.intent_pb2 import *
from proto.generated.intent_pb2_grpc import *
from proto.generated.optimizer_pb2 import *
from proto.generated.optimizer_pb2_grpc import *
from proto.generated.bazi_core_pb2 import *
from proto.generated.bazi_core_pb2_grpc import *
from proto.generated.bazi_analyzer_pb2 import *
from proto.generated.bazi_analyzer_pb2_grpc import *
from proto.generated.bazi_fortune_pb2 import *
from proto.generated.bazi_fortune_pb2_grpc import *
from proto.generated.bazi_rule_pb2 import *
from proto.generated.bazi_rule_pb2_grpc import *
from proto.generated.fortune_analysis_pb2 import *
from proto.generated.fortune_analysis_pb2_grpc import *
from proto.generated.fortune_rule_pb2 import *
from proto.generated.fortune_rule_pb2_grpc import *
from proto.generated.payment_pb2 import *
from proto.generated.payment_pb2_grpc import *

# 为了兼容旧的导入方式
import proto.generated.intent_pb2 as intent_pb2
import proto.generated.intent_pb2_grpc as intent_pb2_grpc
import proto.generated.optimizer_pb2 as optimizer_pb2
import proto.generated.optimizer_pb2_grpc as optimizer_pb2_grpc

