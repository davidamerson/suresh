import glob, sqlite3, re, os
files=glob.glob('localdata/**/*',recursive=True)
dbs=[f for f in files if os.path.isfile(f) and (f.endswith(('.db','.sqlite','.sqlite3')) or open(f,'rb').read(20).startswith(b'SQLite format 3'))]
print('LOCAL_DATABASE_COUNT',len(dbs))
local=re.compile(r'(?i)Sirasa|Derana|Swarnavahini|Rupavahini|Hiru TV|Shakthi|Siyatha|ITN|Vasantham|Supreme TV|TV1|Nethra')
url_re=re.compile(r'https?://[^\s\x22\x27<>]{10,260}',re.I)
for path in dbs:
    print('DB_FILE',os.path.basename(path),'BYTES',os.path.getsize(path))
    try: con=sqlite3.connect('file:'+os.path.abspath(path)+'?mode=ro',uri=True)
    except Exception as e: print('DB_OPEN_ERROR',type(e).__name__);continue
    tables=[r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
    print('TABLE_NAMES',tables[:50])
    for table in tables[:60]:
        try:
            tn=table.replace('"','""')
            cols=[x[1] for x in con.execute('PRAGMA table_info("'+tn+'")')]
            print('TABLE_SCHEMA',table,cols[:35])
            shown=0
            for row in con.execute('select * from "'+tn+'"'):
                s=' | '.join(str(x)[:1500] for x in row if x is not None)
                if not local.search(s):continue
                shown+=1
                public_paths=[u.split('?')[0] for u in url_re.findall(s)]
                redacted=re.sub(r'https?://[^\s|]+','[STREAM_URL]',s)
                print('LOCAL_CHANNEL_RECORD',table,redacted[:280],'URL_PATHS',public_paths[:5])
                if shown>=75:break
            print('LOCAL_CHANNEL_ROWS_SHOWN',table,shown)
        except Exception as e:print('TABLE_READ_ERROR',table,type(e).__name__,str(e)[:120])
    con.close()
print('LOCAL_CACHE_AUDIT_FINISHED')
