import subprocess
import re
from dataclasses import dataclass
from functools import cached_property
from typing import Optional, Iterator, Union


def _rsync_available():
    cmd = ["rsync", "--version"]
    cp = subprocess.run(cmd, capture_output=True)
    if cp.returncode or cp.stderr:
        return False
    match = re.search(r"version\s+(\d+\.\d+\.\d+)", cp.stdout.decode("utf8")).groups()

    return bool(match)


def _rsync(source_paths: str, dest_path: str) -> Iterator[str]:
    """
    Runs rsync and yields lines of output.
    """
    cmd = [
        'rsync',
        '-P',
        source_paths,
        dest_path,
    ]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8") as proc:

        buffer = ''
        while proc.poll() is None:

            for line in proc.stdout.read(1):
                if line == '\n':
                    yield buffer
                    buffer = ''
                    continue
                buffer += line


@dataclass
class Line:
    raw_line: str
    source: str

    @staticmethod
    def _is_transfer_stats(data: str) -> bool:
        """
        Определяет, являются ли данные строкой статистики.

        Возвращает True для строк, которые выглядят следующим образом:

            600,417,190 100%  100.56MB/s    0:00:05 (xfr#1, to-chk=0/2)

        или:

            600,417,190 100%  100.56MB/s    0:00:05
        """

        # работает с незавершенными или завершенными строками статистики
        line = data.strip().split(" (")[0].split()

        result = True

        if len(line) != 4:
            result = False
        elif not line[2].endswith("/s"):
            result = False
        elif not line[1].endswith("%"):
            result = False

        return result

    @staticmethod
    def is_file_name(data: str, source: str) -> bool:
        file_name = source.split("/")[-1]
        if file_name.casefold() == data.casefold():
            return True
        return False

    @staticmethod
    def is_empty(data: str) -> bool:
        return not data

    def is_stats_line(self) -> bool:
        """Определяет, является ли raw_line статистикой rsync."""

        return self._is_transfer_stats(self.raw_line)

    def is_completed_stats_line(self) -> bool:
        """Определяет, raw_line последняя строка статистики или нет."""

        if "xfr" not in self.raw_line:
            return False

        need_one_of = ["ir-chk", "to-chk"]
        if not any(check in self.raw_line for check in need_one_of):
            return False

        return True

    @staticmethod
    def speed_split(data: str) -> list[str]:

        speed = ''
        rate = ''

        for char in data:
            if char.isdigit() or char == ',':
                speed += char
            else:
                rate += char

        return [speed, rate]

    def stats(self) -> Optional[dict]:

        if not self.is_stats_line:
            return None

        line = self.raw_line

        complete = False
        if self.is_completed_stats_line():
            line = line.split(" (")[0].strip()
            complete = True

        components = line.split()

        transfer_speed = ''
        transfer_speed_unit = ''
        for char in components[2]:
            if char.isdigit() or char == ',':
                transfer_speed += char
            else:
                transfer_speed_unit += char

        transferred_bytes = ''
        for char in components[0]:
            if char.isdigit():
                transferred_bytes += char

        info = {
            "transferred_bytes": int(transferred_bytes),
            "percent": int(components[1][:-1]),
            "transfer_speed": transfer_speed,
            "transfer_speed_unit": transfer_speed_unit,
            "time": components[3],
            "is_completed_stats": complete,
        }

        return info


def rsyncwrap(source: str, dest: str) -> Iterator[tuple[str | tuple]]:
    """
    Обёртка двоичной команды rsync для одного файла.
    Копирует «source» в «dest», yield - последовательность обновления статуса.

    Используйте так:

    >>> for update in rsyncwrap("/the_source", "/the_destination"):
    ...     print(update)

    :param source: Файл, который мы хотим скопировать.
    :param dest: Каталог, в который мы хотим скопировать.
    """

    if _rsync_available():

        for line in _rsync(source, dest):

            line = Line(line, source)

            if line.is_stats_line():
                yield 'OK', line.stats()
            elif line.is_file_name(line.raw_line, source):
                continue
            elif line.is_empty(line.raw_line):
                continue
            else:
                yield 'ERROR', line.raw_line

    else:
        yield 'ERROR', 'Rsync not available'
