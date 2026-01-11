import os
import subprocess
import sys
import time
import textwrap

from discord.ext import commands
from remind.util.discord_common import pretty_time_format
from remind.util import clist_api
from remind import constants

RESTART = 42


def git_history():
    def _minimal_ext_cmd(cmd):
        env = {}
        for k in ['SYSTEMROOT', 'PATH']:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            env=env
        ).communicate()[0]
        return out

    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
        branch = out.strip().decode('ascii')
        out = _minimal_ext_cmd(['git', 'log', '--oneline', '-5'])
        history = out.strip().decode('ascii')
        return (
            'Branch:\n' +
            textwrap.indent(branch, '  ') +
            '\nCommits:\n' +
            textwrap.indent(history, '  ')
        )
    except OSError:
        return "Fetching git info failed"


def check_if_superuser(ctx):
    return ctx.author.id in constants.SUPER_USERS


# CHANGED: add name so help shows category
class Meta(commands.Cog, name="Meta"):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @commands.group(brief='Bot control', invoke_without_command=True)
    async def meta(self, ctx):
        """Command the bot or get information about the bot."""
        await ctx.send_help(ctx.command)

    @meta.command(brief='Restarts Remind')
    @commands.check(check_if_superuser)
    async def restart(self, ctx):
        await ctx.send('Restarting...')
        os._exit(RESTART)

    @meta.command(brief='Kill Remind')
    @commands.check(check_if_superuser)
    async def kill(self, ctx):
        await ctx.send('Dying...')
        os._exit(0)

    @meta.command(brief='Is Remind up?')
    async def ping(self, ctx):
        start = time.perf_counter()
        message = await ctx.send(':ping_pong: Pong!')
        end = time.perf_counter()
        duration = (end - start) * 1000
        content = (
            f'REST API latency: {int(duration)}ms\n'
            f'Gateway API latency: {int(self.bot.latency * 1000)}ms'
        )
        await message.edit(content=content)

    @meta.command(brief='Get git information')
    async def git(self, ctx):
        await ctx.send('```yaml\n' + git_history() + '```')

    @meta.command(brief='Prints bot uptime')
    async def uptime(self, ctx):
        await ctx.send(
            'Remind has been running for ' +
            pretty_time_format(time.time() - self.start_time)
        )

    @meta.command(brief='Print bot guilds')
    @commands.check(check_if_superuser)
    async def guilds(self, ctx):
        msg = [
            f'Guild ID: {guild.id} | Name: {guild.name} | Owner: {guild.owner.id}'
            for guild in self.bot.guilds
        ]
        await ctx.send('```' + '\n'.join(msg) + '```')

    @meta.command(brief='Forcefully reset contests')
    @commands.has_any_role('Admin', constants.REMIND_MODERATOR_ROLE)
    async def resetcache(self, ctx):
        try:
            clist_api.cache(True)
            await ctx.send(
                '```Cache reset completed. Restart to reschedule reminders.```'
            )
        except BaseException:
            await ctx.send('```Cache reset failed.```')


# CHANGED: discord.py v2 async setup
async def setup(bot):
    await bot.add_cog(Meta(bot))