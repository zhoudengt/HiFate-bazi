#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微服务调用 Mixin

从 bazi_calculator.py 提取的微服务通信相关方法。
包含 bazi-core、bazi-fortune、bazi-rule 三个微服务的调用/回退逻辑。
"""

import os
import socket
from datetime import datetime

from core.calculators.bazi_logging import safe_log


class BaziServiceClientMixin:
    """微服务调用方法，以 Mixin 方式注入 WenZhenBazi"""

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

                if 'star_fortune' not in pillar_detail or not pillar_detail.get('star_fortune'):
                    star_fortune = calculator.get_stem_fortune(day_stem, pillar.get('branch', ''))
                    pillar_detail['star_fortune'] = star_fortune

                if 'self_sitting' not in pillar_detail or not pillar_detail.get('self_sitting'):
                    self_sitting = calculator.get_stem_fortune(pillar.get('stem', ''), pillar.get('branch', ''))
                    pillar_detail['self_sitting'] = self_sitting

    def _calculate_via_core_service(self):
        """通过 bazi-core 微服务计算排盘（可选，未配置时返回 None）"""
        service_url = os.getenv("BAZI_CORE_SERVICE_URL", "").strip()
        if not service_url:
            return None

        if service_url.startswith("http://"):
            service_url = service_url[7:]
        elif service_url.startswith("https://"):
            service_url = service_url[8:]

        if ":" in service_url:
            host, port_str = service_url.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                host, port = service_url, 9001
        else:
            host, port = service_url, 9001

        import datetime as dt_mod
        request_time = dt_mod.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_log('info', f"[{request_time}] 🔵 bazi_calculator.py: 强制调用 bazi-core-service (gRPC): {service_url}")

        strict = os.getenv("BAZI_CORE_SERVICE_STRICT", "0") == "1"
        try:
            from shared.clients.bazi_core_client_grpc import BaziCoreClient

            client = BaziCoreClient(base_url=service_url, timeout=30.0)
            result = client.calculate_bazi(self.solar_date, self.solar_time, self.gender)
            safe_log('info', f"[{request_time}] ✅ bazi_calculator.py: bazi-core-service 调用成功")
            self._apply_remote_core_result(result)
            return result
        except Exception as exc:
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
                raise RuntimeError(f"微服务调用失败: {exc}") from exc

    @staticmethod
    def _check_service_port(host, port):
        """检查服务端口是否在监听"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

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

        if service_url.startswith("http://"):
            service_url = service_url[7:]
        elif service_url.startswith("https://"):
            service_url = service_url[8:]

        if ":" in service_url:
            host, port_str = service_url.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                host, port = service_url, 9001  # 已合并到 bazi-compute
        else:
            host, port = service_url, 9001  # 已合并到 bazi-compute

        import datetime as dt_mod
        request_time = dt_mod.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_log('info', f"[{request_time}] 🔵 bazi_calculator.py: 强制调用 bazi-fortune-service (gRPC): {service_url}")

        detail = None
        strict = os.getenv("BAZI_FORTUNE_SERVICE_STRICT", "0") == "1"
        try:
            from shared.clients.bazi_fortune_client_grpc import BaziFortuneClient

            client = BaziFortuneClient(base_url=service_url, timeout=30.0)
            detail = client.calculate_detail(
                self.solar_date,
                self.solar_time,
                self.gender,
                current_time=current_time_str,
            )
            safe_log('info', f"[{request_time}] ✅ bazi_calculator.py: bazi-fortune-service 调用成功")
        except Exception as exc:
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
                from core.calculators.helpers import compute_local_detail
                detail = compute_local_detail(
                    self.solar_date,
                    self.solar_time,
                    self.gender,
                    current_time=current_time_obj,
                )
            else:
                raise RuntimeError(f"微服务调用失败: {exc}") from exc

        if detail is None:
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
            current_time_val = detail.get('basic_info', {}).get('current_time')
            if current_time_val:
                try:
                    target_year = int(str(current_time_val)[:4])
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

    def _match_rules_via_service(self, rule_types=None, use_cache=False):
        service_url = os.getenv("BAZI_RULE_SERVICE_URL", "").strip()
        if not service_url:
            raise RuntimeError(
                "❌ BAZI_RULE_SERVICE_URL 未设置！所有展示页面必须调用微服务。\n"
                "请确保已启动微服务并设置环境变量。\n"
                "启动方式: ./start_all_services.sh"
            )

        if service_url.startswith("http://"):
            service_url = service_url[7:]
        elif service_url.startswith("https://"):
            service_url = service_url[8:]

        if ":" in service_url:
            host, port_str = service_url.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                host, port = service_url, 9004
        else:
            host, port = service_url, 9004

        import datetime as dt_mod
        request_time = dt_mod.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rule_types_str = ", ".join(rule_types) if rule_types else "全部"
        safe_log('info', f"[{request_time}] 🔵 bazi_calculator.py: 强制调用 bazi-rule-service (gRPC): {service_url}, rule_types=[{rule_types_str}]")

        strict = os.getenv("BAZI_RULE_SERVICE_STRICT", "0") == "1"
        try:
            from shared.clients.bazi_rule_client_grpc import BaziRuleClient

            client = BaziRuleClient(base_url=service_url, timeout=120.0)
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
                return self._match_rules_locally(rule_types)
            else:
                raise RuntimeError(f"微服务调用失败: {exc}") from exc
