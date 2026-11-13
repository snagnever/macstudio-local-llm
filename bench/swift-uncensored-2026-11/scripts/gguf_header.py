#!/usr/bin/env python3
"""Read GGUF headers from the Hugging Face Hub with HTTP range requests, without the weights.

usage: gguf_header.py scan --out FILE '<label>|<repo>|<revision>|<glob>' [...]
       gguf_header.py check '<label>|<repo>|<revision>|<glob>' [...]

scan writes, per label, the files, the tensor count, the general.* and split.* metadata and the tensor types of
each tensor family (the tensor name with the block number replaced by N). check prints the tensors that Splash
refuses and exits 1 if there is one: Splash loads hc_attn_inject and hc_ffn_inject only as F32, BF16 or Q8_0.
"""
import json,struct,sys,urllib.request,re,collections,fnmatch
T={0:'F32',1:'F16',2:'Q4_0',3:'Q4_1',6:'Q5_0',7:'Q5_1',8:'Q8_0',9:'Q8_1',10:'Q2_K',11:'Q3_K',12:'Q4_K',13:'Q5_K',14:'Q6_K',15:'Q8_K',16:'IQ2_XXS',17:'IQ2_XS',18:'IQ3_XXS',19:'IQ1_S',20:'IQ4_NL',21:'IQ3_S',22:'IQ2_S',23:'IQ4_XS',24:'I8',25:'I16',26:'I32',27:'I64',28:'F64',29:'IQ1_M',30:'BF16'}
class Need(Exception): pass
def parse(b):
    p=[0]
    def rd(fmt):
        n=struct.calcsize(fmt)
        if p[0]+n>len(b): raise Need()
        v=struct.unpack_from(fmt,b,p[0]); p[0]+=n; return v[0]
    def s():
        n=rd('<Q')
        if p[0]+n>len(b): raise Need()
        v=b[p[0]:p[0]+n]; p[0]+=n; return v.decode('utf-8','replace')
    F={0:'<B',1:'<b',2:'<H',3:'<h',4:'<I',5:'<i',6:'<f',7:'<B',10:'<Q',11:'<q',12:'<d'}
    def val(t,keep=True):
        if t==8: return s()
        if t==9:
            et=rd('<I'); n=rd('<Q')
            if et in F and et!=8:
                sz=struct.calcsize(F[et])*n
                if p[0]+sz>len(b): raise Need()
                p[0]+=sz; return '[%d]'%n
            for _ in range(n): val(et)
            return '[%d]'%n
        return rd(F[t])
    assert b[:4]==b'GGUF',b[:4]
    p[0]=4; ver=rd('<I'); nt=rd('<Q'); nk=rd('<Q'); kv={}
    for _ in range(nk):
        k=s(); t=rd('<I'); kv[k]=val(t)
    ts=[]
    for _ in range(nt):
        name=s(); nd=rd('<I'); dims=[rd('<Q') for _ in range(nd)]; ty=rd('<I'); off=rd('<Q'); ts.append((name,dims,ty))
    return ver,kv,ts
def header(url):
    size=8<<20; 
    while True:
        req=urllib.request.Request(url,headers={'Range':'bytes=0-%d'%(size-1)})
        b=urllib.request.urlopen(req,timeout=120).read()
        try: return parse(b)
        except Need:
            if size>(200<<20): raise
            size*=2
def scan(repo,rev,pat):
    info=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{repo}/revision/{rev}',timeout=30))
    files=sorted(s['rfilename'] for s in info['siblings'] if fnmatch.fnmatch(s['rfilename'],pat))
    fam=collections.defaultdict(collections.Counter); kvall={}; n=0
    for f in files:
        ver,kv,ts=header(f'https://huggingface.co/{repo}/resolve/{rev}/{f}')
        for k,v in kv.items(): kvall.setdefault(k,v)
        for name,dims,ty in ts:
            n+=1; fam[re.sub(r'^blk\.\d+\.','blk.N.',name)][T.get(ty,'T%d'%ty)]+=1
    return files,kvall,fam,n


FLOAT_ROW_TYPES = ("F32", "BF16", "Q8_0")
INJECT = ("hc_attn_inject.weight", "hc_ffn_inject.weight")


def check(fam):
    """One line per tensor family that Splash refuses. An empty list means the pack passes."""
    bad = []
    for name in sorted(fam):
        if name.endswith(INJECT):
            bad += [f"{name}: {ty} x{n}" for ty, n in sorted(fam[name].items()) if ty not in FLOAT_ROW_TYPES]
    return bad


def main(argv=None, scan_fn=scan):
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = argv.pop(0) if argv else ""
    out_path = None
    if mode == "scan" and argv[:1] == ["--out"]:
        out_path = argv[1]
        argv = argv[2:]
    if mode not in ("scan", "check") or not argv or (mode == "scan" and not out_path):
        print(__doc__, file=sys.stderr)
        return 64
    out, failed = {}, False
    for spec in argv:
        label, repo, rev, pat = spec.split("|")
        files, kv, fam, n = scan_fn(repo, rev, pat)
        keep = ("general.architecture", "general.name", "general.file_type", "general.quantization_version")
        out[label] = {"files": files, "n": n, "fam": {k: dict(v) for k, v in fam.items()},
                      "kv": {k: v for k, v in kv.items()
                             if k in keep or (k.startswith(("general.", "split.")) and not isinstance(v, str))}}
        if mode == "check":
            bad = check(out[label]["fam"])
            failed = failed or bool(bad) or not files
            for line in bad:
                print(f"{label}: {line}")
            if not files:
                print(f"{label}: no file matches {pat} at {rev}")
            if files and not bad:
                print(f"{label}: ok, {len(files)} files, {n} tensors")
    if out_path:
        with open(out_path, "w") as f:
            json.dump(out, f, indent=1)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
