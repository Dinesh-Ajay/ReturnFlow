"""Read-only full-dataset acceptance evidence; does not repair historical rows.

Run: python -m app.validation.acceptance_audit
Output location follows RETURNFLOW_EXPORTS_DIR.
"""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import inspect, text
from app.config import settings
from app.database.session import SessionLocal
from app.models import Base
from app.services.projection_service import bulk_replay
from app.services.asset_service import AssetService
from app.analytics.metrics import AnalyticsService
from app.validation.financial import FinancialValidator
from app.validation.integrity import IntegrityValidator


def run():
    output = Path(settings.EXPORTS_DIR)
    output.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        structure = IntegrityValidator.validate_all(db)
        finance = FinancialValidator.reconcile_ledger_totals(db)
        # Labels annotate the independent comparison only, never replay or detectors.
        truth_path = Path(settings.GROUND_TRUTH_DIR) / 'ground_truth.json'
        truth = json.loads(truth_path.read_text()) if truth_path.exists() else []
        labelled = {r['asset_id'] for r in truth}
        issues = []
        counts = Counter()
        mismatch_counts = Counter()
        for row in bulk_replay(db):
            counts['assets_checked'] += 1
            row['has_injected_anomaly_label'] = row['asset_id'] in labelled
            for key in row['mismatches']:
                mismatch_counts[key] += 1
            if not row['history_complete']:
                counts['incomplete_histories'] += 1
            if row['mismatches'] or not row['history_complete']:
                issues.append(row)
                counts['assets_with_exceptions'] += 1
                if not row['has_injected_anomaly_label']:
                    counts['unlabelled_assets_with_exceptions'] += 1
            else:
                counts['fully_consistent_assets'] += 1
        items,total = AssetService.list_assets(db,page_size=structure['table_counts']['reusable_assets'])
        kpis = AnalyticsService.get_overview_kpis(db)
        overdue_list = sum(i['is_overdue'] for i in items)
        age_consistent = overdue_list == kpis['overdue_count']
        replay = {**dict(counts), 'mismatch_counts': dict(mismatch_counts),
                  'exception_details': issues,
                  'all_valid_histories_reconstructed': not counts['unlabelled_assets_with_exceptions']}
        schema = inspect(db.get_bind())
        required_tables = set(Base.metadata.tables)
        actual_tables = set(schema.get_table_names())
        missing_indexes, missing_constraints = [], []
        for name,table in Base.metadata.tables.items():
            if name not in actual_tables:
                continue
            indexes = schema.get_indexes(name)
            for index in table.indexes:
                cols = [c.name for c in index.columns]
                if not any(i['column_names'] == cols and bool(i['unique']) == bool(index.unique) for i in indexes):
                    missing_indexes.append({'table':name,'index':index.name})
            fks = schema.get_foreign_keys(name)
            for fk in table.foreign_key_constraints:
                cols = [e.parent.name for e in fk.elements]
                targets = [e.column.name for e in fk.elements]
                target_table = list(fk.elements)[0].column.table.name
                if not any(f['constrained_columns']==cols and f['referred_columns']==targets and f['referred_table']==target_table for f in fks):
                    missing_constraints.append({'table':name,'foreign_key_columns':cols})
            for c in table.constraints:
                if c.__class__.__name__ == 'UniqueConstraint':
                    cols = [x.name for x in c.columns]
                    if not any(u['column_names']==cols for u in schema.get_unique_constraints(name)) and not any(i['column_names']==cols and i['unique'] for i in indexes):
                        missing_constraints.append({'table':name,'unique_columns':cols})
        result = {'audited_at':datetime.now(timezone.utc).isoformat(),
            'database_server_version':db.execute(text('SELECT VERSION()')).scalar_one(),
            'database_foreign_keys_enabled':bool(db.execute(text('SELECT @@FOREIGN_KEY_CHECKS')).scalar_one()),
            'integrity':structure, 'financial':finance,
            'replay_summary':{k:v for k,v in replay.items() if k!='exception_details'},
            'age_consistency':{'reference_date':str(settings.REFERENCE_DATE),'list_total':total,
                'list_overdue_count':overdue_list,'analytics_overdue_count':kpis['overdue_count'],
                'consistent':age_consistent},
            'schema':{'required_tables':sorted(required_tables),'missing_tables':sorted(required_tables-actual_tables),
                'missing_indexes':missing_indexes,'missing_constraints':missing_constraints}}
    (output/'event_replay_exceptions.json').write_text(json.dumps(replay,indent=2,default=str))
    (output/'critical_acceptance_evidence.json').write_text(json.dumps(result,indent=2,default=str))
    print(json.dumps({k:v for k,v in result.items() if k not in ('integrity','financial')},indent=2,default=str))
    print('Financial:', {k:finance[k] for k in ('net_liability','portfolio_arithmetic_balanced','individual_obligations_valid','duplicate_refund_findings','over_refund_findings','is_reconciled')})
    return result


if __name__ == '__main__':
    run()
