# encoding: utf-8

from sdsstools import get_config, get_logger, get_package_version


# pip package name
NAME = "sdss-archon"

# Loads config. config name is the package name.
config = get_config("archon", allow_user=False)

# Inits the logging system as NAME. Remove all the handlers. If a client
# of the library wants the archon logging, it should add its own handler.
log = get_logger(NAME)
log.removeHandler(log.sh)

# package name should be pip package name
__version__ = get_package_version(path=__file__, package_name=NAME)
