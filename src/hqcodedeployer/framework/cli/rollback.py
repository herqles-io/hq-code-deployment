from hqcli.plugins import AbstractPlugin
import logging
import json
import sys
import os.path


class Plugin(AbstractPlugin):

    def __init__(self):
        super(Plugin, self).__init__("cdrollback")
        self.logger = logging.getLogger("hq.cli.plugin.cdrollback")
        self.create_parser = None

    def setup_parser(self, parser):
        subparsers = parser.add_subparsers(help="codedeployer rollback command to run", dest='command')

        list_parser = subparsers.add_parser('list')
        list_parser.add_argument('-p', '--page', default=1, type=int, help='List page')
        list_parser.add_argument('-a', '--app', default=None, type=str, help='The application to filter by')
        list_parser.set_defaults(func=self.list)

        get_parser = subparsers.add_parser('get')
        get_parser.add_argument('rollback_id', type=int, help='Rollback ID')
        get_parser.set_defaults(func=self.get)

        self.create_parser = subparsers.add_parser('create')
        self.create_parser.add_argument('-a', '--app', type=str, help='Application Name')
        self.create_parser.add_argument('-e', '--env', type=str, help='The environment to deploy to')
        self.create_parser.add_argument('-t', '--type', type=str, help='Application Type')
        self.create_parser.add_argument('-d', '--datacenter', type=str, help='The datacenter to deploy to')
        self.create_parser.add_argument('-f', '--file', default=None, type=str, help='The json file to use instead')
        self.create_parser.set_defaults(func=self.create)

    def list(self, args):
        url = self.config.framework_url+"/cd/rollback?page="+str(args.page)

        if args.app is not None:
            url += "&app="+args.app

        r = self.api_call_get(url)

        if r.status_code != 200:
            self.logger.error(r.text)
            sys.exit(1)

        self.logger.info("Deploys\n"+json.dumps(json.loads(r.text), indent=2))

    def get(self, args):
        url = self.config.framework_url+"/cd/rollback/"+str(args.rollback_id)

        r = self.api_call_get(url)

        if r.status_code != 200:
            self.logger.error(r.text)
            sys.exit(1)

        self.logger.info("Deploy "+str(args.rollback_id)+"\n"+json.dumps(json.loads(r.text), indent=2))

    def create(self, args):

        data = {}

        if args.file is not None:

            if not os.path.isfile(args.file):
                self.logger.error("The file "+args.file+" does not exist")
                sys.exit(1)

            with open(args.file) as f:
                data = json.load(f)

        if args.stage_id is not None:
            data['name'] = args.app

        if args.env is not None:
            data['env'] = args.env

        if args.type is not None:
            data['type'] = args.type

        if args.datacenter is not None:
            data['datacenter'] = args.datacenter

        if 'name' is not data and 'env' not in data and 'type' not in data:
            self.create_parser.print_help(sys.stderr)
            sys.exit(2)

        r = self.api_call_post(self.config.framework_url+"/cd/rollback", data=data)

        if r.status_code != 200:
            self.logger.error(r.text)
            sys.exit(1)

        self.logger.info(r.text)
