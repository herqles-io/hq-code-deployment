from hqcli.plugins import AbstractPlugin
import logging
import json
import sys
import os.path


class Plugin(AbstractPlugin):

    def __init__(self):
        super(Plugin, self).__init__("cdstage")
        self.logger = logging.getLogger("hq.cli.plugin.cdstage")
        self.create_parser = None

    def setup_parser(self, parser):
        subparsers = parser.add_subparsers(help="codedeployer stage command to run", dest='command')

        list_parser = subparsers.add_parser('list')
        list_parser.add_argument('-p', '--page', default=1, type=int, help='List page')
        list_parser.add_argument('-a', '--app', default=None, type=str, help='The application to filter by')
        list_parser.add_argument('-b', '--branch', default=None, type=str, help='The branch to filter by')
        list_parser.set_defaults(func=self.list)

        get_parser = subparsers.add_parser('get')
        get_parser.add_argument('stage_id', type=int, help='Stage ID')
        get_parser.set_defaults(func=self.get)

        self.create_parser = subparsers.add_parser('create')
        self.create_parser.add_argument('-a', '--app', type=str, help='Application Name')
        self.create_parser.add_argument('-t', '--type', type=str, help='Application Type')
        self.create_parser.add_argument('-r', '--repo', type=str, help='Application Repo')
        self.create_parser.add_argument('-b', '--branch', type=str, help='Branch to deploy')
        self.create_parser.add_argument('--tags', type=json.loads, help='Additional worker tags to filter')
        self.create_parser.add_argument('-f', '--file', default=None, type=str, help='The json file to use instead')
        self.create_parser.set_defaults(func=self.create)

    def list(self, args):
        url = self.config.framework_url+"/cd/stage?page="+str(args.page)

        if args.app is not None:
            url += "&app="+args.app

        if args.branch is not None:
            url += "&branch="+args.branch

        r = self.api_call_get(url)

        if r.status_code != 200:
            self.logger.error(r.text)
            sys.exit(1)

        self.logger.info("Stages\n"+json.dumps(json.loads(r.text), indent=2))

    def get(self, args):
        url = self.config.framework_url+"/cd/stage/"+str(args.stage_id)

        r = self.api_call_get(url)

        if r.status_code != 200:
            self.logger.error(r.text)
            sys.exit(1)

        self.logger.info("Stage "+str(args.stage_id)+"\n"+json.dumps(json.loads(r.text), indent=2))

    def create(self, args):

        data = {}

        if args.file is not None:

            if not os.path.isfile(args.file):
                self.logger.error("The file "+args.file+" does not exist")
                sys.exit(1)

            with open(args.file) as f:
                data = json.load(f)

        if args.app is not None:
            data['name'] = args.app

        if args.type is not None:
            data['type'] = args.type

        if args.repo is not None:
            data['repo'] = args.repo

        if args.tags is not None:
            if isinstance(args.tags, dict):
                data['tags'] = args.tags

        if args.branch is not None:
            data['branch'] = args.branch

        if 'name' not in data and 'type' not in data and 'repo' not in data:
            self.create_parser.print_help(sys.stderr)
            sys.exit(2)

        r = self.api_call_post(self.config.framework_url+"/cd/stage", data=data)

        if r.status_code != 200:
            self.logger.error(r.text)
            sys.exit(1)

        self.logger.info(r.text)
