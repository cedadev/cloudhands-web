#!/usr/bin/env python
# encoding: UTF-8

__doc__ = """
Command line tool to change LDAP passwords.
"""

def parser(descr=__doc__):
    rv = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=descr)
    rv.add_argument(
        "--name", default=None,
        help="Print a new LDAP record with the given name")
    rv.add_argument(
        "--db", default=DFLT_DB,
        help="Set the path to the database [{}]".format(DFLT_DB))
    rv.add_argument(
        "--version", action="store_true", default=False,
        help="Print the current version number")
    rv.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = 0
    if args.version:
        sys.stdout.write(__version__ + "\n")
    if args.name:
        sys.stdout.write(textwrap.dedent("""
        dn: cn={0},ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        description: JASMIN2 vCloud registration
        cn: {0}
        sn: UNKNOWN
        """.format(args.name)))
    else:
        rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()
