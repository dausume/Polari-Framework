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
        for key,limit in [('id',80),('device',80),('title',160),('app',100),('notes',2000),('volume',200)]:
            v=row.get(key,'')
            if not isinstance(v,str) or len(v)>limit:raise ValueError('Invalid '+key)
            clean[key]=v.strip()
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+',clean['id']) or clean['id'] in seen:raise ValueError('Unique item IDs required')
        seen.add(clean['id'])
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*',clean['device']) or not clean['title']:raise ValueError('Device and title are required')
        for key,choices in [('kind',('catalog','polari','task')),('state',('planned','existing','deferred')),('access',('frequent','occasional','archive'))]:
            if row.get(key) not in choices:raise ValueError('Invalid '+key)
            clean[key]=row[key]
        if clean['kind']=='catalog' and not re.fullmatch(r'[a-zA-Z0-9_.-]+',clean['app']):raise ValueError('Catalog app name is required')
        for key in ('ramMiB','diskMiB','cpus'):
            v=row.get(key)
            if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v<0 or v>1e9):raise ValueError('Costs must be nonnegative numbers or blank')
            clean[key]=v
        result.append(clean)
    return {'title':title.strip(),'items':result}

class PlanStore:
    def __init__(self,path=None):
        if path is None:
            database=os.environ.get('DATABASE_PATH')
            if not database:raise RuntimeError('Persistent DATABASE_PATH is required for shared planning')
            path=Path(database).parent/'isle-placement-plan.json'
        self.path=Path(path)
    def read(self):
        if not self.path.exists():return {'title':'Isle deployment plan','revision':0,'updatedAt':None,'items':[]}
        return json.loads(self.path.read_text())
    def save(self,plan):
        clean=validate(plan)
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            previous=self.read()
            if previous['revision']!=plan['revision']:raise Conflict('Plan changed on another device. Reload before saving; your draft has not been written.')
            clean.update(revision=previous['revision']+1,updatedAt=datetime.now(timezone.utc).isoformat())
            tmp=None
            try:
                with tempfile.NamedTemporaryFile(mode='w',dir=self.path.parent,delete=False) as f:
                    tmp=f.name;json.dump(clean,f,allow_nan=False);f.flush();os.fsync(f.fileno())
                os.replace(tmp,self.path)
            finally:
                if tmp and os.path.exists(tmp):os.unlink(tmp)
            return clean
