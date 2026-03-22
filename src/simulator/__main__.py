# Copyright (c) 2025-2026 Terra Technology (Guangzhou) Co., Ltd.
# Licensed under the MIT License. See LICENSE file in the project root.

"""
Terra EMS 设备模拟器入口

启动方式：
    python -m simulator
    python -m simulator --config config/devices.yaml
"""

import argparse
import json
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
import yaml

from simulator.patterns import generate_increment, generate_value


def main():
    parser = argparse.ArgumentParser(description="Terra EMS 设备模拟器")
    parser.add_argument(
        "--config",
        type=str,
        default="config/devices.yaml",
        help="设备配置文件路径",
    )
    args = parser.parse_args()

    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误：配置文件 {config_path} 不存在")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print(f"已加载配置：{config_path}")
    print(f"设备数量：{len(config['devices'])}")

    # 连接 MQTT Broker（环境变量优先于配置文件）
    import os
    mqtt_config = config.get("mqtt", {})
    broker = os.environ.get("MQTT_HOST") or mqtt_config.get("broker", "localhost")
    port = int(os.environ.get("MQTT_PORT", 0)) or mqtt_config.get("port", 1883)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="terra-simulator",
    )

    username = mqtt_config.get("username", "")
    password = mqtt_config.get("password", "")
    if username:
        client.username_pw_set(username, password)

    def on_connect(client, userdata, flags, reason_code, properties=None):
        print(f"已连接 MQTT Broker: {broker}:{port} (rc={reason_code})")

    def on_disconnect(client, userdata, flags, reason_code, properties=None):
        print(f"MQTT 连接断开 (rc={reason_code})，等待重连...")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        print(f"错误：无法连接 MQTT Broker {broker}:{port} - {e}")
        sys.exit(1)

    client.loop_start()

    # 优雅关闭
    stop_event = threading.Event()

    def signal_handler(sig, frame):
        print("\n收到退出信号，正在停止...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 按协议类型分类设备
    mqtt_devices = [d for d in config["devices"] if d.get("protocol", "mqtt") == "mqtt"]
    modbus_devices = [d for d in config["devices"] if d.get("protocol") == "modbus_tcp"]

    # 初始化 MQTT 设备状态（累积量的当前表底值）
    device_states: dict[str, dict[str, float]] = {}
    for device in mqtt_devices:
        device_id = device["device_id"]
        device_states[device_id] = {}
        for point in device["points"]:
            if point["type"] == "accumulate":
                device_states[device_id][point["code"]] = point["base_value"]

    # 启动 MQTT 设备的上报线程
    threads: list[threading.Thread] = []
    for device in mqtt_devices:
        t = threading.Thread(
            target=_device_loop,
            args=(client, device, device_states[device["device_id"]], stop_event),
            daemon=True,
        )
        t.start()
        threads.append(t)
        print(
            f"  启动设备: {device['name']} "
            f"(网关={device['gateway_id']}, "
            f"设备={device['device_id']}, "
            f"间隔={device['interval']}s, "
            f"点位数={len(device['points'])})"
        )

    # 启动 Modbus 从站模拟器
    if modbus_devices:
        try:
            from simulator.modbus_sim import start_modbus_simulator
            start_modbus_simulator(modbus_devices, stop_event)
        except ImportError:
            print("警告：pymodbus 未安装，跳过 Modbus 模拟。安装方式：pip install pymodbus")

    total = len(mqtt_devices) + len(modbus_devices)
    print(f"\n模拟器已启动，{total} 个设备正在运行（MQTT: {len(mqtt_devices)}, Modbus: {len(modbus_devices)}）...")
    print("按 Ctrl+C 停止\n")

    # 等待退出信号
    stop_event.wait()

    client.loop_stop()
    client.disconnect()
    print("模拟器已停止")


def _device_loop(
    client: mqtt.Client,
    device: dict,
    state: dict[str, float],
    stop_event: threading.Event,
) -> None:
    """单个设备的数据上报循环"""
    gateway_id = device["gateway_id"]
    device_id = device["device_id"]
    device_type = device.get("device_type", "meter")
    interval = device["interval"]
    topic = f"ems/data/{gateway_id}/{device_type}/{device_id}"

    while not stop_event.is_set():
        now = datetime.now()
        hour = now.hour
        timestamp = int(now.timestamp() * 1000)

        points = []
        for point_cfg in device["points"]:
            code = point_cfg["code"]
            point_type = point_cfg["type"]
            pattern = point_cfg.get("pattern", "constant")

            if point_type == "accumulate":
                # 累积量：在当前表底值上累加增量
                inc_range = point_cfg["hourly_increment"]
                increment = generate_increment(
                    pattern, inc_range[0], inc_range[1], hour, interval
                )
                state[code] = state.get(code, point_cfg["base_value"]) + increment
                value = round(state[code], 4)
            else:
                # 瞬时量：直接生成值
                value_range = point_cfg["range"]
                value = round(
                    generate_value(pattern, value_range[0], value_range[1], hour), 2
                )

            points.append({"code": code, "value": value, "quality": 0})

        # 构造消息
        message = {
            "gatewayId": gateway_id,
            "deviceId": device_id,
            "timestamp": timestamp,
            "points": points,
        }

        payload = json.dumps(message)
        result = client.publish(topic, payload, qos=1)

        # 打印日志
        point_summary = ", ".join(
            f"{p['code']}={p['value']}" for p in points
        )
        print(f"[{now.strftime('%H:%M:%S')}] {device['name']}: {point_summary}")

        stop_event.wait(timeout=interval)


if __name__ == "__main__":
    main()
