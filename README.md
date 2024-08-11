# RsyncWrapper


Обёртка двоичной команды rsync для одного файла. 
Копирует «source» в «dest», yield - последовательность обновления статуса.


Используйте так:

    >>> for update in rsyncwrap("/the_source", "/the_destination"):
    ...     print(update)

    source: Файл, который мы хотим скопировать.
    dest: Каталог, в который мы хотим скопировать.
