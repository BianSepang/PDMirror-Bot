import asyncio
import shlex


async def run_command(command, shell=False):
    if shell:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    else:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(command),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    
    stdout, stderr = await process.communicate()
    return stdout.decode(), stderr.decode()


def readable_bytes(size_in_bytes: int, decimal_places: int = 2) -> str:
    """
    Convert a byte size into a human-readable string (e.g., KB, MB, GB, TB).

    Args:
        size_in_bytes (int): The size in bytes.
        decimal_places (int): Number of decimal places to show.

    Returns:
        str: Human-readable size string.
    """
    if size_in_bytes < 0:
        raise ValueError("Size cannot be negative.")

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    index = 0

    while size_in_bytes >= 1024 and index < len(units) - 1:
        size_in_bytes /= 1024
        index += 1

    return f"{size_in_bytes:.{decimal_places}f} {units[index]}"


def format_duration_us(t_us):
    """Formats the given microsecond duration as a string."""

    t_us = int(t_us)

    t_ms = t_us / 1000
    t_s = t_ms / 1000
    t_m = t_s / 60
    t_h = t_m / 60
    t_d = t_h / 24

    if t_d >= 1:
        rem_h = t_h % 24
        return f"{int(t_d)}d {int(rem_h)}h"

    if t_h >= 1:
        rem_m = t_m % 60
        return f"{int(t_h)}h {int(rem_m)}m"

    if t_m >= 1:
        rem_s = t_s % 60
        return f"{int(t_m)}m {int(rem_s)}s"

    if t_s >= 1:
        return f"{int(t_s)} sec"

    if t_ms >= 1:
        return f"{int(t_ms)} ms"

    return f"{int(t_us)} μs"