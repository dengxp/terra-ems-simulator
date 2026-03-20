# Terra EMS Simulator — Device Simulator

<p align="center">
  <strong>Industrial device simulator for the Terra Energy Management System</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/MQTT-paho--mqtt-green?style=flat-square" alt="MQTT"/>
  <img src="https://img.shields.io/badge/Modbus-pymodbus-green?style=flat-square" alt="Modbus"/>
</p>

<p align="center">
  <a href="./README.zh-CN.md">中文文档</a> | <span>English</span>
</p>

---

## Overview

Terra EMS Simulator simulates virtual industrial devices (electricity meters, water meters, sensors) that generate realistic energy data using multiple protocols. It enables development, testing, and demonstration of the [Terra EMS Collector](https://github.com/dengxp/terra-ems-collector) without requiring real hardware.

> Part of the Terra EMS ecosystem:
> [terra-ems-server](https://github.com/dengxp/terra-ems-server) (Java Backend) |
> [terra-ems-web](https://github.com/dengxp/terra-ems-web) (React Frontend) |
> [terra-ems-collector](https://github.com/dengxp/terra-ems-collector) (Rust Acquisition) |
> **terra-ems-simulator** (Python Simulator)

---

## Features

| Feature | Description |
|:---|:---|
| **MQTT Device Simulation** | 4 virtual devices push data to MQTT Broker as JSON messages |
| **Modbus TCP Slave** | Virtual Modbus server responding to register read requests |
| **Realistic Data Patterns** | Industrial, office, HVAC, and constant load curves |
| **Accumulating Meters** | Simulates continuously incrementing meter readings (kWh, m³) |
| **Instant Values** | Simulates fluctuating voltage, current, power readings |
| **YAML Configuration** | Define virtual devices and their characteristics in a config file |
| **Multi-protocol** | MQTT and Modbus TCP devices run simultaneously |
| **Graceful Shutdown** | Ctrl+C to stop, clean MQTT disconnect |

---

## Virtual Devices

### MQTT Devices (via Gateway)

| Device | Gateway | Points | Pattern |
|:---|:---|:---|:---|
| Workshop 1 Meter | GW-001 | Active energy, voltage, current, power | Industrial |
| Workshop 1 Water | GW-001 | Water volume | Industrial |
| Workshop 2 Meter | GW-002 | Active energy, voltage | Industrial |
| Office Meter | GW-003 | Active energy, power | Office |

### Modbus TCP Devices (Direct Poll)

| Device | Address | Points | Pattern |
|:---|:---|:---|:---|
| Workshop 3 Panel | 0.0.0.0:5020, Slave 1 | Voltage, current, power, energy (float32/uint32) | Industrial |

---

## Data Patterns

| Pattern | Use Case | Behavior |
|:---|:---|:---|
| `industrial` | Factory floor | High 8am-6pm, lunch dip, low at night |
| `office` | Office building | Medium 9am-6pm, very low otherwise |
| `hvac` | HVAC systems | Follows temperature curve, peak at afternoon |
| `constant` | Base infrastructure | Nearly flat with minor fluctuation |

---

## Quick Start

### Install Dependencies

```bash
pip install paho-mqtt pyyaml pymodbus
```

### Run

```bash
cd src
python -m simulator --config ../config/devices.yaml
```

### Output

```
已加载配置：../config/devices.yaml
设备数量：5
  启动设备: 1#车间总电表 (网关=GW-001, 设备=METER-001, 间隔=15s, 点位数=4)
  启动设备: 1#车间水表 (网关=GW-001, 设备=WATER-001, 间隔=60s, 点位数=1)
  启动设备: 2#车间电表 (网关=GW-002, 设备=METER-002, 间隔=15s, 点位数=2)
  启动设备: 办公楼总电表 (网关=GW-003, 设备=METER-003, 间隔=15s, 点位数=2)
  启动 Modbus 从站: 3#车间配电柜 (地址=0.0.0.0:5020, 从站=1, 寄存器数=4)

模拟器已启动，5 个设备正在运行（MQTT: 4, Modbus: 1）...

[10:00:15] 1#车间总电表: MP-001=135027.85, MP-002=221.5, MP-003=85.2, MP-004=18.7
[10:00:15] 3#车间配电柜(Modbus): MP-100=222.30, MP-101=78.50, MP-102=17.30, MP-103=56823.45
```

---

## Project Structure

```
terra-ems-simulator/
├── config/
│   └── devices.yaml            # Virtual device configuration
├── src/
│   └── simulator/
│       ├── __init__.py
│       ├── __main__.py         # Entry point
│       ├── patterns.py         # Data fluctuation models
│       └── modbus_sim.py       # Modbus TCP slave simulator
├── pyproject.toml              # Project metadata & dependencies
└── README.md
```

---

## Prerequisites

- Python >= 3.11
- MQTT Broker running (e.g., EMQX on port 1883)
- For Modbus: `pymodbus >= 3.6.0`

---

## License

Proprietary — Copyright © 2025-2026 Terra Technology (Guangzhou) Co., Ltd.
