"""Synthetic-data provenance manifest with byte-level and producer-source hashes."""
import hashlib
import json
from pathlib import Path
from app.config import settings


def build(output=None, *, profile='full', seed=None, producer_commit=None):
    root=Path(settings.BASE_DIR)
    files=[]
    for folder in (Path(settings.GENERATED_DIR),Path(settings.GROUND_TRUTH_DIR)):
        for f in sorted(folder.glob('*')):
            if f.is_file():
                files.append({'path':str(f.relative_to(root)) if f.is_relative_to(root) else str(f.name),
                              'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    seed_sql=Path(settings.EXPORTS_DIR)/'returnflow_seed.sql'
    if seed_sql.is_file():
        files.append({'path':'data/exports/returnflow_seed.sql','bytes':seed_sql.stat().st_size,
                      'sha256':hashlib.sha256(seed_sql.read_bytes()).hexdigest()})
    sources={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest()
             for f in sorted((root/'app/generator').glob('*.py'))}
    result={'profile':profile,'seed':seed if seed is not None else settings.RANDOM_SEED,
        'reference_date':str(settings.REFERENCE_DATE),'generator_version':settings.APP_VERSION,
        'producer_commit':producer_commit,
        'producer_commit_note':'Historical producer commit not established' if producer_commit is None else 'Explicitly supplied provenance',
        'current_generator_source_sha256':sources,
        'synthetic_data_provenance':'Deterministic Python random/Decimal generators and curated fictional masters; intentionally injected anomalies are labelled separately.',
        'external_data_usage':'No external operational dataset used by the inspected generators. Original historical execution provenance is not independently attested.',
        'generated_files':files}
    path=Path(output) if output else root/'data/source_manifest.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    build()
