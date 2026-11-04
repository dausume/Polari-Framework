"""Shared advisory placement intent. Never executes installs or reserves resources.
Stored beside DATABASE_PATH on the persistent backend volume; revisions prevent lost edits.
"""
import fcntl
import json
import math
import os
from pathlib import Path
import re
import tempfile
import uuid
import copy
from datetime import datetime, timezone

class Conflict(ValueError): pass

def validate(plan):
    if not isinstance(plan,dict) or type(plan.get('revision')) is not int or plan['revision']<0:raise ValueError('A nonnegative revision is required')
    title=plan.get('title','')
    if not isinstance(title,str) or not 1<=len(title.strip())<=120:raise ValueError('Plan title must be 1–120 characters')
    items=plan.get('items')
    if not isinstance(items,list) or len(items)>128:raise ValueError('Plan must contain at most128 items')
    result=[];seen=set()
    for row in items:
        if not isinstance(row,dict):raise ValueError('Invalid plan item')
        clean={}
        for key,limit in [('id',80),('device',80),('title',160),('app',100),('notes',2000),('volume',200),('originDevice',80)]:
            v=row.get(key,'')
            if not isinstance(v,str) or len(v)>limit:raise ValueError('Invalid '+key)
            clean[key]=v.strip()
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+',clean['id']) or clean['id'] in seen:raise ValueError('Unique item IDs required')
        seen.add(clean['id'])
        if (clean['device'] and not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*',clean['device'])) or not clean['title']:raise ValueError('Device and title are required')
        for key,choices in [('kind',('catalog','polari','task')),('state',('planned','existing','deferred')),('access',('frequent','occasional','archive'))]:
            if row.get(key) not in choices:raise ValueError('Invalid '+key)
            clean[key]=row[key]
        if clean['kind']=='catalog' and not re.fullmatch(r'[a-zA-Z0-9_.-]+',clean['app']):raise ValueError('Catalog app name is required')
        for key in ('ramMiB','diskMiB','cpus'):
            v=row.get(key)
            if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v<0 or v>1e9):raise ValueError('Costs must be nonnegative numbers or blank')
            clean[key]=v
        origin = clean['originDevice']
        if origin and not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*',origin):raise ValueError('Invalid original device')
        scale = row.get('multiplier',1)
        if type(scale) not in (int,float) or not math.isfinite(scale) or not 1<=scale<=2:raise ValueError('Resource multiplier must be between1 and2')
        if type(row.get('requirementsBased',False)) is not bool:raise ValueError('Invalid requirement basis')
        clean.update(multiplier=scale,requirementsBased=row.get('requirementsBased',False))
        protected=row.get('protectedRoles',[])
        if not isinstance(protected,list) or any(r not in ('router','apt','frontend','backend') for r in protected):raise ValueError('Invalid service roles')
        clean['protectedRoles']=protected
        result.append(clean)
    removed=plan.get('removals',[])
    if not isinstance(removed,list) or len(removed)>128:raise ValueError('Too many removals')
    clean_removed=[]
    for row in removed:
        if not isinstance(row,dict):raise ValueError('Invalid removal')
        clean_row={k:row.get(k,'') for k in ('app','device','title')}
        if any(not isinstance(v,str) or len(v)>160 for v in clean_row.values()):raise ValueError('Invalid removal fields')
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+',clean_row['app']) or not re.fullmatch(r'[a-zA-Z0-9_.-]+',clean_row['device']):raise ValueError('Removal needs app and device')
        if any(i['app']==clean_row['app'] and i['device']==clean_row['device'] and i['state']!='deferred' for i in result):continue
        clean_removed.append(clean_row)
    return {'title':title.strip(),'items':result,'removals':clean_removed,'baselineInitialized':plan.get('baselineInitialized') is True}

class PlanStore:
    def __init__(self,path=None):
        if path is None:
            database=os.environ.get('DATABASE_PATH')
            if not database:raise RuntimeError('Persistent DATABASE_PATH is required for shared planning')
            path=Path(database).parent/'isle-placement-plan.json'
        self.path=Path(path)
    def _document(self):
        if not self.path.exists():
            initial={'id':'default','title':'Isle deployment plan','revision':0,'updatedAt':None,'items':[],'removals':[]}
            return {'schemaVersion':2,'activeId':'default','generation':0,'plans':{'default':[initial]}}
        doc=json.loads(self.path.read_text())
        if doc.get('schemaVersion')==2:return doc
        doc['id']='default';doc.setdefault('removals',[])
        return {'schemaVersion':2,'activeId':'default','generation':0,'plans':{'default':[doc]}}
    def read(self,plan_id=None,revision=None):
        doc=self._document();plan_id=plan_id or doc['activeId']
        versions=doc['plans'].get(plan_id)
        if not versions:raise ValueError('Saved plan does not exist')
        value=versions[-1] if revision is None else next((v for v in versions if v['revision']==revision),None)
        if value is None:raise ValueError('Saved revision is no longer retained')
        return dict(value,active=plan_id==doc['activeId'],activeId=doc['activeId'],generation=doc['generation'])
    def library(self):
        doc=self._document()
        return {'activeId':doc['activeId'],'generation':doc['generation'],'plans':[
            dict(id=k,title=v[-1]['title'],revision=v[-1]['revision'],updatedAt=v[-1]['updatedAt'],active=k==doc['activeId'],
                 versions=[dict(revision=i['revision'],updatedAt=i['updatedAt']) for i in reversed(v)]) for k,v in doc['plans'].items()]}
    def _write(self,doc):
        tmp=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',dir=self.path.parent,delete=False) as f:
                tmp=f.name;json.dump(doc,f,allow_nan=False);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            if tmp and os.path.exists(tmp):os.unlink(tmp)
    def save(self,plan,as_new=False):
        clean=validate(plan)
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);doc=self._document()
            from islemesh.custom.islemesh_plan_safety import violations
            issues=violations(clean,doc['plans'][doc['activeId']][-1])
            if issues:raise ValueError(' '.join(issues))
            previous_active=doc['plans'][doc['activeId']][-1]
            for old in previous_active.get('items',[]):
                app=old.get('app') or old.get('title','').lower();device=old.get('originDevice') or (old.get('device') if old.get('state')=='existing' else '')
                if device and re.fullmatch(r'[a-zA-Z0-9_.-]+',app) and not any((i.get('app') or i.get('title','').lower())==app and i.get('device')==device and i.get('state')!='deferred' for i in clean['items']):
                    removal=dict(app=app,device=device,title=old.get('title',app))
                    if not any(r['app']==app and r['device']==device for r in clean['removals']):clean['removals'].append(removal)
            plan_id=plan.get('id') or doc['activeId']
            if as_new:
                if len(doc['plans'])>=20:raise ValueError('Plan library is full (20 plans).')
                plan_id=uuid.uuid4().hex;versions=[]
            else:
                versions=doc['plans'].get(plan_id)
                if not versions:raise ValueError('Saved plan does not exist')
                if versions[-1]['revision']!=plan['revision']:raise Conflict('Plan changed on another device. Reload before saving; your draft has not been written.')
            clean.update(id=plan_id,revision=(versions[-1]['revision'] if versions else 0)+1,updatedAt=datetime.now(timezone.utc).isoformat())
            doc['plans'][plan_id]=(versions+[clean])[-8:];doc['generation']+=1;self._write(doc)
            return dict(clean,active=plan_id==doc['activeId'],activeId=doc['activeId'],generation=doc['generation'])
    def activate(self,plan_id,generation,revision):
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);doc=self._document()
            if doc['generation']!=generation:raise Conflict('Plan library changed. Reload before switching the active plan.')
            if plan_id not in doc['plans']:raise ValueError('Saved plan does not exist')
            if doc['plans'][plan_id][-1]['revision']!=revision:raise Conflict('Only the latest saved revision can be activated. Save an old revision as a new plan first.')
            from islemesh.custom.islemesh_plan_safety import violations
            issues=violations(doc['plans'][plan_id][-1],doc['plans'][doc['activeId']][-1])
            if issues:raise ValueError(' '.join(issues))
            doc['activeId']=plan_id;doc['generation']+=1;self._write(doc)
        return self.read()
