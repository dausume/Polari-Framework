"""Critical Isle services are deployment roles, not resource budgets."""
REASONS={
 'router':'OpenWrt provides the Isle network and DNS. Keep the router on its current device.',
 'apt':'Keep at least one apt service so devices can obtain Isle packages.',
 'frontend':'Keep at least one Polari frontend so users can open Isle applications.',
 'backend':'Keep at least one Polari backend so the Isle and its applications can function.'}

def roles(item):
    # Exact compatibility identities for plans seeded before roles were recorded.
    name=(item.get('app') or item.get('title') or '').lower()
    mapping={'openwrt':['router'],'apt':['apt'],'polari':['frontend'],
             'polari (launcher)':['frontend'],'polari-api':['backend'],
             'polari-instance':['backend'],'polari-frontend':['frontend'],
             'polari-backend':['backend']}
    return list(set(mapping.get(name,[])+[r for r in item.get('protectedRoles',[]) if r in REASONS]))

def violations(plan,previous):
    present=set();issues=[]
    for i in plan.get('items',[]):
        if i.get('device') and i.get('state')!='deferred':present.update(roles(i))
    required=set()
    for i in previous.get('items',[]):
        if not i.get('device') or i.get('state')=='deferred':continue
        required.update(roles(i))
        if 'router' in roles(i) and not any('router' in roles(j) and j.get('device')==i['device'] and j.get('state')!='deferred' for j in plan.get('items',[])):
            issues.append(REASONS['router'])
    for role in sorted(required-present):
        if REASONS[role] not in issues:issues.append(REASONS[role])
    return issues
