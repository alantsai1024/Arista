COLLECTORS = [

    {
        "name": "system-clock",
        "cmds": ["show clock"],
        "format": "json",
        "interval": 10 ,
        "topic": "network/arista/raw/show-clock",
    },
    {
        "name": "system-hostname",
        "cmds": ["show hostname"],
        "format": "json",
        "interval": 10,
        "topic": "network/arista/raw/show-hostname",
    },
    {
        "name": "interfaces-status",
        "cmds": ["show interfaces status"],
        "interval": 10,
        "format": "json",
        "topic": "network/arista/raw/show-interfaces-status",
    },
    {
        "name": "system-version",
        "cmds": ["show version"],
        "interval": 10,
        "format": "json",
        "topic": "network/arista/raw/show-version",
    },
]
