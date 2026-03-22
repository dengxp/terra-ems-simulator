#!/usr/bin/env python3
"""
从 site YAML 生成模拟器 devices.yaml 配置

用法：
    python scripts/gen_devices_from_site.py config/sites/huawei-food.site.yaml > config/devices.yaml
"""

import sys
import yaml


def extract_meters(node, gateway_id=None):
    """递归提取所有 meter 及其 points"""
    meters = []

    # 当前节点的 meters
    for m in node.get("meters", []):
        gw = m.get("gateway", gateway_id)
        points = []
        for p in m.get("points", []):
            sim_type = p.get("sim_type")
            if not sim_type:
                continue
            point = {"code": p["code"], "name": p.get("name", ""), "type": sim_type}
            if sim_type == "accumulate":
                point["base_value"] = p.get("sim_base_value", 0)
                point["hourly_increment"] = p.get("sim_hourly_increment", [1.0, 10.0])
                point["pattern"] = p.get("sim_pattern", "industrial")
            else:
                point["range"] = p.get("sim_range", [0, 100])
                point["pattern"] = p.get("sim_pattern", "constant")
            points.append(point)

        if points:
            meters.append({
                "name": m.get("name", m["code"]),
                "protocol": "mqtt",
                "gateway_id": gw or "GW-001",
                "device_id": m["code"],
                "device_type": "meter",
                "interval": 15,
                "points": points,
            })

    # 递归子节点
    for child in node.get("children", []):
        meters.extend(extract_meters(child, gateway_id))

    # 递归 equipments 下的 meters
    for eq in node.get("equipments", []):
        for m in eq.get("meters", []):
            gw = m.get("gateway", gateway_id)
            points = []
            for p in m.get("points", []):
                sim_type = p.get("sim_type")
                if not sim_type:
                    continue
                point = {"code": p["code"], "name": p.get("name", ""), "type": sim_type}
                if sim_type == "accumulate":
                    point["base_value"] = p.get("sim_base_value", 0)
                    point["hourly_increment"] = p.get("sim_hourly_increment", [1.0, 10.0])
                    point["pattern"] = p.get("sim_pattern", "industrial")
                else:
                    point["range"] = p.get("sim_range", [0, 100])
                    point["pattern"] = p.get("sim_pattern", "constant")
                points.append(point)

            if points:
                meters.append({
                    "name": m.get("name", m["code"]),
                    "protocol": "mqtt",
                    "gateway_id": gw or "GW-001",
                    "device_id": m["code"],
                    "device_type": "meter",
                    "interval": 15,
                    "points": points,
                })

    return meters


def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <site.yaml>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        site = yaml.safe_load(f)

    devices = []
    for unit in site.get("energy_units", []):
        devices.extend(extract_meters(unit))

    config = {
        "mqtt": {
            "broker": "localhost",
            "port": 1883,
            "username": "",
            "password": "",
        },
        "devices": devices,
    }

    yaml.dump(config, sys.stdout, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"\n# 共生成 {len(devices)} 个设备", file=sys.stderr)


if __name__ == "__main__":
    main()
