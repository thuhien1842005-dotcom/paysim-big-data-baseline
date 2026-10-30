import sys
sys.path.insert(0, 'C:\\Users\\admin\\BD\\paysim-big-data-baseline\\dashboard')
import dashboard_core
from pathlib import Path
import os
import mongomock
from bson import json_util
Path('C:\\Users\\admin\\BD\\paysim-big-data-baseline\\artifacts\\dashboard-presentation-20261029\\build\\captures\\owned-server.pid').write_text(str(os.getpid()))
saved=json_util.loads(Path('C:\\Users\\admin\\BD\\paysim-big-data-baseline\\docs\\evidence\\dashboard-ui\\snapshot.json').read_text(encoding="utf-8"))
db=mongomock.MongoClient(tz_aware=True).paysim
for name, docs in saved["collections"].items():
    if docs: db[name].insert_many(docs)
dashboard_core.get_database=lambda:db
import view_workspace as view
dashboard_core.render(view)
