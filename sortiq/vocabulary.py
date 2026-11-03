"""SORTIQ SVE: local subject vocabularies and optional Wikipedia title discovery."""
import json, re, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from .taxonomy import CATEGORY_TREE

def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[_./\\-]+',' ',unicodedata.normalize('NFKC',s).casefold())).strip()

def valid_category(name):
    parts=name.split(' / ')
    if not parts or len(parts)>6 or name=='Needs Review' or name.startswith('/') or '/' in name.replace(' / ', ''): raise ValueError('Invalid category')
    for p in parts:
        if not p or p.strip()!=p or p in ('.','..') or p[-1] in '. ' or len(p)>70 or any(c in p for c in '<>:"\\|?*') or p.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}: raise ValueError('Unsafe Windows folder name')
    return name

def has(text, word):
    w=norm(word)
    return bool(w and re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)',text))

class Vocabulary:
    def __init__(self, subjects=None):
        self.subjects=subjects or []
        for s in self.subjects: self._register(s['category'])
    def _register(self,name):
        valid_category(name)
        if name not in CATEGORY_TREE: CATEGORY_TREE.insert(-1,name)
    @classmethod
    def load(cls, path):
        p=Path(path)
        return cls(json.loads(p.read_text(encoding='utf8')).get('subjects',[])) if p.exists() else cls()
    def save(self,path):
        p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
        tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps({'subjects':self.subjects},ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(p)
    def set_subject(self,name,terms):
        self._register(name)
        seeds=list(dict.fromkeys(t.strip() for t in re.split('[,;\n]',terms) if 2<len(t.strip())<=85))[:80]
        if not seeds: raise ValueError('Enter some example keywords')
        current=next((s for s in self.subjects if s['category']==name),None)
        if current: current['seeds']=seeds
        else: self.subjects.append({'category':name,'seeds':seeds,'discovered':[]})
    def classify(self,filename,folder,body):
        if not self.subjects:return None
        n,f,b=map(norm,(filename,folder,body[:40000])); results=[]
        for s in self.subjects:
            score=0; proof=[]; seedcount=0
            seednorm={norm(t) for t in s['seeds']}
            for term in list(dict.fromkeys(s['seeds']+[x['term'] for x in s.get('discovered',[])])):
                seed=norm(term) in seednorm; weight=6 if seed else 1.6
                where=[]
                for section,text,mult in [('content',b,1),('filename',n,.75),('folder',f,.14)]:
                    if has(text,term): where.append(section);score+=weight*mult
                if where:
                    proof.append((term,','.join(where),round(weight,1)))
                    if seed and ('content' in where or 'filename' in where):seedcount+=1
            results.append((score,s['category'],proof,seedcount))
        results.sort(key=lambda x:x[0],reverse=True)
        best,cat,proof,seeds=results[0];runner=results[1][0] if len(results)>1 else 0
        if best==0:return None
        ready=best>=10 and seeds>=1 and (best-runner)/best>=.23
        confidence=round(min(.95,.45+.025*best+.19*(best-runner)/best),2)
        category=cat if ready else 'Needs Review'
        details=f'SVE subject: {cat}\nOutcome: {"Ready" if ready else "Needs Review"}\nScore: {best:.1f}; runner-up: {runner:.1f}\nHeuristic, not a calibrated probability.\n\nMatched terms:\n'+'\n'.join(f'{t} ({w})' for t,w,_ in proof[:20])
        return category,confidence,('Ready' if ready else 'Review'),f'SVE: {cat}',details
    def discover(self,name,limit=100):
        """Opt-in public Wikipedia Search. Only subject names and supplied terms sent."""
        s=next((s for s in self.subjects if s['category']==name),None)
        if not s:raise ValueError('Unknown subject')
        limit=max(1,min(int(limit),1000)); known={norm(x) for x in s['seeds']+[d['term'] for d in s['discovered']]}
        added=0
        for query in [name.split(' / ')[-1]]+s['seeds'][:10]:
            if len(s['discovered'])>=limit:break
            params=urllib.parse.urlencode({'action':'query','list':'search','srsearch':query,'srlimit':30,'format':'json'})
            req=urllib.request.Request('https://en.wikipedia.org/w/api.php?'+params,headers={'User-Agent':'SORTIQ-SVE/1.3 (user-initiated vocabulary search; contact: https://www.mediawiki.org/wiki/User-Agent_policy)'})
            with urllib.request.urlopen(req,timeout=12) as r:data=json.load(r)
            for entry in data.get('query',{}).get('search',[]):
                term=entry.get('title','').strip()
                if not 3<=len(term)<=85 or norm(term) in known or not any(has(norm(term+' '+re.sub('<[^>]*>',' ',entry.get('snippet',''))),anchor) for anchor in [query]+s['seeds'] if len(anchor)>=5):continue
                s['discovered'].append({'term':term,'source':'Wikipedia','pageid':entry.get('pageid')});known.add(norm(term));added+=1
                if len(s['discovered'])>=limit:break
        return added
