"""Recompute paired AUC intervals from aligned, digest-pinned scorer evidence."""
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import random

from .asset_integrity import safe_path, sha256


def ranking(scores):
    groups = []
    for i in sorted(range(len(scores)),key=lambda i:scores[i]):
        if not groups or scores[groups[-1][0]] != scores[i]:
            groups.append([])
        groups[-1].append(i)
    return groups


def weighted_auc(labels, groups, weights):
    positive = sum(w*y for w,y in zip(weights,labels))
    negative = sum(weights)-positive
    if not positive or not negative:
        return None
    below = wins = 0
    for group in groups:
        pos = sum(weights[i]*labels[i] for i in group)
        neg = sum(weights[i]*(1-labels[i]) for i in group)
        wins += pos*(below+.5*neg)
        below += neg
    return wins/(positive*negative)


def percentile(values, fraction):
    values = sorted(values)
    index = (len(values)-1)*fraction
    low = int(index); high = min(len(values)-1,low+1)
    return values[low]+(values[high]-values[low])*(index-low)


def interval(labels, left, right, clusters, *, resamples=1000, seed=0):
    if (not labels or len({len(labels),len(left),len(right),len(clusters)}) != 1
            or any(y not in (0,1) for y in labels)
            or any(not math.isfinite(v) for v in left+right)
            or type(resamples) is not int or not 100 <= resamples <= 5000
            or type(seed) is not int):
        raise ValueError('invalid paired interval inputs')
    a,b = ranking(left),ranking(right)
    aa,bb = weighted_auc(labels,a,[1]*len(labels)),weighted_auc(labels,b,[1]*len(labels))
    if aa is None or bb is None:
        raise ValueError('paired AUC requires both classes')
    groups = defaultdict(list)
    for i,key in enumerate(clusters):
        groups[key].append(i)
    keys = sorted(groups)
    if len(keys)<2:
        raise ValueError('paired bootstrap requires at least two clusters')
    rng = random.Random(seed); samples=[]; discarded=0
    for _ in range(resamples):
        counts=Counter(rng.choices(keys,k=len(keys)))
        weights=[0]*len(labels)
        for key,count in counts.items():
            for i in groups[key]:
                weights[i]=count
        av,bv=weighted_auc(labels,a,weights),weighted_auc(labels,b,weights)
        if av is None or bv is None:
            discarded+=1
        else:
            samples.append(av-bv)
    if len(samples)<resamples*.9:
        raise ValueError('too many bootstrap samples lack both classes')
    low,high=percentile(samples,.025),percentile(samples,.975)
    return {'left_auc':aa,'right_auc':bb,'observed_difference':aa-bb,
            'ci95_low':low,'ci95_high':high,'resamples':resamples,'seed':seed,
            'discarded_single_class':discarded,'clusters':len(keys),
            'direction':'positive' if low>0 else 'negative' if high<0 else 'inconclusive',
            'meaning':'left minus right; an interval containing zero does not establish equivalence'}


def from_evidence(dataset, evidence_root, spec):
    dataset,evidence_root=Path(dataset),Path(evidence_root)
    quality=json.loads(safe_path(dataset,'quality.json').read_text())
    meta=json.loads(safe_path(dataset,'meta.json').read_text())
    split=spec['split']
    if split not in ('train','eval','holdout'):
        raise ValueError('invalid paired evidence split')
    path=safe_path(evidence_root,spec['file'])
    if sha256(path)!=spec['sha256']:
        raise ValueError('paired evidence digest mismatch')
    ids,target=meta['id_columns'],quality['target']
    source=safe_path(dataset,quality['splits'][split])
    source_sha=sha256(source)
    with source.open(newline='') as stream:
        rows=list(csv.DictReader(stream))
    actual={tuple(row[c] for c in ids):int(row[target]) for row in rows}
    if len(actual)!=len(rows):
        raise ValueError('duplicate accepted row ids')
    with path.open(newline='') as stream:
        reader=csv.DictReader(stream)
        fields=reader.fieldnames or []
        if len(fields)!=len(set(fields)) or any(c not in fields for c in ids+[target,spec['left'],spec['right']]):
            raise ValueError('paired evidence has missing or duplicate columns')
        evidence=list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in evidence):
            raise ValueError('ragged paired evidence')
    scores={tuple(row[c] for c in ids):row for row in evidence}
    if len(scores)!=len(evidence) or set(scores)!=set(actual):
        raise ValueError('paired evidence must cover every accepted split row exactly once')
    labels,left,right,clusters=[],[],[],[]
    for row in rows:
        key=tuple(row[c] for c in ids); score=scores[key]
        if int(score[target])!=actual[key]:
            raise ValueError('paired evidence label differs from accepted artifact')
        labels.append(actual[key]);left.append(float(score[spec['left']]))
        right.append(float(score[spec['right']]))
        # Cluster fields come from the accepted rows, never from scorer-supplied keys.
        if not spec['cluster_columns']:
            raise ValueError('declare paired bootstrap cluster columns')
        clusters.append(tuple(row[c] for c in spec['cluster_columns']))
    result=interval(labels,left,right,clusters,resamples=spec.get('resamples',1000),seed=spec.get('seed',0))
    if sha256(path)!=spec['sha256'] or sha256(source)!=source_sha:
        raise ValueError('paired input changed during measurement')
    return dict(result,left=spec['left'],right=spec['right'],split=split,
                cluster_columns=spec['cluster_columns'],evidence_sha256=spec['sha256'],
                accepted_split_sha256=source_sha)
