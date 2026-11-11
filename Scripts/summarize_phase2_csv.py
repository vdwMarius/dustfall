"""Summarize Unreal CSV profiler timings without importing Unreal or pandas."""
import argparse
import csv
import gzip
import json
import math
import pathlib
import statistics


def summarize(path, discard=0):
    opener = gzip.open if path.suffix == '.gz' else open
    values = {key: [] for key in ['FrameTime', 'GameThreadTime', 'RenderThreadTime', 'GPUTime']}
    valid = 0
    with opener(path, 'rt', encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            try:
                frame = float(row.get('FrameTime', ''))
            except (TypeError, ValueError):
                continue
            if frame <= 0:
                continue
            valid += 1
            if valid <= discard:
                continue
            for key in values:
                try:
                    number = float(row.get(key, ''))
                    if math.isfinite(number) and number >= 0:
                        values[key].append(number)
                except (TypeError, ValueError):
                    pass
    result = {'file': path.name, 'discarded_warmup_frames': discard, 'timings_ms': {}}
    for key, numbers in values.items():
        if not numbers:
            continue
        numbers.sort()
        n = len(numbers)
        result['timings_ms'][key] = {'samples': n, 'median': round(statistics.median(numbers), 3),
            'p95': round(numbers[min(n-1, math.ceil(n*.95)-1)], 3),
            'p99': round(numbers[min(n-1, math.ceil(n*.99)-1)], 3), 'max': round(numbers[-1], 3)}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='+', type=pathlib.Path)
    parser.add_argument('--discard', type=int, default=0)
    parser.add_argument('--output', required=True, type=pathlib.Path)
    args = parser.parse_args()
    result = {'scope': 'Observed workstation capture; not representative mid-range certification',
              'captures': [summarize(path, args.discard) for path in args.paths]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
