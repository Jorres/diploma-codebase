def print_to_file(filename, data):
    with open(filename, 'a') as f:
        f.write(data + '\n')
    pass


def interrupt(s):
    s.interrupt()
