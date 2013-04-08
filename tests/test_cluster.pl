#!/usr/bin/env perl

use strict;
use warnings;

use File::Path qw(mkpath);
use POSIX;

use WWW::Curl::Easy;

use Test::Simple tests => 47;

sub chk {
    my $res = shift;
    my %q = @_;

    return undef if (exists($q{code}) && $q{code} != $res->{code});
    return undef if (exists($q{content}) && $q{content} ne $res->{content});
    return undef if (exists($q{body}) && $q{body} ne $res->{body});
    return undef if (exists($q{err}) && $q{err} != $res->{err});

    return 1;
}

sub wx {
    my $code = shift;
    for my $i(0..20) {
        sleep 1 if $i > 0;
        return 1 if $code->();
    }
    return undef;
}


sub get_curl {
    my $url = shift;

    my $response_body;
    my $curl = WWW::Curl::Easy->new;
    $curl->setopt(CURLOPT_HEADER, 1);
    $curl->setopt(CURLOPT_URL, $url);
    $curl->setopt(CURLOPT_WRITEDATA, \$response_body);

    my $resp = sub {
        my $ret_code = $curl->perform;

        return 0 == $ret_code ? {
                code => $curl->getinfo(CURLINFO_HTTP_CODE),
                content => $response_body ? $response_body : '',
                body =>  $response_body ? (split /\r?\n\r?\n/,  $response_body)[1] : '',
                err => '',
        } : {
                code => -1,
                content => '',
                body => '',
                err => $curl->strerror($ret_code),
        };
    };

    return ($curl, $resp);
}

my $req = {
	get => sub {
        my ($url) = @_;

        my ($curl, $resp) = get_curl($url);
        return $resp->();
    },
    put => sub {
    	my ($url, $content) = @_;
        my ($curl, $resp) = get_curl($url);

        $curl->setopt(CURLOPT_INFILESIZE, length($content));
        open my $file, '<', \$content;
        $curl->setopt(CURLOPT_READDATA, $file);
        $curl->setopt(CURLOPT_UPLOAD, 1);
        $curl->setopt(CURLOPT_CUSTOMREQUEST, 'PUT');
        return $resp->();
   	},
};

sub tmp_dir {
	(my $tail = shift) =~ s{^/+}{};
	my $file_path = "/tmp/lighthouse-tests/$$/$tail";
	(my $path = $file_path) =~ s{/[^/]*$}{};
	-d $path or mkpath($path) or die "Cannot create directory: \`$path'";
	return $file_path;
}

sub kill_and_wait {
	kill POSIX::SIGTERM, @_;

    for my $pid (@_) {
        waitpid($pid, 0);
    }
}

sub lighthouse {
	my @keys = (
		'data.d',
		'seeds',
        'bind',
        'load-limit',
        'rm-limit',
        'bootstrap',
    );

    my %params = (
    	'out-file' => '/dev/null',
    	@_,
    );

    my @args = map { exists $params{$_} and (defined($params{$_}) ? "--$_=$params{$_}" : "--$_") } @keys;

	defined(my $pid = fork()) or die "Cannot fork";
	if (!$pid) {
		open my $fh, '>', $params{'out-file'};
		open STDOUT, '>&', $fh;
		open STDERR, '>&', $fh;
		close $fh;
	    exec { 'lighthouse/main.py' } ('main.py',  @args);
	}
	return { pid => $pid, log => $params{'out-file'} };
}

sub main {
    my @pids = ();

	push @pids, lighthouse('out-file' => tmp_dir('001.log'), 'seeds' => '127.0.0.1:11001', 'data.d' => tmp_dir('8001/'), 'bootstrap' => undef);

    ok wx sub { chk $req->{get}->("http://127.0.0.1:8001/data"), body => '{}' };

    ok chk $req->{put}->("http://127.0.0.1:8001/lock", "$$"), code => 200;
    ok chk $req->{put}->("http://127.0.0.1:8001/update/$$", '{ "file": "/var/log/apache2/access.log", "size": 1024, "XXX": 12345, "providers": { "alpha": ["192.168.1.1", "192.168.1.2"], "beta": ["192.168.2.1", "192.168.2.2"], "gamma": ["192.168.3.1", "192.168.3.2"] } }'), code => 201;
    ok chk $req->{put}->("http://127.0.0.1:8001/update/bad-key/somewher", 'xxx'), code => 403;
    ok chk $req->{put}->("http://127.0.0.1:8001/update/$$/not/found", '{ "file": "mm" }'), code => 404;
    ok chk $req->{put}->("http://127.0.0.1:8001/lock/$$", ''), code => 200;

    ok chk $req->{put}->("http://127.0.0.1:8001/lock", "$$-201"), code => 200;
    ok chk $req->{put}->("http://127.0.0.1:8001/update/$$-201/XXX", '{ "A0": { "B1": { "C2": { "D3": "Hello World" } } } }'), code => 201;
    ok chk $req->{get}->("http://127.0.0.1:8001/update/$$-201/XXX/A0/B1/C2/D3"), body => '"Hello World"';
    ok chk $req->{put}->("http://127.0.0.1:8001/lock/$$-201", ''), code => 200;
    ok chk $req->{get}->("http://127.0.0.1:8001/data/XXX/A0/B1/C2/D3"), body => '"Hello World"';

    ok chk $req->{put}->("http://127.0.0.1:8001/lock", "$$-321"), code => 200;
    ok chk $req->{put}->("http://127.0.0.1:8001/update/$$-321/XXX/A0/B1/C2/D3", '"Nothing Works"'), code => 201;
    ok chk $req->{get}->("http://127.0.0.1:8001/update/$$-321/XXX/A0/B1/C2/D3"), body => '"Nothing Works"';

    print STDERR "Waiting for expiration of the key...\n";
    sleep 30;
    ok chk $req->{get}->("http://127.0.0.1:8001/update/$$-321/XXX/A0/B1/C2/D3"), code => 403;

    ok do {
        my $copy = $req->{get}->("http://127.0.0.1:8001/copy")->{body};
        kill_and_wait( (shift @pids)->{pid} );
        push @pids, lighthouse('out-file' => tmp_dir('002.log'), 'data.d' => tmp_dir('8001/'));
    
        wx sub { $copy eq $req->{get}->("http://127.0.0.1:8001/copy")->{body} };
    };

    push @pids, lighthouse('out-file' => tmp_dir('011.log'), 'bind' => '127.0.0.1:11001', 'seeds' => '127.0.0.1:8001', 'data.d' => tmp_dir('11001/'));
    ok wx sub { chk $req->{get}->("http://127.0.0.1:11001/state"), 'code' => 200 };
    ok do {
        my $copy_8001 = $req->{get}->("http://127.0.0.1:8001/copy")->{body};
        my $copy_11001 = $req->{get}->("http://127.0.0.1:11001/copy")->{body};
        $copy_8001 eq $copy_11001;
    };

    ok wx sub { $req->{get}->("http://127.0.0.1:8001/state")->{body} =~ m{ "address": "127.0.0.1:11001"} };
    ok wx sub { $req->{get}->("http://127.0.0.1:11001/state")->{body} =~ m{ "address": "127.0.0.1:8001"} };

    ok chk $req->{put}->("http://127.0.0.1:11001/lock", "$$"), code => 200;
    ok chk $req->{put}->("http://127.0.0.1:11001/update/$$/XXX", '3.14'), code => 201;
    ok chk $req->{put}->("http://127.0.0.1:11001/lock/$$", ''), code => 200;

    ok wx sub { chk $req->{get}->("http://127.0.0.1:8001/data/XXX"), body => '3.14' };

    ok do {
        my $copy = $req->{get}->("http://127.0.0.1:11001/copy")->{body};
        kill_and_wait( (pop @pids)->{pid} );
        push @pids, lighthouse('out-file' => tmp_dir('012.log'), 'bind' => '127.0.0.1:11001', 'data.d' => tmp_dir('11001/'));
        wx sub { $copy eq $req->{get}->("http://127.0.0.1:11001/copy")->{body} };
    };

    push @pids, lighthouse('out-file' => tmp_dir('021.log'), 'bind' => '127.0.0.1:12001', 'seeds' => '127.0.0.1:8001', 'data.d' => tmp_dir('12001/'));
    ok wx sub { $req->{get}->("http://127.0.0.1:8001/state")->{body} =~ m{ "address": "127.0.0.1:12001"} };
    ok wx sub { $req->{get}->("http://127.0.0.1:11001/state")->{body} =~ m{ "address": "127.0.0.1:12001"} };
    ok wx sub { $req->{get}->("http://127.0.0.1:12001/state")->{body} =~ m{ "address": "127.0.0.1:8001"} };
    ok wx sub { $req->{get}->("http://127.0.0.1:12001/state")->{body} =~ m{ "address": "127.0.0.1:11001"} };
print STDERR "8001: #" . $req->{get}->("http://127.0.0.1:8001/state")->{body} . "#\n";
print STDERR "11001: #" . $req->{get}->("http://127.0.0.1:11001/state")->{body} . "#\n";
print STDERR "12001: #" . $req->{get}->("http://127.0.0.1:12001/state")->{body} . "#\n";

    ok chk $req->{put}->("http://127.0.0.1:8001/lock", "$$"), code => 200;
    ok chk $req->{put}->("http://127.0.0.1:8001/update/$$/XXX", '3218001'), code => 201;
    ok chk $req->{put}->("http://127.0.0.1:8001/lock/$$", ''), code => 200;
    ok wx sub { chk $req->{get}->("http://127.0.0.1:8001/data/XXX"), body => '3218001' };
    ok wx sub { chk $req->{get}->("http://127.0.0.1:11001/data/XXX"), body => '3218001' };
    ok wx sub { chk $req->{get}->("http://127.0.0.1:12001/data/XXX"), body => '3218001' };

    ok chk $req->{put}->("http://127.0.0.1:11001/lock", "$$"), code => 200;
    ok chk $req->{put}->("http://127.0.0.1:11001/update/$$/XXX", '32111001'), code => 201;
    ok chk $req->{put}->("http://127.0.0.1:11001/lock/$$", ''), code => 200;
    ok wx sub { chk $req->{get}->("http://127.0.0.1:8001/data/XXX"), body => '32111001' };
    ok wx sub { chk $req->{get}->("http://127.0.0.1:11001/data/XXX"), body => '32111001' };
    ok wx sub { chk $req->{get}->("http://127.0.0.1:12001/data/XXX"), body => '32111001' };

    ok chk $req->{put}->("http://127.0.0.1:12001/lock", "$$"), code => 200;
    ok chk $req->{put}->("http://127.0.0.1:12001/update/$$/XXX", '32112001'), code => 201;
    ok chk $req->{put}->("http://127.0.0.1:12001/lock/$$", ''), code => 200;
    ok wx sub { chk $req->{get}->("http://127.0.0.1:8001/data/XXX"), body => '32112001' };
    ok wx sub { chk $req->{get}->("http://127.0.0.1:11001/data/XXX"), body => '32112001' };
    ok wx sub { chk $req->{get}->("http://127.0.0.1:12001/data/XXX"), body => '32112001' };

    while (@pids) {
        kill_and_wait( (shift @pids)->{pid} ) ;
    }
}

main;