"""Check compatibility between aider-agents and installed aider-chat version."""
from __future__ import annotations
import importlib.metadata
import sys

REQUIRED_AIDER_MIN = (0, 50, 0)


def _parse_version(v: str) -> tuple:
    parts = []
    for p in v.split(".")[:3]:
        try:
            parts.append(int(p.split("a")[0].split("b")[0].split("rc")[0]))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_aider() -> dict:
    """Check if aider-chat is installed and meets minimum version requirements."""
    try:
        version_str = importlib.metadata.version("aider-chat")
        version = _parse_version(version_str)
        ok = version >= REQUIRED_AIDER_MIN
        return {
            "installed": True,
            "version": version_str,
            "compatible": ok,
            "required_min": ".".join(str(x) for x in REQUIRED_AIDER_MIN),
            "message": ("OK" if ok else
                        f"aider-chat {version_str} < required "
                        f"{'.' .join(str(x) for x in REQUIRED_AIDER_MIN)}"),
        }
    except importlib.metadata.PackageNotFoundError:
        return {
            "installed": False,
            "version": None,
            "compatible": False,
            "required_min": ".".join(str(x) for x in REQUIRED_AIDER_MIN),
            "message": "aider-chat not installed. Run: pip install aider-chat",
        }


def check_anthropic() -> dict:
    """Check if anthropic package is installed."""
    try:
        version_str = importlib.metadata.version("anthropic")
        return {"installed": True, "version": version_str, "compatible": True, "message": "OK"}
    except importlib.metadata.PackageNotFoundError:
        return {"installed": False, "version": None, "compatible": False,
                "message": "anthropic not installed. Run: pip install anthropic"}


def check_mcp() -> dict:
    """Check if mcp package is installed."""
    try:
        version_str = importlib.metadata.version("mcp")
        return {"installed": True, "version": version_str, "compatible": True, "message": "OK"}
    except importlib.metadata.PackageNotFoundError:
        return {"installed": False, "version": None, "compatible": False,
                "message": "mcp not installed. Run: pip install mcp"}


def main():
    """Run all compatibility checks and report results."""
    print("aider-agents compatibility check")
    print("=" * 40)
    checks = {
        "aider-chat": check_aider(),
        "anthropic": check_anthropic(),
        "mcp": check_mcp(),
    }
    all_ok = True
    for name, result in checks.items():
        status = "OK  " if result.get("compatible") else "FAIL"
        version = result.get("version") or "not installed"
        print(f"  [{status}] {name}: {version}")
        if not result.get("compatible"):
            print(f"         {result.get('message', '')}")
            all_ok = False
    print()
    if all_ok:
        print("All checks passed.")
    else:
        print("Some checks failed. See above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
