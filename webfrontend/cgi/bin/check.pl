#!/usr/bin/perl -w
##########################################################################
# Script zur Anwesenheitserkennung von WLAN-Geräten                      #
# an einer Fritz!Box 7490 in Verbindung mit einem                        #
# Loxone Miniserver                                                      #
# Version: 2016.02.27.15.09.14                                           #
##########################################################################

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

use LWP::Simple;
use LWP::UserAgent;
use XML::Simple;
use JSON qw( decode_json );
use Getopt::Long;
use Config::Simple;
use File::HomeDir;
use Cwd 'abs_path';
use open qw(:std :utf8);
use POSIX qw/ strftime /;
use IO::Socket;

##########################################################################
# Read Settings
##########################################################################

# Version of this script
$version = "1.0.0";

# Figure out in which subfolder we are installed
our $psubfolder = abs_path($0);
$psubfolder =~ s/(.*)\/(.*)\/bin\/(.*)$/$2/g;

my $home = File::HomeDir->my_home;

# my $cfg             = new Config::Simple("$home/config/system/general.cfg");
my $cfg             = new Config::Simple("/opt/loxberry/config/system/general.cfg");
my $lang            = $cfg->param("BASE.LANG");
my $installfolder   = $cfg->param("BASE.INSTALLFOLDER");
my $miniservers     = $cfg->param("BASE.MINISERVERS");
my $clouddns        = $cfg->param("BASE.CLOUDDNS");

# my $pcfg             = new Config::Simple("$installfolder/config/plugins/$psubfolder/wifi_scanner.cfg");
my $pcfg             = new Config::Simple("/opt/loxberry/wifi_scanner.cfg");
my $udpport           = $pcfg->param("BASE.PORT");
my $ip               = $pcfg->param("BASE.FRITZBOX");
my $port             = $pcfg->param("BASE.FRITZBOX_PORT");
my $users            = $pcfg->param("BASE.USERS");

# Commandline options
my $verbose = '';
my $help = '';

GetOptions ('verbose' => \$verbose,
            'quiet'   => sub { $verbose = 0 });

# Starting...
my $logmessage = "<INFO> Starting $0 Version $version\n";
&log;

for ($i=1;$i<=$users;$i++) {
  ${"username" . "$i"} = $pcfg->param("USER$i.NAME");
  ${"macs" . "$i"} = $pcfg->param("USER$i.MACS");
}

# disable SSL checks. No signed certificate!
$ENV{'PERL_LWP_SSL_VERIFY_HOSTNAME'} = 0;
$ENV{HTTPS_DEBUG} = 1;

# Discover Service Parameters
my $ua = new LWP::UserAgent;
$ua->default_headers;
$ua->ssl_opts( verify_hostname => 0 ,SSL_verify_mode => 0x00);

# Read all available services
my $resp_discover = $ua->get("https://$ip:$port/tr64desc.xml");
my $xml_discover;
if ( $resp_discover->is_success )
 {
  $xml_discover = $resp_discover->decoded_content;
 }
else
 {
  die $resp_discover->status_line;
 }
my $discover = XMLin($xml_discover);
$logmessage = "<INFO> $discover->{device}->{modelName} detected...\n";
&log;

# Parse XML service response, get needed parameters for LAN host service
my $control_url = "not set";
my $service_type = "not set";
my $service_command = "GetSpecificHostEntry"; # fixed command for requesting info of specific MAC
foreach(@{$discover->{device}->{deviceList}->{device}->[0]->{serviceList}->{service}})
 {
  if("urn:LanDeviceHosts-com:serviceId:Hosts1" =~ m/.*$_->{serviceId}.*/)
   {
     $control_url = $_->{controlURL};
     $service_type = $_->{serviceType};
   }
 }

if ($control_url eq "not set" or $service_type eq "not set")
 {
    die "control URL/service type not found. Cannot request host info!";
 }

# Prepare request for query LAN host
$ua->default_header( 'SOAPACTION' => "$service_type#$service_command" );
my $any_online = 0; # if arg any specified

for ($i=1;$i<=$users;$i++) {
  my $macs = ${"macs" . "$i"};
  my @macs_splitted = split /;/, $macs;
  ${"online" . "$i"} = 0;

  $logmessage = "<INFO> Checking devices from User: ".${"username" . "$i"}."\n";
  &log;
  foreach my $mac (@macs_splitted)
  {
          my $init_request = <<EOD;
          <?xml version="1.0" encoding="utf-8"?>
          <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" >
                  <s:Header>
                  </s:Header>
                  <s:Body>
                          <u:$service_command xmlns:u="$service_type">
                                  <NewMACAddress>$mac</NewMACAddress>
                          </u:$service_command>
                  </s:Body>
          </s:Envelope>
EOD

          my $init_url = "https://$ip:$port$control_url";
          my $resp_init = $ua->post($init_url, Content_Type => 'text/xml; charset=utf-8', Content => $init_request);
          my $xml_mac_resp = XMLin($resp_init->decoded_content);


          if(exists $xml_mac_resp->{'s:Body'}->{'s:Fault'})
          {
                  if($xml_mac_resp->{'s:Body'}->{'s:Fault'}->{detail}->{UPnPError}->{errorCode} eq "714")
                  {
                          $logmessage = "<ERROR> Mac $mac not found in FritzBox Database!\n";
                          &log;
                  }
           }
          if(exists $xml_mac_resp->{'s:Body'}->{'u:GetSpecificHostEntryResponse'})
          {
                  if($xml_mac_resp->{'s:Body'}->{'u:GetSpecificHostEntryResponse'}->{NewActive} eq "1")
                  {
                          my $name = $xml_mac_resp->{'s:Body'}->{'u:GetSpecificHostEntryResponse'}->{NewHostName};
                          my $ip = $xml_mac_resp->{'s:Body'}->{'u:GetSpecificHostEntryResponse'}->{NewIPAddress};
                          my $iftype =  $xml_mac_resp->{'s:Body'}->{'u:GetSpecificHostEntryResponse'}->{NewInterfaceType};
                          $logmessage = "<INFO> Mac $mac ($name) is online with IP $ip on $iftype\n";
                          &log;
                          ${"online" . "$i"} = 1;
                  }
                  if($xml_mac_resp->{'s:Body'}->{'u:GetSpecificHostEntryResponse'}->{NewActive} eq "0")
                  {
                        my $name = $xml_mac_resp->{'s:Body'}->{'u:GetSpecificHostEntryResponse'}->{NewHostName};
                        $logmessage = "<INFO> Mac $mac ($name) is offline\n";
                        &log;
                  }
         }
  }
}

# Creating UDP socket to every Miniserver
for ($i=1;$i<=$miniservers;$i++) {

  ${"miniservername" . "$i"} = $cfg->param("MINISERVER$i.NAME");

  if ( $cfg->param("MINISERVER$i.USECLOUDDNS") ) {
    my $miniservermac = $cfg->param("MINISERVER$i.CLOUDURL");
    my $dns_info = `$home/webfrontend/cgi/system/tools/showclouddns.pl $miniservermac`;
    my @dns_info_pieces = split /:/, $dns_info;
    if ($dns_info_pieces[0]) {
      $dns_info_pieces[0] =~ s/^\s+|\s+$//g;
      ${"miniserverip" . "$i"} = $dns_info_pieces[0];
      $logmessage = "<INFO> Send Data to " . ${"miniservername" . "$i"} . " at " . ${"miniserverip" . "$i"} . " using CloudDNS.\n";
      &log;
    } else {
      ${"miniserverip" . "$i"} = "127.0.0.1";
      $logmessage = "<ERROR> Could not find IP Address for " . ${"miniservername" . "$i"} . " using CloudDNS.\n";
      &log;
    }
  } else {
    if ( $cfg->param("MINISERVER$i.IPADDRESS") ) {
      ${"miniserverip" . "$i"} = $cfg->param("MINISERVER$i.IPADDRESS");
      $logmessage = "<INFO> Send Data to " . ${"miniservername" . "$i"}  . " at " . ${"miniserverip" . "$i"} . ".\n";
      &log;
    } else {
      ${"miniserverip" . "$i"} = "127.0.0.1";
      $logmessage = "<ERROR> Could not find IP Address for " . ${"miniservername" . "$i"} . ".\n";
      &log;
    }
  }
}
for ($i=1;$i<=$miniservers;$i++) {
  # Send value
  my $sock = IO::Socket::INET->new(
    Proto    => 'udp',
    PeerPort => $udpport,
    PeerAddr => ${"miniserverip" . "$i"},
    Type        => SOCK_DGRAM
  ) or die "<ERROR> Could not create socket: $!\n";
  for ($j=1;$j<=$users;$j++) {
    $sock->send(${"username" . "$j"}.":".${"online" . "$j"}) or die "Send error: $!\n";
    if ($verbose) {
      $logmessage = "<INFO> Sending Data '".${"username" . "$j"}.":".${"online" . "$j"}."' to " . ${"miniservername" . "$i"} . ". IP:" . ${"miniserverip" . "$i"} . " Port:$udpport\n";
      &log;
    }
  }
  $sock->close();
}

#
# Subroutines
#

sub log {
  # Print
  if ($verbose) {print $logmessage;}
  return();
}
