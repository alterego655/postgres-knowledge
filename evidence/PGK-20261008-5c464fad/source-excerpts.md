# Source evidence

Read from the working tree on 2026-10-08. HEAD: `e797f46d6a58e28bbcada551e3f3bac7126c6b8d`; branch: `codex/recovery-buffer-pin-wakeups-v9`. No tracked modifications were reported. Unrelated untracked files existed. These are source excerpts, not runtime test output. Full-file hashes identify the inspected bytes.

## src/test/perl/PostgreSQL/Test/Cluster.pm

SHA-256: `a15eab5b989ec389bdf78dd167501abae99595b48e204401cc291666ff6dfac6`

Lines 2065–2150:

```text
2065: =pod
2066: 
2067: =item $node->safe_psql($dbname, $sql) => stdout
2068: 
2069: Invoke B<psql> to run B<sql> on B<dbname> and return its stdout on success.
2070: Die if the SQL produces an error. Runs with B<ON_ERROR_STOP> set.
2071: 
2072: Takes optional extra params like timeout and timed_out parameters with the same
2073: options as psql.
2074: 
2075: =cut
2076: 
2077: sub safe_psql
2078: {
2079: 	my ($self, $dbname, $sql, %params) = @_;
2080: 
2081: 	local %ENV = $self->_get_env();
2082: 
2083: 	my ($stdout, $stderr);
2084: 
2085: 	my $ret = $self->psql(
2086: 		$dbname, $sql,
2087: 		%params,
2088: 		stdout => \$stdout,
2089: 		stderr => \$stderr,
2090: 		on_error_die => 1,
2091: 		on_error_stop => 1);
2092: 
2093: 	# psql can emit stderr from NOTICEs etc
2094: 	if ($stderr ne "")
2095: 	{
2096: 		print "#### Begin standard error\n";
2097: 		print $stderr;
2098: 		print "\n#### End standard error\n";
2099: 	}
2100: 
2101: 	return $stdout;
2102: }
2103: 
2104: =pod
2105: 
2106: =item $node->psql($dbname, $sql, %params) => psql_retval
2107: 
2108: Invoke B<psql> to execute B<$sql> on B<$dbname> and return the return value
2109: from B<psql>, which is run with on_error_stop by default so that it will
2110: stop running sql and return 3 if the passed SQL results in an error.
2111: 
2112: As a convenience, if B<psql> is called in array context it returns an
2113: array containing ($retval, $stdout, $stderr).
2114: 
2115: psql is invoked in tuples-only unaligned mode with reading of B<.psqlrc>
2116: disabled.  That may be overridden by passing extra psql parameters.
2117: 
2118: stdout and stderr are transformed to UNIX line endings if on Windows. Any
2119: trailing newline is removed.
2120: 
2121: Dies on failure to invoke psql but not if psql exits with a nonzero
2122: return code (unless on_error_die specified).
2123: 
2124: If psql exits because of a signal, an exception is raised.
2125: 
2126: =over
2127: 
2128: =item stdout => \$stdout
2129: 
2130: B<stdout>, if given, must be a scalar reference to which standard output is
2131: written.  If not given, standard output is not redirected and will be printed
2132: unless B<psql> is called in array context, in which case it's captured and
2133: returned.
2134: 
2135: =item stderr => \$stderr
2136: 
2137: Same as B<stdout> but gets standard error. If the same scalar is passed for
2138: both B<stdout> and B<stderr> the results may be interleaved unpredictably.
2139: 
2140: =item on_error_stop => 1
2141: 
2142: By default, the B<psql> method invokes the B<psql> program with ON_ERROR_STOP=1
2143: set, so SQL execution is stopped at the first error and exit code 3 is
2144: returned.  Set B<on_error_stop> to 0 to ignore errors instead.
2145: 
2146: =item on_error_die => 0
2147: 
2148: By default, this method returns psql's result code. Pass on_error_die to
2149: instead die with an informative message.
2150: 
```

Lines 2196–2250:

```text
2196: sub psql
2197: {
2198: 	my ($self, $dbname, $sql, %params) = @_;
2199: 
2200: 	local %ENV = $self->_get_env();
2201: 
2202: 	my $stdout = $params{stdout};
2203: 	my $stderr = $params{stderr};
2204: 	my $replication = $params{replication};
2205: 	my $timeout = undef;
2206: 	my $timeout_exception = 'psql timed out';
2207: 
2208: 	# Build the connection string.
2209: 	my $psql_connstr;
2210: 	if (defined $params{connstr})
2211: 	{
2212: 		$psql_connstr = $params{connstr};
2213: 	}
2214: 	else
2215: 	{
2216: 		$psql_connstr = $self->connstr($dbname);
2217: 	}
2218: 	$psql_connstr .= defined $replication ? " replication=$replication" : "";
2219: 
2220: 	my @psql_params = (
2221: 		$self->installed_command('psql'),
2222: 		'--no-psqlrc', '--no-align', '--tuples-only', '--quiet',
2223: 		'--dbname' => $psql_connstr,
2224: 		'--file' => '-');
2225: 
2226: 	# If the caller wants an array and hasn't passed stdout/stderr
2227: 	# references, allocate temporary ones to capture them so we
2228: 	# can return them. Otherwise we won't redirect them at all.
2229: 	if (wantarray)
2230: 	{
2231: 		if (!defined($stdout))
2232: 		{
2233: 			my $temp_stdout = "";
2234: 			$stdout = \$temp_stdout;
2235: 		}
2236: 		if (!defined($stderr))
2237: 		{
2238: 			my $temp_stderr = "";
2239: 			$stderr = \$temp_stderr;
2240: 		}
2241: 	}
2242: 
2243: 	$params{on_error_stop} = 1 unless defined $params{on_error_stop};
2244: 	$params{on_error_die} = 0 unless defined $params{on_error_die};
2245: 
2246: 	push @psql_params, '--variable' => 'ON_ERROR_STOP=1'
2247: 	  if $params{on_error_stop};
2248: 	push @psql_params, @{ $params{extra_params} }
2249: 	  if defined $params{extra_params};
2250: 
```

Lines 2340–2460:

```text
2340: 	if ($ret && $params{on_error_die})
2341: 	{
2342: 		croak "psql error: stderr: '$$stderr'\nwhile running '@psql_params'"
2343: 		  if $ret == 1;
2344: 		croak "connection error: '$$stderr'\nwhile running '@psql_params'"
2345: 		  if $ret == 2;
2346: 		croak
2347: 		  "error running SQL: '$$stderr'\nwhile running '@psql_params' with sql '$sql'"
2348: 		  if $ret == 3;
2349: 		croak "psql returns $ret: '$$stderr'\nwhile running '@psql_params'";
2350: 	}
2351: 
2352: 	if (wantarray)
2353: 	{
2354: 		return ($ret, $$stdout, $$stderr);
2355: 	}
2356: 	else
2357: 	{
2358: 		return $ret;
2359: 	}
2360: }
2361: 
2362: =pod
2363: 
2364: =item $node->background_psql($dbname, %params) => PostgreSQL::Test::BackgroundPsql instance
2365: 
2366: Invoke B<psql> on B<$dbname> and return a BackgroundPsql object.
2367: 
2368: psql is invoked in tuples-only unaligned mode with reading of B<.psqlrc>
2369: disabled.  That may be overridden by passing extra psql parameters.
2370: 
2371: Dies on failure to invoke psql, or if psql fails to connect.  Errors occurring
2372: later are the caller's problem.  psql runs with on_error_stop by default so
2373: that it will stop running sql and return 3 if passed SQL results in an error.
2374: 
2375: Be sure to "quit" the returned object when done with it.
2376: 
2377: =over
2378: 
2379: =item on_error_stop => 1
2380: 
2381: By default, the B<psql> method invokes the B<psql> program with ON_ERROR_STOP=1
2382: set, so SQL execution is stopped at the first error and exit code 3 is
2383: returned.  Set B<on_error_stop> to 0 to ignore errors instead.
2384: 
2385: =item timeout => 'interval'
2386: 
2387: Set a timeout for a background psql session. By default, timeout of
2388: $PostgreSQL::Test::Utils::timeout_default is set up.
2389: 
2390: =item connstr => B<value>
2391: 
2392: If set, use this as the connection string for the connection to the
2393: backend.
2394: 
2395: =item replication => B<value>
2396: 
2397: If set, add B<replication=value> to the conninfo string.
2398: Passing the literal value C<database> results in a logical replication
2399: connection.
2400: 
2401: =item extra_params => ['--single-transaction']
2402: 
2403: If given, it must be an array reference containing additional parameters to B<psql>.
2404: 
2405: =item wait => 1
2406: 
2407: By default, this method will not return until connection has completed (or
2408: failed). Set B<wait> to 0 to return immediately instead. (Clients can call the
2409: session's C<wait_connect> method manually when needed.)
2410: 
2411: =back
2412: 
2413: =cut
2414: 
2415: sub background_psql
2416: {
2417: 	my ($self, $dbname, %params) = @_;
2418: 
2419: 	local %ENV = $self->_get_env();
2420: 
2421: 	my $replication = $params{replication};
2422: 	my $timeout = undef;
2423: 
2424: 	# Build the connection string.
2425: 	my $psql_connstr;
2426: 	if (defined $params{connstr})
2427: 	{
2428: 		$psql_connstr = $params{connstr};
2429: 	}
2430: 	else
2431: 	{
2432: 		$psql_connstr = $self->connstr($dbname);
2433: 	}
2434: 	$psql_connstr .= defined $replication ? " replication=$replication" : "";
2435: 
2436: 	my @psql_params = (
2437: 		$self->installed_command('psql'),
2438: 		'--no-psqlrc', '--no-align',
2439: 		'--tuples-only', '--quiet',
2440: 		'--dbname' => $psql_connstr,
2441: 		'--file' => '-');
2442: 
2443: 	$params{on_error_stop} = 1 unless defined $params{on_error_stop};
2444: 	$params{wait} = 1 unless defined $params{wait};
2445: 	$timeout = $params{timeout} if defined $params{timeout};
2446: 
2447: 	push @psql_params, '--set' => 'ON_ERROR_STOP=1' if $params{on_error_stop};
2448: 	push @psql_params, @{ $params{extra_params} }
2449: 	  if defined $params{extra_params};
2450: 
2451: 	return PostgreSQL::Test::BackgroundPsql->new(0, \@psql_params, $timeout,
2452: 		$params{wait});
2453: }
2454: 
2455: =pod
2456: 
2457: =item $node->interactive_psql($dbname, %params) => BackgroundPsql instance
2458: 
2459: Invoke B<psql> on B<$dbname> and return a BackgroundPsql object, which the
2460: caller may use to send interactive input to B<psql>.
```

Lines 2759–2823:

```text
2759: =pod
2760: 
2761: =item $node->poll_query_until($dbname, $query [, $expected ])
2762: 
2763: Run B<$query> repeatedly, until it returns the B<$expected> result
2764: ('t', or SQL boolean true, by default).
2765: Continues polling if B<psql> returns an error result.
2766: Times out after $PostgreSQL::Test::Utils::timeout_default seconds.
2767: Returns 1 if successful, 0 if timed out.
2768: 
2769: =cut
2770: 
2771: sub poll_query_until
2772: {
2773: 	my ($self, $dbname, $query, $expected) = @_;
2774: 
2775: 	local %ENV = $self->_get_env();
2776: 
2777: 	$expected = 't' unless defined($expected);    # default value
2778: 
2779: 	my $cmd = [
2780: 		$self->installed_command('psql'), '--no-psqlrc',
2781: 		'--no-align', '--tuples-only',
2782: 		'--dbname' => $self->connstr($dbname)
2783: 	];
2784: 	my ($stdout, $stderr);
2785: 	my $max_attempts = 10 * $PostgreSQL::Test::Utils::timeout_default;
2786: 	my $attempts = 0;
2787: 
2788: 	while ($attempts < $max_attempts)
2789: 	{
2790: 		my $result = IPC::Run::run $cmd,
2791: 		  '<' => \$query,
2792: 		  '>' => \$stdout,
2793: 		  '2>' => \$stderr;
2794: 
2795: 		chomp($stdout);
2796: 		chomp($stderr);
2797: 
2798: 		if ($stdout eq $expected && $stderr eq '')
2799: 		{
2800: 			return 1;
2801: 		}
2802: 
2803: 		# Wait 0.1 second before retrying.
2804: 		usleep(100_000);
2805: 
2806: 		$attempts++;
2807: 	}
2808: 
2809: 	# Give up. Print the output from the last attempt, hopefully that's useful
2810: 	# for debugging.
2811: 	my $msg_query = $query;
2812: 	$msg_query = '(connection attempt only)' unless defined $query;
2813: 	diag qq(poll_query_until timed out executing this query:
2814: $msg_query
2815: expecting this output:
2816: $expected
2817: last actual query output:
2818: $stdout
2819: with stderr:
2820: $stderr);
2821: 	return 0;
2822: }
2823: 
```

## src/test/perl/PostgreSQL/Test/BackgroundPsql.pm

SHA-256: `f8746687700e5c33d928611249784024e8960cdd28e84238c54ebceb66cc532e`

Lines 200–357:

```text
200: Terminate the current session and connect again.
201: 
202: =cut
203: 
204: sub reconnect_and_clear
205: {
206: 	my ($self) = @_;
207: 
208: 	# If psql isn't dead already, tell it to quit as \q, when already dead,
209: 	# causes IPC::Run to unhelpfully error out with "ack Broken pipe:".
210: 	$self->{run}->pump_nb();
211: 	if ($self->{run}->pumpable())
212: 	{
213: 		$self->{stdin} .= "\\q\n";
214: 	}
215: 	$self->{run}->finish;
216: 
217: 	# restart
218: 	$self->{run}->run();
219: 	$self->{stdin} = '';
220: 	$self->{stdout} = '';
221: 
222: 	$self->wait_connect();
223: }
224: 
225: =pod
226: 
227: =item $session->query()
228: 
229: Executes a query in the current session and returns the output in scalar
230: context and (output, error) in list context where error is 1 in case there
231: was output generated on stderr when executing the query.
232: 
233: By default, the query and its results are printed to the test output. This
234: can be disabled by passing the keyword parameter verbose => false.
235: 
236: =cut
237: 
238: sub query
239: {
240: 	my ($self, $query, %params) = @_;
241: 	my $ret;
242: 	my $output;
243: 	my $query_cnt = $self->{query_cnt}++;
244: 
245: 	$params{verbose} = 1 unless defined $params{verbose};
246: 
247: 	local $Test::Builder::Level = $Test::Builder::Level + 1;
248: 
249: 	note "issuing query $query_cnt via background psql: $query"
250: 	  unless !$params{verbose};
251: 
252: 	$self->{timeout}->start() if (defined($self->{query_timer_restart}));
253: 
254: 	# Feed the query to psql's stdin, followed by \n (so psql processes the
255: 	# line), by a ; (so that psql issues the query, if it doesn't include a ;
256: 	# itself), and a separator echoed both with \echo and \warn, that we can
257: 	# wait on.
258: 	#
259: 	# To avoid somehow confusing the separator from separately issued queries,
260: 	# and to make it easier to debug, we include a per-psql query counter in
261: 	# the separator.
262: 	#
263: 	# We need both \echo (printing to stdout) and \warn (printing to stderr),
264: 	# because on windows we can get data on stdout before seeing data on
265: 	# stderr (or vice versa), even if psql printed them in the opposite
266: 	# order. We therefore wait on both.
267: 	#
268: 	# In interactive psql we emit \r\n, so we need to allow for that.
269: 	# Also, include quotes around the banner string in the \echo and \warn
270: 	# commands, not because the string needs quoting but so that $banner_match
271: 	# can't match readline's echoing of these commands.
272: 	my $banner = "background_psql: QUERY_SEPARATOR $query_cnt:";
273: 	my $banner_match = qr/$banner\r?\n/;
274: 	$self->{stdin} .= "$query\n;\n\\echo '$banner'\n\\warn '$banner'\n";
275: 	$self->{run}->pump()
276: 	  until ($self->{stdout} =~ /$banner_match/
277: 		  && $self->{stderr} =~ /$banner_match/)
278: 	  || $self->{timeout}->is_expired;
279: 
280: 	note "results query $query_cnt:\n",
281: 	  explain {
282: 		stdout => $self->{stdout},
283: 		stderr => $self->{stderr},
284: 	  }
285: 	  unless !$params{verbose};
286: 
287: 	die "psql query timed out" if $self->{timeout}->is_expired;
288: 
289: 	# Remove banner from stdout and stderr, our caller doesn't want it.
290: 	# Also remove the query output's trailing newline, if present (there
291: 	# would not be one if consuming an empty query result).
292: 	$banner_match = qr/\r?\n?$banner\r?\n/;
293: 	$output = $self->{stdout};
294: 	$output =~ s/$banner_match//;
295: 	$self->{stderr} =~ s/$banner_match//;
296: 
297: 	# clear out output for the next query
298: 	$self->{stdout} = '';
299: 
300: 	$ret = $self->{stderr} eq "" ? 0 : 1;
301: 
302: 	return wantarray ? ($output, $ret) : $output;
303: }
304: 
305: =pod
306: 
307: =item $session->query_safe()
308: 
309: Wrapper around C<query> which errors out if the query failed to execute.
310: Query failure is determined by it producing output on stderr.
311: 
312: =cut
313: 
314: sub query_safe
315: {
316: 	my ($self, $query, %params) = @_;
317: 
318: 	my $ret = $self->query($query, %params);
319: 
320: 	if ($self->{stderr} ne "")
321: 	{
322: 		die "query failed: $self->{stderr}";
323: 	}
324: 
325: 	return $ret;
326: }
327: 
328: =pod
329: 
330: =item $session->query_until(until, query)
331: 
332: Issue C<query> and wait for C<until> appearing in the query output rather than
333: waiting for query completion. C<query> needs to end with newline and semicolon
334: (if applicable, interactive psql input may not require it) for psql to process
335: the input.
336: 
337: =cut
338: 
339: sub query_until
340: {
341: 	my ($self, $until, $query) = @_;
342: 	my $ret;
343: 	local $Test::Builder::Level = $Test::Builder::Level + 1;
344: 
345: 	$self->{timeout}->start() if (defined($self->{query_timer_restart}));
346: 	$self->{stdin} .= $query;
347: 
348: 	pump_until($self->{run}, $self->{timeout}, \$self->{stdout}, $until);
349: 
350: 	die "psql query timed out" if $self->{timeout}->is_expired;
351: 
352: 	$ret = $self->{stdout};
353: 
354: 	# clear out output for the next query
355: 	$self->{stdout} = '';
356: 
357: 	return $ret;
```

## src/test/recovery/t/049_wait_for_lsn.pl

SHA-256: `bb3ae870cc4510a65d2f3a4c0a46e1076944c17d8004776794b3583b3e156123`

Lines 94–187:

```text
94: 
95: # And some content and take a backup
96: $node_primary->safe_psql('postgres',
97: 	"CREATE TABLE wait_test AS SELECT generate_series(1,10) AS a");
98: my $backup_name = 'my_backup';
99: $node_primary->backup($backup_name);
100: 
101: # Create a streaming standby with a 1 second delay from the backup
102: my $node_standby = PostgreSQL::Test::Cluster->new('standby');
103: my $delay = 1;
104: $node_standby->init_from_backup($node_primary, $backup_name,
105: 	has_streaming => 1);
106: $node_standby->append_conf(
107: 	'postgresql.conf', qq[
108: 	recovery_min_apply_delay = '${delay}s'
109: ]);
110: $node_standby->start;
111: 
112: # 1. Make sure that WAIT FOR works: add new content to
113: # primary and memorize primary's insert LSN, then wait for that LSN to be
114: # replayed on standby.
115: $node_primary->safe_psql('postgres',
116: 	"INSERT INTO wait_test VALUES (generate_series(11, 20))");
117: my $lsn1 =
118:   $node_primary->safe_psql('postgres', "SELECT pg_current_wal_insert_lsn()");
119: my $output = $node_standby->safe_psql(
120: 	'postgres', qq[
121: 	WAIT FOR LSN '${lsn1}' WITH (timeout '1d');
122: 	SELECT pg_lsn_cmp(pg_last_wal_replay_lsn(), '${lsn1}'::pg_lsn);
123: ]);
124: 
125: # Make sure the current LSN on standby is at least as big as the LSN we
126: # observed on primary's before.
127: ok((split("\n", $output))[-1] >= 0,
128: 	"standby reached the same LSN as primary after WAIT FOR");
129: 
130: # 2. Check that new data is visible after calling WAIT FOR
131: $node_primary->safe_psql('postgres',
132: 	"INSERT INTO wait_test VALUES (generate_series(21, 30))");
133: my $lsn2 =
134:   $node_primary->safe_psql('postgres', "SELECT pg_current_wal_insert_lsn()");
135: $output = $node_standby->safe_psql(
136: 	'postgres', qq[
137: 	WAIT FOR LSN '${lsn2}';
138: 	SELECT count(*) FROM wait_test;
139: ]);
140: 
141: # Make sure the count(*) on standby reflects the recent changes on primary
142: ok((split("\n", $output))[-1] eq 30,
143: 	"standby reached the same LSN as primary");
144: 
145: # 3. Check that WAIT FOR works with standby_write, standby_flush, and
146: # primary_flush modes.
147: $node_primary->safe_psql('postgres',
148: 	"INSERT INTO wait_test VALUES (generate_series(31, 40))");
149: my $lsn_write =
150:   $node_primary->safe_psql('postgres', "SELECT pg_current_wal_insert_lsn()");
151: $output = $node_standby->safe_psql(
152: 	'postgres', qq[
153: 	WAIT FOR LSN '${lsn_write}' WITH (MODE 'standby_write', timeout '1d');
154: 	SELECT pg_lsn_cmp((SELECT written_lsn FROM pg_stat_wal_receiver), '${lsn_write}'::pg_lsn);
155: ]);
156: 
157: ok( (split("\n", $output))[-1] >= 0,
158: 	"standby wrote WAL up to target LSN after WAIT FOR with MODE 'standby_write'"
159: );
160: 
161: $node_primary->safe_psql('postgres',
162: 	"INSERT INTO wait_test VALUES (generate_series(41, 50))");
163: my $lsn_flush =
164:   $node_primary->safe_psql('postgres', "SELECT pg_current_wal_insert_lsn()");
165: $output = $node_standby->safe_psql(
166: 	'postgres', qq[
167: 	WAIT FOR LSN '${lsn_flush}' WITH (MODE 'standby_flush', timeout '1d');
168: 	SELECT pg_lsn_cmp(pg_last_wal_receive_lsn(), '${lsn_flush}'::pg_lsn);
169: ]);
170: 
171: ok( (split("\n", $output))[-1] >= 0,
172: 	"standby flushed WAL up to target LSN after WAIT FOR with MODE 'standby_flush'"
173: );
174: 
175: # Check primary_flush mode on primary
176: $node_primary->safe_psql('postgres',
177: 	"INSERT INTO wait_test VALUES (generate_series(51, 60))");
178: my $lsn_primary_flush =
179:   $node_primary->safe_psql('postgres', "SELECT pg_current_wal_insert_lsn()");
180: $output = $node_primary->safe_psql(
181: 	'postgres', qq[
182: 	WAIT FOR LSN '${lsn_primary_flush}' WITH (MODE 'primary_flush', timeout '1d');
183: 	SELECT pg_lsn_cmp(pg_current_wal_flush_lsn(), '${lsn_primary_flush}'::pg_lsn);
184: ]);
185: 
186: ok( (split("\n", $output))[-1] >= 0,
187: 	"primary flushed WAL up to target LSN after WAIT FOR with MODE 'primary_flush'"
```

Lines 498–615:

```text
498: # A wait whose target has already been reached returns without sleeping, so it
499: # cannot join a cycle and stays allowed regardless of the locks held.
500: my $reached = $node_standby->safe_psql(
501: 	'postgres', qq[
502: 	BEGIN;
503: 	LOCK TABLE wait_test IN ACCESS SHARE MODE;
504: 	WAIT FOR LSN '${lsn1}';]);
505: is($reached, 'success',
506: 	"allow an already-reached wait while holding a relation lock");
507: 
508: # 7a. Check the scenario of multiple standby_replay waiters.  We make 5
509: # background psql sessions each waiting for a corresponding insertion.  When
510: # waiting is finished, stored procedures logs if there are visible as many
511: # rows as should be.
512: $node_primary->safe_psql(
513: 	'postgres', qq[
514: CREATE FUNCTION log_count(i int) RETURNS void AS \$\$
515:   DECLARE
516:     count int;
517:   BEGIN
518:     SELECT count(*) FROM wait_test INTO count;
519:     IF count >= 31 + i THEN
520:       RAISE LOG 'count %', i;
521:     END IF;
522:   END
523: \$\$
524: LANGUAGE plpgsql;
525: 
526: CREATE FUNCTION log_wait_done(prefix text, i int) RETURNS void AS \$\$
527:   BEGIN
528:     RAISE LOG '% %', prefix, i;
529:   END
530: \$\$
531: LANGUAGE plpgsql;
532: ]);
533: 
534: $node_standby->safe_psql('postgres', "SELECT pg_wal_replay_pause();");
535: 
536: my @psql_sessions;
537: for (my $i = 0; $i < 5; $i++)
538: {
539: 	$node_primary->safe_psql('postgres',
540: 		"INSERT INTO wait_test VALUES (${i});");
541: 	my $lsn =
542: 	  $node_primary->safe_psql('postgres',
543: 		"SELECT pg_current_wal_insert_lsn()");
544: 	$psql_sessions[$i] = $node_standby->background_psql('postgres');
545: 	$psql_sessions[$i]->query_until(
546: 		qr/start/, qq[
547: 		\\echo start
548: 		WAIT FOR LSN '${lsn}';
549: 		SELECT log_count(${i});
550: 	]);
551: }
552: 
553: my $log_offset = -s $node_standby->logfile;
554: $node_standby->safe_psql('postgres', "SELECT pg_wal_replay_resume();");
555: for (my $i = 0; $i < 5; $i++)
556: {
557: 	$node_standby->wait_for_log("count ${i}", $log_offset);
558: 	$psql_sessions[$i]->quit;
559: }
560: 
561: ok(1, 'multiple standby_replay waiters reported consistent data');
562: 
563: # 7b. Check the scenario of multiple standby_write waiters.
564: # Stop walreceiver to ensure waiters actually block.
565: stop_walreceiver($node_standby);
566: 
567: # Generate WAL on primary (standby won't receive it yet)
568: my @write_lsns;
569: for (my $i = 0; $i < 5; $i++)
570: {
571: 	$node_primary->safe_psql('postgres',
572: 		"INSERT INTO wait_test VALUES (100 + ${i});");
573: 	$write_lsns[$i] =
574: 	  $node_primary->safe_psql('postgres',
575: 		"SELECT pg_current_wal_insert_lsn()");
576: }
577: 
578: # Start standby_write waiters (they will block since walreceiver is stopped)
579: my @write_sessions;
580: for (my $i = 0; $i < 5; $i++)
581: {
582: 	$write_sessions[$i] = $node_standby->background_psql('postgres');
583: 	$write_sessions[$i]->query_until(
584: 		qr/start/, qq[
585: 		\\echo start
586: 		WAIT FOR LSN '$write_lsns[$i]' WITH (MODE 'standby_write', timeout '1d');
587: 		SELECT log_wait_done('write_done', $i);
588: 	]);
589: }
590: 
591: # Verify waiters are blocked
592: $node_standby->poll_query_until('postgres',
593: 	"SELECT count(*) = 5 FROM pg_stat_activity WHERE wait_event = 'WaitForWalWrite'"
594: );
595: 
596: # Restore walreceiver to unblock waiters
597: my $write_log_offset = -s $node_standby->logfile;
598: resume_walreceiver($node_standby);
599: 
600: # Wait for all waiters to complete and close sessions
601: for (my $i = 0; $i < 5; $i++)
602: {
603: 	$node_standby->wait_for_log("write_done $i", $write_log_offset);
604: 	$write_sessions[$i]->quit;
605: }
606: 
607: # Verify on standby that WAL was written up to the target LSN
608: $output = $node_standby->safe_psql('postgres',
609: 	"SELECT pg_lsn_cmp((SELECT written_lsn FROM pg_stat_wal_receiver), '$write_lsns[4]'::pg_lsn);"
610: );
611: 
612: ok($output >= 0,
613: 	"multiple standby_write waiters: standby wrote WAL up to target LSN");
614: 
615: # 7c. Check the scenario of multiple standby_flush waiters.
```

## src/test/recovery/t/031_recovery_conflict.pl

SHA-256: `3973040e13ca33e1d7df40679693615805ea7ae6a66c5cf07aba75866fef322d`

Lines 20–38:

```text
20: 
21: $node_primary->append_conf(
22: 	'postgresql.conf', qq[
23: allow_in_place_tablespaces = on
24: log_temp_files = 0
25: 
26: # for deadlock test
27: max_prepared_transactions = 10
28: 
29: # wait some to test the wait paths as well, but not long for obvious reasons
30: max_standby_streaming_delay = 50ms
31: 
32: temp_tablespaces = $tablespace1
33: # Some of the recovery conflict logging code only gets exercised after
34: # deadlock_timeout. The test doesn't rely on that additional output, but it's
35: # nice to get some minimal coverage of that code.
36: log_recovery_conflict_waits = on
37: deadlock_timeout = 10ms
38: ]);
```

Lines 70–124:

```text
70: # a longrunning psql that we can use to trigger conflicts
71: my $psql_standby =
72:   $node_standby->background_psql($test_db, on_error_stop => 0);
73: my $expected_conflicts = 0;
74: 
75: 
76: ## RECOVERY CONFLICT 1: Buffer pin conflict
77: my $sect = "buffer pin conflict";
78: $expected_conflicts++;
79: 
80: # Aborted INSERT on primary that will be cleaned up by vacuum. Has to be old
81: # enough so that there's not a snapshot conflict before the buffer pin
82: # conflict.
83: 
84: $node_primary->safe_psql(
85: 	$test_db,
86: 	qq[
87: 	BEGIN;
88: 	INSERT INTO $table1 VALUES (1,0);
89: 	ROLLBACK;
90: 	-- ensure flush, rollback doesn't do so
91: 	BEGIN; LOCK $table1; COMMIT;
92: 	]);
93: 
94: $node_primary->wait_for_replay_catchup($node_standby);
95: 
96: my $cursor1 = "test_recovery_conflict_cursor";
97: 
98: # DECLARE and use a cursor on standby, causing buffer with the only block of
99: # the relation to be pinned on the standby
100: my $res = $psql_standby->query_safe(
101: 	qq[
102:     BEGIN;
103:     DECLARE $cursor1 CURSOR FOR SELECT b FROM $table1;
104:     FETCH FORWARD FROM $cursor1;
105: ]);
106: # FETCH FORWARD should have returned a 0 since all values of b in the table
107: # are 0
108: like($res, qr/^0$/m, "$sect: cursor with conflicting pin established");
109: 
110: # to check the log starting now for recovery conflict messages
111: my $log_location = -s $node_standby->logfile;
112: 
113: # VACUUM FREEZE on the primary
114: $node_primary->safe_psql($test_db, qq[VACUUM FREEZE $table1;]);
115: 
116: # Wait for catchup. Existing connection will be terminated before replay is
117: # finished, so waiting for catchup ensures that there is no race between
118: # encountering the recovery conflict which causes the disconnect and checking
119: # the logfile for the terminated connection.
120: $node_primary->wait_for_replay_catchup($node_standby);
121: 
122: check_conflict_log("User was holding shared buffer pin for too long");
123: $psql_standby->reconnect_and_clear();
124: check_conflict_stat("bufferpin");
```
