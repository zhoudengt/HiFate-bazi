#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
八字排盘主模块 - WenZhenBazi 类

自动检测并使用项目虚拟环境 (.venv)
如果检测到项目根目录下有 .venv，自动切换到 .venv/bin/python3

⚠️ 模块化重构说明：
此文件正在进行渐进式模块化重构，部分功能已迁移到 core/calculators/ 子目录：
- core/calculators/bazi_core/ - 核心计算（element_relations.py, ten_gods.py）
- core/calculators/bazi_data/ - 数据构建（待迁移）
- core/calculators/bazi_rules/ - 规则匹配（待迁移）

新代码可以直接使用模块化版本：from core.calculators.bazi_core import ...
此文件保留用于向后兼容，后续将逐步迁移。
"""
import sys
import os
from pathlib import Path

# 检测并确保使用 .venv
def _ensure_venv():
    """确保使用项目的 .venv 虚拟环境"""
    # 获取项目根目录（假设脚本在 src/ 目录下）
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    venv_python = project_root / ".venv" / "bin" / "python3"
    
    # 如果 .venv 存在
    if venv_python.exists():
        current_python = Path(sys.executable).resolve()
        venv_python_resolved = venv_python.resolve()
        # 如果当前 Python 不是 .venv 中的，提示用户
        if current_python != venv_python_resolved:
            logger.info("=" * 60, file=sys.stderr)
            logger.info("⚠️  检测到未使用项目虚拟环境 (.venv)", file=sys.stderr)
            logger.info("=" * 60, file=sys.stderr)
            logger.info(f"当前 Python: {current_python}", file=sys.stderr)
            logger.info(f"项目虚拟环境: {venv_python_resolved}", file=sys.stderr)
            logger.info("", file=sys.stderr)
            logger.info("请使用以下方式执行：", file=sys.stderr)
            script_path = Path(__file__).resolve()
            logger.info(f"  {venv_python_resolved} {script_path}", file=sys.stderr)
            logger.info("", file=sys.stderr)
            logger.info("或者激活虚拟环境后执行：", file=sys.stderr)
            logger.info(f"  source {project_root}/.venv/bin/activate", file=sys.stderr)
            logger.info(f"  python {script_path}", file=sys.stderr)
            logger.info("=" * 60, file=sys.stderr)
            sys.exit(1)

_ensure_venv()

import json
import logging
from lunar_python import Solar, Lunar
from datetime import datetime, timedelta

# 添加模块路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载微服务环境变量配置（如果直接运行脚本）
def _load_services_env():
    """加载微服务环境变量配置"""
    project_root = Path(__file__).resolve().parent.parent
    services_env_file = project_root / "config" / "services.env"
    if services_env_file.exists():
        try:
            with open(services_env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "export " in line:
                        # 解析 export KEY="VALUE" 格式
                        if "=" in line:
                            key_value = line.replace("export ", "").strip()
                            if "=" in key_value:
                                key, value = key_value.split("=", 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                # 只在环境变量未设置时设置默认值
                                if key not in os.environ:
                                    os.environ[key] = value
        except Exception as exc:
            logger.info(f"⚠️  加载环境变量配置失败: {exc}", file=sys.stderr)

# 自动加载环境变量
_load_services_env()

from core.data.constants import *
from core.data.stems_branches import *
from core.config.deities_config import DeitiesCalculator
from core.config.star_fortune_config import StarFortuneCalculator
from core.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
from core.data.relations import (
    STEM_HE,
    BRANCH_LIUHE,
    BRANCH_CHONG,
    BRANCH_XING,
    BRANCH_HAI,
    BRANCH_PO,
    BRANCH_SANHE_GROUPS,
    BRANCH_SANHUI_GROUPS,
)

# 安全的 StreamHandler，捕获 Broken pipe 异常
class SafeStreamHandler(logging.StreamHandler):
    """安全的 StreamHandler，捕获 Broken pipe 异常"""
    def emit(self, record):
        try:
            super().emit(record)
        except (BrokenPipeError, OSError):
            # 忽略 Broken pipe 错误，这在客户端断开连接时是正常的
            pass

# 配置日志记录器
logger = logging.getLogger(__name__)
if not logger.handlers:
    # 使用安全的 StreamHandler，避免 Broken pipe 错误
    handler = SafeStreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def safe_log(level, message):
    """
    安全的日志输出函数，捕获 Broken pipe 等异常
    在 Web 服务环境中，客户端断开连接时可能触发 Broken pipe 错误
    """
    try:
        if level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'error':
            logger.error(message)
        elif level == 'debug':
            logger.debug(message)
        else:
            logger.info(message)
    except (BrokenPipeError, OSError) as e:
        # 忽略 Broken pipe 错误，这在客户端断开连接时是正常的
        # 完全忽略，不尝试任何输出，避免再次触发 Broken pipe
        pass




class WenZhenBazi:
    """HiFate排盘主类 - 最完整版本"""

    _rule_filter_map = None

    def __init__(self, solar_date, solar_time, gender='male'):
        self.solar_date = solar_date
        self.solar_time = solar_time
        self.gender = gender
        self.lunar_date = None
        self.bazi_pillars = {}
        self.details = {}
        self.adjusted_solar_date = solar_date  # 记录调整后的日期
        self.adjusted_solar_time = solar_time  # 记录调整后的时间
        self.is_zi_shi_adjusted = False  # 标记是否进行了子时调整
        self.last_result = None
        self.last_fortune_detail = None
        self.last_fortune_snapshot = None
        self.last_matched_rules = []
        self.last_rule_context = {}
        self.last_unmatched_rules = []

        # 五行生克关系
        self.element_relations = {
            '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
            '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
            '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
            '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
            '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
        }

    def get_main_star(self, day_stem, target_stem, pillar_type):
        """
        计算主星（十神）- 修正版本
        与HiFate逻辑一致
        """
        if pillar_type == 'day':
            return '元男' if self.gender == 'male' else '元女'

        day_element = STEM_ELEMENTS[day_stem]
        target_element = STEM_ELEMENTS[target_stem]
        day_yinyang = STEM_YINYANG[day_stem]
        target_yinyang = STEM_YINYANG[target_stem]

        relation_type = self._get_element_relation(day_element, target_element)
        is_same_yinyang = (day_yinyang == target_yinyang)

        if relation_type == 'same':
            return '比肩' if is_same_yinyang else '劫财'
        elif relation_type == 'me_producing':
            return '食神' if is_same_yinyang else '伤官'
        elif relation_type == 'me_controlling':
            return '偏财' if is_same_yinyang else '正财'
        elif relation_type == 'controlling_me':
            return '七杀' if is_same_yinyang else '正官'
        elif relation_type == 'producing_me':
            return '偏印' if is_same_yinyang else '正印'

        return '未知'

    def _get_element_relation(self, day_element, target_element):
        """判断五行生克关系"""
        if day_element == target_element:
            return 'same'

        relations = self.element_relations[day_element]

        if target_element == relations['produces']:
            return 'me_producing'
        elif target_element == relations['controls']:
            return 'me_controlling'
        elif target_element == relations['produced_by']:
            return 'producing_me'
        elif target_element == relations['controlled_by']:
            return 'controlling_me'

        return 'unknown'

    def get_branch_ten_gods(self, day_stem, branch):
        """
        计算地支藏干的十神（副星）- 修正版本
        与HiFate逻辑一致
        """
        hidden_stems = HIDDEN_STEMS.get(branch, [])
        branch_gods = []

        for hidden_stem in hidden_stems:
            stem_char = hidden_stem[0] if len(hidden_stem) > 0 else hidden_stem
            ten_god = self.get_main_star(day_stem, stem_char, 'hidden')
            branch_gods.append(ten_god)

        return branch_gods

    def calculate(self):
        """执行八字排盘计算（优先微服务，无微服务时使用本地计算）"""
        # 尝试使用微服务（如果配置了）
        try:
            service_result = self._calculate_via_core_service()
            if service_result is not None:
                return service_result
        except Exception as e:
            safe_log('warning', f"⚠️  微服务调用跳过: {e}")

        # 使用本地计算
        safe_log('info', "ℹ️  使用本地计算")
        try:
            # 1. 使用lunar-python计算四柱和农历（包含子时处理）
            self._calculate_with_lunar()

            # 2. 计算十神 - 使用修正后的计算器
            self._calculate_ten_gods()

            # 3. 计算藏干
            self._calculate_hidden_stems()

            # 4. 计算星运和自坐
            self._calculate_star_fortune()

            # 5. 计算空亡
            self._calculate_kongwang()

            # 6. 计算纳音
            self._calculate_nayin()

            # 7. 计算神煞
            self._calculate_deities()

            result = self._format_result()
            self.last_result = result
            return result
        except Exception as e:
            safe_log('error', f"本地计算也失败: {e}")
            import traceback
            try:
                traceback.print_exc()
            except (BrokenPipeError, OSError):
                # 忽略 Broken pipe 错误
                pass
            raise RuntimeError(f"微服务调用失败，本地计算也失败: {e}") from e

    def _calculate_with_lunar(self):
        """使用lunar-python计算四柱八字和农历日期，修正年柱计算"""
        # 解析日期时间
        year, month, day = map(int, self.solar_date.split('-'))
        hour, minute = map(int, self.solar_time.split(':'))

        # 处理子时情况（23:00-24:00）
        adjusted_year, adjusted_month, adjusted_day = year, month, day
        
        adjusted_hour, adjusted_minute = hour, minute

        self.is_zi_shi_adjusted = False

        if hour >= 23:
            # 日期加1天，时间设为0点
            current_date = datetime(year, month, day)
            next_date = current_date + timedelta(days=1)
            adjusted_year, adjusted_month, adjusted_day = next_date.year, next_date.month, next_date.day
            adjusted_hour = 0
            self.is_zi_shi_adjusted = True
            logger.info(f"注意：23点以后，日期调整为: {adjusted_year:04d}-{adjusted_month:02d}-{adjusted_day:02d} 00:{minute:02d}")

        # 保存调整后的日期和时间
        self.adjusted_solar_date = f"{adjusted_year:04d}-{adjusted_month:02d}-{adjusted_day:02d}"
        self.adjusted_solar_time = f"{adjusted_hour:02d}:{minute:02d}"

        # 创建阳历对象（使用调整后的日期时间）
        solar = Solar.fromYmdHms(adjusted_year, adjusted_month, adjusted_day, adjusted_hour, adjusted_minute, 0)

        # 转换为农历
        lunar = solar.getLunar()

        # 获取八字信息
        bazi = lunar.getBaZi()

        # 【关键修正】确保年柱始终基于原始日期计算
        # 获取原始日期的年柱
        original_solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
        original_lunar = original_solar.getLunar()
        original_bazi = original_lunar.getBaZi()

        # 解析四柱 - 年柱使用原始日期，其他柱使用调整后日期
        self.bazi_pillars = {
            'year': {'stem': original_bazi[0][0], 'branch': original_bazi[0][1]},  # 使用原始日期年柱
            'month': {'stem': bazi[1][0], 'branch': bazi[1][1]},  # 使用调整后日期
            'day': {'stem': bazi[2][0], 'branch': bazi[2][1]},    # 使用调整后日期
            'hour': {'stem': bazi[3][0], 'branch': bazi[3][1]}    # 使用调整后日期
        }

        # 保存农历日期
        self.lunar_date = {
            'year': lunar.getYear(),
            'month': lunar.getMonth(),
            'day': lunar.getDay(),
            'month_name': lunar.getMonthInChinese(),
            'day_name': lunar.getDayInChinese()
        }

        # 输出调试信息
        if self.is_zi_shi_adjusted:
            logger.info(f"年柱保持为: {self.bazi_pillars['year']['stem']}{self.bazi_pillars['year']['branch']}")

    def _calculate_ten_gods(self):
        """计算十神 - 使用修正后的计算器"""
        day_stem = self.bazi_pillars['day']['stem']

        for pillar_type, pillar in self.bazi_pillars.items():
            # 计算主星
            main_star = self.get_main_star(day_stem, pillar['stem'], pillar_type)

            # 计算副星
            branch_gods = self.get_branch_ten_gods(day_stem, pillar['branch'])

            # 修正时柱亥的副星顺序
            if pillar_type == 'hour' and pillar['branch'] == '亥':
                if branch_gods == ['正印', '劫财']:
                    branch_gods = ['劫财', '正印']  # 修正顺序

            if pillar_type not in self.details:
                self.details[pillar_type] = {}

            self.details[pillar_type].update({
                'main_star': main_star,
                'hidden_stars': branch_gods
            })

    def _calculate_hidden_stems(self):
        """计算藏干"""
        for pillar_type, pillar in self.bazi_pillars.items():
            branch = pillar['branch']
            hidden_stems = HIDDEN_STEMS.get(branch, [])
            self.details[pillar_type]['hidden_stems'] = hidden_stems

    def _calculate_star_fortune(self):
        """计算星运和自坐"""
        calculator = StarFortuneCalculator()

        # 获取日干
        day_stem = self.bazi_pillars['day']['stem']

        for pillar_type, pillar in self.bazi_pillars.items():
            # 星运：日干在各地支的十二长生状态
            star_fortune = calculator.get_stem_fortune(day_stem, pillar['branch'])

            # 自坐：各柱天干在各自地支的十二长生状态
            self_sitting = calculator.get_stem_fortune(pillar['stem'], pillar['branch'])

            self.details[pillar_type].update({
                'star_fortune': star_fortune,
                'self_sitting': self_sitting
            })

    def _calculate_kongwang(self):
        """计算空亡 - 修正为每柱单独计算空亡"""
        calculator = StarFortuneCalculator()

        for pillar_type, pillar in self.bazi_pillars.items():
            # 每柱单独计算空亡
            pillar_ganzhi = f"{pillar['stem']}{pillar['branch']}"
            kongwang = calculator.get_kongwang(pillar_ganzhi)

            if pillar_type not in self.details:
                self.details[pillar_type] = {}

            self.details[pillar_type]['kongwang'] = kongwang

    def _calculate_nayin(self):
        """计算纳音"""
        for pillar_type, pillar in self.bazi_pillars.items():
            nayin = NAYIN_MAP.get((pillar['stem'], pillar['branch']), '')
            self.details[pillar_type]['nayin'] = nayin

    def _calculate_deities(self):
        """计算神煞 - 基于已计算好的四柱数据"""
        calculator = DeitiesCalculator()

        # 直接使用已经计算好的四柱数据
        year_stem = self.bazi_pillars['year']['stem']
        year_branch = self.bazi_pillars['year']['branch']
        month_stem = self.bazi_pillars['month']['stem']
        month_branch = self.bazi_pillars['month']['branch']
        day_stem = self.bazi_pillars['day']['stem']
        day_branch = self.bazi_pillars['day']['branch']
        hour_stem = self.bazi_pillars['hour']['stem']
        hour_branch = self.bazi_pillars['hour']['branch']

        # 计算各柱神煞
        year_deities = calculator.calculate_year_deities(year_stem, year_branch, self.bazi_pillars)
        month_deities = calculator.calculate_month_deities(month_stem, month_branch, self.bazi_pillars)
        day_deities = calculator.calculate_day_deities(day_stem, day_branch, self.bazi_pillars)
        hour_deities = calculator.calculate_hour_deities(hour_stem, hour_branch, self.bazi_pillars)

        # 赋值到details中
        self.details['year']['deities'] = year_deities
        self.details['month']['deities'] = month_deities
        self.details['day']['deities'] = day_deities
        self.details['hour']['deities'] = hour_deities

    def _apply_remote_core_result(self, result: dict):
        """接收微服务排盘结果并同步到当前实例"""
        if not result:
            return

        basic = result.get('basic_info', {})
        self.last_result = result
        self.bazi_pillars = result.get('bazi_pillars', {}) or {}
        self.details = result.get('details', {}) or {}
        self.lunar_date = basic.get('lunar_date')
        self.adjusted_solar_date = basic.get('adjusted_solar_date', self.solar_date)
        self.adjusted_solar_time = basic.get('adjusted_solar_time', self.solar_time)
        self.is_zi_shi_adjusted = basic.get('is_zi_shi_adjusted', False)
        
        # 检查并补充星运和自坐字段（如果微服务没有返回）
        if self.bazi_pillars and self.details:
            from core.config.star_fortune_config import StarFortuneCalculator
            calculator = StarFortuneCalculator()
            day_stem = self.bazi_pillars.get('day', {}).get('stem', '')
            
            for pillar_type in ['year', 'month', 'day', 'hour']:
                pillar = self.bazi_pillars.get(pillar_type, {})
                if not pillar:
                    continue
                    
                pillar_detail = self.details.get(pillar_type, {})
                if not isinstance(pillar_detail, dict):
                    self.details[pillar_type] = {}
                    pillar_detail = self.details[pillar_type]
                
                # 如果缺少星运字段，计算并补充
                if 'star_fortune' not in pillar_detail or not pillar_detail.get('star_fortune'):
                    star_fortune = calculator.get_stem_fortune(day_stem, pillar.get('branch', ''))
                    pillar_detail['star_fortune'] = star_fortune
                
                # 如果缺少自坐字段，计算并补充
                if 'self_sitting' not in pillar_detail or not pillar_detail.get('self_sitting'):
                    self_sitting = calculator.get_stem_fortune(pillar.get('stem', ''), pillar.get('branch', ''))
                    pillar_detail['self_sitting'] = self_sitting

    def _calculate_via_core_service(self):
        """通过 bazi-core 微服务计算排盘（可选，未配置时返回 None）"""
        service_url = os.getenv("BAZI_CORE_SERVICE_URL", "").strip()
        if not service_url:
            # 未配置微服务，返回 None 使用本地计算
            return None

        # 移除 http:// 前缀（如果存在）
        if service_url.startswith("http://"):
            service_url = service_url[7:]
        elif service_url.startswith("https://"):
            service_url = service_url[8:]

        # 解析主机和端口
        if ":" in service_url:
            host, port_str = service_url.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                host, port = service_url, 9001  # 默认端口
        else:
            host, port = service_url, 9001

        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_log('info', f"[{request_time}] 🔵 bazi_calculator.py: 强制调用 bazi-core-service (gRPC): {service_url}")

        strict = os.getenv("BAZI_CORE_SERVICE_STRICT", "0") == "1"
        try:
            from shared.clients.bazi_core_client_grpc import BaziCoreClient

            # 使用30秒超时，确保有足够时间处理复杂计算
            client = BaziCoreClient(base_url=service_url, timeout=30.0)
            result = client.calculate_bazi(self.solar_date, self.solar_time, self.gender)
            safe_log('info', f"[{request_time}] ✅ bazi_calculator.py: bazi-core-service 调用成功")
            self._apply_remote_core_result(result)
            return result
        except Exception as exc:
            # 检查服务是否真的在运行
            is_port_listening = self._check_service_port(host, port)
            
            if "DEADLINE_EXCEEDED" in str(exc):
                if is_port_listening:
                    error_msg = f"微服务调用超时（服务在运行但响应慢，端口 {port} 正在监听）: {exc}"
                    safe_log('warning', f"[{request_time}] ⚠️  bazi_calculator.py: {error_msg}")
                else:
                    error_msg = f"微服务调用超时（服务可能已挂，端口 {port} 未在监听）: {exc}"
                    safe_log('error', f"[{request_time}] ❌ bazi_calculator.py: {error_msg}")
            elif "Connection refused" in str(exc) or isinstance(exc, ConnectionError):
                error_msg = f"微服务连接被拒绝（服务已挂，端口 {port} 未在监听）: {exc}"
                safe_log('error', f"[{request_time}] ❌ bazi_calculator.py: {error_msg}")
            else:
                error_msg = f"微服务调用失败: {exc}"
                safe_log('error', f"[{request_time}] ❌ bazi_calculator.py: {error_msg}")
            
            if strict:
                raise RuntimeError(f"微服务调用失败（严格模式）: {exc}") from exc
            
            # 检查是否是连接错误或超时（服务真正挂了或响应慢）
            is_connection_error = (
                isinstance(exc, (ConnectionError, TimeoutError)) or
                "DEADLINE_EXCEEDED" in str(exc) or
                "Connection refused" in str(exc) or
                "Name resolution" in str(exc)
            )
            
            if is_connection_error:
                if is_port_listening:
                    safe_log('warning', f"[{request_time}] ⚠️  服务响应超时但端口在监听，允许回退到本地计算")
                else:
                    safe_log('warning', f"[{request_time}] ⚠️  服务端口未监听，允许回退到本地计算")
                return None
            else:
                # 其他错误（如数据格式错误）直接抛出
                raise RuntimeError(f"微服务调用失败: {exc}") from exc

    def _format_result(self):
        """格式化输出结果"""
        ten_gods_stats = self._build_ten_gods_stats()
        elements = self._build_elements_info()
        element_counts = self._build_element_counts(elements)
        relationships = self._build_element_relationships(elements)
        relationships.update(self._build_ganzhi_relationships())

        result = {
            'basic_info': {
                'solar_date': self.solar_date,
                'solar_time': self.solar_time,
                'adjusted_solar_date': self.adjusted_solar_date,
                'adjusted_solar_time': self.adjusted_solar_time,
                'lunar_date': self.lunar_date,
                'gender': self.gender,
                'is_zi_shi_adjusted': self.is_zi_shi_adjusted
            },
            'bazi_pillars': self.bazi_pillars,
            'details': self.details,
            'ten_gods_stats': ten_gods_stats,
            'elements': elements,
            'element_counts': element_counts,
            'relationships': relationships
        }
        return result

    def _normalize_current_time(self, current_time=None):
        if current_time is None:
            return None, None
        if isinstance(current_time, datetime):
            return current_time, current_time.isoformat()
        try:
            parsed = datetime.fromisoformat(str(current_time))
            return parsed, parsed.isoformat()
        except Exception:
            return None, str(current_time)

    def _ensure_fortune_detail(self, current_time=None):
        if self.last_fortune_detail is not None:
            return self.last_fortune_detail

        current_time_obj, current_time_str = self._normalize_current_time(current_time)

        service_url = os.getenv("BAZI_FORTUNE_SERVICE_URL", "").strip()
        if not service_url:
            raise RuntimeError(
                "❌ BAZI_FORTUNE_SERVICE_URL 未设置！所有展示页面必须调用微服务。\n"
                "请确保已启动微服务并设置环境变量。\n"
                "启动方式: ./start_all_services.sh"
            )

        # 移除 http:// 前缀（如果存在）
        if service_url.startswith("http://"):
            service_url = service_url[7:]
        elif service_url.startswith("https://"):
            service_url = service_url[8:]

        # 解析主机和端口
        if ":" in service_url:
            host, port_str = service_url.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                host, port = service_url, 9002  # 默认端口
        else:
            host, port = service_url, 9002

        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_log('info', f"[{request_time}] 🔵 bazi_calculator.py: 强制调用 bazi-fortune-service (gRPC): {service_url}")

        detail = None
        strict = os.getenv("BAZI_FORTUNE_SERVICE_STRICT", "0") == "1"
        try:
            from shared.clients.bazi_fortune_client_grpc import BaziFortuneClient

            # 使用30秒超时，确保有足够时间处理大运流年计算
            client = BaziFortuneClient(base_url=service_url, timeout=30.0)
            detail = client.calculate_detail(
                self.solar_date,
                self.solar_time,
                self.gender,
                current_time=current_time_str,
            )
            safe_log('info', f"[{request_time}] ✅ bazi_calculator.py: bazi-fortune-service 调用成功")
        except Exception as exc:
            # 检查服务是否真的在运行
            is_port_listening = self._check_service_port(host, port)
            
            if "DEADLINE_EXCEEDED" in str(exc):
                if is_port_listening:
                    error_msg = f"微服务调用超时（服务在运行但响应慢，端口 {port} 正在监听）: {exc}"
                    safe_log('warning', f"[{request_time}] ⚠️  bazi_calculator.py: {error_msg}")
                else:
                    error_msg = f"微服务调用超时（服务可能已挂，端口 {port} 未在监听）: {exc}"
                    safe_log('error', f"[{request_time}] ❌ bazi_calculator.py: {error_msg}")
            elif "Connection refused" in str(exc) or isinstance(exc, ConnectionError):
                error_msg = f"微服务连接被拒绝（服务已挂，端口 {port} 未在监听）: {exc}"
                safe_log('error', f"[{request_time}] ❌ bazi_calculator.py: {error_msg}")
            else:
                error_msg = f"微服务调用失败: {exc}"
                safe_log('error', f"[{request_time}] ❌ bazi_calculator.py: {error_msg}")
            
            if strict:
                raise RuntimeError(f"微服务调用失败（严格模式）: {exc}") from exc
            
            # 检查是否是连接错误或超时（服务真正挂了或响应慢）
            is_connection_error = (
                isinstance(exc, (ConnectionError, TimeoutError)) or
                "DEADLINE_EXCEEDED" in str(exc) or
                "Connection refused" in str(exc) or
                "Name resolution" in str(exc)
            )
            
            if is_connection_error:
                if is_port_listening:
                    safe_log('warning', f"[{request_time}] ⚠️  服务响应超时但端口在监听，允许回退到本地计算")
                else:
                    safe_log('warning', f"[{request_time}] ⚠️  服务端口未监听，允许回退到本地计算")
                # 允许回退到本地计算
                from core.calculators.helpers import compute_local_detail
                detail = compute_local_detail(
                    self.solar_date,
                    self.solar_time,
                    self.gender,
                    current_time=current_time_obj,
                )
            else:
                # 其他错误（如数据格式错误）直接抛出
                raise RuntimeError(f"微服务调用失败: {exc}") from exc

        if detail is None:
            # 如果仍然为 None，使用本地计算作为最后回退
            from core.calculators.helpers import compute_local_detail
            detail = compute_local_detail(
                self.solar_date,
                self.solar_time,
                self.gender,
                current_time=current_time_obj,
            )

        self.last_fortune_detail = detail
        return detail

    def _build_fortune_snapshot(self, detail):
        if not detail:
            return {}

        fortune = {}
        details = detail.get('details', {}) or {}
        liunian_info = detail.get('liunian_info', {}) or {}
        current_liunian = details.get('liunian') or liunian_info.get('current_liunian') or {}
        liunian_sequence = (
            detail.get('liunian_sequence')
            or details.get('liunian_sequence')
            or []
        )

        liunian_copy = dict(current_liunian) if current_liunian else {}
        target_year = None
        if liunian_copy and liunian_sequence:
            for entry in liunian_sequence:
                if (
                    entry.get('stem') == liunian_copy.get('stem')
                    and entry.get('branch') == liunian_copy.get('branch')
                ):
                    target_year = entry.get('year')
                    if target_year:
                        break

        if target_year is None:
            current_time = detail.get('basic_info', {}).get('current_time')
            if current_time:
                try:
                    target_year = int(str(current_time)[:4])
                except Exception:
                    target_year = None

        if target_year is None:
            context = details.get('current_context', {}) or {}
            target_year = context.get('selected_year')

        if liunian_copy and target_year is not None:
            liunian_copy.setdefault('year', target_year)

        fortune['current_liunian'] = liunian_copy
        if target_year is not None:
            fortune['current_year'] = target_year
        if liunian_sequence:
            fortune['liunian_sequence'] = liunian_sequence

        return fortune

    def _ensure_fortune_snapshot(self, current_time=None):
        if self.last_fortune_snapshot is not None:
            return self.last_fortune_snapshot
        detail = self._ensure_fortune_detail(current_time=current_time)
        snapshot = self._build_fortune_snapshot(detail)
        self.last_fortune_snapshot = snapshot
        return snapshot

    @staticmethod
    def _check_service_port(host, port):
        """检查服务端口是否在监听"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # 1秒超时
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0  # 0 表示连接成功
        except Exception:
            return False

    def _match_rules_via_service(self, rule_types=None, use_cache=False):
        service_url = os.getenv("BAZI_RULE_SERVICE_URL", "").strip()
        if not service_url:
            raise RuntimeError(
                "❌ BAZI_RULE_SERVICE_URL 未设置！所有展示页面必须调用微服务。\n"
                "请确保已启动微服务并设置环境变量。\n"
                "启动方式: ./start_all_services.sh"
            )

        # 移除 http:// 前缀（如果存在）
        if service_url.startswith("http://"):
            service_url = service_url[7:]
        elif service_url.startswith("https://"):
            service_url = service_url[8:]

        # 解析主机和端口
        if ":" in service_url:
            host, port_str = service_url.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                host, port = service_url, 9004  # 默认端口
        else:
            host, port = service_url, 9004

        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rule_types_str = ", ".join(rule_types) if rule_types else "全部"
        safe_log('info', f"[{request_time}] 🔵 bazi_calculator.py: 强制调用 bazi-rule-service (gRPC): {service_url}, rule_types=[{rule_types_str}]")

        strict = os.getenv("BAZI_RULE_SERVICE_STRICT", "0") == "1"
        try:
            from shared.clients.bazi_rule_client_grpc import BaziRuleClient

            # 规则匹配可能需要较长时间（处理462条规则），使用60秒超时
            # 增加超时时间到 120 秒，因为规则匹配可能需要较长时间
            client = BaziRuleClient(base_url=service_url, timeout=120.0)
            # 优化：默认启用缓存，除非明确指定 use_cache=False
            use_cache_optimized = use_cache if use_cache is not None else True
            response = client.match_rules(
                self.solar_date,
                self.solar_time,
                self.gender,
                rule_types=rule_types,
                use_cache=use_cache_optimized,
            )
            matched_count = len(response.get("matched", []))
            safe_log('info', f"[{request_time}] ✅ bazi_calculator.py: bazi-rule-service 调用成功，匹配 {matched_count} 条规则")
            
            matched = response.get("matched", [])
            unmatched = response.get("unmatched", [])
            context = response.get("context", {})

            self.last_matched_rules = matched
            self.last_unmatched_rules = unmatched
            self.last_rule_context = context or {}

            return matched, unmatched
        except Exception as exc:
            import traceback
            
            # 检查服务是否真的在运行
            is_port_listening = self._check_service_port(host, port)
            
            if "DEADLINE_EXCEEDED" in str(exc):
                if is_port_listening:
                    error_msg = f"微服务调用超时（服务在运行但响应慢，端口 {port} 正在监听）: {exc}"
                    safe_log('warning', f"[{request_time}] ⚠️  bazi_calculator.py: {error_msg}")
                else:
                    error_msg = f"微服务调用超时（服务可能已挂，端口 {port} 未在监听）: {exc}"
                    safe_log('error', f"[{request_time}] ❌ bazi_calculator.py: {error_msg}")
            elif "Connection refused" in str(exc) or isinstance(exc, ConnectionError):
                error_msg = f"微服务连接被拒绝（服务已挂，端口 {port} 未在监听）: {exc}"
                safe_log('error', f"[{request_time}] ❌ bazi_calculator.py: {error_msg}")
            else:
                error_msg = f"微服务调用失败: {exc}"
                safe_log('error', f"[{request_time}] ❌ bazi_calculator.py: {error_msg}")
            
            if strict:
                raise RuntimeError(f"微服务调用失败（严格模式）: {exc}") from exc
            
            # 检查是否是连接错误或超时（服务真正挂了或响应慢）
            is_connection_error = (
                isinstance(exc, (ConnectionError, TimeoutError)) or
                "DEADLINE_EXCEEDED" in str(exc) or
                "Connection refused" in str(exc) or
                "Name resolution" in str(exc)
            )
            
            if is_connection_error:
                if is_port_listening:
                    safe_log('warning', f"[{request_time}] ⚠️  服务响应超时但端口在监听，允许回退到本地规则匹配")
                else:
                    safe_log('warning', f"[{request_time}] ⚠️  服务端口未监听，允许回退到本地规则匹配")
                # 回退到本地规则匹配
                return self._match_rules_locally(rule_types)
            else:
                # 其他错误（如数据格式错误）直接抛出
                raise RuntimeError(f"微服务调用失败: {exc}") from exc

    def _build_ten_gods_stats(self):
        """构建十神统计信息，仅统计主星与副星"""
        stats = {'main': {}, 'sub': {}, 'totals': {}}

        def record(group, star, pillar):
            if not star:
                return
            entry = stats[group].setdefault(star, {'count': 0, 'pillars': {}})
            entry['count'] += 1
            entry['pillars'][pillar] = entry['pillars'].get(pillar, 0) + 1

            total_entry = stats['totals'].setdefault(star, {'count': 0, 'pillars': {}})
            total_entry['count'] += 1
            total_entry['pillars'][pillar] = total_entry['pillars'].get(pillar, 0) + 1

        for pillar in ['year', 'month', 'day', 'hour']:
            detail = self.details.get(pillar, {})
            record('main', detail.get('main_star'), pillar)
            for star in detail.get('hidden_stars', []):
                record('sub', star, pillar)

        stats['ten_gods_main'] = stats['main']
        stats['ten_gods_sub'] = stats['sub']
        stats['ten_gods_total'] = stats['totals']
        return stats

    def _build_elements_info(self):
        """构建四柱五行信息"""
        elements = {}
        for pillar in ['year', 'month', 'day', 'hour']:
            pillar_data = self.bazi_pillars.get(pillar, {})
            stem = pillar_data.get('stem')
            branch = pillar_data.get('branch')
            elements[pillar] = {
                'stem': stem,
                'branch': branch,
                'stem_element': STEM_ELEMENTS.get(stem, ''),
                'branch_element': BRANCH_ELEMENTS.get(branch, '')
            }
        return elements

    def _build_element_counts(self, elements):
        """统计五行数量"""
        counts = {}
        for info in elements.values():
            stem_element = info.get('stem_element')
            branch_element = info.get('branch_element')
            if stem_element:
                counts[stem_element] = counts.get(stem_element, 0) + 1
            if branch_element:
                counts[branch_element] = counts.get(branch_element, 0) + 1
        return counts

    def _build_element_relationships(self, elements):
        """构建常用五行关系"""
        relationships = {'element_relations': {}}

        def describe(src, dst):
            if not src or not dst:
                return 'unknown'
            if src == dst:
                return 'same'
            rel = self.element_relations.get(src, {})
            if dst == rel.get('produces'):
                return 'generate'
            if dst == rel.get('controls'):
                return 'control'
            if dst == rel.get('produced_by'):
                return 'generated_by'
            if dst == rel.get('controlled_by'):
                return 'controlled_by'
            return 'unknown'

        day_stem_el = elements.get('day', {}).get('stem_element')
        day_branch_el = elements.get('day', {}).get('branch_element')
        relationships['element_relations']['day_stem->day_branch'] = describe(day_stem_el, day_branch_el)
        relationships['element_relations']['day_branch->day_stem'] = describe(day_branch_el, day_stem_el)
        return relationships

    def _build_ganzhi_relationships(self):
        pillars = ['year', 'month', 'day', 'hour']
        stem_map = {pillar: self.bazi_pillars.get(pillar, {}).get('stem') for pillar in pillars}
        branch_map = {pillar: self.bazi_pillars.get(pillar, {}).get('branch') for pillar in pillars}

        stem_relations = {
            'he': [],
            'map': {pillar: [] for pillar in pillars},
        }

        branch_relations = {
            'liuhe': [],
            'chong': [],
            'xing': [],
            'hai': [],
            'po': [],
            'map': {
                'liuhe': {pillar: [] for pillar in pillars},
                'chong': {pillar: [] for pillar in pillars},
                'xing': {pillar: [] for pillar in pillars},
                'hai': {pillar: [] for pillar in pillars},
                'po': {pillar: [] for pillar in pillars},
            },
            'sanhe': [],
            'sanhui': [],
        }

        for i in range(len(pillars)):
            for j in range(i + 1, len(pillars)):
                pillar_a = pillars[i]
                pillar_b = pillars[j]
                stem_a = stem_map.get(pillar_a)
                stem_b = stem_map.get(pillar_b)
                branch_a = branch_map.get(pillar_a)
                branch_b = branch_map.get(pillar_b)

                if stem_a and stem_b and STEM_HE.get(stem_a) == stem_b:
                    entry = {'pillars': [pillar_a, pillar_b], 'stems': [stem_a, stem_b]}
                    stem_relations['he'].append(entry)
                    stem_relations['map'][pillar_a].append(pillar_b)
                    stem_relations['map'][pillar_b].append(pillar_a)

                if branch_a and branch_b:
                    if BRANCH_LIUHE.get(branch_a) == branch_b:
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['liuhe'].append(entry)
                        branch_relations['map']['liuhe'][pillar_a].append(pillar_b)
                        branch_relations['map']['liuhe'][pillar_b].append(pillar_a)
                    if BRANCH_CHONG.get(branch_a) == branch_b:
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['chong'].append(entry)
                        branch_relations['map']['chong'][pillar_a].append(pillar_b)
                        branch_relations['map']['chong'][pillar_b].append(pillar_a)
                    if branch_b in BRANCH_XING.get(branch_a, []):
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['xing'].append(entry)
                        branch_relations['map']['xing'][pillar_a].append(pillar_b)
                    if branch_a in BRANCH_XING.get(branch_b, []):
                        branch_relations['map']['xing'][pillar_b].append(pillar_a)
                    if branch_b in BRANCH_HAI.get(branch_a, []):
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['hai'].append(entry)
                        branch_relations['map']['hai'][pillar_a].append(pillar_b)
                    if branch_a in BRANCH_HAI.get(branch_b, []):
                        branch_relations['map']['hai'][pillar_b].append(pillar_a)
                    if BRANCH_PO.get(branch_a) == branch_b:
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['po'].append(entry)
                        branch_relations['map']['po'][pillar_a].append(pillar_b)
                        branch_relations['map']['po'][pillar_b].append(pillar_a)

        branch_values = {pillar: branch for pillar, branch in branch_map.items() if branch}
        for group in BRANCH_SANHE_GROUPS:
            group_set = set(group)
            matched_pillars = [pillar for pillar, branch in branch_values.items() if branch in group_set]
            matched_branches = {branch_values[p] for p in matched_pillars}
            if len(matched_branches) == len(group_set):
                branch_relations['sanhe'].append({
                    'group': list(group),
                    'pillars': matched_pillars,
                })

        for group in BRANCH_SANHUI_GROUPS:
            group_set = set(group)
            matched_pillars = [pillar for pillar, branch in branch_values.items() if branch in group_set]
            matched_branches = {branch_values[p] for p in matched_pillars}
            if len(matched_branches) == len(group_set):
                branch_relations['sanhui'].append({
                    'group': list(group),
                    'pillars': matched_pillars,
                })

        return {
            'stem_relations': stem_relations,
            'branch_relations': branch_relations,
        }

    def print_result(self):
        """打印排盘结果"""
        result = self.calculate()
        if not result:
            logger.info("排盘失败，请检查输入参数")
            return

        logger.info("=" * 60)
        logger.info("HiFate排盘 - 最完整版本")
        logger.info("=" * 60)

        basic = result['basic_info']
        logger.info(f"阳历: {basic['solar_date']} {basic['solar_time']}")

        # 如果日期被调整过，显示调整后的日期
        if basic['is_zi_shi_adjusted']:
            logger.info(f"调整后: {basic['adjusted_solar_date']} {basic['adjusted_solar_time']} (子时调整)")

        # 显示农历日期
        lunar = basic['lunar_date']
        lunar_year = lunar['year']
        lunar_month_name = lunar.get('month_name', '')
        lunar_day_name = lunar.get('day_name', '')

        if not lunar_month_name:
            lunar_month_name = f"{lunar['month']}月"
        if not lunar_day_name:
            lunar_day_name = f"{lunar['day']}日"

        logger.info(f"农历: {lunar_year}年{lunar_month_name}{lunar_day_name}")
        logger.info(f"性别: {'男' if basic['gender'] == 'male' else '女'}")
        logger.info("")

        pillars = result['bazi_pillars']
        details = result['details']



        self._print_detailed_table(pillars, details)

    def _print_detailed_table(self, pillars, details):
        """打印详细排盘表格"""
        headers = ["日期", "年柱", "月柱", "日柱", "时柱"]

        # 构建表格行
        rows = [
            ["主星"] + [details.get(p, {}).get('main_star', '') for p in ['year', 'month', 'day', 'hour']],
            ["天干"] + [pillars[p]['stem'] for p in ['year', 'month', 'day', 'hour']],
            ["地支"] + [pillars[p]['branch'] for p in ['year', 'month', 'day', 'hour']],
            ]

        # 处理藏干和副星 - 将逗号分隔的值分行显示
        hidden_stems_data = [details.get(p, {}).get('hidden_stems', []) for p in ['year', 'month', 'day', 'hour']]
        hidden_stars_data = [details.get(p, {}).get('hidden_stars', []) for p in ['year', 'month', 'day', 'hour']]

        # 计算最大行数（用于对齐）
        max_hidden_rows = max(len(stems) for stems in hidden_stems_data) if any(hidden_stems_data) else 0
        max_stars_rows = max(len(stars) for stars in hidden_stars_data) if any(hidden_stars_data) else 0

        # 添加藏干行
        if max_hidden_rows > 0:
            rows.append(["藏干"] + ["" for _ in range(4)])  # 标题行
            for i in range(max_hidden_rows):
                row_data = []
                for j in range(4):
                    if i < len(hidden_stems_data[j]):
                        row_data.append(hidden_stems_data[j][i])
                    else:
                        row_data.append("")
                rows.append([""] + row_data)

        # 添加副星行
        if max_stars_rows > 0:
            rows.append(["副星"] + ["" for _ in range(4)])  # 标题行
            for i in range(max_stars_rows):
                row_data = []
                for j in range(4):
                    if i < len(hidden_stars_data[j]):
                        row_data.append(hidden_stars_data[j][i])
                    else:
                        row_data.append("")
                rows.append([""] + row_data)

        # 添加其他行
        other_rows = [
            ["星运"] + [details.get(p, {}).get('star_fortune', '') for p in ['year', 'month', 'day', 'hour']],
            ["自坐"] + [details.get(p, {}).get('self_sitting', '') for p in ['year', 'month', 'day', 'hour']],
            ["空亡"] + [details.get(p, {}).get('kongwang', '') for p in ['year', 'month', 'day', 'hour']],
            ["纳音"] + [details.get(p, {}).get('nayin', '') for p in ['year', 'month', 'day', 'hour']]
        ]
        rows.extend(other_rows)

        # 处理神煞 - 将逗号分隔的值分行显示（放在最后）
        deities_data = [details.get(p, {}).get('deities', []) for p in ['year', 'month', 'day', 'hour']]

        # 计算最大行数（用于对齐）
        max_deities_rows = max(len(deities) for deities in deities_data) if any(deities_data) else 0

        # 添加神煞行
        if max_deities_rows > 0:
            rows.append(["神煞"] + ["" for _ in range(4)])  # 标题行
            for i in range(max_deities_rows):
                row_data = []
                for j in range(4):
                    if i < len(deities_data[j]):
                        row_data.append(deities_data[j][i])
                    else:
                        row_data.append("")
                rows.append([""] + row_data)

        col_widths = [8, 20, 20, 20, 20]

        header_line = "".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers)))
        logger.info(header_line)
        logger.info("-" * len(header_line))

        for row in rows:
            row_line = "".join(f"{row[i]:<{col_widths[i]}}" for i in range(len(row)))
            logger.info(row_line)



    # 新增日柱性别分析方法：
    def print_rizhu_gender_analysis(self):
        """打印日柱性别查询分析结果"""
        logger.info("\n" + "=" * 80)
        #logger.info("日柱性别命理分析")
        #logger.info("=" * 80)

        # 确保已经计算了八字
        if not self.bazi_pillars or not self.details:
            self.calculate()

        # 创建日柱性别分析器
        analyzer = RizhuGenderAnalyzer(self.bazi_pillars, self.gender)

        # 获取分析结果
        analysis_output = analyzer.get_formatted_output()
        logger.info(analysis_output)

    # 新增匹配规则的方法，将内部计算结果发送给规则引擎
    def match_rules(self, rule_types=None, use_cache=False):
        """匹配规则，返回 (matched_rules, unmatched_rules_with_reason) 并记录上下文"""
        from server.services.rule_service import RuleService
        from server.engines.rule_condition import EnhancedRuleCondition

        if not self.last_result:
            self.calculate()

        # 优先尝试通过微服务匹配规则
        try:
            remote_result = self._match_rules_via_service(rule_types, use_cache)
            if remote_result is not None:
                return remote_result
        except RuntimeError as exc:
            # 如果是环境变量未设置等错误，继续使用本地匹配
            if "未设置" in str(exc):
                safe_log('warning', f"⚠️  bazi_calculator.py: {exc}")
            else:
                raise
        except Exception as exc:
            # 如果是连接错误，已经在 _match_rules_via_service 中处理了回退
            # 这里捕获其他异常，继续使用本地匹配
            import traceback
            safe_log('warning', f"⚠️  bazi_calculator.py: 微服务规则匹配失败，使用本地匹配: {exc}")

        # 回退到本地规则匹配
        return self._match_rules_locally(rule_types=rule_types, use_cache=use_cache)

    def _match_rules_locally(self, rule_types=None, use_cache=False):
        """本地规则匹配（仅在微服务挂掉时使用）"""
        from server.services.rule_service import RuleService
        from server.engines.rule_condition import EnhancedRuleCondition

        if not self.last_result:
            self.calculate()

        try:
            bazi_data = self.build_rule_input()
        except Exception as e:
            safe_log('error', f"❌ build_rule_input 失败: {e}")
            import traceback
            traceback.print_exc()
            return [], []

        try:
            matched = RuleService.match_rules(
                bazi_data,
                rule_types=rule_types,
                use_cache=use_cache
            )
        except Exception as e:
            safe_log('error', f"❌ RuleService.match_rules 调用失败: {e}")
            import traceback
            traceback.print_exc()
            return [], []
        
        # 确保 matched 是列表，且每个元素都是字典
        if not isinstance(matched, list):
            safe_log('warning', f"⚠️  RuleService.match_rules 返回了非列表类型: {type(matched)}, 值: {matched}")
            matched = []
        
        # 过滤掉非字典元素，并打印详细信息
        filtered_matched = []
        for idx, rule in enumerate(matched):
            if not isinstance(rule, dict):
                safe_log('warning', f"⚠️  匹配规则列表中的第 {idx} 个元素不是字典: {type(rule)}, 值: {repr(rule)[:100]}")
                continue
            filtered_matched.append(rule)
        matched = filtered_matched
        self.last_matched_rules = matched

        try:
            engine = RuleService.get_engine()
        except Exception as e:
            safe_log('error', f"❌ RuleService.get_engine 失败: {e}")
            import traceback
            traceback.print_exc()
            return matched, []
        
        # 确保 engine.rules 是列表，且每个元素都是字典
        if not isinstance(engine.rules, list):
            safe_log('warning', f"⚠️  engine.rules 不是列表类型: {type(engine.rules)}")
            engine.rules = []
        
        relevant_rules = []
        for idx, rule in enumerate(engine.rules):
            if not isinstance(rule, dict):
                safe_log('warning', f"⚠️  engine.rules 中第 {idx} 个元素不是字典: {type(rule)}, 值: {repr(rule)[:100]}")
                continue
            try:
                rule_type = rule.get('rule_type')
                if not rule_types or rule_type in rule_types:
                    relevant_rules.append(rule)
            except Exception as e:
                safe_log('warning', f"⚠️  处理规则时出错 (索引 {idx}): {e}")
                continue
        
        matched_ids = set()
        for idx, rule in enumerate(matched):
            if not isinstance(rule, dict):
                safe_log('warning', f"⚠️  匹配规则列表中第 {idx} 个元素不是字典: {type(rule)}, 值: {repr(rule)[:100]}")
                continue
            try:
                rule_id = rule.get('rule_code') or rule.get('rule_id')
                if rule_id:
                    matched_ids.add(rule_id)
            except Exception as e:
                safe_log('warning', f"⚠️  获取规则 ID 时出错 (索引 {idx}): {e}, 规则: {repr(rule)[:100]}")
                continue

        def explain(condition, path=""):
            if not condition:
                return "条件为空"
            if not isinstance(condition, dict):
                return f"条件不是字典类型: {type(condition)}"
            try:
                for key, value in condition.items():
                    current_path = f"{path}/{key}" if path else key
                    if key == "all":
                        if not isinstance(value, list):
                            return f"{current_path} 应该是列表类型，但实际是: {type(value)}"
                        for idx, sub in enumerate(value or []):
                            if not EnhancedRuleCondition.match(sub, bazi_data):
                                return explain(sub, f"{current_path}[{idx}]")
                    elif key == "any":
                        if not isinstance(value, list):
                            return f"{current_path} 应该是列表类型，但实际是: {type(value)}"
                        if any(EnhancedRuleCondition.match(sub, bazi_data) for sub in (value or [])):
                            continue
                        return f"{current_path} 中所有分支均未满足"
                    elif key == "not":
                        if EnhancedRuleCondition.match(value, bazi_data):
                            return f"{current_path} 应该不成立，但实际成立"
                    else:
                        if not EnhancedRuleCondition.match({key: value}, bazi_data):
                            return f"{current_path} 条件未满足，期望 {value}"
            except Exception as e:
                return f"解释条件时出错: {e}"
            return f"{path or '条件'} 未满足（原因未知）"

        unmatched = []
        context_map = {}
        for idx, rule in enumerate(relevant_rules):
            try:
                if not isinstance(rule, dict):
                    safe_log('warning', f"⚠️  relevant_rules 中第 {idx} 个元素不是字典: {type(rule)}, 值: {repr(rule)[:100]}")
                    continue
                
                rule_id = rule.get('rule_id') or rule.get('rule_code')
                if not rule_id:
                    continue
                    
                if rule_id in matched_ids:
                    conditions = rule.get('conditions', {})
                    if isinstance(conditions, dict):
                        try:
                            context_map[rule_id] = self._collect_condition_values(conditions, bazi_data)
                        except Exception as e:
                            safe_log('warning', f"⚠️  收集条件值时出错 (规则 {rule_id}): {e}")
                    continue
                
                conditions = rule.get('conditions', {})
                if not isinstance(conditions, dict):
                    safe_log('warning', f"⚠️  规则 {rule_id} 的 conditions 不是字典类型: {type(conditions)}, 值: {repr(conditions)[:100]}")
                    conditions = {}
                
                try:
                    if EnhancedRuleCondition.match(conditions, bazi_data):
                        try:
                            context_map[rule_id] = self._collect_condition_values(conditions, bazi_data)
                        except Exception as e:
                            safe_log('warning', f"⚠️  收集条件值时出错 (规则 {rule_id}): {e}")
                        continue
                except Exception as e:
                    safe_log('warning', f"⚠️  匹配规则 {rule_id} 时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                reason = explain(conditions)
                try:
                    rule_snapshot = {
                        key: rule.get(key)
                        for key in ('rule_id', 'rule_code', 'rule_name', 'rule_type', 'conditions', 'content')
                    }
                except Exception as e:
                    safe_log('warning', f"⚠️  构建 rule_snapshot 时出错 (规则 {rule_id}): {e}")
                    rule_snapshot = {}
                
                unmatched.append({
                    'rule_id': rule_id,
                    'rule_name': rule.get('rule_name', '') if isinstance(rule, dict) else '',
                    'rule_type': rule.get('rule_type', '') if isinstance(rule, dict) else '',
                    'reason': reason,
                    'rule': rule_snapshot,
                })
                
                try:
                    context_map[rule_id] = self._collect_condition_values(conditions, bazi_data)
                except Exception as e:
                    safe_log('warning', f"⚠️  收集条件值时出错 (规则 {rule_id}): {e}")
            except Exception as e:
                safe_log('error', f"❌ 处理规则时发生未捕获的异常 (索引 {idx}): {e}")
                import traceback
                traceback.print_exc()
                continue

        self.last_rule_context = context_map
        self.last_unmatched_rules = unmatched

        return matched, unmatched

    def build_rule_input(self, current_time=None):
        if not self.last_result:
            self.calculate()
        
        # 优化：如果不需要大运流年信息，可以快速返回空字典
        # 这样可以避免调用 gRPC 服务导致的超时
        try:
            fortune_snapshot = self._ensure_fortune_snapshot(current_time=current_time)
        except Exception as e:
            # 如果获取大运流年失败，使用空字典，不影响规则匹配
            fortune_snapshot = {}
        
        # 确保 ten_gods_stats 是字典类型，如果是字符串则反序列化
        ten_gods_stats = self.last_result.get('ten_gods_stats', {})
        if isinstance(ten_gods_stats, str):
            try:
                import json
                ten_gods_stats = json.loads(ten_gods_stats)
            except (json.JSONDecodeError, TypeError):
                ten_gods_stats = {}
        elif not isinstance(ten_gods_stats, dict):
            ten_gods_stats = {}
        
        # 确保 ten_gods_stats 内部的 stats 也是字典类型
        if isinstance(ten_gods_stats, dict):
            for key in ['main', 'sub', 'totals', 'ten_gods_main', 'ten_gods_sub', 'ten_gods_total']:
                stats_value = ten_gods_stats.get(key)
                if isinstance(stats_value, str):
                    try:
                        import json
                        ten_gods_stats[key] = json.loads(stats_value)
                    except (json.JSONDecodeError, TypeError):
                        ten_gods_stats[key] = {}
                elif not isinstance(stats_value, dict) and stats_value is not None:
                    ten_gods_stats[key] = {}
        
        return {
            'basic_info': self.last_result.get('basic_info', {}),
            'bazi_pillars': self.last_result.get('bazi_pillars', {}),
            'details': self.last_result.get('details', {}),
            'ten_gods_stats': ten_gods_stats,
            'elements': self.last_result.get('elements', {}),
            'element_counts': self.last_result.get('element_counts', {}),
            'relationships': self.last_result.get('relationships', {}),
            'fortune': fortune_snapshot
        }

    @classmethod
    def _load_rule_filters(cls):
        """加载规则筛选条件（已移除外部文件依赖，使用数据库规则）"""
        if cls._rule_filter_map is not None:
            return
        # 不再从外部文件读取，规则筛选条件应该从数据库获取
        # 如果需要此功能，请在数据库 bazi_rules 表中添加相应字段
        cls._rule_filter_map = {}

    @classmethod
    def _get_rule_filters(cls, rule_id: str):
        """获取规则筛选条件（已移除外部文件依赖）"""
        cls._load_rule_filters()
        return cls._rule_filter_map.get(rule_id, {})

    def _collect_condition_values(self, condition, data, acc=None):
        if acc is None:
            acc = []
        if not condition or not isinstance(condition, dict):
            return acc

        for key, value in condition.items():
            if key == "all":
                for sub in value or []:
                    self._collect_condition_values(sub, data, acc)
            elif key == "any":
                for sub in value or []:
                    self._collect_condition_values(sub, data, acc)
            elif key == "not":
                if isinstance(value, dict):
                    self._collect_condition_values(value, data, acc)
            elif key == "gender":
                basic_info = data.get('basic_info', {})
                if not isinstance(basic_info, dict):
                    basic_info = {}
                gender = basic_info.get('gender', '')
                acc.append(f"gender={gender}")
            elif key == "liunian_relation":
                fortune = data.get('fortune', {}) or {}
                if not isinstance(fortune, dict):
                    fortune = {}
                liunian = fortune.get('current_liunian', {}) or {}
                if not isinstance(liunian, dict):
                    liunian = {}
                part = value.get('part', 'stem') if isinstance(value, dict) else 'stem'
                acc.append(f"liunian.{part}={liunian.get(part, '') if isinstance(liunian, dict) else ''}")
                target = value.get('target') if isinstance(value, dict) else None
                if target:
                    bazi_pillars = data.get('bazi_pillars', {})
                    if not isinstance(bazi_pillars, dict):
                        bazi_pillars = {}
                    pillar = bazi_pillars.get(target, {})
                    if not isinstance(pillar, dict):
                        pillar = {}
                    part_key = 'stem' if part == 'stem' else 'branch'
                    acc.append(f"{target}.{part_key}={pillar.get(part_key, '') if isinstance(pillar, dict) else ''}")
            elif key == "liunian_deities":
                fortune = data.get('fortune', {}) or {}
                if not isinstance(fortune, dict):
                    fortune = {}
                liunian = fortune.get('current_liunian', {}) or {}
                if not isinstance(liunian, dict):
                    liunian = {}
                deities = liunian.get('deities', []) if isinstance(liunian, dict) else []
                if not isinstance(deities, list):
                    deities = []
                acc.append(f"liunian.deities={','.join(deities)}")
            elif key == "main_star_in_day":
                details = data.get('details', {})
                if not isinstance(details, dict):
                    details = {}
                day_detail = details.get('day', {})
                if not isinstance(day_detail, dict):
                    day_detail = {}
                star = day_detail.get('main_star', '') if isinstance(day_detail, dict) else ''
                acc.append(f"day.main_star={star}")
            elif key == "main_star_in_pillar":
                if isinstance(value, dict):
                    pillar = value.get('pillar')
                    details = data.get('details', {})
                    if not isinstance(details, dict):
                        details = {}
                    pillar_detail = details.get(pillar or '', {})
                    if not isinstance(pillar_detail, dict):
                        pillar_detail = {}
                    star = pillar_detail.get('main_star', '') if isinstance(pillar_detail, dict) else ''
                    expected = value.get('eq') or value.get('in')
                    acc.append(f"{pillar}.main_star={star} (期望={expected})")
            elif key in ("ten_gods_main", "ten_gods_sub", "ten_gods_total"):
                stats_key_map = {
                    "ten_gods_main": "main",
                    "ten_gods_sub": "sub",
                    "ten_gods_total": "totals"
                }
                ten_gods_stats = data.get('ten_gods_stats', {})
                # 确保 ten_gods_stats 是字典类型
                if not isinstance(ten_gods_stats, dict):
                    if isinstance(ten_gods_stats, str):
                        try:
                            import json
                            ten_gods_stats = json.loads(ten_gods_stats)
                        except (json.JSONDecodeError, TypeError):
                            ten_gods_stats = {}
                    else:
                        ten_gods_stats = {}
                
                stats_map = ten_gods_stats.get(stats_key_map[key], {})
                # 确保 stats_map 是字典类型
                if not isinstance(stats_map, dict):
                    if isinstance(stats_map, str):
                        try:
                            import json
                            stats_map = json.loads(stats_map)
                        except (json.JSONDecodeError, TypeError):
                            stats_map = {}
                    else:
                        stats_map = {}
                
                names = []
                specified_pillars = None
                if isinstance(value, dict):
                    names = value.get('names') or []
                    specified_pillars = value.get('pillars')  # 条件中指定的柱子
                if not names:
                    names = list(stats_map.keys()) if isinstance(stats_map, dict) else []
                parts = []
                for name in names:
                    entry = stats_map.get(name, {'count': 0, 'pillars': {}}) if isinstance(stats_map, dict) else {'count': 0, 'pillars': {}}
                    # 确保 entry 是字典类型
                    if not isinstance(entry, dict):
                        if isinstance(entry, str):
                            try:
                                import json
                                entry = json.loads(entry)
                            except (json.JSONDecodeError, TypeError):
                                entry = {'count': 0, 'pillars': {}}
                        else:
                            entry = {'count': 0, 'pillars': {}}
                    
                    all_pillars = entry.get('pillars', {}) if isinstance(entry, dict) else {}
                    # 确保 all_pillars 是字典类型
                    if not isinstance(all_pillars, dict):
                        all_pillars = {}
                    
                    # 如果条件中指定了 pillars，只显示这些 pillars 的统计
                    if specified_pillars:
                        # 只保留在 specified_pillars 中的 pillars，过滤掉其他 pillars
                        filtered_pillars = {}
                        for pillar in specified_pillars:
                            if pillar in all_pillars:
                                filtered_pillars[pillar] = all_pillars[pillar]
                        # 计算指定 pillars 的总数（只统计指定 pillars 的数量）
                        filtered_count = sum(filtered_pillars.values())
                        pillar_detail = ", ".join(f"{pillar}:{cnt}" for pillar, cnt in filtered_pillars.items()) or "无"
                        parts.append(f"{name} -> count={filtered_count} [{pillar_detail}]")
                    else:
                        # 没有指定 pillars，显示所有统计
                        pillar_detail = ", ".join(f"{pillar}:{cnt}" for pillar, cnt in all_pillars.items()) or "无"
                        parts.append(f"{name} -> count={entry.get('count',0)} [{pillar_detail}]")
                requirement = self._format_requirement(value if isinstance(value, dict) else None)
                acc.append(f"{key} {requirement}".strip() + " | " + "; ".join(parts))
            elif key == "day_branch_in":
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                day_pillar = bazi_pillars.get('day', {})
                if not isinstance(day_pillar, dict):
                    day_pillar = {}
                branch = day_pillar.get('branch', '') if isinstance(day_pillar, dict) else ''
                acc.append(f"day.branch={branch} (期望∈{value})")
            elif key == "day_branch_equals":
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                day_pillar = bazi_pillars.get('day', {})
                if not isinstance(day_pillar, dict):
                    day_pillar = {}
                branch = day_pillar.get('branch', '') if isinstance(day_pillar, dict) else ''
                acc.append(f"day.branch={branch} (期望={value})")
            elif key == "day_branch_element_in":
                elements = data.get('elements', {})
                if not isinstance(elements, dict):
                    if isinstance(elements, str):
                        try:
                            import json
                            elements = json.loads(elements)
                        except (json.JSONDecodeError, TypeError):
                            elements = {}
                    else:
                        elements = {}
                day_element_info = elements.get('day', {})
                if not isinstance(day_element_info, dict):
                    if isinstance(day_element_info, str):
                        try:
                            import json
                            day_element_info = json.loads(day_element_info)
                        except (json.JSONDecodeError, TypeError):
                            day_element_info = {}
                    else:
                        day_element_info = {}
                element = day_element_info.get('branch_element', '') if isinstance(day_element_info, dict) else ''
                acc.append(f"day.branch_element={element} (期望∈{value})")
            elif key == "pillar_element" and isinstance(value, dict):
                pillar = value.get('pillar')
                part = value.get('part', 'branch')
                elements = data.get('elements', {})
                if not isinstance(elements, dict):
                    if isinstance(elements, str):
                        try:
                            import json
                            elements = json.loads(elements)
                        except (json.JSONDecodeError, TypeError):
                            elements = {}
                    else:
                        elements = {}
                pillar_element_info = elements.get(pillar or '', {})
                if not isinstance(pillar_element_info, dict):
                    if isinstance(pillar_element_info, str):
                        try:
                            import json
                            pillar_element_info = json.loads(pillar_element_info)
                        except (json.JSONDecodeError, TypeError):
                            pillar_element_info = {}
                    else:
                        pillar_element_info = {}
                element = pillar_element_info.get(f"{part}_element", '') if isinstance(pillar_element_info, dict) else ''
                expected = value.get('in') or value.get('equals')
                acc.append(f"{pillar}.{part}_element={element} (期望={expected})")
            elif key == "element_total" and isinstance(value, dict):
                element_counts = data.get('element_counts', {})
                # 确保 element_counts 是字典类型
                if not isinstance(element_counts, dict):
                    element_counts = {}
                
                names = value.get('names') or list(element_counts.keys()) if isinstance(element_counts, dict) else []
                contributions = self._describe_element_sources(data)
                # 确保 contributions 是字典类型
                if not isinstance(contributions, dict):
                    contributions = {}
                
                parts = []
                for name in names:
                    detail_sources_list = contributions.get(name, []) if isinstance(contributions, dict) else []
                    if not isinstance(detail_sources_list, list):
                        detail_sources_list = []
                    detail_sources = ", ".join(detail_sources_list) or "无"
                    count_value = element_counts.get(name, 0) if isinstance(element_counts, dict) else 0
                    parts.append(f"{name}:{count_value} [{detail_sources}]")
                requirement = self._format_requirement(value)
                acc.append(f"element_total {requirement}".strip() + " | " + "; ".join(parts))
            elif key == "element_relation":
                relationships = data.get('relationships', {})
                if not isinstance(relationships, dict):
                    if isinstance(relationships, str):
                        try:
                            import json
                            relationships = json.loads(relationships)
                        except (json.JSONDecodeError, TypeError):
                            relationships = {}
                    else:
                        relationships = {}
                relations = relationships.get('element_relations', {}) if isinstance(relationships, dict) else {}
                acc.append("element_relations -> " + str(relations) + f" (期望={value})")
            elif key == "pillar_in" and isinstance(value, dict):
                pillar = value.get('pillar')
                part = value.get('part', 'branch')
                actual = self._get_pillar_part_value_for_debug(data, pillar, part)
                expected = value.get('values') or value.get('in')
                acc.append(f"pillar_in[{pillar}.{part}]={actual} (期望∈{expected})")
            elif key == "pillar_equals" and isinstance(value, dict):
                pillar = value.get('pillar')
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                pillar_data = bazi_pillars.get(pillar or '', {})
                if not isinstance(pillar_data, dict):
                    pillar_data = {}
                actual = f"{pillar_data.get('stem','')}{pillar_data.get('branch','')}"
                acc.append(f"{pillar}.pillar={actual} (期望={value.get('values')})")
            elif key == "stems_count" and isinstance(value, dict):
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                stems = []
                for p in ['year', 'month', 'day', 'hour']:
                    pillar = bazi_pillars.get(p, {})
                    if isinstance(pillar, dict):
                        stems.append(pillar.get('stem', ''))
                    else:
                        stems.append('')
                stem_counts = {}
                for s in stems:
                    stem_counts[s] = stem_counts.get(s, 0) + 1
                requirement = self._format_requirement(value)
                acc.append(f"stems={stems}; 统计={stem_counts} {requirement}".strip())
            elif key == "branches_count" and isinstance(value, dict):
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                branches = []
                for p in ['year', 'month', 'day', 'hour']:
                    pillar = bazi_pillars.get(p, {})
                    if isinstance(pillar, dict):
                        branches.append(pillar.get('branch', ''))
                    else:
                        branches.append('')
                branch_counts = {}
                for b in branches:
                    branch_counts[b] = branch_counts.get(b, 0) + 1
                requirement = self._format_requirement(value)
                acc.append(f"branches={branches}; 统计={branch_counts} {requirement}".strip())
            elif key == "pillar_relation" and isinstance(value, dict):
                pillar_a = value.get('pillar_a')
                pillar_b = value.get('pillar_b')
                part = value.get('part', 'branch')
                va = self._get_pillar_part_value_for_debug(data, pillar_a, part)
                vb = self._get_pillar_part_value_for_debug(data, pillar_b, part)
                relation = value.get('relation')
                acc.append(f"relation[{pillar_a}.{part},{pillar_b}.{part}]={va},{vb} (期望={relation})")
            elif key == "ten_god_combines" and isinstance(value, dict):
                god = value.get('god', '')
                source = value.get('source', 'any')
                pillars = value.get('pillars', [])
                target_pillars = value.get('target_pillars', [])
                target_part = value.get('target_part', 'stem')
                relation = value.get('relation', 'he')
                
                details = data.get('details', {})
                # 确保 details 是字典类型
                if not isinstance(details, dict):
                    if isinstance(details, str):
                        try:
                            import json
                            details = json.loads(details)
                        except (json.JSONDecodeError, TypeError):
                            details = {}
                    else:
                        details = {}
                
                bazi_pillars = data.get('bazi_pillars', {})
                # 确保 bazi_pillars 是字典类型
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                
                found_info = []
                for pillar in pillars:
                    detail = details.get(pillar, {}) if isinstance(details, dict) else {}
                    # 确保 detail 是字典类型
                    if not isinstance(detail, dict):
                        if isinstance(detail, str):
                            try:
                                import json
                                detail = json.loads(detail)
                            except (json.JSONDecodeError, TypeError):
                                detail = {}
                        else:
                            detail = {}
                    
                    candidate_stars = []
                    if source in {'main', 'any'}:
                        main_star = detail.get('main_star') if isinstance(detail, dict) else None
                        if main_star:
                            candidate_stars.append(f"主星:{main_star}")
                    if source in {'sub', 'any'}:
                        sub_stars = []
                        if isinstance(detail, dict):
                            sub_stars = detail.get('sub_stars') or detail.get('hidden_stars') or []
                        if not isinstance(sub_stars, list):
                            sub_stars = []
                        if sub_stars:
                            candidate_stars.append(f"副星:{','.join(sub_stars)}")
                    
                    main_star_list = []
                    if isinstance(detail, dict):
                        main_star = detail.get('main_star')
                        if main_star:
                            main_star_list = [main_star]
                    
                    sub_stars_list = []
                    if isinstance(detail, dict):
                        sub_stars_list = detail.get('sub_stars') or detail.get('hidden_stars') or []
                        if not isinstance(sub_stars_list, list):
                            sub_stars_list = []
                    
                    if god in main_star_list + sub_stars_list:
                        pillar_data = bazi_pillars.get(pillar, {}) if isinstance(bazi_pillars, dict) else {}
                        if not isinstance(pillar_data, dict):
                            pillar_data = {}
                        source_value = pillar_data.get(target_part) if target_part in ('stem', 'branch') and isinstance(pillar_data, dict) else None
                        if source_value:
                            found_info.append(f"{pillar}柱({source_value})")
                
                target_info = []
                for target_pillar in target_pillars:
                    target_data = bazi_pillars.get(target_pillar, {}) if isinstance(bazi_pillars, dict) else {}
                    if not isinstance(target_data, dict):
                        target_data = {}
                    target_value = target_data.get(target_part) if target_part in ('stem', 'branch') and isinstance(target_data, dict) else None
                    if target_value:
                        target_info.append(f"{target_pillar}柱({target_value})")
                
                relation_name = {'he': '天干合', 'liuhe': '地支六合', 'chong': '冲', 'xing': '刑', 'hai': '害', 'po': '破'}.get(relation, relation)
                acc.append(f"ten_god_combines: 查找{god}({source}) -> 在{pillars}柱中查找 -> 找到: {', '.join(found_info) if found_info else '无'} -> 目标{target_part}({','.join(target_info)}) -> 关系:{relation_name}")
            elif key in ("deities_in_year", "deities_in_month", "deities_in_day", "deities_in_hour"):
                # 神煞条件调试信息
                pillar_map = {
                    "deities_in_year": "year",
                    "deities_in_month": "month",
                    "deities_in_day": "day",
                    "deities_in_hour": "hour"
                }
                pillar = pillar_map.get(key)
                if pillar:
                    details = data.get('details', {})
                    # 确保 details 是字典类型
                    if not isinstance(details, dict):
                        if isinstance(details, str):
                            try:
                                import json
                                details = json.loads(details)
                            except (json.JSONDecodeError, TypeError):
                                details = {}
                        else:
                            details = {}
                    
                    pillar_details = details.get(pillar, {}) if isinstance(details, dict) else {}
                    # 确保 pillar_details 是字典类型
                    if not isinstance(pillar_details, dict):
                        if isinstance(pillar_details, str):
                            try:
                                import json
                                pillar_details = json.loads(pillar_details)
                            except (json.JSONDecodeError, TypeError):
                                pillar_details = {}
                        else:
                            pillar_details = {}
                    
                    deities = pillar_details.get('deities', []) if isinstance(pillar_details, dict) else []
                    if not isinstance(deities, list):
                        deities = [deities] if deities else []
                    
                    expected_deities = value if isinstance(value, list) else [value]
                    found_deities = [d for d in expected_deities if d in deities]
                    missing_deities = [d for d in expected_deities if d not in deities]
                    
                    if found_deities:
                        found_str = f"找到: {', '.join(found_deities)}"
                    else:
                        found_str = "未找到"
                    
                    if missing_deities:
                        missing_str = f"缺少: {', '.join(missing_deities)}"
                    else:
                        missing_str = ""
                    
                    all_deities_str = f"该柱所有神煞: {', '.join(deities) if deities else '无'}"
                    acc.append(f"{key}: {found_str} {missing_str} | {all_deities_str}")
            elif key == "branch_adjacent" and isinstance(value, dict):
                # 地支相邻条件调试信息
                pairs = value.get('pairs', [])
                pillars = data.get('bazi_pillars', {})
                branches = [
                    pillars.get('year', {}).get('branch', ''),
                    pillars.get('month', {}).get('branch', ''),
                    pillars.get('day', {}).get('branch', ''),
                    pillars.get('hour', {}).get('branch', '')
                ]
                
                found_pairs = []
                for pair in pairs:
                    if len(pair) == 2:
                        a, b = pair[0], pair[1]
                        # 检查是否紧挨
                        for i in range(len(branches) - 1):
                            if (branches[i] == a and branches[i+1] == b) or (branches[i] == b and branches[i+1] == a):
                                found_pairs.append(f"{branches[i]}{branches[i+1]}")
                                break
                
                if found_pairs:
                    found_str = f"找到紧挨的地支对: {', '.join(found_pairs)}"
                else:
                    found_str = "未找到紧挨的地支对"
                
                expected_pairs_str = ", ".join([f"{p[0]}{p[1]}" for p in pairs])
                branches_str = "".join(branches)
                acc.append(f"{key}: {found_str} | 期望: {expected_pairs_str} | 实际地支序列: {branches_str}")
            elif key == "branch_offset" and isinstance(value, dict):
                # 地支偏移条件调试信息
                source = value.get('source', '')
                target = value.get('target', '')
                offset = value.get('offset', 0)
                
                pillars = data.get('bazi_pillars', {})
                source_branch = pillars.get(source, {}).get('branch', '')
                target_branch = pillars.get(target, {}).get('branch', '')
                
                if source_branch and target_branch:
                    # 十二地支顺序
                    branch_sequence = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
                    try:
                        source_index = branch_sequence.index(source_branch)
                        target_index = branch_sequence.index(target_branch)
                        actual_offset = target_index - source_index
                        # 处理循环偏移（例如：亥到子，offset=1 或 -11）
                        if actual_offset > 6:
                            actual_offset -= 12
                        elif actual_offset < -6:
                            actual_offset += 12
                        
                        expected_index = (source_index + offset) % len(branch_sequence)
                        expected_branch = branch_sequence[expected_index]
                        
                        pillar_names = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}
                        source_name = pillar_names.get(source, source)
                        target_name = pillar_names.get(target, target)
                        
                        if actual_offset == offset:
                            match_str = "✓ 满足"
                        else:
                            match_str = "✗ 不满足"
                        
                        acc.append(f"{key}: {match_str} | {source_name}支={source_branch}(索引{source_index}) + offset({offset}) = 期望{expected_branch}(索引{expected_index}) | 实际{target_name}支={target_branch}(索引{target_index}, 实际偏移{actual_offset})")
                    except ValueError:
                        acc.append(f"{key}: 错误 - 无法找到地支索引")
                else:
                    acc.append(f"{key}: 错误 - 缺少{source}支或{target}支")
            else:
                acc.append(f"{key}:当前值暂无调试信息")
        return acc

    def _get_pillar_part_value_for_debug(self, data, pillar, part):
        if not pillar:
            return None
        
        if part == 'stem':
            bazi_pillars = data.get('bazi_pillars', {})
            if not isinstance(bazi_pillars, dict):
                bazi_pillars = {}
            pillar_info = bazi_pillars.get(pillar, {})
            if not isinstance(pillar_info, dict):
                pillar_info = {}
            return pillar_info.get('stem', '') if isinstance(pillar_info, dict) else ''
        
        if part == 'branch':
            bazi_pillars = data.get('bazi_pillars', {})
            if not isinstance(bazi_pillars, dict):
                bazi_pillars = {}
            pillar_info = bazi_pillars.get(pillar, {})
            if not isinstance(pillar_info, dict):
                pillar_info = {}
            return pillar_info.get('branch', '') if isinstance(pillar_info, dict) else ''
        
        if part == 'nayin':
            details = data.get('details', {})
            if not isinstance(details, dict):
                if isinstance(details, str):
                    try:
                        import json
                        details = json.loads(details)
                    except (json.JSONDecodeError, TypeError):
                        details = {}
                else:
                    details = {}
            pillar_detail = details.get(pillar, {}) if isinstance(details, dict) else {}
            if not isinstance(pillar_detail, dict):
                if isinstance(pillar_detail, str):
                    try:
                        import json
                        pillar_detail = json.loads(pillar_detail)
                    except (json.JSONDecodeError, TypeError):
                        pillar_detail = {}
                else:
                    pillar_detail = {}
            return pillar_detail.get('nayin', '') if isinstance(pillar_detail, dict) else ''
        
        if part == 'kongwang':
            details = data.get('details', {})
            if not isinstance(details, dict):
                if isinstance(details, str):
                    try:
                        import json
                        details = json.loads(details)
                    except (json.JSONDecodeError, TypeError):
                        details = {}
                else:
                    details = {}
            pillar_detail = details.get(pillar, {}) if isinstance(details, dict) else {}
            if not isinstance(pillar_detail, dict):
                if isinstance(pillar_detail, str):
                    try:
                        import json
                        pillar_detail = json.loads(pillar_detail)
                    except (json.JSONDecodeError, TypeError):
                        pillar_detail = {}
                else:
                    pillar_detail = {}
            return pillar_detail.get('kongwang', '') if isinstance(pillar_detail, dict) else ''
        
        if part == 'pillar':
            bazi_pillars = data.get('bazi_pillars', {})
            if not isinstance(bazi_pillars, dict):
                bazi_pillars = {}
            pillar_data = bazi_pillars.get(pillar, {})
            if not isinstance(pillar_data, dict):
                pillar_data = {}
            return f"{pillar_data.get('stem','')}{pillar_data.get('branch','')}"
        
        details = data.get('details', {})
        if not isinstance(details, dict):
            if isinstance(details, str):
                try:
                    import json
                    details = json.loads(details)
                except (json.JSONDecodeError, TypeError):
                    details = {}
            else:
                details = {}
        pillar_detail = details.get(pillar, {}) if isinstance(details, dict) else {}
        if not isinstance(pillar_detail, dict):
            if isinstance(pillar_detail, str):
                try:
                    import json
                    pillar_detail = json.loads(pillar_detail)
                except (json.JSONDecodeError, TypeError):
                    pillar_detail = {}
            else:
                pillar_detail = {}
        return pillar_detail.get(part, '') if isinstance(pillar_detail, dict) else ''

    def _format_requirement(self, spec):
        if not spec or not isinstance(spec, dict):
            return ""
        parts = []
        if spec.get('names'):
            parts.append(f"names={spec['names']}")
        if spec.get('eq') is not None:
            parts.append(f"= {spec['eq']}")
        if spec.get('min') is not None:
            parts.append(f"≥ {spec['min']}")
        if spec.get('max') is not None:
            parts.append(f"≤ {spec['max']}")
        if spec.get('pillars'):
            parts.append(f"pillars={spec['pillars']}")
        return "(" + ", ".join(parts) + ")" if parts else ""

    def _describe_element_sources(self, data):
        elements = data.get('elements', {}) or {}
        # 确保 elements 是字典类型
        if not isinstance(elements, dict):
            if isinstance(elements, str):
                try:
                    import json
                    elements = json.loads(elements)
                except (json.JSONDecodeError, TypeError):
                    elements = {}
            else:
                elements = {}
        
        contributions = {}
        for pillar, info in elements.items():
            # 确保 info 是字典类型
            if not isinstance(info, dict):
                if isinstance(info, str):
                    try:
                        import json
                        info = json.loads(info)
                    except (json.JSONDecodeError, TypeError):
                        info = {}
                else:
                    info = {}
            
            stem = info.get('stem') if isinstance(info, dict) else None
            stem_el = info.get('stem_element') if isinstance(info, dict) else None
            if stem_el and stem:
                contributions.setdefault(stem_el, []).append(f"{pillar}.stem({stem})")
            branch = info.get('branch') if isinstance(info, dict) else None
            branch_el = info.get('branch_element') if isinstance(info, dict) else None
            if branch_el and branch:
                contributions.setdefault(branch_el, []).append(f"{pillar}.branch({branch})")
        return contributions


if __name__ == "__main__":


    # bazi = WenZhenBazi(
    #     solar_date='2008-09-08',
    #     solar_time='16:03',
    #     gender='female'    #female
    # )

    # bazi = WenZhenBazi(
    #     solar_date='1979-07-22',
    #     solar_time='07:15',
    #     gender='male'    #female
    # )
    # bazi = WenZhenBazi(
    #     solar_date='1983-09-13',
    #     solar_time='04:30',
    #     gender='male'    #female
    # )

    # bazi = WenZhenBazi(
    #     solar_date='1984-03-08',
    #     solar_time='09:15',
    #     gender='male'    #female
    # )

    # bazi = WenZhenBazi(
    #     solar_date='1988-09-16',
    #     solar_time='05:55',
    #     gender='male'    #female
    # )

    bazi = WenZhenBazi(
        solar_date='1987-01-07',
        solar_time='09:55',
        gender='male'    #female
    )
    bazi.print_result()
    bazi.print_rizhu_gender_analysis()


    # 打印规则匹配结果
    try:
        matched_rules, unmatched_rules = bazi.match_rules(
            rule_types=[
                "marriage_ten_gods",
                "marriage_element",
                "marriage_day_stem",
                "marriage_day_branch",
                "marriage_day_pillar",
                "marriage_stem_pattern",
                "marriage_branch_pattern",
                "marriage_bazi_pattern",
                "marriage_deity",
                "marriage_month_branch",
                "marriage_year_branch",
                "marriage_year_stem",
                "marriage_year_pillar",
                "marriage_nayin",
                "marriage_lunar_birthday",
                "marriage_hour_pillar",
                "marriage_year_event",
                "marriage_luck_cycle",
                "marriage_general",  # 添加婚姻通用规则类型
                "taohua_general",    # 添加桃花通用规则类型
                "rizhu_gender_dynamic"
            ]
        )
        if matched_rules:
            logger.info("\n匹配到的规则：")
            for idx, rule in enumerate(matched_rules, 1):
                rule_code = rule.get('rule_code') or rule.get('rule_id', '')
                rule_name = rule.get('rule_name', '')
                rule_type = rule.get('rule_type', '')
                logger.info(f"{idx}. [{rule_type}] {rule_code} - {rule_name}")
                filters = WenZhenBazi._get_rule_filters(rule_code)
                if filters:
                    if filters.get('category'):
                        logger.info(f"   规则类型: {filters['category']}")
                    if filters.get('gender'):
                        logger.info(f"   对应性别: {filters['gender']}")
                    if filters.get('condition1'):
                        logger.info(f"   筛选条件1: {filters['condition1']}")
                    if filters.get('condition2'):
                        logger.info(f"   筛选条件2: {filters['condition2']}")
                content = rule.get('content', {})
                text = ''
                if isinstance(content, dict):
                    text = content.get('text', '')
                    if not text and 'items' in content:
                        text = "\n   ".join(item.get('text', '') for item in content['items'])
                elif isinstance(content, str):
                    text = content
                if text:
                    logger.info(f"   {text}")
                context_lines = bazi.last_rule_context.get(rule_code) or (
                    bazi.last_rule_context.get(rule.get('rule_id', ''))
                )
                if context_lines:
                    for line in context_lines:
                        logger.info(f"   相关值: {line}")
        else:
            logger.info("\n未匹配到任何婚姻或日柱规则。")

        if unmatched_rules:
            logger.info("\n未命中的规则（全部列出）：")
            for idx, item in enumerate(unmatched_rules, 1):
                logger.info(f"{idx}. [{item['rule_type']}] {item['rule_id']} - {item['rule_name']}")
                logger.info(f"   未命中原因: {item['reason']}")
                rule_snapshot = item.get('rule') or {}
                if rule_snapshot:
                    conditions_json = json.dumps(rule_snapshot.get('conditions', {}), ensure_ascii=False)
                    logger.info(f"   规则条件: {conditions_json}")
                    content = rule_snapshot.get('content')
                    if content:
                        logger.info(f"   规则内容: {json.dumps(content, ensure_ascii=False)}")
                filters = WenZhenBazi._get_rule_filters(item['rule_id'])
                if filters:
                    if filters.get('category'):
                        logger.info(f"   规则类型: {filters['category']}")
                    condition1 = filters.get('condition1')
                    condition2 = filters.get('condition2')
                    gender = filters.get('gender')
                    if gender:
                        logger.info(f"   对应性别: {gender}")
                    if condition1:
                        logger.info(f"   筛选条件1: {condition1}")
                    if condition2:
                        logger.info(f"   筛选条件2: {condition2}")
                context_lines = bazi.last_rule_context.get(item['rule_id'])
                if context_lines:
                    for line in context_lines:
                        logger.info(f"   相关值: {line}")
    except Exception as exc:
        logger.info(f"规则匹配失败: {exc}")