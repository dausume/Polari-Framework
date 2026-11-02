"""Local-Isle observations. No benchmarks, cross-user pooling or declared-floor edits."""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from datetime import datetime,timezone

class UsageStore:
    def __init__(self,path=None):
        self.path=Path(path) if path else Path(os.environ['DATABASE_PATH']).parent/'isle-app-usage.json'
    def read(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {'series':{}}
    def ingest(self,device,fact):
        if fact.get('status')!='observed':return
        stamp=fact.get('observed_at','');at=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        age=(datetime.now(timezone.utc)-at).total_seconds()
        if not -30<=age<=300:return
        raw=fact.get('value','')
        if not isinstance(raw,str) or len(raw)>131072:return
        samples=json.loads(raw).get('appUsage',[])
        if not isinstance(samples,list) or len(samples)>64:return
        # Sum replicas/containers of an app version on one device before averaging.
        groups={}
        for s in samples:
            if not isinstance(s,dict):continue
            if any(not isinstance(s.get(k),str) or not 0<len(s[k])<=160 for k in ('app','version')):continue
            key=(s['app'],s['version']);values=groups.setdefault(key,{})
            for metric in ('ramMiB','cpus'):
                v=s.get(metric)
                if type(v) in (float,int) and math.isfinite(v) and 0<=v<=1e8:values[metric]=values.get(metric,0)+v
        if not groups:return
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);doc=self.read();series=doc['series']
            for (app,version),values in groups.items():
                key=hashlib.sha256(json.dumps([device,app,version]).encode()).hexdigest()
                row=series.get(key,dict(device=device,app=app,version=version,firstAt=stamp,lastAt='',metrics={}))
                if row['lastAt'] and at<=datetime.fromisoformat(row['lastAt'].replace('Z','+00:00')):continue
                for metric,v in values.items():
                    m=row['metrics'].setdefault(metric,dict(count=0,mean=0,peak=0))
                    m['count']+=1;m['mean']+=(v-m['mean'])/m['count'];m['peak']=max(m['peak'],v)
                row['lastAt']=stamp;series[key]=row
            doc['series']=dict(sorted(series.items(),key=lambda kv:kv[1]['lastAt'])[-512:])
            tmp=None
            try:
                with tempfile.NamedTemporaryFile(mode='w',dir=self.path.parent,delete=False) as f:
                    tmp=f.name;json.dump(doc,f,allow_nan=False);f.flush();os.fsync(f.fileno())
                os.replace(tmp,self.path)
            finally:
                if tmp and os.path.exists(tmp):os.unlink(tmp)
    def for_app(self,app):
        return sorted([v for v in self.read()['series'].values() if v['app']==app],key=lambda r:r['lastAt'],reverse=True)
