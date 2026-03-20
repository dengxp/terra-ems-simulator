# Copyright (c) 2025-2026 Terra Technology (Guangzhou) Co., Ltd.
# Licensed under the MIT License. See LICENSE file in the project root.

"""
数据波动模型

模拟真实工厂的用能曲线，让模拟数据具有真实感。
支持多种模式：工业负荷、办公负荷、空调负荷、恒定负荷。
"""

import math
import random
from datetime import datetime


def get_load_factor(pattern: str, hour: int) -> float:
    """
    根据模式和当前小时获取负荷系数（0.0 ~ 1.0）

    Args:
        pattern: 波动模式名称
        hour: 当前小时（0-23）

    Returns:
        负荷系数，0.0 表示最低负荷，1.0 表示最高负荷
    """
    if pattern == "industrial":
        return _industrial(hour)
    elif pattern == "office":
        return _office(hour)
    elif pattern == "hvac":
        return _hvac(hour)
    elif pattern == "constant":
        return _constant(hour)
    else:
        return _constant(hour)


def generate_value(
    pattern: str,
    value_min: float,
    value_max: float,
    hour: int,
) -> float:
    """
    根据模式生成瞬时值

    Args:
        pattern: 波动模式
        value_min: 最小值
        value_max: 最大值
        hour: 当前小时

    Returns:
        模拟值
    """
    load = get_load_factor(pattern, hour)
    noise = random.gauss(0, 0.02)
    load = max(0.0, min(1.0, load + noise))
    return value_min + (value_max - value_min) * load


def generate_increment(
    pattern: str,
    inc_min: float,
    inc_max: float,
    hour: int,
    interval_secs: int,
) -> float:
    """
    根据模式生成累积量的时段增量

    Args:
        pattern: 波动模式
        inc_min: 每小时最小增量
        inc_max: 每小时最大增量
        hour: 当前小时
        interval_secs: 上报间隔（秒）

    Returns:
        此间隔内的增量
    """
    load = get_load_factor(pattern, hour)
    noise = random.gauss(0, 0.01)
    load = max(0.0, min(1.0, load + noise))

    hourly_inc = inc_min + (inc_max - inc_min) * load
    # 按间隔比例缩放
    return hourly_inc * (interval_secs / 3600.0)


def _industrial(hour: int) -> float:
    """工业负荷：白班高、午休略降、夜班低"""
    if 8 <= hour < 12:
        return 0.85 + random.uniform(0, 0.15)
    elif 12 <= hour < 13:
        return 0.50 + random.uniform(0, 0.10)
    elif 13 <= hour < 18:
        return 0.80 + random.uniform(0, 0.15)
    elif 18 <= hour < 22:
        return 0.30 + random.uniform(0, 0.10)
    else:
        return 0.05 + random.uniform(0, 0.05)


def _office(hour: int) -> float:
    """办公负荷：工作时间中等，其余极低"""
    if 9 <= hour < 12:
        return 0.50 + random.uniform(0, 0.20)
    elif 12 <= hour < 13:
        return 0.30 + random.uniform(0, 0.10)
    elif 13 <= hour < 18:
        return 0.45 + random.uniform(0, 0.20)
    elif 18 <= hour < 20:
        return 0.15 + random.uniform(0, 0.05)
    else:
        return 0.03 + random.uniform(0, 0.02)


def _hvac(hour: int) -> float:
    """空调负荷：跟随气温，午后最高"""
    temp_factor = 0.5 + 0.5 * math.sin((hour - 6) * math.pi / 12)
    return max(0.0, min(1.0, temp_factor + random.gauss(0, 0.05)))


def _constant(hour: int) -> float:
    """恒定负荷：基本不变，微小波动"""
    return 0.90 + random.uniform(0, 0.10)
