from threading import Timer


def print_to_file(filename, data):
    with open(filename, 'a') as f:
        f.write(data + '\n')
    pass


def interrupt(s):
    s.interrupt()


def while_true_generator():
    while True:
        yield


def solve_with_timeout(solver, assumptions, timeout):
    timer = Timer(timeout, interrupt, [solver])
    timer.start()

    result = solver.solve_limited(assumptions=assumptions, expect_interrupt=True)

    if result is None:
        solver.clear_interrupt()
    else:
        timer.cancel()

    return result
