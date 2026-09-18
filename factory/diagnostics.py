"""Offline resource and checkout observations, separate from deployment policy."""
from pathlib import Path


def memory_status(meminfo=Path("/proc/meminfo"), cgroup=Path("/sys/fs/cgroup")):
    result = {"source": None, "total_mib": None, "available_mib": None,
              "swap_total_mib": None, "cgroup_limit_mib": None,
              "cgroup_headroom_mib": None, "effective_available_mib": None}
    try:
        fields = {}
        for line in meminfo.read_text().splitlines():
            name, value = line.split(":", 1)
            if name in ("MemTotal", "MemAvailable", "SwapTotal"):
                fields[name] = int(value.split()[0]) / 1024
        result.update(source="/proc/meminfo", total_mib=fields.get("MemTotal"),
                      available_mib=fields.get("MemAvailable"), swap_total_mib=fields.get("SwapTotal"))
    except (OSError, ValueError, IndexError):
        pass
    # These files are exposed at the cgroup mount root on namespace-isolated hosts.
    # If unavailable, retain the proc observation; do not guess a container limit.
    try:
        maximum = (cgroup / "memory.max").read_text().strip()
        if maximum != "max":
            maximum = int(maximum)
            current = int((cgroup / "memory.current").read_text().strip())
            if maximum >= 0 and current >= 0:
                result["cgroup_limit_mib"] = maximum / 1024**2
                result["cgroup_headroom_mib"] = max(0, maximum - current) / 1024**2
    except (OSError, ValueError):
        pass
    available = [result[key] for key in ("available_mib", "cgroup_headroom_mib") if result[key] is not None]
    result["effective_available_mib"] = min(available) if available else None
    return {key: round(value, 1) if isinstance(value, float) else value for key, value in result.items()}


def benchmark_status(root):
    checkout = root.parent / "harness_benchmark"
    names = ("airline", "fraud", "credit")
    required = ("meta.json", "public/train.csv", "public/eval.csv", "private/holdout.csv")
    return {
        "source_present": (checkout / "bench").is_dir(),
        "preparation_scripts": {name: (checkout / "datasets" / f"prepare_{name}.py").is_file() for name in names},
        "prepared_tasks": {
            name: all((checkout / "data/prepared" / name / file).is_file() for file in required)
            for name in names
        },
        "saved_baselines": {name: (checkout / "results/baselines" / f"{name}.json").is_file() for name in names},
        "note": "File presence only, not validation. Prepare data and run benchmarks on workers.",
    }
