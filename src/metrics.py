import time
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class Metrics:
    start_time: float = field(default_factory=time.time)

    connects_total: int = 0
    disconnects_total: int = 0
    subscribes_total: int = 0
    publishes_total: int = 0
    bytes_in_total: int = 0
    bytes_out_total: int = 0

    # packet timing
    packet_count: Dict[str, int] = field(default_factory=lambda: {})
    packet_time_sum_ms: Dict[str, float] = field(default_factory=lambda: {})
    packet_time_max_ms: Dict[str, float] = field(default_factory=lambda: {})

    def observe_packet(self, name: str, ms: float):
        self.packet_count[name] = self.packet_count.get(name, 0) + 1
        self.packet_time_sum_ms[name] = self.packet_time_sum_ms.get(name, 0.0) + ms
        self.packet_time_max_ms[name] = max(self.packet_time_max_ms.get(name, 0.0), ms)

    def snapshot(self):
        up = time.time() - self.start_time
        avg_ms = {}
        for k, c in self.packet_count.items():
            avg_ms[k] = (self.packet_time_sum_ms.get(k, 0.0) / c) if c else 0.0

        return {
            "uptime_sec": round(up, 2),
            "connects_total": self.connects_total,
            "disconnects_total": self.disconnects_total,
            "subscribes_total": self.subscribes_total,
            "publishes_total": self.publishes_total,
            "bytes_in_total": self.bytes_in_total,
            "bytes_out_total": self.bytes_out_total,
            "packet_count": self.packet_count,
            "packet_avg_ms": {k: round(v, 3) for k, v in avg_ms.items()},
            "packet_max_ms": {k: round(v, 3) for k, v in self.packet_time_max_ms.items()},
        }

METRICS = Metrics()