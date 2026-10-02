"""
@module firmwarefaults.custom.sink

WHERE A RUN'S ROWS GO: into a live server's object tree (the API's POST /api/firmwarefaults/run — upsert by name, saved
through manager.db) or, from the CLI with no server, into a local JSON record per run under
$POLARI_FAULTS_HOME (default ~/.cache/polari-faults/runs/<run>.json) that `pol faults show` reads back. The rows are the
same dicts either way (ScenarioRun, its ScenarioTraceCycle rows, the MathClaim + ProofRun, the Technique's measured cost,
the fault row's measured rate).
"""
import json
import os
import re


def home():
    return os.path.expanduser(os.environ.get('POLARI_FAULTS_HOME', '~/.cache/polari-faults'))


def safe_name(name):
    return re.sub(r'[^A-Za-z0-9_.@+-]+', '_', name)[:180]


def _class_of(cls_name):
    from firmwarefaults import firmwarefaults_basis as B
    if hasattr(B, cls_name):
        return getattr(B, cls_name)
    if cls_name in ('MathClaim', 'ProofRun'):
        from mathproofs.mathproofs_basis import MathClaim, ProofRun
        return {'MathClaim': MathClaim, 'ProofRun': ProofRun}[cls_name]
    raise KeyError(cls_name)


class ManagerSink:
    """Upsert rows by name into a live manager; fields a class does not take are dropped (never a crash)."""

    def __init__(self, manager, save=True):
        self.manager = manager
        self.save = save
        self.written = []

    def get(self, cls_name, name):
        for r in ((self.manager.objectTables or {}).get(cls_name, {}) or {}).values():
            if getattr(r, 'name', None) == name:
                return r
        return None

    def rows(self, cls_name):
        return list(((self.manager.objectTables or {}).get(cls_name, {}) or {}).values())

    def upsert(self, cls_name, fields):
        import inspect
        cls = _class_of(cls_name)
        allowed = set(inspect.signature(cls.__init__).parameters) - {'self', 'manager'}
        f = {k: v for k, v in fields.items() if k in allowed}
        row = self.get(cls_name, f['name'])
        if row is None:
            row = cls(manager=self.manager, **f)
        else:
            for k, v in f.items():
                setattr(row, k, v)
        db = getattr(self.manager, 'db', None)
        if self.save and db is not None and hasattr(db, 'saveInstanceInDB'):
            try:
                db.saveInstanceInDB(row)
            except Exception:  # noqa: BLE001 — a save failure is logged by the DB layer; the row stays in the tree
                pass
        self.written.append((cls_name, f['name']))
        return row


class LocalSink:
    """The CLI's sink: rows collected per class; flush(run_name) writes one JSON record."""

    def __init__(self):
        self.tables = {}

    def get(self, cls_name, name):
        return self.tables.get(cls_name, {}).get(name)

    def rows(self, cls_name):
        return list(self.tables.get(cls_name, {}).values())

    def upsert(self, cls_name, fields):
        self.tables.setdefault(cls_name, {})[fields['name']] = {k: v for k, v in fields.items() if not k.startswith('_')}
        return fields

    def flush(self, run_name):
        d = os.path.join(home(), 'runs')
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, safe_name(run_name) + '.json')
        json.dump({k: list(v.values()) for k, v in self.tables.items()}, open(p, 'w'), indent=1, default=str)
        return p


def local_runs():
    d = os.path.join(home(), 'runs')
    out = []
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.json'):
                try:
                    rec = json.load(open(os.path.join(d, fn)))
                except Exception:  # noqa: BLE001
                    continue
                for r in rec.get('ScenarioRun', []):
                    out.append((r, rec, os.path.join(d, fn)))
    return sorted(out, key=lambda t: t[0].get('ran_at', ''), reverse=True)


def local_records():
    """sc-2: every local record (newest file first) → [(record, path)] — campaigns, formal and static checks read back."""
    d = os.path.join(home(), 'runs')
    out = []
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d), key=lambda f: os.path.getmtime(os.path.join(d, f)), reverse=True):
            if fn.endswith('.json'):
                try:
                    out.append((json.load(open(os.path.join(d, fn))), os.path.join(d, fn)))
                except Exception:  # noqa: BLE001
                    continue
    return out
