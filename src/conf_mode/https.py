#!/usr/bin/env python3
#
# Copyright (C) 2019 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import sys
import os

import jinja2

from vyos.config import Config
from vyos import ConfigError

config_file = '/etc/nginx/sites-available/default'

# Please be careful if you edit the template.
config_tmpl = """

### Autogenerated by http-api.py ###
# Default server configuration
#
server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;
        return 302 https://$server_name$request_uri;
}

server {

        # SSL configuration
        #
        listen 443 ssl default_server;
        listen [::]:443 ssl default_server;
        #
        # Self signed certs generated by the ssl-cert package
        # Don't use them in a production server!
        #
        include snippets/snakeoil.conf;

{% for l_addr in listen_address %}
        server_name {{ l_addr }};
{% endfor %}

        # proxy settings for HTTP API, if enabled; 503, if not
        location ~ /(retrieve|configure) {
{% if api %}
                proxy_pass http://localhost:{{ api.port }};
                proxy_buffering off;
{% else %}
                return 503;
{% endif %}
        }

        error_page 501 502 503 =200 @50*_json;

        location @50*_json {
                default_type application/json;
                return 200 '{"error": "Start service in configuration mode: set service https api"}';
        }

}
"""

default_config_data = {
    'listen_address' : [ '127.0.0.1' ]
}

default_api_config_data = {
    'port' : '8080',
}

def get_config():
    https = default_config_data
    conf = Config()
    if not conf.exists('service https'):
        return None
    else:
        conf.set_level('service https')

    if conf.exists('listen-address'):
        addrs = conf.return_values('listen-address')
        https['listen_address'] = addrs[:]

    if conf.exists('api'):
        https['api'] = default_api_config_data

    if conf.exists('api port'):
        port = conf.return_value('api port')
        https['api']['port'] = port

    return https

def verify(https):
    return None

def generate(https):
    if https is None:
        return None

    tmpl = jinja2.Template(config_tmpl, trim_blocks=True)
    config_text = tmpl.render(https)
    with open(config_file, 'w') as f:
        f.write(config_text)

    return None

def apply(https):
    if https is not None:
        os.system('sudo systemctl restart nginx.service')
    else:
        os.system('sudo systemctl stop nginx.service')

if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        sys.exit(1)
