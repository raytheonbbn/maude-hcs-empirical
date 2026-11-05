# Single-HCS confidentiality features from CP3 PCAPs

These results extract the same 15 network features used by the confidentiality
SMC/testbed analysis from the completed Iodine, Mastodon, Obfs, Skyhook, and
Webtunnel HCS-only runs in `maude-hcs-exp/orchestrator-results/single-hcs-24-trials`.

| Experiment | Collected trials | Valid 600-second samples | Cases / plots |
| --- | ---: | ---: | ---: |
| SingleHCSIodineConfidentiality | 24 | 24 | 90 |
| SingleHCSMastodonConfidentiality | 24 | 23 | 90 |
| SingleHCSObfsConfidentiality | 24 | 24 | 90 |
| SingleHCSSkyhookConfidentiality | 24 | 24 | 90 |
| SingleHCSWebtunnelConfidentiality | 24 | 24 | 90 |

Open [index.html](index.html) to browse all 450 plots. The complete suite
contains 120 collected trials and 119 valid 600-second samples.

## Format and interpretation

The directory layout matches the earlier confidentiality testbed exports:
each experiment has `experiment.json` and an `analysis/` directory containing
`cases.json`, `cases_sorted.json`, `provenance.json`, `index.html`, and ECDF
PNGs. The JSON case fields match the SMC-style confidentiality schema.

Each `test_samples` entry is one trial's cumulative measurement over the first
600 seconds after `capture_metadata.start_epoch`. The unsorted JSON follows
ascending trial number; provenance identifies the corresponding archives.
The window includes startup traffic and does not begin at the first IRC
message. The saved configuration is in `provenance.json` under
`test.configuration`.

These runs used `-R` (HCS only) and have **no matched control arm**.
`control_samples` is empty; `ks_distance`, `ks_location`, `p_value`, and
`passed` are null; status remains `CaseStatus.PENDING`. These are measured
feature distributions, not evidence of a confidentiality pass or failure.
No synthetic control or unrelated previous TGen run is substituted.

`provenance.json` also contains 60 diagnostic bins of 10 seconds per trial
and vantage under `test.trials[].bins`. Bins are not independent trial samples.

## Vantage points

All six available network vantages are included:

| Vantage | Network |
| --- | --- |
| `ixpN` | IXP router |
| `srvN` | `server_net` |
| `minN` | `minio_net` |
| `masN` | `mastodon_net` |
| `dnsN` | `dns_net` |
| `cl[1]` | The configuration's sole client network: `client_net_iodine`, `client_net_mastodon`, `client_net_obfs`, `client_net_sky`, or `client_net_racetunnel` |

Client indices are configuration-local. Use `vantage_networks` when comparing
with earlier suites, where the same client network can have a different
index. Absent client networks are not exported as artificial zero series.

`minN` and `masN` use the recorded service-router WAN interfaces because these
runs did not record service LAN captures. Those observations cover traffic
crossing the router, not LAN-local traffic. Other network vantages use their
recorded LAN captures; IXP uses its recorded router-network interface.
Per-trial interface selection is saved in provenance. The extractor excludes
BGP infrastructure traffic and avoids merging duplicate LAN/WAN observations.

## Exclusion and units

Mastodon trial 005 captured only **333.308 seconds**, shorter than the required
600-second window. It is excluded without zero-padding or rescaling. Its IRC
conversation also never started, as noted in the earlier performance analysis.
The other 119 captures meet the full-window requirement. Archive hashes and
the excluded-trial details are included in provenance; source manifests and
PCAPs remain unchanged.

TCP packet sizes and size standard deviations use captured frame bytes;
`tcpUpRate` and `tcpDownRate` are **bytes per second**, not bits per second.
DNS sizes use UDP payload bytes; packet/query rates are per second;
interarrival times are seconds. Ratios are dimensionless. Direction changes,
active directed flows, and new TCP connections are counts over the window.
Physical packetization, retransmissions, framing, and timing differ from SMC
abstractions.

## Reproduction

From `maude-hcs-exp`, with Python 3.12, the confidentiality requirements, and
`tshark`/`mergecap` available:

```sh
python3.12 orchestrator-results/single-hcs-24-trials/analyze_confidentiality.py iodine
python3.12 orchestrator-results/single-hcs-24-trials/analyze_confidentiality.py mastodon
python3.12 orchestrator-results/single-hcs-24-trials/analyze_confidentiality.py obfs
python3.12 orchestrator-results/single-hcs-24-trials/analyze_confidentiality.py skyhook
python3.12 orchestrator-results/single-hcs-24-trials/analyze_confidentiality.py webtunnel
```

The batch script delegates feature extraction, JSON construction, and plotting
to `orchestrator/confidentiality.py`. It validates capture duration and uses a
temporary filtered manifest for the documented exclusion. Both source-code
hashes and input-archive hashes are saved in each analysis provenance file.
Raw captures remain in the original orchestrator result directories.
