import web, datetime

web.config.debug_sql = False 
db_debug_mode = True

if(db_debug_mode):
    db = web.database(dbn="sqlite", db="/tmp/test.db")
else:
    db = web.database(dbn="sqlite", db=":memory:")

def init_db():
    db._db_cursor().execute("""
CREATE TABLE IF NOT EXISTS `task`  (
  `idtask` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
  `tittle` varchar(85) NOT NULL,
  `status` int(11) DEFAULT NULL,
  `srcname` varchar(45) DEFAULT NULL,
  `resname` varchar(45) DEFAULT NULL
)
""")    

def get_tasks():
    return db.select('task', order='idtask DESC')

def get_task(id):
    try:
        return db.select('task', where='idtask=$id', vars=locals())[0]
    except IndexError:
        return None

def get_task_content(id):
    try:
        task = get_task(id)
        f = open(task.resname, 'r') 
        read_data = f.read()        
        f.close()
        return read_data
    except:
        return 'Error conversion'

def get_task_to_process():
    try:
        return db.select('task', where='status = 0', vars=locals())[0]
    except IndexError:
        return None
        
def new_task(title, status, src_file):
    return db.insert('task', tittle=title, status=status, srcname=src_file)
    
    
def del_task(id):
    db.delete('task', where="idtask=$id", vars=locals())

def update_task(id, status, resname=''):
    db.update('task', where="idtask=$id", vars=locals(),
        status=status, resname=resname)
        
def is_ready(id):
    try:
        return db.select('task',what='count(*) as ready', where='idtask=$id and status =10', vars=locals())[0]
    except IndexError:
        return None