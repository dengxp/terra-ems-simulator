# Copyright (c) 2025-2026 Terra Technology (Guangzhou) Co., Ltd.
# Licensed under the MIT License. See LICENSE file in the project root.

"""
Modbus TCP 从站模拟器

模拟 Modbus TCP 设备（电表），让 Collector 的 Modbus 采集任务可以轮询读取。
寄存器值按数据波动模型定时更新，模拟真实仪表读数变化。
"""

import struct
import threading
import time
from datetime import datetime

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.server import StartTcpServer

from simulator.patterns import generate_increment, generate_value


def start_modbus_simulator(
    devices: list[dict],
    stop_event: threading.Event,
) -> None:
    """
    启动 Modbus TCP 从站模拟器

    Args:
        devices: Modbus 设备配置列表（从 devices.yaml 中筛选 protocol=modbus_tcp 的设备）
        stop_event: 停止信号
    """
    if not devices:
        return

    for device in devices:
        host = device.get("host", "0.0.0.0")
        port = device.get("port", 5020)
        slave_id = device.get("slave_id", 1)
        registers = device.get("registers", [])

        # 计算需要的寄存器空间（找最大地址 + 数据类型占用的寄存器数）
        max_addr = 0
        for reg in registers:
            addr = reg.get("address", 0)
            dtype = reg.get("data_type", "float32")
            count = _reg_count(dtype)
            max_addr = max(max_addr, addr + count)

        # 创建寄存器数据块（预留足够空间）
        block_size = max(max_addr + 10, 100)
        hr_block = ModbusSequentialDataBlock(0, [0] * block_size)

        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0] * 10),
            co=ModbusSequentialDataBlock(0, [0] * 10),
            hr=hr_block,
            ir=ModbusSequentialDataBlock(0, [0] * 10),
        )
        context = ModbusServerContext(slaves={slave_id: store}, single=False)

        # 初始化寄存器值
        _update_registers(store, registers, init=True)

        # 后台线程定时更新寄存器值
        update_thread = threading.Thread(
            target=_register_update_loop,
            args=(store, registers, device, stop_event),
            daemon=True,
        )
        update_thread.start()

        # 启动 Modbus TCP Server（在独立线程中）
        server_thread = threading.Thread(
            target=_run_server,
            args=(context, host, port, device["name"]),
            daemon=True,
        )
        server_thread.start()

        print(
            f"  启动 Modbus 从站: {device['name']} "
            f"(地址={host}:{port}, "
            f"从站={slave_id}, "
            f"寄存器数={len(registers)})"
        )


def _run_server(context, host: str, port: int, name: str) -> None:
    """运行 Modbus TCP Server"""
    try:
        StartTcpServer(context=context, address=(host, port))
    except Exception as e:
        print(f"Modbus Server [{name}] 启动失败: {e}")


def _register_update_loop(
    store: ModbusSlaveContext,
    registers: list[dict],
    device: dict,
    stop_event: threading.Event,
) -> None:
    """定时更新寄存器值"""
    interval = device.get("interval", 15)
    name = device.get("name", "unknown")

    # 维护累积量状态
    accum_state: dict[str, float] = {}
    for reg in registers:
        if reg.get("type") == "accumulate":
            accum_state[reg["point_code"]] = float(reg.get("base_value", 0))

    while not stop_event.is_set():
        _update_registers(store, registers, accum_state=accum_state, interval=interval)

        # 打印日志
        now = datetime.now()
        values = []
        for reg in registers:
            addr = reg["address"]
            dtype = reg.get("data_type", "float32")
            count = _reg_count(dtype)
            raw_regs = store.getValues(3, addr, count=count)  # 3 = Holding Register
            val = _decode_registers(raw_regs, dtype)
            scale = reg.get("scale", 1.0)
            offset = reg.get("offset", 0.0)
            actual = val * scale + offset
            values.append(f"{reg['point_code']}={actual:.2f}")

        print(f"[{now.strftime('%H:%M:%S')}] {name}(Modbus): {', '.join(values)}")

        stop_event.wait(timeout=interval)


def _update_registers(
    store: ModbusSlaveContext,
    registers: list[dict],
    init: bool = False,
    accum_state: dict[str, float] | None = None,
    interval: int = 15,
) -> None:
    """更新寄存器值"""
    hour = datetime.now().hour

    for reg in registers:
        addr = reg["address"]
        dtype = reg.get("data_type", "float32")
        pattern = reg.get("pattern", "constant")
        reg_type = reg.get("type", "instant")

        if reg_type == "accumulate" and accum_state is not None:
            # 累积量：递增
            inc_range = reg.get("hourly_increment", [1, 10])
            if init:
                raw_val = reg.get("base_value", 0)
            else:
                increment = generate_increment(
                    pattern, inc_range[0], inc_range[1], hour, interval
                )
                accum_state[reg["point_code"]] = accum_state.get(
                    reg["point_code"], reg.get("base_value", 0)
                ) + increment
                # 将实际值转回寄存器原始值（除以 scale）
                scale = reg.get("scale", 1.0)
                raw_val = accum_state[reg["point_code"]] / scale if scale != 0 else 0
        else:
            # 瞬时量
            value_range = reg.get("range", [0, 100])
            if init:
                raw_val = (value_range[0] + value_range[1]) / 2
            else:
                actual = generate_value(pattern, value_range[0], value_range[1], hour)
                scale = reg.get("scale", 1.0)
                raw_val = (actual - reg.get("offset", 0.0)) / scale if scale != 0 else 0

        # 编码为寄存器值并写入
        encoded = _encode_value(raw_val, dtype)
        store.setValues(3, addr, encoded)  # 3 = Holding Register


def _encode_value(value: float, data_type: str) -> list[int]:
    """将数值编码为 Modbus 寄存器值列表（大端序）"""
    if data_type in ("uint16",):
        return [int(value) & 0xFFFF]
    elif data_type in ("int16",):
        raw = struct.pack(">h", int(value))
        return [struct.unpack(">H", raw)[0]]
    elif data_type in ("uint32",):
        val = int(value) & 0xFFFFFFFF
        return [(val >> 16) & 0xFFFF, val & 0xFFFF]
    elif data_type in ("int32",):
        raw = struct.pack(">i", int(value))
        return [struct.unpack(">HH", raw)[0], struct.unpack(">HH", raw)[1]]
    elif data_type in ("float32",):
        raw = struct.pack(">f", value)
        return [
            struct.unpack(">H", raw[0:2])[0],
            struct.unpack(">H", raw[2:4])[0],
        ]
    elif data_type in ("float64",):
        raw = struct.pack(">d", value)
        return [
            struct.unpack(">H", raw[i : i + 2])[0] for i in range(0, 8, 2)
        ]
    else:
        return [int(value) & 0xFFFF]


def _decode_registers(regs: list[int], data_type: str) -> float:
    """将寄存器值解码为数值（用于日志）"""
    if data_type == "uint16":
        return float(regs[0])
    elif data_type == "int16":
        raw = struct.pack(">H", regs[0])
        return float(struct.unpack(">h", raw)[0])
    elif data_type in ("uint32", "int32"):
        return float((regs[0] << 16) | regs[1])
    elif data_type == "float32":
        raw = struct.pack(">HH", regs[0], regs[1])
        return struct.unpack(">f", raw)[0]
    elif data_type == "float64":
        raw = struct.pack(">HHHH", *regs[:4])
        return struct.unpack(">d", raw)[0]
    return 0.0


def _reg_count(data_type: str) -> int:
    """数据类型需要的寄存器数量"""
    if data_type in ("uint16", "int16"):
        return 1
    elif data_type in ("uint32", "int32", "float32"):
        return 2
    elif data_type == "float64":
        return 4
    return 1
