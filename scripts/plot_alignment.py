import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import re
import argparse
import os
import numpy as np

def extract_all_data(json_path, start_time_str, time_offset, max_t=float('inf')):
    """
    Extracts time series data for all cumulative metrics.
    Returns a dict mapping metric groups (e.g. 'latency', 'goodput', 'availability') to their data.
    """
    # Initialize latency structure specifically since it has quantiles
    data = {"latency": {"latency0": {}, "latency25": {}, "latency50": {}, "latency75": {}, "latency100": {}}}
    num_samples = 0
    
    with open(json_path, 'r') as f:
        d = json.load(f)
        
    results = d["results"]
    pattern = re.compile(r'cumulative:([a-zA-Z0-9_]+):t(\d+)_t(\d+)')
    
    for key, val in results.items():
        match = pattern.match(key)
        if match:
            raw_metric = match.group(1)
            start_t = int(match.group(2))
            end_t = int(match.group(3))
            
            if str(start_t) == start_time_str:
                if num_samples == 0 and 'samples' in val:
                    num_samples = len(val['samples'])
                normalized_t = end_t - time_offset
                if normalized_t <= max_t:
                    # Group all latency metrics under 'latency'
                    point_data = {'mean': val['mean'], 'std': val.get('stddev', 0.0)}
                    if raw_metric.startswith("latency"):
                        if raw_metric not in data["latency"]:
                            data["latency"][raw_metric] = {}
                        data["latency"][raw_metric][normalized_t] = point_data
                    else:
                        if raw_metric not in data:
                            data[raw_metric] = {}
                        data[raw_metric][normalized_t] = point_data
                    
    # Sort the data by time for each metric
    for m_group, series in data.items():
        if m_group == "latency":
            for m in series:
                series[m] = dict(sorted(series[m].items()))
        else:
            data[m_group] = dict(sorted(series.items()))
        
    return data, num_samples

def plot_latency(tb_latency, sim_latency, tb_samples, sim_samples, output_path):
    fig, axs = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle(f'Latency Comparison\n(Testbed: {tb_samples} samples, Simulated: {sim_samples} samples)', fontsize=16)
    
    metrics = ["latency0", "latency25", "latency50", "latency75", "latency100"]
    titles = ["Minimum (0th)", "25th Percentile", "Median (50th)", "75th Percentile", "Maximum (100th)"]
    axs = axs.flatten()
    
    has_data = False
    for i, metric in enumerate(metrics):
        ax = axs[i]
        
        tb_times = list(tb_latency.get(metric, {}).keys())
        tb_means = [d['mean'] for d in tb_latency.get(metric, {}).values()]
        tb_stds = [d['std'] for d in tb_latency.get(metric, {}).values()]
        if tb_times:
            has_data = True
            ax.plot(tb_times, tb_means, marker='o', label='Testbed (Empirical)', color='blue')
            ax.fill_between(tb_times, np.array(tb_means) - np.array(tb_stds), np.array(tb_means) + np.array(tb_stds), color='blue', alpha=0.2)
            
        sim_times = list(sim_latency.get(metric, {}).keys())
        sim_means = [d['mean'] for d in sim_latency.get(metric, {}).values()]
        sim_stds = [d['std'] for d in sim_latency.get(metric, {}).values()]
        if sim_times:
            has_data = True
            ax.plot(sim_times, sim_means, marker='x', label='Simulated (Maude-HCS)', color='red', linestyle='--')
            ax.fill_between(sim_times, np.array(sim_means) - np.array(sim_stds), np.array(sim_means) + np.array(sim_stds), color='red', alpha=0.2)
            
        ax.set_title(f"{titles[i]} Latency")
        ax.set_xlabel('Time Window (Normalized seconds)')
        ax.set_ylabel('Latency (s)')
        ax.grid(True, alpha=0.3)
        ax.legend()

    if not has_data:
        plt.close(fig)
        return

    # Remove empty subplot
    fig.delaxes(axs[5])
    
    # plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_path, dpi=300)
    print(f"Saved latency plot to {output_path}")
    plt.close(fig)

def plot_single_metric(tb_data, sim_data, tb_samples, sim_samples, metric, output_path):
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle(f'{metric.capitalize()} Comparison\n(Testbed: {tb_samples} samples, Simulated: {sim_samples} samples)', fontsize=16)
    
    tb_times = list(tb_data.keys())
    tb_means = [d['mean'] for d in tb_data.values()]
    tb_stds = [d['std'] for d in tb_data.values()]
    has_data = False
    
    if tb_times:
        has_data = True
        ax.plot(tb_times, tb_means, marker='o', label='Testbed (Empirical)', color='blue')
        ax.fill_between(tb_times, np.array(tb_means) - np.array(tb_stds), np.array(tb_means) + np.array(tb_stds), color='blue', alpha=0.2)
        
    sim_times = list(sim_data.keys())
    sim_means = [d['mean'] for d in sim_data.values()]
    sim_stds = [d['std'] for d in sim_data.values()]
    if sim_times:
        has_data = True
        ax.plot(sim_times, sim_means, marker='x', label='Simulated (Maude-HCS)', color='red', linestyle='--')
        ax.fill_between(sim_times, np.array(sim_means) - np.array(sim_stds), np.array(sim_means) + np.array(sim_stds), color='red', alpha=0.2)
        
    if not has_data:
        plt.close(fig)
        return
        
    ax.set_xlabel('Time Window (Normalized seconds)')
    ax.set_ylabel(metric.capitalize())
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"Saved {metric} plot to {output_path}")
    plt.close(fig)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot comparison between testbed and simulated results.")
    parser.add_argument('--testbed', type=str, required=True, help="Path to the testbed JSON file")
    parser.add_argument('--smc', type=str, required=True, help="Path to the simulated (SMC) JSON file")
    parser.add_argument('--outdir', type=str, default="./align_plots", help="Directory to save the output plots")
    parser.add_argument('--metric', type=str, default='all', help="Metric to plot (e.g. latency, goodput, availability). Defaults to 'all'")
    
    args = parser.parse_args()
    
    print("Loading testbed data...")
    tb_data, tb_samples = extract_all_data(args.testbed, "0", 0)
    
    print("Loading simulated data...")
    sim_data, sim_samples = extract_all_data(args.smc, "0", 0)
    
    if not os.path.exists(args.outdir):
        os.makedirs(args.outdir)
        
    # Determine which metrics to plot
    all_metrics = set(tb_data.keys()).union(set(sim_data.keys()))
    if args.metric.lower() != 'all':
        metrics_to_plot = [args.metric.lower()]
    else:
        metrics_to_plot = list(all_metrics)
        
    print(f"Metrics to plot: {metrics_to_plot}")
    
    for m in metrics_to_plot:
        out_path = os.path.join(args.outdir, f"{m}.png")
        if m == 'latency':
            plot_latency(tb_data.get('latency', {}), sim_data.get('latency', {}), tb_samples, sim_samples, out_path)
        else:
            plot_single_metric(tb_data.get(m, {}), sim_data.get(m, {}), tb_samples, sim_samples, m, out_path)
