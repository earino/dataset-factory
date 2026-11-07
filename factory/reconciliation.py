"""Repeat completed worker bookkeeping without a model or lifecycle mutation.

New results and any mismatch still go to the bounded follow-up session. This
does not qualify datasets, advance candidates, approve releases or launch jobs.
"""
import hashlib
import json
from pathlib import Path
import subprocess

from . import worker
from .cloud import Cloud
from .common import FactoryError, identifier, locked, utcnow, write_json

VERSION = '1.0.0'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular(root, relative):
    path = Path(root) / relative
    for parent in (path, *path.parents):
        if parent.is_symlink(): raise FactoryError('Bookkeeping path is a symlink')
        if parent == Path(root): break
    return path


def committed_record(root, job_id):
    name = 'jobs/' + identifier(job_id) + '.json'; path = regular(root, name)
    if not path.is_file() or path.stat().st_size >= worker.REPORT_LIMIT:
        raise FactoryError('A bounded committed job ledger is required')
    payload = path.read_bytes()
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
        old = subprocess.check_output(['git', 'show', commit + ':' + name], cwd=root, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        raise FactoryError('Job outcome is not recorded in the current committed ledger') from exc
    if old != payload: raise FactoryError('Job ledger has uncommitted outcome changes')
    return json.loads(payload), sha(payload), commit


def terminal(record, job_id, config):
    report = record.get('result', {})
    if (record.get('job', {}).get('id') != job_id or record.get('project') != config['project']
            or record.get('status') != 'deleted' or not record.get('collected_at')
            or not record.get('deleted_at') or not record.get('server_id')):
        raise FactoryError('Only previously collected, deleted and committed jobs are mechanical close-outs')
    if report.get('job_id') != job_id or report.get('status') not in ('succeeded', 'failed'):
        raise FactoryError('Recorded terminal result is missing or inconsistent')
    code = report.get('exit_code')
    if type(code) is not int or (report['status'] == 'succeeded') != (code == 0):
        raise FactoryError('Recorded terminal status and exit code disagree')
    return report


def provider_absent(cloud, record):
    job_id = record['job']['id']; project = record['project']; server_id = record['server_id']
    if cloud.server(server_id) is not None:
        raise FactoryError('Recorded worker still exists at the provider')
    if any(s.get('labels', {}).get('job') == job_id for s in cloud.list_resources('servers', project)):
        raise FactoryError('A worker with this job label still exists')
    # Check all tenant IPs, including an unassigned recorded address whose labels
    # changed. A recycled address assigned to a different server is not this job.
    page = 1; count = 0
    while page:
        if page > 20: raise FactoryError('Provider IP inventory exceeds bounded verification')
        response = cloud.request('GET', f'primary_ips?per_page=50&page={page}')
        for ip in response['primary_ips']:
            count += 1
            labels = ip.get('labels', {})
            if ((labels.get('factory') == project and labels.get('job') == job_id)
                    or (ip.get('ip') == record.get('ipv4') and ip.get('assignee_id') in (None, server_id))):
                raise FactoryError('A primary IP for this job remains; cleanup is incomplete')
        following = response.get('meta', {}).get('pagination', {}).get('next_page')
        if following is not None and (type(following) is not int or following <= page):
            raise FactoryError('Invalid provider IP pagination')
        page = following
    return {'server_id_absent': server_id, 'job_label_servers_absent': True,
            'job_primary_ips_absent': True, 'tenant_ip_entries_checked': count}


def bookkeep(root, job_id, config, *, cloud=None, api=None):
    root = Path(root); identifier(job_id)
    try:
        regular(root, '.factory')
        with locked(root):
            record, identity, commit = committed_record(root, job_id)
            report = terminal(record, job_id, config)
            local = regular(root, '.factory/' + job_id + '/result.json')
            if local.is_file() and (local.stat().st_size >= worker.REPORT_LIMIT or json.loads(local.read_text()) != report):
                raise FactoryError('Local collected result differs from the committed ledger')
            staging = worker.verify_preserved_report(record, report, api or worker.github(config))
            provider = provider_absent(cloud or Cloud(), record)
            if committed_record(root, job_id)[1] != identity:
                raise FactoryError('Job ledger changed during verification')
            implementation = {name: sha(Path(__file__).with_name(name).read_bytes())
                              for name in ('reconciliation.py', 'worker.py', 'cloud.py')}
            binding = sha(json.dumps({'ledger': identity, 'implementation': implementation}, sort_keys=True).encode())
            folder = regular(root, '.factory/' + job_id); folder.mkdir(parents=True, exist_ok=True)
            receipt = regular(root, '.factory/' + job_id + '/reconciliation-' + binding + '.json')
            value = {'version': VERSION, 'job': job_id, 'ledger_sha256': identity, 'source_commit': commit,
                     'implementation': implementation, 'checked_at': utcnow().isoformat(),
                     'staging': staging, 'provider': provider,
                     'scope': 'Previously recorded worker outcome verified; no dataset or release approval'}
            if receipt.exists():
                prior = json.loads(receipt.read_text())
                if any(prior.get(k) != value[k] for k in ('version', 'job', 'ledger_sha256', 'implementation', 'staging')):
                    raise FactoryError('Existing bookkeeping receipt is inconsistent')
            else:
                write_json(receipt, value)
            marker = regular(root, '.factory/' + job_id + '/handled')
            if not marker.exists():
                write_json(marker, {'by': 'deterministic-worker-reconciler', 'receipt': receipt.name,
                                    'sha256': sha(receipt.read_bytes())})
            return {'handled': True, 'job': job_id, 'ledger_sha256': identity,
                    'receipt': receipt.relative_to(root).as_posix(), 'live_verified': True}
    except (FactoryError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return {'handled': False, 'job': job_id, 'reason': str(exc)[:400], 'needs_model': True}
