import os, pathlib, subprocess, time, json, shutil, re
repo=pathlib.Path('/Users/qqj/dev/postgres')
art=repo/'.cache/wait-for-lsn-runtime/head-revert'
root=pathlib.Path('/tmp/pg-wait-investigation/head-runs'); root.mkdir(exist_ok=True)
source=pathlib.Path('/tmp/pg-wait-investigation/head-source')
results=[]
for i in range(1,3):
 for tag in ['head','reverted']:
  label=f'clean-{tag}-{i}'
  data=root/(label+'-data'); data.mkdir()
  log=art/(label+'-log'); log.mkdir()
  env=dict(os.environ,enable_injection_points='yes',PATH='/tmp/pg-wait-investigation/head-clean-install/bin:'+os.environ['PATH'],PG_REGRESS=str(source/'src/test/regress/pg_regress'),TESTDATADIR=str(data),TESTLOGDIR=str(log))
  start=time.monotonic();captured=False
  with (art/(label+'.out')).open('w') as out:
   p=subprocess.Popen(['/usr/bin/prove','-v','-I',str(source/'src/test/perl'),str(art/(tag+'.pl'))],env=env,stdout=out,stderr=subprocess.STDOUT)
   while p.poll() is None:
    standby=log/(tag+'_standby.log')
    if not captured and standby.exists() and "log_wait_done('mixed_done'" in standby.read_text():
     wal=data/('t_'+tag+'_primary_data')/'pgdata/pg_wal'
     dest=art/(label+'-wal');dest.mkdir()
     for f in wal.iterdir():
      if re.fullmatch('[0-9A-F]{24}',f.name):shutil.copyfile(f,dest/f.name)
     captured=True
    time.sleep(.1)
  result=dict(label=label,seconds=round(time.monotonic()-start,3),exit_code=p.returncode,wal_captured=captured)
  results.append(result);print(json.dumps(result),flush=True)
  (art/'clean-results.json').write_text(json.dumps(results,indent=2)+'\n')
  if p.returncode:raise SystemExit(p.returncode)
