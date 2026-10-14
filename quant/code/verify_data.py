import numpy as np, pandas as pd, sys, io
R=sys.argv[1]
raw=open(f'{R}/data/F-F_Research_Data_Factors_daily.csv').read().splitlines()
start=[i for i,l in enumerate(raw) if l.strip().startswith(',Mkt-RF') or l.replace(' ','').startswith(',Mkt-RF')][0]
rows=[l for l in raw[start+1:] if l[:8].strip().isdigit()]
ff=pd.read_csv(io.StringIO("\n".join(rows)),header=None,names=['d','mkt_rf','smb','hml','rf'])
ff.index=pd.to_datetime(ff.d.astype(str).str.strip(),format='%Y%m%d'); ff=ff.drop(columns='d')/100
spy=pd.read_csv(f'{R}/data/spy.csv',index_col=0,parse_dates=True).Close.pct_change()
j=pd.concat([spy.rename('spy'),(ff.mkt_rf+ff.rf).rename('ff_mkt')],axis=1).dropna()
print("Ken French daily file ends:",ff.index[-1].date(), " overlap days:",len(j))
print("daily corr SPY(yfinance adj) vs FF market total return: %.4f"%j.corr().iloc[0,1])
m=(1+j).resample('ME').prod()-1
print("monthly corr: %.4f ; mean annual return SPY %.2f%% vs FF mkt %.2f%%"%(m.corr().iloc[0,1],100*((1+j.spy).prod()**(252/len(j))-1),100*((1+j.ff_mkt).prod()**(252/len(j))-1)))
diff=(j.spy-j.ff_mkt); print("largest daily discrepancies:"); print(diff.abs().nlargest(3))
ff.to_csv(f'{R}/data/ff3_daily.csv')
