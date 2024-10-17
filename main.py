import json
import time
import datetime
import pathlib
import typing

import docker

class ContainerHealthMonitor:
    """Class for monitoring health status of Docker containers."""

    def __init__(self, output_dir: str = "container_stats"):
        self.client = docker.from_env()
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    @staticmethod
    def bytes_to_human_readable(num_bytes: float) -> str:
        """Convert bytes to human readable format."""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        for unit in units:
            if num_bytes < 1024:
                return f"{num_bytes:.2f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.2f} {units[-1]}"

    @staticmethod
    def format_cpu_usage(usage_ns: int) -> str:
        """Format CPU usage in seconds."""
        return f"{usage_ns / 1e9:.2f} seconds"

    @staticmethod
    def calculate_cpu_percentage(stats: typing.Dict) -> float:
        """Calculate CPU usage percentage."""
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                    stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                       stats["precpu_stats"]["system_cpu_usage"]
        return (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0

    def get_container_stats(self) -> typing.Dict[str, typing.Any]:
        """Collect statistics for all running containers."""
        containers = self.client.containers.list()
        stats_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_containers": len(containers),
            "containers": {}
        }

        for container in containers:
            try:
                stats = self.client.api.stats(container.id, stream=False)
                cpu_percent = self.calculate_cpu_percentage(stats)
                memory_usage = stats["memory_stats"]["usage"]
                memory_limit = stats["memory_stats"]["limit"]
                memory_percent = (memory_usage / memory_limit) * 100
                network_stats = stats["networks"]["eth0"]

                stats_data["containers"][container.name] = {
                    "basic_info": {
                        "id": container.id[:12],
                        "name": container.name,
                        "status": container.status,
                        "image": container.image.tags[0] if container.image.tags else "unnamed",
                        "created": container.attrs["Created"]
                    },
                    "resources": {
                        "cpu": {
                            "percentage": round(cpu_percent, 2),
                            "total_usage": self.format_cpu_usage(stats["cpu_stats"]["cpu_usage"]["total_usage"])
                        },
                        "memory": {
                            "percentage": round(memory_percent, 2),
                            "usage": self.bytes_to_human_readable(memory_usage),
                            "limit": self.bytes_to_human_readable(memory_limit),
                            "raw": {"usage": memory_usage, "limit": memory_limit}
                        },
                        "network": {
                            "received": self.bytes_to_human_readable(network_stats["rx_bytes"]),
                            "transmitted": self.bytes_to_human_readable(network_stats["tx_bytes"]),
                            "raw": {
                                "rx_bytes": network_stats["rx_bytes"],
                                "tx_bytes": network_stats["tx_bytes"],
                                "rx_packets": network_stats["rx_packets"],
                                "tx_packets": network_stats["tx_packets"]
                            }
                        }
                    }
                }
            except Exception as e:
                stats_data["containers"][container.name] = {
                    "error": str(e),
                    "timestamp": datetime.datetime.now().isoformat()
                }

        return stats_data

    def export_to_json(self, data: typing.Dict) -> str:
        """Export container statistics to a JSON file and return the filename."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = self.output_dir / f"container_stats_{timestamp}.json"
        with open(file_name, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=2, ensure_ascii=False)
        return str(file_name)

    def monitor_once(self) -> str:
        """Collect and export stats once, return the JSON file path."""
        stats = self.get_container_stats()
        return self.export_to_json(stats)

    def start_monitoring(self, interval: int = 5) -> None:
        """Start continuous monitoring at specified intervals."""
        try:
            while True:
                self.monitor_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Monitoring stopped by user.")

if __name__ == "__main__":
    monitor = ContainerHealthMonitor()
    # For single snapshot
    json_file = monitor.monitor_once()
    print(f"Stats exported to: {json_file}")

    # For continuous monitoring, uncomment the following line:
    # monitor.start_monitoring(5)
