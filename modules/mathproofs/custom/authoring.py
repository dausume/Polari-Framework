"""
@module mathproofs.custom.authoring

THE DOORS A PERSON WRITES A CLAIM THROUGH (plan §I.7 pf-3) — never a raw row insert:

  preview(manager, term)              the term validated, its LaTeX DERIVED (one derivation, here — the editor's live
                                      preview renders what the backend derives, it never authors LaTeX), the tier that
                                      would speak to it, its statement_hash
  author(manager, fields)             a MathClaim written from a row's page: validated (the errors name the path), the
                                      name unique, then checked at once through its cheapest tier — except lean, which
                                      a person asks for by name (plan §I.9)
  propose_from_discovery(manager, …)  a discovery result's door: the candidate mapping's validity on THIS selection,
                                      as a durable, re-checkable row — MathClaim `subset(scope:<claim>, validity:<m>)`
                                      with the selection's ranges as the claim's scope, and a ProofObligation under the
                                      rule name `proposed-from-discovery` (a person's, not a seeded InferenceRule); with
                                      `via` = the mapping the person arrived through, the chain pair the rules would
                                      demand (domains + dims) is proposed too. The interval tier decides at once; a
                                      refutation names the dim; the row goes stale the moment the mapping's validity
                                      moves.
"""
import datetime
import json

from mathproofs.custom import checkers, terms
from mathproofs.custom.rows import by_name, _rows

KINDS = ('identity', 'inequality', 'domain-inclusion', 'composition', 'conservation', 'symmetry', 'commutation', 'bound', 'well-typed')


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def preview(manager, term):
    errs = terms.validate(term) if term not in (None, '', {}) else ['$: an empty term']
    out = {'valid': not errs, 'errors': errs, 'latex': terms.to_latex(term) if not errs else '', 'statement_hash': terms.statement_hash(term) if not errs else '',
           'tier': checkers.auto_tier(term) if not errs else None, 'canonical': terms.canonical(term) if not errs else ''}
    if not errs and out['tier'] == 'lean':
        out['note'] = 'the general statement: only a committed theorem proves it — ask ?tier=lean once the claim exists; nothing runs at boot'
    return out


def author(manager, fields, make=None, save=True):
    """fields: name, kind, about (list of "<Class>:<name>"), statement (the term), description, scope (dict), assumptions (list),
    budget_s, tier (optional: a non-lean tier to run now; lean is never run here). Returns {'ok', 'claim', 'check'} or {'ok': False, 'error', 'errors'}."""
    from mathproofs.mathproofs_basis import MathClaim
    name = str(fields.get('name') or '').strip()
    if not name:
        return {'ok': False, 'error': 'a claim needs a name'}
    if by_name(manager, 'MathClaim', name) is not None:
        return {'ok': False, 'error': 'a MathClaim named %r already exists — claims are re-checked, not re-written' % name, 'status': 409}
    kind = str(fields.get('kind') or 'identity')
    if kind not in KINDS:
        return {'ok': False, 'error': 'kind must be one of %s' % ', '.join(KINDS)}
    term = fields.get('statement')
    if isinstance(term, str):
        try:
            term = json.loads(term)
        except Exception as exc:
            return {'ok': False, 'error': 'statement is not JSON: %s' % exc}
    errs = terms.validate(term) if term not in (None, '', {}) else ['$: an empty term']
    if errs:
        return {'ok': False, 'error': 'the statement is not a well-formed term', 'errors': errs}
    about = fields.get('about') or []
    if isinstance(about, str):
        about = [a.strip() for a in about.split(',') if a.strip()]
    missing = [a for a in about if ':' in a and by_name(manager, a.partition(':')[0], a.partition(':')[2]) is None]
    if missing:
        return {'ok': False, 'error': 'the claim speaks of rows that do not exist: %s' % ', '.join(missing)}
    tier = fields.get('tier') or None
    if tier and tier not in ('numeric', 'interval', 'sympy', 'z3'):
        return {'ok': False, 'error': 'tier to run now must be numeric | interval | sympy | z3 (lean is asked for by name once the claim exists)'}
    scope = fields.get('scope') or {}
    make = make or (lambda cls, **f: cls(manager=manager, **f))
    claim = make(MathClaim, name=name, description=str(fields.get('description') or ''), kind=kind, about_refs_json=json.dumps(about), statement_json=json.dumps(term),
                 statement_latex=terms.to_latex(term), assumptions_json=json.dumps(fields.get('assumptions') or []), scope_json=json.dumps(scope), proof_status='conjectured', checker='',
                 certificate_ref='', counterexample_json='{}', evidence_level='none', statement_hash=terms.statement_hash(term), budget_s=float(fields.get('budget_s') or 25.0),
                 provenance='authored by a person (%s)%s' % (_now(), (' from ' + str(fields['from'])) if fields.get('from') else ''), notes=str(fields.get('notes') or ''))
    db = getattr(manager, 'db', None)
    if save and db is not None and hasattr(db, 'saveInstanceInDB'):
        db.saveInstanceInDB(claim)
    result = None
    auto = checkers.auto_tier(term)
    if tier or auto != 'lean':
        result = checkers.check(manager, claim, tier=tier, make=make, save=save)
    else:
        result = {'verdict': None, 'tier': 'lean', 'note': 'the general statement: not run here (plan §I.9) — POST /claims/%s/check?tier=lean' % name}
    return {'ok': True, 'claim': name, 'status': str(claim.proof_status), 'check': result}


def propose_from_discovery(manager, mapping, selection, via='', proposed_by='', make=None, save=True):
    """The door on a discovery result. Returns {'ok', 'proposed': [{obligation, claim, status, verdict, counterexample}], …}."""
    from mathproofs.mathproofs_basis import MathClaim, ProofObligation
    m = by_name(manager, 'TensorMapping', mapping)
    if m is None:
        return {'ok': False, 'error': 'no TensorMapping %r' % mapping, 'status': 404}
    sel = by_name(manager, 'TensorSelection', selection)
    if sel is None:
        return {'ok': False, 'error': 'no TensorSelection %r (POST /api/tensortree/select creates one)' % selection, 'status': 404}
    m1 = by_name(manager, 'TensorMapping', via) if via else None
    if via and m1 is None:
        return {'ok': False, 'error': 'no TensorMapping %r (via)' % via, 'status': 404}
    node = by_name(manager, 'TensorNode', str(getattr(sel, 'node', '')))
    tree = str(getattr(node, 'tree', '')) if node is not None else ''
    try:
        ranges = json.loads(getattr(sel, 'ranges_json', '{}') or '{}')
    except Exception:
        ranges = {}
    make = make or (lambda cls, **f: cls(manager=manager, **f))
    db = getattr(manager, 'db', None)
    stamp = _now()
    who = ('proposed by %s' % proposed_by) if proposed_by else 'proposed by a person'

    def upsert(cls, cls_name, fields):
        row = by_name(manager, cls_name, fields['name'])
        if row is None:
            row = make(cls, **fields)
        else:
            for k, v in fields.items():
                if k not in ('proof_status', 'checker', 'certificate_ref', 'counterexample_json', 'evidence_level'):
                    setattr(row, k, v)
        if save and db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(row)
        return row

    wanted = [('valid-on-selection', 'domain-inclusion', {'subset': ['scope:{self}', 'validity:%s' % mapping]}, ['TensorMapping:%s' % mapping, 'TensorSelection:%s' % selection],
               {'selection': selection, 'mapping': mapping}, ranges, 'the candidate is valid on the whole selection: the selection\'s ranges lie inside the mapping\'s validity domain')]
    if m1 is not None:
        wanted += [('chain-domain-inclusion', 'domain-inclusion', {'subset': ['validity:%s' % mapping, 'validity:%s' % via]}, ['TensorMapping:%s' % via, 'TensorMapping:%s' % mapping],
                    {'chain': [via, mapping], 'selection': selection}, {}, 'the link arrived through composes: the second link\'s validity lies inside the first\'s'),
                   ('dims-compose', 'well-typed', {'dims_subset': ['%s.source_dims' % mapping, '%s.target_dims' % via]}, ['TensorMapping:%s' % via, 'TensorMapping:%s' % mapping],
                    {'chain': [via, mapping], 'selection': selection}, {}, 'what the second link consumes is what the first produced')]
    out = []
    for what, kind, term, refs, structure, scope, why in wanted:
        cname = 'ob:proposed:%s:%s%s' % (selection, mapping, (':via-' + via) if (via and what != 'valid-on-selection') else '')
        if what != 'valid-on-selection':
            cname += ':' + what
        term = json.loads(json.dumps(term).replace('{self}', cname))
        claim = upsert(MathClaim, 'MathClaim', {'name': cname, 'description': '%s — %s' % (why, who), 'kind': kind, 'about_refs_json': json.dumps(refs), 'statement_json': json.dumps(term),
                                                 'statement_latex': terms.to_latex(term), 'assumptions_json': '[]', 'scope_json': json.dumps(scope), 'statement_hash': terms.statement_hash(term), 'budget_s': 25.0,
                                                 'provenance': 'proposed from a discovery result (%s)' % stamp, 'notes': '', 'proof_status': 'conjectured', 'checker': '', 'certificate_ref': '', 'counterexample_json': '{}', 'evidence_level': 'none'})
        r = checkers.check(manager, claim, make=make, save=save)
        ob = upsert(ProofObligation, 'ProofObligation', {'name': cname, 'description': why, 'tree': tree, 'rule': 'proposed-from-discovery', 'structure_json': json.dumps(structure),
                                                          'about_refs_json': json.dumps(refs), 'discharged_by': cname, 'status': checkers.status_of(manager, claim), 'generated_at': stamp, 'notes': who})
        out.append({'obligation': cname, 'what': what, 'claim': cname, 'status': str(ob.status), 'verdict': r['verdict'], 'counterexample': r.get('counterexample'), 'latex': str(claim.statement_latex)})
    return {'ok': True, 'mapping': mapping, 'selection': selection, 'via': via, 'tree': tree, 'proposed': out,
            'note': 'a proposed obligation is a durable row: it goes stale when the mapping\'s validity moves and is re-checked on the next generation; a refutation names the dim'}
