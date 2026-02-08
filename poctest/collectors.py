import requests

def eapi_url(host: str, https: bool) -> str:
    scheme = "https" if https else "http"
    return f"{scheme}://{host}/command-api"


def run_cmds_raw(host, https, user, password, cmds, fmt, verify_tls, timeout):
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {
            "version": 1,
            "cmds": cmds,
            "format": fmt,
        },
        "id": 1,
    }

    r = requests.post(
        eapi_url(host, https),
        auth=(user, password),
        json=payload,
        verify=verify_tls,
        timeout=timeout,
    )
    r.raise_for_status()

    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"])

    return data.get("result")

