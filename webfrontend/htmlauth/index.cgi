#!/usr/bin/perl

# Copyright 2018 Dominik Holland, dominik.holland@googlemail.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


##########################################################################
# Modules
##########################################################################

use CGI;
use LoxBerry::System;
use LoxBerry::Web;

# cgi
my $cgi = CGI->new;
$cgi->import_names('R');

# Version of this script
my $version = LoxBerry::System::pluginversion();
my $pname = "wifi_scanner";

# config
my $cfg = new Config::Simple("$lbpconfigdir/wifi_scanner.cfg");

# Template
my $template = HTML::Template->new(
    filename => "$lbptemplatedir/index.html",
    global_vars => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
    associate => $cfg,
);

# Language
my %L = LoxBerry::Web::readlanguage($template, "language.ini");


if ($R::saveformdata) {
    # Write configuration file(s)
    $cfg->param("BASE.ENABLED", "$R::enable");
    $cfg->param("BASE.PORT", "$R::udpport");
    $cfg->param("BASE.FRITZBOX_ENABLE", "$R::fritz_enable");
    $cfg->param("BASE.UDP_ENABLE", "$R::udp_enable");
    $cfg->param("BASE.ACTIVE_SCAN", "$R::active_scan");
    $cfg->param("BASE.FRITZBOX", "$R::fritzbox");
    $cfg->param("BASE.FRITZBOX_PORT", "$R::fritzbox_port");
    $cfg->param("BASE.USERS", "$R::user_count");
    $cfg->param("BASE.CRON", "$R::cron");

    for (my $i=1;$i<=$R::user_count;$i++) {
        no strict 'refs';
        my $username = ${"R::username$i"};
        my $macs = ${"R::macs$i"};
        $cfg->param("USER$i.NAME", "$username");
        $cfg->param("USER$i.MACS", "$macs");
    }

    $cfg->save();

    # Unlink all existing Cronjobs
    unlink ("$lbhomedir/system/cron/cron.01min/$pname");
    unlink ("$lbhomedir/system/cron/cron.03min/$pname");
    unlink ("$lbhomedir/system/cron/cron.05min/$pname");
    unlink ("$lbhomedir/system/cron/cron.10min/$pname");
    unlink ("$lbhomedir/system/cron/cron.15min/$pname");
    unlink ("$lbhomedir/system/cron/cron.30min/$pname");
    unlink ("$lbhomedir/system/cron/cron.hourly/$pname");

    # Create new Cronjob
    if ($R::enable eq "1") {
        if ($R::cron == 60) {
            system ("ln -s $lbpbindir/check.pl $lbhomedir/system/cron/cron.hourly/$pname");
        } else {
            my $number = sprintf("%02d", $R::cron);
            system ("ln -s $lbpbindir/check.pl $lbhomedir/system/cron/cron.".$number."min/$pname");
        }
    }
    # Template output
    &save;

    if ($R::enable eq "1") {
        # Start one scan right away
        # Without the following workaround
        # the script cannot be executed as
        # background process via CGI
        my $pid = fork();
        die "Fork failed: $!" if !defined $pid;
        if ($pid == 0) {
            # do this in the child
            open STDIN, "</dev/null";
            open STDOUT, ">/dev/null";
            open STDERR, ">/dev/null";
            system("$lbpbindir/check.pl &");
        }
    }

    exit;
}

# Enabled
@values = ('0', '1' );
%labels = (
      '0' => $L{'SETTINGS.OFF'},
      '1' => $L{'SETTINGS.ON'},
  );
my $enable = $cgi->popup_menu(
      -name    => 'enable',
      -id      => 'enable',
      -values  => \@values,
      -labels  => \%labels,
      -default => $cfg->param('BASE.ENABLED'),
  );
$template->param( ENABLE => $enable );

# Cron
@values = ('1', '3', '5', '10', '15', '30', '60' );
%labels = (
      '1'  => $L{'SETTINGS.CRON_1'},
      '3'  => $L{'SETTINGS.CRON_2'},
      '5'  => $L{'SETTINGS.CRON_3'},
      '10' => $L{'SETTINGS.CRON_4'},
      '15' => $L{'SETTINGS.CRON_5'},
      '30' => $L{'SETTINGS.CRON_6'},
      '60' => $L{'SETTINGS.CRON_7'},
  );
my $cron = $cgi->popup_menu(
      -name    => 'cron',
      -id      => 'cron',
      -values  => \@values,
      -labels  => \%labels,
      -default => $cfg->param('BASE.CRON'),
  );
$template->param( CRON => $cron );

# Fritz Enabled
@values = ('0', '1' );
%labels = (
      '0' => $L{'SETTINGS.OFF'},
      '1' => $L{'SETTINGS.ON'},
  );
my $fritz_enable = $cgi->popup_menu(
      -name    => 'fritz_enable',
      -id      => 'fritz_enable',
      -values  => \@values,
      -labels  => \%labels,
      -default => $cfg->param('BASE.FRITZBOX_ENABLE'),
  );
$template->param( FRITZ_ENABLE => $fritz_enable );

# Active scan Enabled
my $active_scan = $cgi->popup_menu(
      -name    => 'active_scan',
      -id      => 'active_scan',
      -values  => \@values,
      -labels  => \%labels,
      -default => $cfg->param('BASE.ACTIVE_SCAN'),
  );
$template->param( ACTIVE_SCAN => $active_scan );


# UDP Enabled
my $loxberryversion = LoxBerry::System::lbversion();

if($loxberryversion == 2) {
    @values = ('0', '1' );
    %labels = (
          '0' => "mqtt",
          '1' => "UDP",
      );
} else {
    @values = ('1');
    %labels = (
          '1' => "UDP",
      );
}
my $udp_enable = $cgi->popup_menu(
      -name    => 'udp_enable',
      -id      => 'udp_enable',
      -values  => \@values,
      -labels  => \%labels,
      -default => $cfg->param('BASE.UDP_ENABLE'),
  );
$template->param( UDP_ENABLE => $udp_enable );

my @users= ();
my $user_count = $cfg->param('BASE.USERS');
for ($i=1;$i<=$user_count;$i++) {
    my %d;
    $d{INDEX} = $i;
    $d{NAME} = $cfg->param("USER$i.NAME");
    $d{MACS} = $cfg->param("USER$i.MACS");

    push(@users, \%d);
}
$template->param( USER_DATA => \@users);

$template->param( LOG_URL => "/admin/system/tools/logfile.cgi?logfile=$lbplogdir/wifi_scanner.log&header=html&format=template&only=once&package=$lbpplugindir&name=wifi_scanner.log");
$template->param( LOG_URL => LoxBerry::Web::loglist_url());
$template->param( "FORM", 1);

# Template
LoxBerry::Web::lbheader($L{'SETTINGS.PLUGINTITLE'} . " V$version", "http://www.loxwiki.eu/display/LOXBERRY/Wifi+Scanner", "help.html");
print $template->output();
LoxBerry::Web::lbfooter();

exit;

#####################################################
# Save
#####################################################

sub save
{
    $template->param( "SAVE", 1);
    LoxBerry::Web::lbheader($L{'SETTINGS.PLUGINTITLE'} . " V$version", "http://www.loxwiki.eu/display/LOXBERRY/Wifi+Scanner", "");
    print $template->output();
    LoxBerry::Web::lbfooter();

    exit;
}
