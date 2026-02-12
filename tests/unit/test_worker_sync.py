#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/unit/test_worker_sync.py
Worker 同步模块单元测试
"""

import os
import json
import time
import tempfile
import pytest
from unittest.mock import patch, MagicMock


# ════════════════════ 辅助工具 ════════════════════


@pytest.fixture
def isolated_sync(tmp_path):
    """
    创建隔离的 WorkerSyncManager（使用临时路径，避免影响生产环境）
    """
    from server.hot_reload.worker_sync import WorkerSyncManager

    # 保存原始路径
    orig_signal = WorkerSyncManager.SIGNAL_FILE
    orig_ack = WorkerSyncManager.ACK_DIR

    # 替换为临时路径
    WorkerSyncManager.SIGNAL_FILE = str(tmp_path / "signal.json")
    WorkerSyncManager.ACK_DIR = str(tmp_path / "ack")
    WorkerSyncManager._instance = None  # 重置单例

    yield WorkerSyncManager

    # 恢复
    WorkerSyncManager.SIGNAL_FILE = orig_signal
    WorkerSyncManager.ACK_DIR = orig_ack
    WorkerSyncManager._instance = None


# ════════════════════ trigger_all_workers ════════════════════


class TestTriggerAllWorkers:

    def test_creates_signal_file(self, isolated_sync):
        result = isolated_sync.trigger_all_workers(
            modules=["source"], wait_ack=False
        )
        assert result["success"] is True
        assert result["version"] == 1
        assert os.path.exists(isolated_sync.SIGNAL_FILE)

    def test_signal_version_increments(self, isolated_sync):
        isolated_sync.trigger_all_workers(wait_ack=False)
        r2 = isolated_sync.trigger_all_workers(wait_ack=False)
        assert r2["version"] == 2

    def test_signal_file_valid_json(self, isolated_sync):
        isolated_sync.trigger_all_workers(modules=["rules"], wait_ack=False)
        with open(isolated_sync.SIGNAL_FILE, "r") as f:
            data = json.load(f)
        assert data["version"] == 1
        assert "rules" in data["modules"]
        assert "trigger_pid" in data

    def test_ack_cleanup_after_signal(self, isolated_sync):
        """旧 ACK 文件应在新信号写入后被清理"""
        ack_dir = isolated_sync.ACK_DIR
        os.makedirs(ack_dir, exist_ok=True)
        # 写一个旧 ACK
        old_ack = os.path.join(ack_dir, "worker_old.json")
        with open(old_ack, "w") as f:
            json.dump({"worker_id": "old", "version": 0}, f)

        isolated_sync.trigger_all_workers(wait_ack=False)
        # 旧 ACK 应被清理
        assert not os.path.exists(old_ack)


# ════════════════════ _check_signal ════════════════════


class TestCheckSignal:

    def test_detects_new_signal(self, isolated_sync):
        """检测到新信号时执行回调"""
        callback = MagicMock()
        mgr = isolated_sync.get_instance()
        mgr._reload_callback = callback
        mgr._last_signal_version = 0
        mgr._last_signal_time = 0

        # 写入信号
        isolated_sync.trigger_all_workers(wait_ack=False)
        mgr._check_signal()

        callback.assert_called_once()
        assert mgr._last_signal_version == 1

    def test_ignores_old_signal(self, isolated_sync):
        """已处理过的信号不应再触发回调"""
        callback = MagicMock()
        mgr = isolated_sync.get_instance()
        mgr._reload_callback = callback

        isolated_sync.trigger_all_workers(wait_ack=False)
        mgr._check_signal()
        callback.reset_mock()

        # 再次检查，不应触发
        mgr._check_signal()
        callback.assert_not_called()

    def test_no_signal_file(self, isolated_sync):
        """无信号文件时不崩溃"""
        mgr = isolated_sync.get_instance()
        mgr._reload_callback = MagicMock()
        mgr._check_signal()  # 不应抛异常


# ════════════════════ _write_ack ════════════════════


class TestWriteAck:

    def test_writes_ack_file(self, isolated_sync):
        mgr = isolated_sync.get_instance()
        mgr._write_ack(version=5, success=True)

        ack_file = os.path.join(
            isolated_sync.ACK_DIR, f"worker_{mgr._worker_id}.json"
        )
        assert os.path.exists(ack_file)
        with open(ack_file, "r") as f:
            data = json.load(f)
        assert data["version"] == 5
        assert data["success"] is True

    def test_ack_file_is_valid_json(self, isolated_sync):
        """ACK 文件应为合法 JSON（原子写入保证）"""
        mgr = isolated_sync.get_instance()
        mgr._write_ack(version=1, success=False)

        ack_file = os.path.join(
            isolated_sync.ACK_DIR, f"worker_{mgr._worker_id}.json"
        )
        with open(ack_file, "r") as f:
            data = json.load(f)  # 不应抛 JSONDecodeError
        assert data["success"] is False


# ════════════════════ signal file atomic write ════════════════════


class TestAtomicWrite:

    def test_signal_no_temp_files_left(self, isolated_sync):
        """原子写入后不应残留 .tmp 文件"""
        isolated_sync.trigger_all_workers(wait_ack=False)
        signal_dir = os.path.dirname(isolated_sync.SIGNAL_FILE)
        tmp_files = [f for f in os.listdir(signal_dir) if f.endswith(".tmp")]
        assert tmp_files == []

    def test_ack_no_temp_files_left(self, isolated_sync):
        """ACK 原子写入后不应残留 .tmp 文件"""
        mgr = isolated_sync.get_instance()
        mgr._write_ack(version=1, success=True)
        tmp_files = [f for f in os.listdir(isolated_sync.ACK_DIR) if f.endswith(".tmp")]
        assert tmp_files == []


# ════════════════════ singleton ════════════════════


class TestSingleton:

    def test_get_instance_returns_same(self, isolated_sync):
        a = isolated_sync.get_instance()
        b = isolated_sync.get_instance()
        assert a is b


# ════════════════════ start / stop ════════════════════


class TestStartStop:

    def test_start_and_stop(self, isolated_sync):
        mgr = isolated_sync.get_instance()
        callback = MagicMock()
        mgr.start(reload_callback=callback)
        assert mgr._running is True
        assert mgr._thread is not None

        mgr.stop()
        assert mgr._running is False
