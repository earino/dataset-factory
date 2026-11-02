#!/usr/bin/env python3
"""Fill the fts-baseline bundle from fts-appeal-003's collected result (one-shot).

Repo-relative; run from the dataset-factory root. Candidate-scoped session mechanics for the
runner-contract baseline job, kept beside the bundle it fills.

Reads .factory/fts-appeal-003/result.json + the staging release manifest, verifies every
digest, then:
  1. downloads 003's qualification report -> baseline/qualification.json
  2. downloads 003's references report -> .factory/fts-appeal-003/reports/references.json
  3. fills baseline/job.json fetch block (5 extract assets: ids/sizes/sha256)
  4. writes baseline/expected_artifact.json
  5. patches the references comment in baseline/run.sh with 003's measured figures
Fails loudly on any mismatch. Run only AFTER `worker collect fts-appeal-003` reports succeeded.
"""
import hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # candidates/<id>/baseline/ -> repo root
tok = Path('/opt/data/.secrets/github-staging.token').read_text().strip()  # coordinator credential file, never in the bundle
BL = ROOT / 'candidates/ocha-fts-appeal-funding-trajectory/baseline'

def api(url, binary=False):
    cmd = ['curl', '-sL', '-H', f'Authorization: Bearer {tok}']
    cmd += ['-H', 'Accept: application/octet-stream'] if binary else []
    raw = subprocess.run(cmd + [url], capture_output=True).stdout
    return raw

result = json.loads((ROOT / '.factory/fts-appeal-003/result.json').read_text())
assert result['status'] == 'succeeded' and result['uploaded'] is True, result.get('status')
release = int(result['release_id'])

assets_api = json.loads(api(
    f'https://api.github.com/repos/earino/dataset-factory-staging/releases/{release}/assets?per_page=100'))
manifest_asset = [a['id'] for a in assets_api if a['name'] == 'manifest.json']
assert len(manifest_asset) == 1, 'manifest.json asset not found'
manifest = json.loads(api(
    'https://api.github.com/repos/earino/dataset-factory-staging/releases/assets/'
    f'{manifest_asset[0]}', binary=True))
by_file = {a['file']: a for a in manifest['assets']}

def fetch_verified(logical):
    """Download the manifest entry for `logical`, verifying sha256; tolerate byte-identical twins."""
    entry = by_file[logical]
    candidates = [a['id'] for a in assets_api if a['size'] == entry['size']]
    assert candidates, f'no release asset matches size for {logical}'
    for asset_id in candidates:
        raw = api(f'https://api.github.com/repos/earino/dataset-factory-staging/releases/assets/{asset_id}',
                  binary=True)
        if hashlib.sha256(raw).hexdigest() == entry['sha256']:
            return raw, asset_id
    raise AssertionError(f'no release asset verifies the manifest digest for {logical}')

# 1. qualification report -> baseline/qualification.json
qraw, q_id = fetch_verified('output/qualification-ocha-fts-appeal-funding-trajectory.json')
(BL / 'qualification.json').write_bytes(qraw)
gate = json.loads(qraw)
assert gate.get('ok') is True and gate.get('failed_checks') == [], 'gate not clean'
artifact_digest = gate['artifact']['artifact_version']['digest']

# 2. references -> .factory/fts-appeal-003/reports/references.json
rraw, _ = fetch_verified('output/references-ocha-fts-appeal-funding-trajectory.json')
(ROOT / '.factory/fts-appeal-003/reports').mkdir(parents=True, exist_ok=True)
(ROOT / '.factory/fts-appeal-003/reports/references.json').write_bytes(rraw)
refs = json.loads(rraw)
assert refs['references']['persistence_last_coverage']['eval_auc'] is not None

# 3. fetch block for the five extract files
FIVE = ['output/extract/meta.json', 'output/extract/public/train.csv',
        'output/extract/public/eval.csv', 'output/extract/private/holdout.csv',
        'output/extract/quality.json']
fetch_assets = []
for logical in FIVE:
    entry = by_file[logical]
    _, asset_id = fetch_verified(logical)
    fetch_assets.append({'asset_id': asset_id,
                         'dest': 'extract/' + logical.split('output/extract/')[1],
                         'size': entry['size'], 'sha256': entry['sha256']})
assert len({a['asset_id'] for a in fetch_assets}) == 5, 'extract assets not five distinct ids'

job = json.loads((BL / 'job.json').read_text())
job['fetch'] = {'repo': 'earino/dataset-factory-staging', 'release': release, 'assets': fetch_assets}
job['what'] = (
    "Runner-contract baseline on the accepted ocha-fts-appeal-funding-trajectory artifact "
    f"{artifact_digest[:16]}... (gate {gate['gate_version']}, failed_checks empty, exact-byte --accept "
    f"ACCEPTED in job fts-appeal-003), fetched from private staging release {release} rather than "
    "rebuilt: re-accept the five fetched files against the gate's own collected report, materialize "
    "the runner workdir (public train+eval only; the private holdout is fetched for --accept over the "
    "full artifact but never copied into a workdir), then run the benchmark's own train.py and "
    "validate.sh unmodified and record both eval AUCs. Contract only, no agent loop, no holdout score. "
    "Construction-time references measured on the same eval rows (job fts-appeal-003, "
    f"post-acceptance): persistence_last_coverage {refs['references']['persistence_last_coverage']['eval_auc']:.5f} "
    f"(the headroom reference), prior_mean_rate {refs['references']['prior_mean_rate']['eval_auc']:.5f}, "
    f"ask_size_rate {refs['references']['ask_size_rate']['eval_auc']:.5f}, country_hist_rate "
    f"{refs['references']['country_hist_rate']['eval_auc']:.5f}, plan_type_rate "
    f"{refs['references']['plan_type_rate']['eval_auc']:.5f}, majority-class accuracy "
    f"{refs['references']['majority_class']['accuracy_this_split']:.5f}."
)
(BL / 'job.json').write_text(json.dumps(job, indent=2) + '\n')

# 4. expected_artifact.json
expected = {
    'job': 'fts-appeal-003',
    'staging_release': release,
    'gate_version': gate['gate_version'],
    'artifact_version': artifact_digest,
    'files': {logical.split('output/extract/')[1]:
              {'bytes': by_file[logical]['size'], 'sha256': by_file[logical]['sha256']}
              for logical in FIVE},
    'verification': (
        f"the five artifact digests are the worker-written staging manifest entries for release {release} "
        f"(tag job-fts-appeal-003), read back from the release manifest and re-verified on download; "
        f"job fts-appeal-003's gate {gate['gate_version']} report (bundled as baseline/qualification.json, "
        f"sha256 {hashlib.sha256(qraw).hexdigest()}, staging asset {q_id}) accepted exactly these bytes on "
        f"the worker (artifact {artifact_digest}). The baseline job re-fetches the same five assets with "
        "every sha256 verified on arrival and re-accepts them against that report before any score "
        "exists. The extract stays in staging; the CSVs are never held in the factory repository.")
}
(BL / 'expected_artifact.json').write_text(json.dumps(expected, indent=2) + '\n')

# 5. patch run.sh references comment
runsh = (BL / 'run.sh').read_text()
lines = runsh.splitlines()
target = [i for i, l in enumerate(lines) if 'Construction-time references measured on the same eval rows' in l]
assert len(target) == 1, f'references comment lines: {target}'
new_block = [
    "# Construction-time references measured on the same eval rows (job fts-appeal-003, run",
    f"# post-acceptance): persistence_last_coverage {refs['references']['persistence_last_coverage']['eval_auc']:.5f} "
    "(the headroom reference the candidate",
    f"# record names first), prior_mean_rate {refs['references']['prior_mean_rate']['eval_auc']:.5f}, "
    f"ask_size_rate {refs['references']['ask_size_rate']['eval_auc']:.5f},",
    f"# country_hist_rate {refs['references']['country_hist_rate']['eval_auc']:.5f}, plan_type_rate "
    f"{refs['references']['plan_type_rate']['eval_auc']:.5f}, majority-class accuracy",
    f"# {refs['references']['majority_class']['accuracy_this_split']:.5f}. The comparison against those "
    "references is made after this",
    "# job returns, never inside it.",
]
# replace the two comment lines starting at target
end = target[0] + 1
while end < len(lines) and lines[end].startswith('#'):
    end += 1
lines[target[0]:end] = new_block
(BL / 'run.sh').write_text('\n'.join(lines) + '\n')

print('gate:', gate['gate_version'], 'ok:', gate['ok'], 'failed:', gate['failed_checks'])
print('artifact:', artifact_digest)
print('release:', release)
print('persistence AUC:', refs['references']['persistence_last_coverage']['eval_auc'])
print('eval rows:', refs['rows'])
print('baseline fill-in complete')
