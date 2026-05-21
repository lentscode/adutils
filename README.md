# Utils for Attack&Defense CTFs

Little package containing useful classes for Attack&Defense CTFs.

## Purpose

During my first A&D based CTFs, my workflow was:

1. Building the `exploit.py` script.
2. Copy-pasting an `exploit.sh` script, whose only job was to spin up multiple `python exploit.py`, each targetting a different vulnbox.
3. Run a `submit_flags.py` to collect the points.

At first it was great, but then things got complicated, and the `exploit.sh` reached ~100-line length for something that in Python needs half.

Plus, I don't want multiple copies of the same files scattered across my filesystem. I just want to `pip install <x>` in my venv.

Here it comes `adutils`! 

## Installation

You can install it via:

```bash
pip install lents_adutils
```

## Usage

When writing an exploit for an A&D CTF, you want to run the same exploit towards multiple vulnboxes at the same time. The `Exploit` class lets you do exactly that by extending it.

```python
from adutils import Exploit

class MyExploit(Exploit):
# ...
```

Then you have to implement the `run(self, ip: str)` method, which gives you access to the IP address of one of the vulnbox you're targeting.

```python
class MyExploit(Exploit):
    def run(self, ip: str):
        flag = exploit() # imagine you get the flag via exploit()
        self.flagout(flag) # you add the flag to a list of flags
```

At the end of each cycle, the `submit_flags` method will be run for you.

If you want to run the full exploit, you create an instance of `MyExploit` and then call the `start` method. 

```python
if __name__ == "main":
    port = 1234
    team_token = "deadbeef"
    my_exploit = MyExploit(port, team_token)

    my_exploit.start()
```

There are lots of options that allow you to fully customize the workflow. You can also override the existing methods to meet your needs.

```python
# The Exploit initializer
def __init__(
    self,
    team_token: str,
    n_teams: int = 80,                                   # number of teams
    sleep_interval: int = 60,                            # time between cycles
    ignore: list[int] = [],                              # list of team ids to ignore
    verbose: bool = True,                                # additional logs
    submit_url: str = "http://10.10.0.1/flags",          # endpoint to submit flags
    submit_timeout: int = 5,
    flag_ids_url: str = "http://10.10.0.1:8081/flagIds", # endpoint that exposes info for challenges
    flag_regex: Pattern = compile(r"^[A-Z0-9]{31}=$")
):
```
