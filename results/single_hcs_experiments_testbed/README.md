# CP3 single-HCS testbed results

This batch contains 24 collected HCS-only trials each for Iodine, Mastodon,
and Obfs (72 trial archives total), collected from `single-hcs-24-trials` in
`maude-hcs-exp/orchestrator-results`. Skyhook and Webtunnel are not included
in this export because their batches were still running when it was prepared.

Iodine and Obfs each provide 24 analyzed samples per metric. Mastodon
provides 23: trial 005 was marked successful by collection, but its IRC
conversation never started. `alice_2` remained at Connecting and `alice_1`
waited for all clients to become ready. The analyzer rejected that trial
because neither client log contained recognizable conversation events; no
synthetic or zero-valued replacement sample is included. The original
manifest is preserved unchanged, and the exclusion is recorded in provenance.

Each trial uses two HCS clients, `-R`, a 600-second conversation, a maximum
startup delay of 120 seconds, and a 600-second analysis window. There are no
TGens or paired control trials.

Each channel directory follows the existing `isolated_channel_hcs_only`
layout: `analysis.json`, its referenced experiment YAML, and
`user_models/static/` profiles. The analysis JSON uses the existing
`yaml_filename`, `run_time`, `no_tgens`, `no_hcs`, and `results` schema;
each metric has a query, sorted samples, mean, and population standard
deviation. Independent and cumulative queries both cover [0, 600).
Goodput is in bits per second, latency is in seconds, and availability and
integrity are dimensionless. Undefined latency samples are omitted by the
orchestrator analyzer rather than replaced with zeros.

Additional reproducibility files are included in each channel directory:

- `experiment.json`: the original preparation specification and input hashes.
- `source.yaml`: the unchanged original single-HCS input.
- `manifest.json`: the original 24-trial collection manifest (collection
  success does not guarantee a valid IRC conversation; see the exclusion above).
- `provenance.json`: source locations, analyzer code hashes, file hashes,
  archive hashes, and the mapping from original profile paths to the exported
  `user_models/static/` paths.

The raw ZIPs, PCAPs, and trial logs remain in the source result directory and
are not included in this Git export. Existing older result batches are
unchanged. These are performance results; no paired confidentiality KS plots
are generated for this HCS-only batch.

To reproduce the analysis, run the following from `maude-hcs-exp` with
Python 3.12 (the default local Python 3.10 rejects the nanosecond Docker
server timestamps):

```sh
python3.12 -m orchestrator analyze orchestrator-results/single-hcs-24-trials/SingleHCSIodine
python3.12 -m orchestrator analyze orchestrator-results/single-hcs-24-trials/SingleHCSMastodon
python3.12 -m orchestrator analyze orchestrator-results/single-hcs-24-trials/SingleHCSObfs
```

The configuration differs from the older `isolated_channel_hcs_only` batch;
use the saved YAMLs and specifications when comparing results.
