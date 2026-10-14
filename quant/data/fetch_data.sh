#!/usr/bin/env bash
# Re-download every raw dataset used in the research. Run from the quant/ folder:
#   bash data/fetch_data.sh && python3 -I code/<script>.py .
# Scripts take one argument: the folder that CONTAINS data/ (i.e. quant/).
set -e; cd "$(dirname "$0")"
KF=https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp
for f in F-F_Research_Data_Factors_daily_CSV F-F_Research_Data_5_Factors_2x3_CSV F-F_Momentum_Factor_CSV \
         F-F_Momentum_Factor_daily_CSV 30_Industry_Portfolios_CSV 30_Industry_Portfolios_daily_CSV \
         Portfolios_Formed_on_BETA_CSV Portfolios_Formed_on_VAR_CSV; do
  curl -sL -o $f.zip "$KF/$f.zip" && unzip -o -q $f.zip && rm $f.zip; done
for s in VIXCLS T10Y2Y BAMLH0A0HYM2 DGS3MO DGS1 DGS2 DGS5 DGS10 DGS30; do
  curl -sL -o $s.csv "https://fred.stlouisfed.org/graph/fredgraph.csv?id=$s"; done
curl -sL -A "Mozilla/5.0" -o aqr_tsmom.xlsx "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx"
# Yahoo prices (SPY etc.) are downloaded inside the scripts via yfinance. Polymarket: python3 -I code/p2_fetch.py .
# NOTE: several scripts expect a parsed daily FF3 file ff3_daily.csv (columns mkt_rf,smb,hml,rf as decimals) and spy.csv;
# code/a1_sweeps.py writes spy.csv and code/verify_data.py writes ff3_daily.csv — run those first.
echo done
