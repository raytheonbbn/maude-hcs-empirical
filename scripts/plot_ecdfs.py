from pathlib import Path
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from scipy.stats import ks_2samp
import numpy as np
import json

THIS_PATH = Path(__file__).resolve()

# wtfffff ok cl[5] is sometimes present, sometimes not. it HAS to be present for anything in webtunnel network.
# So, depending on the run, I need to know which cl to isolate and convert.

NAME_MAP = {
    "single_tgen_mastodon": "SingleTgenMastodonConfidentiality",
    "single_tgen_dns": "SingleTgenDnsConfidentiality",
    "single_tgen_ftp_obfs": "SingleTgenFtpObfsConfidentiality",
    "single_tgen_ftp_webtunnel": "SingleTgenFtpWebtunnelConfidentiality",
    "single_tgen_gorilla_obfs": "SingleTgenGorillaObfsConfidentiality",
    "single_tgen_gorilla_webtunnel": "SingleTgenGorillaWebtunnelConfidentiality",
    "single_tgen_irc_obfs": "SingleTgenIrcObfsConfidentiality",
    "single_tgen_irc_webtunnel": "SingleTgenIrcWebtunnelConfidentiality",
    "single_tgen_minio": "SingleTgenMinioConfidentiality"
}

VANTAGE_MAP = {
    "SingleTgenMastodonConfidentiality": "cl[1]",
    "SingleTgenDnsConfidentiality": "cl[3]",
    "SingleTgenFtpObfsConfidentiality": "cl[2]",
    "SingleTgenFtpWebtunnelConfidentiality": "cl[5]",
    "SingleTgenGorillaObfsConfidentiality": "cl[2]",
    "SingleTgenGorillaWebtunnelConfidentiality": "cl[5]",
    "SingleTgenIrcObfsConfidentiality": "cl[2]",
    "SingleTgenIrcWebtunnelConfidentiality": "cl[5]",
    "SingleTgenMinioConfidentiality": "cl[4]"
}

def plot_ecdfs(
    samps0: list[float],
    samps1: list[float],
    title: str,
    xlabel: str,
    label0: str,
    label1: str,
    dest: Path,
) -> str:

    ecdf0 = sorted(samps0)
    ecdf1 = sorted(samps1)

    ks = ks_2samp(ecdf0, ecdf1)
    ks_loc, ks_dist = ks.statistic_location, ks.statistic

    support = np.unique(np.concatenate((ecdf0, ecdf1)))
    padding = max(float(np.ptp(support)) * .04, .01)
    grid = np.r_[support[0] - padding, support, support[-1] + padding]
    fig = Figure(figsize=(9, 5.5))
    FigureCanvasAgg(fig)  # Render in workers/headless test environments without a GUI.
    ax = fig.subplots()

    for values, label in ((ecdf0, label0), (ecdf1, label1)):
        ax.step(grid, np.searchsorted(values, grid, side='right') / len(values),
                where='post', label=f'{label} (n={len(values)})', linewidth=1.8)

    heights = [np.searchsorted(values, ks_loc, side='right') / len(values)
               for values in (ecdf0, ecdf1)]

    ax.axvline(ks_loc, color='0.4', linestyle=':', label=f'KS location = {ks_loc:.6g}')
    ax.plot([ks_loc, ks_loc], heights, color='crimson', marker='o', linewidth=2.5,
            label=f"KS gap = {ks_dist:.4g}")

    ax.set(xlabel=xlabel,
           ylabel='Empirical cumulative probability', ylim=(-.025, 1.025),
           title=title)

    ax.grid(alpha=.2)
    ax.legend(loc='best', fontsize=9)
    fig.tight_layout()

    fig.savefig(dest, dpi=160, bbox_inches='tight')

def case_list_to_dict(cases: list[dict]) -> dict:
    d = {
        f"{case["feat"]}+{case["vantage"]}+{case["window_size"]}": case
        for case in cases
    }
    return d

if __name__ == "__main__":
    smc_results_path = THIS_PATH.parent.parent / "results" / "single_tgen_experiments"
    testbed_results_path = THIS_PATH.parent.parent / "results" / "single_tgen_confidentiality_experiments_testbed"
    graph_dir = THIS_PATH.parent.parent / "results" / "single_tgen_graphs"
    graph_dir.mkdir(exist_ok=True)

    # Isolate stem of filename and remove hidden files
    map_name_and_strip_dot = lambda lst: list(filter(
        lambda x: not x.startswith("."),
        map(lambda x: x.name, lst)
    ))

    smc_exps = map_name_and_strip_dot(smc_results_path.iterdir())
    testbed_exps = map_name_and_strip_dot(testbed_results_path.iterdir())

    assert set(map(lambda x: NAME_MAP[x], smc_exps)) == set(testbed_exps)

    for exp in smc_exps:

        testbed_exp = NAME_MAP[exp]

        # Remove all client network vantage cases besides the one specified
        def filter_cl(cl, lst):
            return list(filter(lambda case: case["vantage"] == cl, lst))

        smc_cases_lst = json.loads((smc_results_path / exp / "cases.json").read_text())
        testbed_cases_lst = json.loads((testbed_results_path / testbed_exp / "analysis" / "cases.json").read_text())

        for case in testbed_cases_lst:

            # cl[0] doesn't actually exist, so these should always be zero
            if case["vantage"] in ["cl[0]"]:
                assert all(map(lambda x: x == 0, case["test_samples"]))
                assert all(map(lambda x: x == 0, case["control_samples"]))

            # This isn't really for a two-pronged experiment, so remove test_samples
            case["samples"] = case["control_samples"]
            del case["test_samples"]
            del case["control_samples"]

        # Since only a single client net is ever active, only cl[1] should be present.
        for case in smc_cases_lst:
            if case["vantage"] in ["cl[2]", "cl[3]", "cl[4]", "cl[5]"]:
                assert all(map(lambda x: x == 0, case["samples"]))

        testbed_cases_lst = filter_cl(VANTAGE_MAP[testbed_exp], testbed_cases_lst)
        smc_cases_lst = filter_cl("cl[1]", smc_cases_lst)

        # Rename the last remaining client net to "cl[1]" to match smc cases
        for case in testbed_cases_lst:
            if case["vantage"].startswith("cl["):
                case["vantage"] = "cl[1]"

        smc_cases = case_list_to_dict(smc_cases_lst)
        testbed_cases = case_list_to_dict(testbed_cases_lst)

        keys = smc_cases.keys()
        print(set(keys).difference(set(testbed_cases.keys())))
        print(set(testbed_cases.keys()).difference(set(keys)))
        assert set(keys) == set(testbed_cases.keys())

        exp_graph_dir = graph_dir / exp
        exp_graph_dir.mkdir(exist_ok=True)

        for key in keys:
            smc_case, testbed_case = smc_cases[key], testbed_cases[key]

            plot_ecdfs(
                smc_case["samples"],
                testbed_case["samples"],
                key,
                key,
                "smc",
                "testbed",
                exp_graph_dir / f"{key}.png"
            )