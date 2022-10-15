import numpy as np


def get_hosts(with_countdown=False):
    hosts, countdown = None, None
    with open("public_data/whinetime_order.txt", "r") as f:
        hosts = f.readline().split(",")
        hosts = [host.rstrip() for host in hosts]
        if with_countdown:
            countdown = int(f.readline())

    if with_countdown:
        return hosts, countdown
    else:
        return hosts


def randomise_hosts():
    hosts = get_hosts(with_countdown=False)
    np.random.shuffle(hosts)
    with open("public_data/whinetime_order.txt", "w") as f:
        f.writelines([','.join(hosts) + '\n', str(len(hosts))])
    return hosts

def rotate_hosts():
    hosts, countdown = get_hosts(with_countdown=True)
    new_hosts = hosts[1:] + hosts[:1]
    countdown -= 1
    with open("public_data/whinetime_order.txt", "w") as f:
        f.writelines([','.join(new_hosts) + '\n', str(countdown)])


def get_next_host():
    hosts, countdown = get_hosts(with_countdown=True)
    if countdown <= 0:
        hosts = randomise_hosts()
    return hosts[0]


def weeks_until_host(host):
    hosts = get_hosts()
    return hosts.index(host)