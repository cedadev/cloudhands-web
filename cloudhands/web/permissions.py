#!/usr/bin/env python3
#   encoding: UTF-8

paving = set(["user.add", "rpm.install"])
access = set(["ssh.copy", "sshd.config", "initctl.restart"])
firewall = set(["kmod.write",
               "iptables.write", "iptables.restore", "iptables.save"])
proxy = set(["rpm.install", "nginx.write", "nginx.reload", "initctl.restart"])
logging = set(["logrotate.write", "initctl.restart"])
app = set()
