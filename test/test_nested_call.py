from noodles import schedule, run_parallel, run_single, gather, run_logging
import sys


@schedule
def sqr(a):
    return a*a


@schedule
def sum(a, buildin_sum=sum):
    return buildin_sum(a)


@schedule
def map(f, lst):
    return gather(*[f(x) for x in lst])


@schedule
def num_range(a, b):
    return range(a, b)


def test_higher_order():
    w = sum(map(sqr, num_range(0, 10)))
    assert run_parallel(w, 4) == 285


@schedule
def g(x):
    return f(x)


@schedule
def f(x):
    return x


class Display:
    def __call__(self, q):
        self.q = q
        for status, key, data in q.source():
            print(status, key, data, file=sys.stderr)

    def wait(self):
        self.q.wait()


def test_single_node():
    display = Display()
    assert run_logging(g(5), 1, display, None) == 5
    display.wait()
