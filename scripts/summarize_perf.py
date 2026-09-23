#!/usr/bin/env python3
"""Summarize IRC goodput, latency, integrity, and availability experiments.

The input may be one experiment directory or a quoted glob that selects several
experiment directories.  The output contains per-experiment values plus
population mean and standard deviation across successfully analyzed runs.
"""

import argparse
import glob
import json
import math
import re
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from statistics import fmean, pstdev


TIMESTAMP = "%Y-%m-%d %H:%M:%S.%f"
SENT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) INFO Sent to (#\w+): (.*)$")
RECEIVED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) INFO \[(#\w+)\] (\w+): (.*)$")
START_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) INFO (\w+) Starting\.\.\.$")
END_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) INFO All messages sent\.$")
HEADER_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} INFO CP3 IRC Client: (\w+)$")


def parse_log(path: Path) -> dict:
    """Parse one Alice IRC client log."""
    name = None
    start = end = None
    events, sent, received, activity = [], [], [], []
    with path.open(encoding="utf-8", errors="replace") as log:
        for raw in log:
            line = raw.strip()
            header = HEADER_RE.match(line)
            if header:
                name = name or header.group(1)
                continue
            match = START_RE.match(line)
            if match:
                start = datetime.strptime(match.group(1), TIMESTAMP)
                name = name or match.group(2)
                events.append(start)
                continue
            match = END_RE.match(line)
            if match:
                end = datetime.strptime(match.group(1), TIMESTAMP)
                events.append(end)
                continue
            match = SENT_RE.match(line)
            if match:
                when = datetime.strptime(match.group(1), TIMESTAMP)
                sent.append((when, match.group(2), match.group(3)))
                activity.append((match.group(2), name, match.group(3)))
                events.append(when)
                continue
            match = RECEIVED_RE.match(line)
            if match:
                when = datetime.strptime(match.group(1), TIMESTAMP)
                received.append((when, match.group(2), match.group(3), match.group(4)))
                activity.append((match.group(2), match.group(3), match.group(4)))
                events.append(when)

    if not events:
        raise ValueError("contains no recognizable IRC events")
    first, last = min(events), max(events)
    start, end = start or first, end or last
    return {
        "name": name or path.stem,
        "path": str(path),
        "sent": sent,
        "received": received,
        "activity": activity,
        "start": start,
        "end": end,
        "duration_s": max(0.0, (end - start).total_seconds()),
    }


def edit_distance(first, second):
    previous = list(range(len(second) + 1))
    for i, item in enumerate(first, 1):
        current = [i]
        for j, other in enumerate(second, 1):
            current.append(previous[j - 1] if item == other else 1 + min(previous[j], current[-1], previous[j - 1]))
        previous = current
    return previous[-1]


def percentile(values, percentage):
    """Return a linearly interpolated percentile, matching NumPy's default."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage / 100.0
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def find_logs(experiment: Path):
    logs = sorted(experiment.glob("raceboat_users/**/code/alice*.log"))
    if len(logs) < 2:
        raise ValueError("expected at least two logs under raceboat_users/**/code/alice*.log")
    return logs


def analyze_experiment(experiment: Path) -> dict:
    clients = [parse_log(path) for path in find_logs(experiment)]
    names = [client["name"] for client in clients]
    if len(names) != len(set(names)):
        raise ValueError(f"duplicate client names: {names}")

    sent_bytes = sum(len(message.encode("utf-8")) for client in clients for _, _, message in client["sent"])
    received_bytes = sum(len(message.encode("utf-8")) for client in clients for _, _, _, message in client["received"])
    sent_messages = sum(len(client["sent"]) for client in clients)
    received_messages = sum(len(client["received"]) for client in clients)
    starts, ends = [c["start"] for c in clients], [c["end"] for c in clients]
    duration = max(0.0, (max(ends) - min(starts)).total_seconds())
    total_goodput = (sent_bytes + received_bytes) * 8.0 / duration if duration else 0.0

    latencies = []
    delivered = 0
    received_by_client = {}
    for receiver in clients:
        # Each peer should receive its own copy of a sent message.  Keep queues
        # per receiver so duplicate messages are matched in send order.
        outstanding = defaultdict(deque)
        for sender_client in clients:
            if sender_client["name"] == receiver["name"]:
                continue
            for sent_at, room, message in sender_client["sent"]:
                outstanding[(sender_client["name"], room, message)].append(sent_at)
        local_view = defaultdict(list)
        for room, sender, message in receiver["activity"]:
            local_view[room].append((sender, message))
        for when, room, sender, message in receiver["received"]:
            queue = outstanding[(sender, room, message)]
            if queue:
                sent_at = queue.popleft()
                latency = (when - sent_at).total_seconds()
                if latency >= 0:
                    latencies.append(latency)
                    delivered += 1
        received_by_client[receiver["name"]] = local_view

    all_sent = sorted(
        (when, room, sender["name"], message)
        for sender in clients for when, room, message in sender["sent"]
    )
    global_by_room = defaultdict(list)
    for _, room, sender, message in all_sent:
        global_by_room[room].append((sender, message))
    integrity_values = []
    for local_view in received_by_client.values():
        room_values = []
        for room, view in local_view.items():
            global_view = global_by_room[room]
            length = max(len(view), len(global_view))
            room_values.append(1.0 if not length else 1.0 - edit_distance(view, global_view) / length)
        integrity_values.append(fmean(room_values) if room_values else 1.0)

    expected_deliveries = sum(len(client["sent"]) for client in clients) * (len(clients) - 1)
    return {
        "experiment": str(experiment),
        "clients": names,
        "log_files": [str(path) for path in find_logs(experiment)],
        "goodput_bps": total_goodput,
        "latency_s": {
            "matched_messages": len(latencies),
            "mean": fmean(latencies) if latencies else None,
            "stddev": pstdev(latencies) if len(latencies) > 1 else 0.0 if latencies else None,
            "percentiles": {
                "p0_min": percentile(latencies, 0),
                "p25": percentile(latencies, 25),
                "p50_median": percentile(latencies, 50),
                "p75": percentile(latencies, 75),
                "p100_max": percentile(latencies, 100),
            },
        },
        "availability": {"delivered_messages": delivered, "expected_deliveries": expected_deliveries,
                         "rate": delivered / expected_deliveries if expected_deliveries else None},
        "integrity": {"system": fmean(integrity_values), "per_client": dict(zip(names, integrity_values))},
        "network_duration_s": duration,
        "irc_messages": {"sent": sent_messages, "received": received_messages,
                         "total": sent_messages + received_messages},
        "payload_bytes": {"sent": sent_bytes, "received": received_bytes,
                          "total": sent_bytes + received_bytes},
    }


def summary(values):
    values = [value for value in values if value is not None and math.isfinite(value)]
    return {"count": len(values), "mean": fmean(values) if values else None,
            "stddev": pstdev(values) if len(values) > 1 else 0.0 if values else None}


def per_client_integrity_summary(results):
    values_by_client = defaultdict(list)
    for result in results:
        for client, value in result["integrity"]["per_client"].items():
            values_by_client[client].append(value)
    return {client: summary(values) for client, values in sorted(values_by_client.items())}


def expand_inputs(inputs):
    paths = set()
    for value in inputs:
        matches = glob.glob(value)
        if not matches and Path(value).is_dir():
            matches = [value]
        paths.update(Path(match).resolve() for match in matches if Path(match).is_dir())
    return sorted(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiments", nargs="+", help="Experiment directory or quoted glob pattern")
    parser.add_argument("-o", "--output", default="irc_experiment_results.json", help="JSON output path")
    args = parser.parse_args()
    experiments = expand_inputs(args.experiments)
    if not experiments:
        parser.error("no experiment directories matched")

    results, failures = [], []
    for experiment in experiments:
        try:
            results.append(analyze_experiment(experiment))
        except (OSError, ValueError) as error:
            failures.append({"experiment": str(experiment), "error": str(error)})
    document = {
        "standard_deviation": "population",
        "experiments": results,
        "summary": {
            "experiments_analyzed": len(results),
            "goodput_bps": summary([item["goodput_bps"] for item in results]),
            "latency_mean_s": summary([item["latency_s"]["mean"] for item in results]),
            "latency_percentiles_s": {
                key: summary([item["latency_s"]["percentiles"][key] for item in results])
                for key in ("p0_min", "p25", "p50_median", "p75", "p100_max")
            },
            "availability_rate": summary([item["availability"]["rate"] for item in results]),
            "integrity_system": summary([item["integrity"]["system"] for item in results]),
            "integrity_per_client": per_client_integrity_summary(results),
            "irc_messages_total": summary([item["irc_messages"]["total"] for item in results]),
            "payload_bytes_total": summary([item["payload_bytes"]["total"] for item in results]),
        },
        "failures": failures,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} ({len(results)} analyzed, {len(failures)} skipped)")
    if not results:
        sys.exit(1)


if __name__ == "__main__":
    main()
