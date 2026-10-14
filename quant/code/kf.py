import pandas as pd, io
def read_kf(path, first_block=True):
    """Parse a Ken French CSV: returns first data block (value-weighted for industries) as decimal returns."""
    lines=open(path,encoding='latin-1').read().splitlines()
    i=next(k for k,l in enumerate(lines) if l.strip().startswith(',') and k+1<len(lines) and lines[k+1].split(',')[0].strip().isdigit())
    hdr=[h.strip() for h in lines[i].split(',')]; rows=[]
    for l in lines[i+1:]:
        p=l.split(',')
        if not p[0].strip().isdigit(): break
        rows.append(p)
    df=pd.DataFrame(rows,columns=['date']+hdr[1:]); d=df.date.str.strip()
    df.index=pd.to_datetime(d,format='%Y%m%d') if len(d.iloc[0])==8 else pd.to_datetime(d,format='%Y%m')+pd.offsets.MonthEnd(0)
    df=df.drop(columns='date').apply(pd.to_numeric,errors='coerce')
    df=df.where(df>-99)/100
    return df
