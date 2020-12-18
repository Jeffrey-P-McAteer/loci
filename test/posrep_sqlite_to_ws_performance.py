

def test():
  import subprocess
  import os
  import time
  import json
  import sqlite3
  import random
  import string

  import websocket # python -m pip install --user websocket_client
  

  def windows_host():
    return os.name == 'nt'

  def rand_hex_s(num=8):
    return ''.join( [random.choice(string.ascii_letters + string.digits) for n in range(0, num)] )

  loci_env = {}
  loci_env.update(os.environ)
  # our test needs no GUI
  loci_env['LOCI_NO_GUI'] = '1'
  # We also do not require these, but we may want to test with them for performance reasons later.
  loci_env['LOCI_DISABLED_SUBPROGRAMS'] = 'dump1090,postgis,geoserver'

  print('LOCI_RELEASE_EXE={}'.format(os.environ['LOCI_RELEASE_EXE']))

  loci_p = subprocess.Popen([
    os.environ['LOCI_RELEASE_EXE'],
  ],
    env=loci_env,
    #stdout=subprocess.DEVNULL,
  )

  primary_test_e = None
  performance_rep_line = 'Performance Unmeasured!'
  try:
    ws = websocket.WebSocket()
    ws_url = 'ws://127.0.0.1:8080/ws'

    retries = 99
    while retries > 0:
      try:
        ws.connect(ws_url, timeout=3.0)
        break
      except Exception as e:
        retries -= 1
        time.sleep(0.2)

    if retries < 1:
      raise Exception('Could not connect to {} to perform test'.format(ws_url))

    if windows_host():
      db_f = os.path.join(os.environ['LocalAppData'], 'DeVil-Tech', 'Loci', 'db', 'db.db')
    else:
      db_f = os.path.expanduser('~/.local/share/Loci/db/db.db')

    retries = 180
    while retries > 0 and not os.path.exists(db_f):
      time.sleep(0.5)
      retries -= 1

    db_c = sqlite3.connect(db_f, isolation_level='IMMEDIATE')

    # Wait until the pos_reps table exists...
    retries = 99
    while retries > 0:
      try:
        db_c.execute('select id from pos_reps limit 1;')
        break
      except Exception as e:
        retries -= 1
        time.sleep(0.2)

    if retries < 1:
      raise Exception('Could not select from pos_reps; table does not exist!')

    # The test writes 1 pos rep to the DB, then queries for the last 50 posreps.
    # If the written posrep is not part of the returned set the test fails.
    # We print throughput as a test statistic

    reps = 400
    payload_size = 100

    time_start_s = time.time()

    for _ in range(0, reps):
      # Gen payload_size posreps
      pos_reps = []
      
      db_c.execute('DELETE FROM pos_reps WHERE 1=1;');

      for _ in range(0, payload_size):
        rand_name = rand_hex_s()
        rand_lat = round( (random.random() * 180.0) - 90.0, 3)
        rand_lon = round( (random.random() * 180.0) - 90.0, 3)
        db_c.execute(
          "INSERT INTO pos_reps(id, lat, lon) VALUES(\"{}\", {}, {});".format(
            rand_name, rand_lat, rand_lon
          )
        )
        pos_reps.append(
          (rand_name, rand_lat, rand_lon)
        )
      
      db_c.commit()

      ws.send(json.dumps({
        'type': 'db-query-constant',
        'query': 'select id, lat, lon from pos_reps limit {};'.format(payload_size+2),
        'callback': '',
      }));

      resp = ws.recv()

      for pr in pos_reps:
        rand_name = pr[0]
        if not ( rand_name in resp ):
          raise Exception('Coud not find posrep for ship {} in returned data: {}'.format(rand_name, resp))


    time_end_s = time.time()
    time_per_iter_ms = round( ((time_end_s-time_start_s) / reps) * 1000.0, 1)
    
    # Our target is 2000 posreps/second
    target_posrep_n = 2000
    target_posrep_ms = 1000.0

    target_time_per_payload_ms = round( (target_posrep_ms / target_posrep_n) * payload_size, 2)
    performance_rep_line = 'INSERT and query {} pos reps: {}ms (test fails when {} takes >{}ms; {} iter)'.format(
      payload_size, time_per_iter_ms, payload_size, target_time_per_payload_ms, reps
    )

    if time_per_iter_ms > target_time_per_payload_ms:
      raise Exception('Test failed because it took {}ms to move {} posreps, must be below {}ms'.format(
        time_per_iter_ms, payload_size, target_time_per_payload_ms
      ))

    ws.close()
  except Exception as e:
    primary_test_e = e

  try:
    loci_p.terminate()
    loci_p.kill()
  except:
    pass

  if primary_test_e:
    raise primary_test_e

  return performance_rep_line



