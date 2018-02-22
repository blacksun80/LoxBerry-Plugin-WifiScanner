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

use CGI::Carp qw(fatalsToBrowser);
use CGI qw/:standard/;
use LWP::UserAgent;
use JSON qw( decode_json );
use Config::Simple;
use File::HomeDir;
use Cwd 'abs_path';
#use warnings;
#use strict;
#no strict "refs"; # we need it for template system

##########################################################################
# Variables
##########################################################################

our $cfg;
our $pcfg;
our $phrase;
our $namef;
our $value;
our %query;
our $lang;
our $template_title;
our $help;
our @help;
our $helptext;
our $helplink;
our $installfolder;
our $planguagefile;
our $version;
our $error;
our $saveformdata = 0;
our $output;
our $message;
our $nexturl;
our $do = "form";
my  $home = File::HomeDir->my_home;
our $psubfolder;
our $pname;
our $verbose;
our $languagefileplugin;
our $phraseplugin;
our $scanner_active;
our $cron;
our $wulang;
our $metric;
our $sendudp;
our $udpport;
our $senddfc;
our $sendhfc;
our $var;
our $theme;
our $iconset;
our $ua;
our $res;
our $json;
our $urlstatus;
our $urlstatuscode;
our $decoded_json;
our $query;
our $querystation;
our $found;
our $i;

##########################################################################
# Read Settings
##########################################################################

# Version of this script
$version = "0.0.1";

# Figure out in which subfolder we are installed
$psubfolder = abs_path($0);
$psubfolder =~ s/(.*)\/(.*)\/(.*)$/$2/g;

$cfg             = new Config::Simple("$home/config/system/general.cfg");
$installfolder   = $cfg->param("BASE.INSTALLFOLDER");
$lang            = $cfg->param("BASE.LANG");

#########################################################################
# Parameter
#########################################################################

# Everything from URL
foreach (split(/&/,$ENV{'QUERY_STRING'}))
{
  ($namef,$value) = split(/=/,$_,2);
  $namef =~ tr/+/ /;
  $namef =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
  $value =~ tr/+/ /;
  $value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
  $query{$namef} = $value;
}

# Set parameters coming in - get over post
if ( !$query{'saveformdata'} ) {
	if ( param('saveformdata') ) {
		$saveformdata = quotemeta(param('saveformdata'));
	} else {
		$saveformdata = 0;
	}
} else {
	$saveformdata = quotemeta($query{'saveformdata'});
}
if ( !$query{'lang'} ) {
	if ( param('lang') ) {
		$lang = quotemeta(param('lang'));
	} else {
		$lang = "de";
	}
} else {
	$lang = quotemeta($query{'lang'});
}
if ( !$query{'do'} ) {
	if ( param('do')) {
		$do = quotemeta(param('do'));
	} else {
		$do = "form";
	}
} else {
	$do = quotemeta($query{'do'});
}

# Clean up saveformdata variable
$saveformdata =~ tr/0-1//cd;
$saveformdata = substr($saveformdata,0,1);

# Init Language
# Clean up lang variable
$lang =~ tr/a-z//cd;
$lang = substr($lang,0,2);

# If there's no language phrases file for choosed language, use german as default
if (!-e "$installfolder/templates/plugins/$psubfolder/$lang/language.dat") {
	$lang = "de";
}

# Read translations / phrases
$planguagefile	= "$installfolder/templates/plugins/$psubfolder/$lang/language.dat";
$pphrase = new Config::Simple($planguagefile);
$pphrase->import_names('T');

##########################################################################
# Main program
##########################################################################

if ($saveformdata) {
  &save;

} else {
  &form;

}

exit;

#####################################################
#
# Subroutines
#
#####################################################

#####################################################
# Form-Sub
#####################################################

sub form {

	$pcfg             = new Config::Simple("$installfolder/config/plugins/$psubfolder/wifi_scanner.cfg");
	$scanner_active   = $pcfg->param("BASE.ENABLED");
	$cron             = $pcfg->param("BASE.CRON");
	$udpport          = $pcfg->param("BASE.PORT");
  $fritzbox         = $pcfg->param("BASE.FRITZBOX");
  $fritzbox_port    = $pcfg->param("BASE.FRITZBOX_PORT");
  $users            = $pcfg->param("BASE.USERS");

  # GETWUDATA
  if ($scanner_active eq "1") {
    $scanner_active_on = "selected=selected";
  } else {
    $scanner_active_off = "selected=selected";
  }
	# CRON
	if ($cron eq "1") {
	  $selectedcron1 = "selected=selected";
	} elsif ($cron eq "3") {
	  $selectedcron2 = "selected=selected";
	} elsif ($cron eq "5") {
	  $selectedcron3 = "selected=selected";
	} elsif ($cron eq "10") {
	  $selectedcron4 = "selected=selected";
	} elsif ($cron eq "15") {
	  $selectedcron5 = "selected=selected";
	} elsif ($cron eq "30") {
	  $selectedcron6 = "selected=selected";
	} elsif ($cron eq "60") {
	  $selectedcron7 = "selected=selected";
	} else {
	  $selectedcron2 = "selected=selected";
	}

	print "Content-Type: text/html\n\n";

	$template_title = $pphrase->param("TXT0001");

	# Print Template
	&lbheader;
	open(F,"$installfolder/templates/plugins/$psubfolder/multi/settings_start.html") || die "Missing template plugins/$psubfolder/$lang/settings_end.html";
	  while (<F>)
	  {
	    $_ =~ s/<!--\$(.*?)-->/${$1}/g;
	    print $_;
	  }
	close(F);
  for ($i=1;$i<=$users;$i++) {
    $username = $pcfg->param("USER$i.NAME");
    $macs = $pcfg->param("USER$i.MACS");
    $index = $i;
    open(F,"$installfolder/templates/plugins/$psubfolder/multi/user_row.html") || die "Missing template plugins/$psubfolder/$lang/user_row.html";
  	  while (<F>)
  	  {
  	    $_ =~ s/<!--\$(.*?)-->/${$1}/g;
  	    print $_;
  	  }
  	close(F);
  }
  open(F,"$installfolder/templates/plugins/$psubfolder/multi/settings_end.html") || die "Missing template plugins/$psubfolder/$lang/settings_end.html";
    while (<F>)
    {
      $_ =~ s/<!--\$(.*?)-->/${$1}/g;
      print $_;
    }
  close(F);
	&footer;
	exit;

}

#####################################################
# Save-Sub
#####################################################

sub save
{

	# Read Config
	$pcfg    = new Config::Simple("$installfolder/config/plugins/$psubfolder/wifi_scanner.cfg");
	$pname   = $pcfg->param("PLUGIN.SCRIPTNAME");

	# Everything from Forms
  $scanner_active = param('scanner_active');
	$cron           = param('cron');
	$udpport        = param('udpport');
  $fritzbox       = param('fritzbox');
  $fritzbox_port  = param('fritzbox_port');
  $user_count     = param('user_count');

	# Filter
	$cron          = quotemeta($cron);
	$udpport       = quotemeta($udpport);
  #$fritzbox      = quotemeta($fritzbox);
  $fritzbox_port = quotemeta($fritzbox_port);

	# OK - now installing...

	# Write configuration file(s)
  $pcfg->param("BASE.ENABLED", "$scanner_active");
	$pcfg->param("BASE.PORT", "$udpport");
  $pcfg->param("BASE.FRITZBOX", "$fritzbox");
  $pcfg->param("BASE.FRITZBOX_PORT", "$fritzbox_port");
  $pcfg->param("BASE.USERS", "$user_count");
  $pcfg->param("BASE.CRON", "$cron");

  for ($i=1;$i<=$user_count;$i++) {
    $username = quotemeta(param("username$i"));
    $macs = param("macs$i");
    $pcfg->param("USER$i.NAME", "$username");
    $pcfg->param("USER$i.MACS", "$macs");
  }

	$pcfg->save();

	# Create Cronjob
	if ($scanner_active eq "1")
	{
	  if ($cron eq "1")
	  {
	    system ("ln -s $installfolder/webfrontend/cgi/plugins/$psubfolder/bin/check.pl $installfolder/system/cron/cron.01min/$pname");
	    unlink ("$installfolder/system/cron/cron.03min/$pname");
	    unlink ("$installfolder/system/cron/cron.05min/$pname");
	    unlink ("$installfolder/system/cron/cron.10min/$pname");
	    unlink ("$installfolder/system/cron/cron.15min/$pname");
	    unlink ("$installfolder/system/cron/cron.30min/$pname");
	    unlink ("$installfolder/system/cron/cron.hourly/$pname");
	  }
	  if ($cron eq "3")
	  {
	    system ("ln -s $installfolder/webfrontend/cgi/plugins/$psubfolder/bin/check.pl $installfolder/system/cron/cron.03min/$pname");
	    unlink ("$installfolder/system/cron/cron.01min/$pname");
	    unlink ("$installfolder/system/cron/cron.05min/$pname");
	    unlink ("$installfolder/system/cron/cron.10min/$pname");
	    unlink ("$installfolder/system/cron/cron.15min/$pname");
	    unlink ("$installfolder/system/cron/cron.30min/$pname");
	    unlink ("$installfolder/system/cron/cron.hourly/$pname");
	  }
	  if ($cron eq "5")
	  {
	    system ("ln -s $installfolder/webfrontend/cgi/plugins/$psubfolder/bin/check.pl $installfolder/system/cron/cron.05min/$pname");
	    unlink ("$installfolder/system/cron/cron.01min/$pname");
	    unlink ("$installfolder/system/cron/cron.03min/$pname");
	    unlink ("$installfolder/system/cron/cron.10min/$pname");
	    unlink ("$installfolder/system/cron/cron.15min/$pname");
	    unlink ("$installfolder/system/cron/cron.30min/$pname");
	    unlink ("$installfolder/system/cron/cron.hourly/$pname");
	  }
	  if ($cron eq "10")
	  {
	    system ("ln -s $installfolder/webfrontend/cgi/plugins/$psubfolder/bin/check.pl $installfolder/system/cron/cron.10min/$pname");
	    unlink ("$installfolder/system/cron/cron.1min/$pname");
	    unlink ("$installfolder/system/cron/cron.3min/$pname");
	    unlink ("$installfolder/system/cron/cron.5min/$pname");
	    unlink ("$installfolder/system/cron/cron.15min/$pname");
	    unlink ("$installfolder/system/cron/cron.30min/$pname");
	    unlink ("$installfolder/system/cron/cron.hourly/$pname");
	  }
	  if ($cron eq "15")
	  {
	    system ("ln -s $installfolder/webfrontend/cgi/plugins/$psubfolder/bin/check.pl $installfolder/system/cron/cron.15min/$pname");
	    unlink ("$installfolder/system/cron/cron.01min/$pname");
	    unlink ("$installfolder/system/cron/cron.03min/$pname");
	    unlink ("$installfolder/system/cron/cron.05min/$pname");
	    unlink ("$installfolder/system/cron/cron.10min/$pname");
	    unlink ("$installfolder/system/cron/cron.30min/$pname");
	    unlink ("$installfolder/system/cron/cron.hourly/$pname");
	  }
	  if ($cron eq "30")
	  {
	    system ("ln -s $installfolder/webfrontend/cgi/plugins/$psubfolder/bin/check.pl $installfolder/system/cron/cron.30min/$pname");
	    unlink ("$installfolder/system/cron/cron.01min/$pname");
	    unlink ("$installfolder/system/cron/cron.03min/$pname");
	    unlink ("$installfolder/system/cron/cron.05min/$pname");
	    unlink ("$installfolder/system/cron/cron.10min/$pname");
	    unlink ("$installfolder/system/cron/cron.15min/$pname");
	    unlink ("$installfolder/system/cron/cron.hourly/$pname");
	  }
	  if ($cron eq "60")
	  {
	    system ("ln -s $installfolder/webfrontend/cgi/plugins/$psubfolder/bin/check.pl $installfolder/system/cron/cron.hourly/$pname");
	    unlink ("$installfolder/system/cron/cron.01min/$pname");
	    unlink ("$installfolder/system/cron/cron.03min/$pname");
	    unlink ("$installfolder/system/cron/cron.05min/$pname");
	    unlink ("$installfolder/system/cron/cron.10min/$pname");
	    unlink ("$installfolder/system/cron/cron.15min/$pname");
	    unlink ("$installfolder/system/cron/cron.30min/$pname");
	  }
	}
	else
	{
	  unlink ("$installfolder/system/cron/cron.01min/$pname");
	  unlink ("$installfolder/system/cron/cron.03min/$pname");
	  unlink ("$installfolder/system/cron/cron.05min/$pname");
	  unlink ("$installfolder/system/cron/cron.10min/$pname");
	  unlink ("$installfolder/system/cron/cron.15min/$pname");
	  unlink ("$installfolder/system/cron/cron.30min/$pname");
	  unlink ("$installfolder/system/cron/cron.hourly/$pname");
	}

	$template_title = $pphrase->param("TXT0001");
	$message = $pphrase->param("TXT0002");
	$nexturl = "./index.cgi?do=form";

	print "Content-Type: text/html\n\n";
	&lbheader;
	open(F,"$installfolder/templates/system/$lang/success.html") || die "Missing template system/$lang/error.html";
	while (<F>)
	{
		$_ =~ s/<!--\$(.*?)-->/${$1}/g;
		print $_;
	}
	close(F);
	&footer;

  if ($scanner_active eq "1")
  {
    # Start one scan right away
    # Without the following workaround
    # the script cannot be executed as
    # background process via CGI
    my $pid = fork();
    die "Fork failed: $!" if !defined $pid;
    if ($pid == 0)
    {
      # do this in the child
      open STDIN, "</dev/null";
      open STDOUT, ">/dev/null";
      open STDERR, ">/dev/null";
      system("$installfolder/webfrontend/cgi/plugins/$psubfolder/bin/check.pl &");
    }
  }
	exit;

}


#####################################################
# Error-Sub
#####################################################

sub error
{
	$template_title = $pphrase->param("TXT0001");
	print "Content-Type: text/html\n\n";
	&lbheader;
	open(F,"$installfolder/templates/system/$lang/error.html") || die "Missing template system/$lang/error.html";
	while (<F>)
	{
		$_ =~ s/<!--\$(.*?)-->/${$1}/g;
		print $_;
	}
	close(F);
	&footer;
	exit;
}

#####################################################
# Page-Header-Sub
#####################################################

	sub lbheader
	{
		 # Create Help page
	  $helplink = "http://www.loxwiki.eu/display/LOXBERRY/Wifi+Scanner";
	  open(F,"$installfolder/templates/plugins/$psubfolder/$lang/help.html") || die "Missing template plugins/$psubfolder/$lang/help.html";
	    @help = <F>;
	    foreach (@help)
	    {
	      s/[\n\r]/ /g;
	      $_ =~ s/<!--\$(.*?)-->/${$1}/g;
	      $helptext = $helptext . $_;
	    }
	  close(F);
	  open(F,"$installfolder/templates/system/$lang/header.html") || die "Missing template system/$lang/header.html";
	    while (<F>)
	    {
	      $_ =~ s/<!--\$(.*?)-->/${$1}/g;
	      print $_;
	    }
	  close(F);
	}

#####################################################
# Footer
#####################################################

	sub footer
	{
	  open(F,"$installfolder/templates/system/$lang/footer.html") || die "Missing template system/$lang/footer.html";
	    while (<F>)
	    {
	      $_ =~ s/<!--\$(.*?)-->/${$1}/g;
	      print $_;
	    }
	  close(F);
	}
