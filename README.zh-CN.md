# Terra EMS Simulator — 设备模拟器

<p align="center">
  <strong>泰若能源管理系统 — 工业设备模拟器</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/MQTT-paho--mqtt-green?style=flat-square" alt="MQTT"/>
  <img src="https://img.shields.io/badge/Modbus-pymodbus-green?style=flat-square" alt="Modbus"/>
</p>

<p align="center">
  <span>中文文档</span> | <a href="./README.md">English</a>
</p>

---

## 项目简介

Terra EMS Simulator 模拟多种工业设备（电表、水表、传感器），通过 MQTT 和 Modbus TCP 协议生成逼真的能源数据，用于 [Terra EMS Collector](https://github.com/dengxp/terra-ems-collector) 的开发、测试和演示，无需依赖真实硬件。

> Terra EMS 生态：
> [terra-ems-server](https://github.com/dengxp/terra-ems-server)（Java 后端）|
> [terra-ems-web](https://github.com/dengxp/terra-ems-web)（React 前端）|
> [terra-ems-collector](https://github.com/dengxp/terra-ems-collector)（Rust 采集）|
> **terra-ems-simulator**（Python 模拟器）

---

## 功能特性

| 功能 | 说明 |
|:---|:---|
| **MQTT 设备模拟** | 4 个虚拟设备以 JSON 格式向 MQTT Broker 推送数据 |
| **Modbus TCP 从站** | 虚拟 Modbus 服务器，响应采集服务的寄存器读取请求 |
| **真实数据曲线** | 工业负荷、办公负荷、空调负荷、恒定负荷四种波动模型 |
| **累积量模拟** | 模拟电表/水表持续递增的表底值（kWh、m³） |
| **瞬时量模拟** | 模拟电压、电流、功率等波动值 |
| **YAML 配置** | 通过配置文件定义虚拟设备清单和参数 |
| **多协议并行** | MQTT 和 Modbus TCP 设备同时运行 |
| **优雅关闭** | Ctrl+C 停止，正常断开 MQTT 连接 |

---

## 虚拟设备清单

### MQTT 设备（通过网关上报）

| 设备 | 网关 | 采集点位 | 波动模式 |
|:---|:---|:---|:---|
| 1#车间总电表 | GW-001 | 有功电能、电压、电流、功率 | 工业 |
| 1#车间水表 | GW-001 | 累计水量 | 工业 |
| 2#车间电表 | GW-002 | 有功电能、电压 | 工业 |
| 办公楼总电表 | GW-003 | 有功电能、功率 | 办公 |

### Modbus TCP 设备（采集服务轮询）

| 设备 | 地址 | 采集点位 | 波动模式 |
|:---|:---|:---|:---|
| 3#车间配电柜 | 0.0.0.0:5020, 从站 1 | 电压、电流、功率、电能（float32/uint32） | 工业 |

---

## 数据波动模型

| 模式 | 适用场景 | 特征 |
|:---|:---|:---|
| `industrial` | 生产车间 | 8-18 点高负荷，午休略降，夜间极低 |
| `office` | 办公楼 | 9-18 点中等，其余极低 |
| `hvac` | 空调系统 | 跟随气温变化，午后最高 |
| `constant` | 基础设施 | 基本恒定，微小波动 |

---

## 快速开始

### 安装依赖

```bash
pip install paho-mqtt pyyaml pymodbus
```

### 运行

```bash
cd src
python -m simulator --config ../config/devices.yaml
```

### 运行输出

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

## 项目结构

```
terra-ems-simulator/
├── config/
│   └── devices.yaml            # 虚拟设备配置
├── src/
│   └── simulator/
│       ├── __init__.py
│       ├── __main__.py         # 入口
│       ├── patterns.py         # 数据波动模型
│       └── modbus_sim.py       # Modbus TCP 从站模拟
├── pyproject.toml              # 项目配置与依赖
└── README.md
```

---

## 运行环境

- Python >= 3.11
- MQTT Broker 已运行（如 EMQX，端口 1883）
- Modbus 功能需要 `pymodbus >= 3.6.0`

---

## 许可证

专有软件 — Copyright © 2025-2026 泰若科技（广州）有限公司
