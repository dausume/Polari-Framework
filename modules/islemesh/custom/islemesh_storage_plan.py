"""Storage-migration plan support (stm-2/2b): validation, digest, display-only planned actions.
Pure stdlib functions. Nothing here executes, stores or decides: status is derived from rows the doors stored.
Mirrors isle-cli/scripts/storage_contract.py (same whitelist, payload keys, canonical JSON).
See docs/STORAGE-MIGRATION-CONTRACT.md section 1.
"""
import hashlib
import json
import re

DATASET = re.compile(r'[a-z0-9][a-z0-9-]{0,63}\Z')
DOMAIN = re.compile(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){1,7}isle\Z')
HEX64 = re.compile(r'[a-f0-9]{64}\Z')
ITEM_ID = re.compile(r'[a-zA-Z0-9_.-]{1,80}\Z')
PLAN_ID = re.compile(r'[a-f0-9]{32}\Z')
APP_NAME = re.compile(r'[a-z0-9][a-z0-9-]{0,63}\Z')
ITEM_STATES = ('planned', 'existing', 'deferred')
HEADROOM_PERCENT = 5
NOT_EXECUTABLE = 'not executable: storage migration executor not released'
VERBS = ('authorize', 'migrate', 'cutover')
# Phase A: the source host is the origin that publication, sync and rollback need, so a storage
# source is never removable. Phase B (a replacement origin exists) flips this to False; the receipt,
# hosting and last-provider checks then decide alone.
PHASE_A_SOURCE_RETAINED = True
PHASE_A_REASON = 'Phase A: the source still serves publication and sync; source removal returns in Phase B'


def is_storage_item(item):
    """Return True when item is a plan item of kind storage."""
    return isinstance(item, dict) and item.get('kind') == 'storage'


def _int(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('%s must be an integer of at least %d.' % (name, minimum))
    return value


def _text(value, name, limit, spaces=False):
    if not isinstance(value, str) or not value or len(value) > limit or '\x00' in value:
        raise ValueError('%s must be a non-empty string of at most %d characters.' % (name, limit))
    if not spaces and re.search(r'\s', value):
        raise ValueError('%s must not contain whitespace.' % name)
    return value


def _mapping(value, name):
    if not isinstance(value, dict):
        raise ValueError('%s must be an object.' % name)
    return value


def required_capacity(total_bytes):
    """Return ceil(total_bytes * 1.05) using integer arithmetic only."""
    return (total_bytes * (100 + HEADROOM_PERCENT) + 99) // 100


def _relative_path(value):
    _text(value, 'storage.target.relativePath', 200, spaces=True)
    if value.startswith('/'):
        raise ValueError('storage.target.relativePath must be relative and must not start with a slash.')
    if '..' in value.split('/'):
        raise ValueError('storage.target.relativePath must not contain parent traversal (..).')
    return value


def _hex_or_none(value, name):
    if value is not None and not (isinstance(value, str) and HEX64.match(value)):
        raise ValueError('%s must be 64 lowercase hex characters or null.' % name)
    return value


def _source(raw):
    raw = _mapping(raw, 'storage.source')
    taken = raw.get('snapshotTakenAt')
    if taken is not None:
        _text(taken, 'storage.source.snapshotTakenAt', 64)
    out = {'device': _text(raw.get('device'), 'storage.source.device', 100),
           'path': _text(raw.get('path'), 'storage.source.path', 200, spaces=True),
           'snapshotSha256': _hex_or_none(raw.get('snapshotSha256'), 'storage.source.snapshotSha256'),
           'snapshotTakenAt': taken,
           'totalBytes': _int(raw.get('totalBytes'), 'storage.source.totalBytes'),
           'entries': _int(raw.get('entries'), 'storage.source.entries')}
    # Optional keys appear only when set, so an absent key hashes like the CLI's older whitelist.
    content = _hex_or_none(raw.get('contentSha256'), 'storage.source.contentSha256')
    if content is not None:
        out['contentSha256'] = content
    apps = raw.get('apps', [])
    if not isinstance(apps, list) or len(apps) > 8 or len(set(apps)) != len(apps) \
            or any(not isinstance(a, str) or not APP_NAME.match(a) for a in apps):
        raise ValueError('storage.source.apps must be a list of at most 8 distinct names matching [a-z0-9][a-z0-9-]{0,63}.')
    if apps:
        out['apps'] = list(apps)
    return out


def _target(raw):
    raw = _mapping(raw, 'storage.target')
    mount = _text(raw.get('mountpoint'), 'storage.target.mountpoint', 200, spaces=True)
    if not mount.startswith('/') or '..' in mount.split('/'):
        raise ValueError('storage.target.mountpoint must be absolute without parent traversal.')
    return {'device': _text(raw.get('device'), 'storage.target.device', 100),
            'filesystemUuid': _text(raw.get('filesystemUuid'), 'storage.target.filesystemUuid', 200),
            'relativePath': _relative_path(raw.get('relativePath')),
            'capacityBytes': _int(raw.get('capacityBytes'), 'storage.target.capacityBytes'),
            'mountpoint': mount}


def validate_storage_block(block):
    """Return a new, whitelisted copy of a storage block or raise ValueError."""
    block = _mapping(block, 'storage')
    if type(block.get('schemaVersion')) is not int or block.get('schemaVersion') != 1:
        raise ValueError('storage.schemaVersion must be 1.')
    dataset = block.get('dataset')
    if not isinstance(dataset, str) or not DATASET.match(dataset):
        raise ValueError('storage.dataset must match [a-z0-9][a-z0-9-]{0,63}.')
    domain = block.get('domain')
    if not isinstance(domain, str) or len(domain) > 253 or not DOMAIN.match(domain):
        raise ValueError('storage.domain must be a DNS hostname of 2-8 labels ending in .isle (at most 253 characters).')
    out = {'schemaVersion': 1, 'dataset': dataset, 'domain': domain,
           'source': _source(block.get('source')), 'target': _target(block.get('target'))}
    if out['target']['capacityBytes'] < required_capacity(out['source']['totalBytes']):
        raise ValueError('storage.target.capacityBytes must be at least storage.source.totalBytes plus 5 percent.')
    if block.get('sourceRemoval') != 'dependent':
        raise ValueError('storage.sourceRemoval must be "dependent" in version 1.')
    out['sourceRemoval'] = 'dependent'
    return out


def validate_hosting_release(release):
    """Return a rebuilt {name, version, manifestSha256} or raise ValueError."""
    release = _mapping(release, 'hostingRelease')
    sha = release.get('manifestSha256')
    if not isinstance(sha, str) or not HEX64.match(sha):
        raise ValueError('hostingRelease.manifestSha256 must be 64 lowercase hex characters.')
    return {'name': _text(release.get('name'), 'hostingRelease.name', 100),
            'version': _text(release.get('version'), 'hostingRelease.version', 100),
            'manifestSha256': sha}


def validate_storage_item(item):
    """Validate a plan item of kind storage; return its validated storage block."""
    item = _mapping(item, 'item')
    if item.get('kind') != 'storage':
        raise ValueError('Plan item kind must be "storage".')
    app = _text(item.get('app'), 'item.app', 100)
    if item.get('state') not in ITEM_STATES:
        raise ValueError('Plan item state must be one of %s.' % ', '.join(ITEM_STATES))
    block = validate_storage_block(item.get('storage'))
    if item.get('device') != block['target']['device']:
        raise ValueError('Plan item device must equal storage.target.device.')
    if item.get('originDevice') != block['source']['device']:
        raise ValueError('Plan item originDevice must equal storage.source.device.')
    if validate_hosting_release(item.get('hostingRelease'))['name'] != app:
        raise ValueError('hostingRelease.name must equal the item app.')
    return block


def storage_digest_payload(plan_id, revision, item):
    """Return the execution tuple as a dict (the exact object that is hashed)."""
    item = _mapping(item, 'item')
    block = validate_storage_item(item)
    if not isinstance(plan_id, str) or not PLAN_ID.match(plan_id):
        raise ValueError('Plan id must be 32 lowercase hex characters.')
    _int(revision, 'Revision')
    if not isinstance(item.get('id'), str) or not ITEM_ID.match(item['id']):
        raise ValueError('Item id must match [a-zA-Z0-9_.-]{1,80}.')
    return {'planId': plan_id, 'revision': revision, 'itemId': item['id'],
            'device': item['device'], 'originDevice': item['originDevice'],
            'app': item['app'], 'state': item['state'], 'storage': block,
            'hostingRelease': validate_hosting_release(item.get('hostingRelease'))}


def storage_digest(plan_id, revision, item):
    """Return sha256 of the canonical JSON execution tuple."""
    payload = storage_digest_payload(plan_id, revision, item)
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def suppresses_removal(items, app, device):
    """True when a storage item in items explains why app on device is leaving the plan:
    its originDevice is device and app is its own app or listed in storage.source.apps."""
    for item in items:
        if not is_storage_item(item) or item.get('originDevice') != device:
            continue
        listed = ((item.get('storage') or {}).get('source') or {}).get('apps') or []
        if app == item.get('app') or app in listed:
            return True
    return False


def _present(plan, app, device):
    return any((i.get('app') or i.get('title', '').lower()) == app and i.get('device') == device
               and i.get('state') != 'deferred' for i in plan.get('items', []))


def source_removal_allowed(previous_plan, new_plan, rows=None):
    """Return reasons (empty = allowed) why dropping a storage source from new_plan is refused.
    previous_plan is the stored ACTIVE plan (with id and revision); rows is any object offering
    _storage_views() and _storage_receipt_documents() (None means no evidence). Decided from
    stored receipts and the placement view alone; protectedRoles is never read."""
    previous_plan, new_plan = previous_plan or {}, new_plan or {}
    previous_items = previous_plan.get('items', [])
    storage = [i for i in previous_items if is_storage_item(i)]
    storage += [i for i in new_plan.get('items', []) if is_storage_item(i) and i not in storage
                and not any(is_storage_item(p) and p.get('id') == i.get('id') for p in storage)]
    if not storage:
        return []
    views, receipts = _views(rows), _receipts(rows)
    reasons = []
    for old in previous_items:
        if is_storage_item(old) or old.get('state') != 'existing' or not old.get('device'):
            continue
        app, device = old.get('app') or old.get('title', '').lower(), old['device']
        if _present(new_plan, app, device):
            continue
        for item in storage:
            if not suppresses_removal([item], app, device):
                continue
            label = '%s on %s' % (app, device)
            try:
                block = validate_storage_item(item)
                digest = storage_digest(previous_plan.get('id'), previous_plan.get('revision'), item) \
                    if any(p is item for p in previous_items) else None
            except ValueError:
                block, digest = None, None
            if digest is None:
                reasons.append('%s is the source of a storage move with no stored plan revision to check receipts against' % label)
            else:
                action_id = 'isle.storage.migrate:%s@%s:%s' % (block['dataset'], block['target']['device'], digest)
                if not any(migrate_qualifies(r, action_id, digest) for r in receipts):
                    reasons.append('%s is the source of storage %s: no verified migrate receipt is stored for this plan digest'
                                   % (label, block['dataset']))
                view = views.get(block['dataset']) if isinstance(views.get(block['dataset']), dict) else None
                view_digest = None if view is None else (view.get('planDigest') or (view.get('plan') or {}).get('digest'))
                if view is None or view.get('state') != 'hosting' or view_digest != digest:
                    reasons.append('%s: the placement of storage %s is not hosting for this plan digest' % (label, block['dataset']))
            if PHASE_A_SOURCE_RETAINED:
                reasons.append(PHASE_A_REASON)
            if not any((j.get('app') or j.get('title', '').lower()) == app and j.get('device') != device
                       and j.get('device') and j.get('state') != 'deferred' and not is_storage_item(j)
                       for j in new_plan.get('items', [])):
                reasons.append('%s is the last provider of %s; keep one other provider' % (label, app))
    return list(dict.fromkeys(reasons))


def _argv_text(argv):
    return 'sudo isle ' + ' '.join(argv)


def migrate_qualifies(receipt, action_id, digest):
    """True when a stored receipt (the parsed section 2.6 document) proves a finished migrate for this
    action: ok, contentVerified, stagedDeploy, readinessVerified and the digest of the stored plan."""
    return (isinstance(receipt, dict) and receipt.get('kind') == 'isle.storage.migrate'
            and receipt.get('actionId') == action_id and (receipt.get('plan') or {}).get('digest') == digest
            and all(receipt.get(key) is True for key in ('ok', 'contentVerified', 'stagedDeploy', 'readinessVerified')))


def _action(verb, device, block, plan_id, revision, item, digest, depends, view):
    state = (view or {}).get('state')
    return {'kind': 'isle.storage.' + verb,
            'id': 'isle.storage.%s:%s@%s:%s' % (verb, block['dataset'], device, digest),
            'device': device, 'dataset': block['dataset'], 'planId': plan_id, 'revision': revision,
            'itemId': item['id'], 'digest': digest, 'dependsOn': depends,
            'status': 'blocked', 'statusWords': NOT_EXECUTABLE, 'execute': None,
            'operatorCommand': None, 'undo': None, 'placementState': state, 'chain': []}


def _set(action, status, words, command=None):
    action['status'], action['statusWords'], action['operatorCommand'] = status, words, command


def planned_actions(plan, core_device, placement_view=None, receipts=None):
    """Return display-only actions (authorize, migrate, cutover) for each executable-shaped storage item.
    placement_view maps dataset -> view dict (state, generation, planDigest or plan.digest); receipts is a list
    of parsed section 2.6 receipts as stored (unverified). Status is derived from those only (never from the plan
    revision): planned when every dependsOn is satisfied and nothing is recorded, blocked otherwise, succeeded when
    the stored evidence shows it done. `execute` is always null; operatorCommand is the section 2.1 argv text for a
    planned action only. Items that cannot be digested are skipped."""
    out = []
    views, receipts = placement_view or {}, receipts or []
    for item in plan.get('items', []):
        if not is_storage_item(item) or item.get('state') != 'planned':
            continue
        try:
            block = validate_storage_item(item)
            if block['source']['snapshotSha256'] is None:
                continue
            digest = storage_digest(plan.get('id'), plan.get('revision'), item)
        except ValueError:
            continue
        view = views.get(block['dataset']) if isinstance(views.get(block['dataset']), dict) else None
        view_digest = None if view is None else (view.get('planDigest') or (view.get('plan') or {}).get('digest'))
        view_matches = view is not None and view_digest == digest
        state = (view or {}).get('state')
        auth = _action('authorize', core_device, block, plan['id'], plan['revision'], item, digest, [], view)
        mig = _action('migrate', block['target']['device'], block, plan['id'], plan['revision'], item, digest, [auth['id']], view)
        cut = _action('cutover', core_device, block, plan['id'], plan['revision'], item, digest, [mig['id']], view)
        authorized = view_matches
        if authorized:
            _set(auth, 'succeeded', 'placement view shows %s for this plan digest' % state)
        else:
            _set(auth, 'planned', 'waiting for the core to authorize this plan digest' if view is None
                 else 'the placement view is for a different plan digest; authorize this revision',
                 _argv_text(['storage', 'authorize', '--dataset', block['dataset'], '--plan', plan['id'],
                             '--revision', str(plan['revision']), '--item', item['id'], '--digest', digest]))
        done = next((r for r in receipts if migrate_qualifies(r, mig['id'], digest)), None)
        if done is not None:
            _set(mig, 'succeeded', 'receipt stored (poster not verified by the backend)')
        elif authorized:
            _set(mig, 'planned', 'authorized; ready to run on the target',
                 _argv_text(['storage', 'migrate', '--dataset', block['dataset'], '--plan', plan['id'],
                             '--revision', str(plan['revision']), '--item', item['id'], '--digest', digest]))
        else:
            _set(mig, 'blocked', 'blocked until the authorize action is satisfied')
        generation = (view or {}).get('generation')
        if view_matches and state in ('cutover', 'hosting'):
            _set(cut, 'succeeded', 'placement view shows %s' % state)
        elif done is not None and view_matches and state == 'migrated':
            command = None
            if type(generation) is int and generation >= 1:
                command = _argv_text(['storage', 'cutover', '--dataset', block['dataset'], '--generation', str(generation)])
            _set(cut, 'planned', 'migrated; ready for the core to cut over', command)
        else:
            _set(cut, 'blocked', 'blocked until the migrate receipt is stored and the placement is migrated')
        out.extend([auth, mig, cut])
    return out


def _core_device(owner):
    devices = owner._capability_devices()
    return next((d.get('name', '') for d in devices if d.get('agent_mode') == 'core'), '')


def _views(owner):
    """dataset -> placement view dict from the owner's stored rows (empty when it has none)."""
    reader = getattr(owner, '_storage_views', None)
    return reader() if callable(reader) else {}


def _receipts(owner):
    reader = getattr(owner, '_storage_receipt_documents', None)
    return reader() if callable(reader) else []


def attach_planned_actions(media, owner):
    """Add plannedActions to a GET placement-plan response dict. Read-only; never raises, never alters the plan."""
    try:
        plan = media.get('plan') or {}
        if not any(is_storage_item(i) for i in plan.get('items', [])):
            media['plannedActions'] = []
            return
        core = _core_device(owner)
        if not core:
            media['plannedActions'] = []
            media['plannedActionsError'] = 'The core device is not known, so no planned actions are shown.'
            return
        media['plannedActions'] = planned_actions(plan, core, _views(owner), _receipts(owner))
    except Exception:
        media['plannedActions'] = []
        media['plannedActionsError'] = 'Planned actions are unavailable.'
