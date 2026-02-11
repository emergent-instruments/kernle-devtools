"""DevtoolsPlugin — registers 'dev dashboard' command via PluginProtocol."""


class DevtoolsPlugin:
    """Admin dashboard plugin for kernle."""

    name = "kernle-devtools"
    version = "0.1.0"
    protocol_version = 1
    description = "Admin dashboard for kernle memory stacks"

    def cli_commands(self) -> list[str]:
        return ["dev"]

    def register_cli(self, subparsers):
        dev = subparsers.add_parser("dev", help="Admin dev tools")
        dev_sub = dev.add_subparsers(dest="dev_action", required=True)
        from kernle_devtools.parsers import add_dashboard_parser

        add_dashboard_parser(dev_sub)

    def handle_cli(self, args, k):
        if args.dev_action == "dashboard":
            from kernle_devtools.cli.dashboard import cmd_dashboard

            cmd_dashboard(args, k)

    def activate(self, context):
        self._context = context

    def deactivate(self):
        pass

    def capabilities(self) -> list[str]:
        return ["devtools", "dashboard"]

    def register_tools(self) -> list:
        return []

    def on_load(self, ctx):
        pass

    def on_status(self, status):
        pass

    def health_check(self):
        from kernle.types import PluginHealth

        return PluginHealth(healthy=True, message="Devtools ready")
