from zoneinfo import ZoneInfo
from datetime import datetime, timezone

now = 'Thu, 12 Aug 2021 00:00:00 GMT'

dtobj = datetime.strptime(now, '%a, %d %b %Y %H:%M:%S %Z')
print(dtobj.date())