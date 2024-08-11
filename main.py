from rsyncwrap.main import rsyncwrap
from config import SOURCE, DESTINATION


for update in rsyncwrap(SOURCE, DESTINATION):
    print(update)
