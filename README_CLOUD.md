# chai1号 Cloud

スマホ閲覧用の最小構成です。

Entrypoint:
`app_chai1_cloud_v31_2.py`

必要ファイル:
- app_chai1_cloud_v31_2.py
- requirements.txt
- cloud_data/latest.json

Windows側で `build_cloud_snapshot_v31_2.py` を実行して `cloud_data/latest.json` を更新し、
GitHubへ push すると Streamlit Community Cloud 側が更新されます。
