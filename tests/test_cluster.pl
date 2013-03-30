#!/usr/bin/env perl

use strict;
use warnings;

use POSIX;

use Test::Simple tests => 1;

sub lighthouse {
	my %params = (
		'out-file' => '/dev/null',
        'data.d' => undef,
        'seeds' => undef,
        'bind' => undef,
        'load-limit' => undef,
        'rm-limit' => undef,
        'bootstrap' => undef,
        @_
    );

	defined(my $pid = fork()) or die "Cannot fork";
	if (!$pid) {
		open my $fh, '>', $params{'out-file'};
		open STDOUT, '>&', $fh;
		open STDERR, '>&', $fh;
		close $fh;
	    exec { 'lighthouse/main.py' } @_;
	}
	return $pid;
}


sub kill_and_wait {
	kill POSIX::SIGTERM, @_;

    for my $pid (@_) {
        waitpid($pid, 0);
    }
}

sub main {
	my $lighthouse_pid = lighthouse('out-file' => '/tmp/xxx.log');

    sleep(5);

    kill_and_wait($lighthouse_pid);

	ok(1);
}

main;