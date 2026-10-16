import os, pathlib, subprocess, time, json
root = pathlib.Path('/tmp/pg-wait-investigation')
results = []
for i in range(1,3):
 for tag in ['before-fixed']:
  label=f'historical-{tag}-{i}'
  data=root/(label+'-data'); data.mkdir(exist_ok=True)
  log=root/(label+'-log'); log.mkdir(exist_ok=True)
  env=dict(os.environ, PATH='/tmp/pg-wait-investigation/historical-install/bin:'+os.environ['PATH'], PG_REGRESS='/tmp/pg-wait-investigation/historical/src/test/regress/pg_regress', TESTDATADIR=str(data),TESTLOGDIR=str(log))
  start=time.monotonic()
  with (root/(label+'.out')).open('w') as out:
   p=subprocess.run(['/usr/bin/prove','-v','-I','/tmp/pg-wait-investigation/historical/src/test/perl',str(root/(tag+'.pl'))],env=env,stdout=out,stderr=subprocess.STDOUT)
  result=dict(label=label,seconds=round(time.monotonic()-start,3),exit_code=p.returncode)
  results.append(result); print(json.dumps(result),flush=True)
(root/'fixed-results.json').write_text(json.dumps(results,indent=2)+'\n')
