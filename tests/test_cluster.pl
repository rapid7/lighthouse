#!/usr/bin/env perl

use strict;
use warnings;

use File::Path qw(mkpath);
use POSIX;

use WWW::Curl::Easy;

use Test::Simple tests => 5;

sub chk {
    my $res = shift;
    my %q = @_;

    return undef if (exists($q{code}) && $q{code} != $res->{code});
    return undef if (exists($q{content}) && $q{content} ne $res->{content});
    return undef if (exists($q{body}) && $q{body} ne $res->{body});
    return undef if (exists($q{err}) && $q{err} != $res->{err});

    return 1;
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

        my $ret = 0 == $ret_code ? {
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
	my $file_path = "/tmp/$$/$tail";
	(my $path = $file_path) =~ s{/[^/]*$}{};
	mkpath($path) or die "Cannot create directory: \`$path'";
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

    my @args = map { exists $params{$_} and "--$_=$params{$_}" } @keys;

	defined(my $pid = fork()) or die "Cannot fork";
	if (!$pid) {
		open my $fh, '>', $params{'out-file'};
		open STDOUT, '>&', $fh;
		open STDERR, '>&', $fh;
		close $fh;
	    exec { 'lighthouse/main.py' } ('main.py',  @args);
	}
	return $pid;
}

sub main {
	my $log_file = tmp_dir('001.log');
	my $lighthouse_pid = lighthouse('out-file' => $log_file, 'seeds' => '127.0.0.1:11001');
    sleep(6);

    ok $req->{get}->("http://127.0.0.1:8001/data")->{body} eq '{}';
    ok chk $req->{get}->("http://127.0.0.1:8001/data"), body => '{}';

    ok chk $req->{put}->("http://127.0.0.1:8001/lock", "$$"), code => 200;
    ok chk $req->{put}->("http://127.0.0.1:8001/update/$$", '{ "file": "/var/log/apache2/access.log", "size": 1024, "XXX": 12345, "providers": { "alpha": ["192.168.1.1", "192.168.1.2"], "beta": ["192.168.2.1", "192.168.2.2"], "gamma": ["192.168.3.1", "192.168.3.2"] } }'), code => 201;
    ok chk $req->{put}->("http://127.0.0.1:8001/lock/$$", ''), code => 200;

    kill_and_wait($lighthouse_pid);
}

main;